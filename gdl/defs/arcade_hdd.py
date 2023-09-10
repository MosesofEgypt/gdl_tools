import os

from supyr_struct.defs.block_def import BlockDef
from supyr_struct.buffer import get_rawdata_context
from ..common_descs import *

FILE_BLOCK_TYPE_DIRECTORY = 2
FILE_BLOCK_TYPE_REGULAR   = 4

MASTER_BOOT_RECORD_SIG  = 0xFEEDF00D
FILE_TABLE_SIG          = 0xF00DFACE
REGULAR_FILE_SIG        = 0xC0EDBABE
SECTOR_SIZE             = 512


def read_file_fragments(*, block_header, rawdata, disc=0):
    fragments = (
        block_header.fragments_ter if disc == 2 else
        block_header.fragments_sec if disc == 1 else
        block_header.fragments_pri
        )

    data_remaining = block_header.data_size
    ft_data = b''

    for i in range(0, len(fragments), 2):
        # read in and concatenate all fragments of the file
        read_size = min(data_remaining, fragments[i+1]*SECTOR_SIZE)
        if read_size <= 0:
            break

        rawdata.seek(fragments[i]*SECTOR_SIZE)
        ft_data += rawdata.read(read_size)
        data_remaining = max(0, data_remaining - read_size)

    return ft_data


def read_file_table(*, filepath=None, rawdata=None, disc=0):
    assert disc in (0, 1, 2)
    with get_rawdata_context(filepath=filepath, rawdata=rawdata) as fin:
        hdd_block = arcade_hdd_def.build(rawdata=fin)
        ft_header = (
            hdd_block.file_table_header_ter if disc == 2 else
            hdd_block.file_table_header_sec if disc == 1 else
            hdd_block.file_table_header_pri
            )
        ft_data = read_file_fragments(
            block_header=ft_header, rawdata=fin, disc=disc
            )

    file_table = file_table_def.build(rawdata=ft_data)
    return file_table.file_table


def read_file_headers(*, file_table=None, filepath=None, rawdata=None, disc=0):
    assert disc in (0, 1, 2)

    if file_table is None:
        file_table = read_file_table(
            filepath=filepath, rawdata=rawdata, disc=disc
            )

    headers = []
    with get_rawdata_context(filepath=filepath, rawdata=rawdata) as fin:
        for record in file_table:
            header = block_header_def.build(
                rawdata=fin, offset=record[disc] * SECTOR_SIZE
                )
            headers.append(header.block_header)

    return headers


def parse_directory_tree(*, file_headers=None, filepath=None, rawdata=None, disc=0):
    if file_headers is None:
        file_headers = read_file_headers(
            filepath=filepath, rawdata=rawdata, disc=disc
            )

    # root of tree is file header 2(0 is the file table, and 1 is unknown)
    unknown_file_index = 1
    root_index = 2

    dir_tree = {
        'unknown': file_headers[unknown_file_index]
        }
    dir_flat = {
        root_index: dir_tree,
        unknown_file_index: file_headers[unknown_file_index]
        }

    dir_blocks  = {root_index: file_headers[root_index]}
    with get_rawdata_context(filepath=filepath, rawdata=rawdata) as fin:
        while dir_blocks:
            next_dir_blocks = {}
            for dir_idx, dir_block in dir_blocks.items():
                if dir_block.file_type.data != FILE_BLOCK_TYPE_DIRECTORY:
                    continue

                dir_data = read_file_fragments(
                    block_header=dir_block, rawdata=fin, disc=disc
                    )
                dir_list = dir_entry_list_def.build(rawdata=dir_data).dir_entry_list

                parent_dir_dict = dir_flat[dir_idx]
                for dir_entry in dir_list:
                    if dir_entry.table_index in dir_flat:
                        continue

                    idx = dir_entry.table_index
                    file_header = file_headers[idx]

                    if file_headers[idx].file_type.data == FILE_BLOCK_TYPE_DIRECTORY:
                        dir_entry_block = {}  # regular dict to hold all files and dir dicts
                        next_dir_blocks[idx] = file_header
                    else:
                        dir_entry_block = file_header

                    dir_flat[idx] = dir_entry_block
                    parent_dir_dict[dir_entry.name] = dir_entry_block

            dir_blocks = next_dir_blocks

    return dir_tree


def _dump_hdd(dir_tree, output_path, rawdata, disc, skip_empty):
    for name, block in dir_tree.items():
        if isinstance(block, dict):
            # directory. append name to output path and call recursive
            _dump_hdd(block, f"{output_path}/{name}", rawdata, disc, skip_empty)
            continue

        file_data = read_file_fragments(
            block_header=block, rawdata=rawdata, disc=disc
            )
        if skip_empty and not file_data:
            continue

        os.makedirs(output_path, exist_ok=True)
        with open(f"{output_path}/{name}", "wb") as fout:
            fout.write(file_data)


def dump_hdd(*, output_dir, filepath=None, rawdata=None, disc=0, skip_empty=True):
    dir_tree = parse_directory_tree(
        filepath=filepath, rawdata=rawdata, disc=disc
        )
    with get_rawdata_context(filepath=filepath, rawdata=rawdata) as fin:
        _dump_hdd(dir_tree, output_dir, fin, disc, skip_empty)


def file_table_header_pointer(parent=None, new_value=None, disc=0, **kw):
    assert disc in (0, 1, 2)
    try:
        return parent.mbr_block.file_table_record[disc] * SECTOR_SIZE
    except AttributeError:
        return 0


def has_next_file_entry(rawdata=None, offset=0, root_offset=0, **kw):
    try:
        return len(rawdata) - (root_offset + offset) >= 12
    except TypeError:
        return False

def has_next_dir_entry(rawdata=None, offset=0, root_offset=0, **kw):
    try:
        return len(rawdata) - (root_offset + offset) >= 5
    except TypeError:
        return False


file_table_record = QStruct('file_table_record',
    UInt32('sector_pri'),
    UInt32('sector_sec'),
    UInt32('sector_ter')
    )

file_table = WhileArray("file_table",
    SUB_STRUCT=file_table_record,
    CASE=has_next_file_entry
    )

partition_block = QStruct('partition_block',
    UInt32('sig', DEFAULT=fourcc_to_int('PART', 'big')),
    ALIGN=512
    # TODO: fill this the rest of the way out
    )

mbr_block = Struct('mbr_block',
    UInt32('sig', DEFAULT=MASTER_BOOT_RECORD_SIG),
    UInt16('unknown0', DEFAULT=5),
    UInt16('unknown1', DEFAULT=1),
    UInt16('unknown2', DEFAULT=104),
    UInt16('unknown3', DEFAULT=2),
    UInt16('unknown4', DEFAULT=1),
    UInt16('unknown5', DEFAULT=504),
    UInt16('unknown6', DEFAULT=20),
    Pad(8),
    UInt16('unknown7', DEFAULT=1),
    UInt16('unknown8', DEFAULT=1),
    UInt16('unknown9', DEFAULT=8),
    UInt16('unknown10', DEFAULT=1),
    UInt16('unknown11', DEFAULT=3),
    UInt16('unknown12', DEFAULT=10),
    Pad(18),
    UInt32('unknown13', DEFAULT=0xFE1DFAED),
    UInt32('unknown14', DEFAULT=8),
    UInt32('unknown15', DEFAULT=8),
    QStruct("file_table_record", INCLUDE=file_table_record),
    QStruct("executable_record", INCLUDE=file_table_record),
    UInt32('unknown16', DEFAULT=5008500),
    UInt32('unknown17', DEFAULT=512000),
    ALIGN=512
    )

dir_entry = Container('dir_entry',
    UInt16('table_index'),
    UInt16('unknown', DEFAULT=0x0100),
    UInt8('name_len'),
    StrLatin1("name", SIZE=".name_len"),
    )

dir_entry_list = WhileArray("dir_entry_list",
    SUB_STRUCT=dir_entry,
    CASE=has_next_dir_entry
    )

file_fragment_locator = QStruct('file_fragment_locator',
    UInt32('first_sector'),
    UInt32('sector_count'),
    )

block_header = Struct("block_header",
    UEnum32("block_type",
        ('file_table', FILE_TABLE_SIG),
        ('file',       REGULAR_FILE_SIG),
        ),
    UInt32('data_size'),
    UInt32('sectors_used'),
    UInt8('unknown0',  DEFAULT=1),
    UEnum8('file_type',
        ('directory', FILE_BLOCK_TYPE_DIRECTORY),
        ('regular',   FILE_BLOCK_TYPE_REGULAR),
        ),
    Pad(2),
    # NOTE: checksums are only set for regular files(not file table or dirs)
    StrHex("checksum0", SIZE=4),
    StrHex("checksum1", SIZE=4),
    # NOTE: doing this as uint32 arrays for speed
    UInt32Array("fragments_pri", SIZE=160),
    UInt32Array("fragments_sec", SIZE=160),
    UInt32Array("fragments_ter", SIZE=160),
    #Array("fragments_pri", SUB_STRUCT=file_fragment_locator, SIZE=20),
    #Array("fragments_sec", SUB_STRUCT=file_fragment_locator, SIZE=20),
    #Array("fragments_ter", SUB_STRUCT=file_fragment_locator, SIZE=20),
    )

arcade_hdd_def = BlockDef("arcade_hdd",
    partition_block,
    mbr_block,
    Struct("file_table_header_pri",
        INCLUDE=block_header,
        POINTER=lambda *a, **kw: file_table_header_pointer(*a, disc=0, **kw)
        ),
    Struct("file_table_header_sec",
        INCLUDE=block_header,
        POINTER=lambda *a, **kw: file_table_header_pointer(*a, disc=1, **kw)
        ),
    Struct("file_table_header_ter",
        INCLUDE=block_header,
        POINTER=lambda *a, **kw: file_table_header_pointer(*a, disc=2, **kw)
        ),
    # TODO: figure what to do about the multiple data copies
    endian="<"
    )

dir_entry_list_def = BlockDef("dir_entry_list",
    dir_entry_list,
    endian="<"
    )

file_table_def = BlockDef("file_table",
    file_table,
    endian="<"
    )

block_header_def = BlockDef("block_header",
    block_header,
    endian="<"
    )
