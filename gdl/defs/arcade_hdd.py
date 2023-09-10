from supyr_struct.defs.block_def import BlockDef
from supyr_struct.buffer import get_rawdata_context
from ..common_descs import *


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

    for fragment in fragments:
        # read in and concatenate all fragments of the file table
        read_size = min(data_remaining, fragment.sector_count*SECTOR_SIZE)
        if read_size <= 0:
            continue

        rawdata.seek(fragment.first_sector*SECTOR_SIZE)
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
            header = file_block_header_def.build(
                rawdata=fin, offset=record[disc] * SECTOR_SIZE
                )
            headers.append(header.file_block_header)

    return headers


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
    UInt16('unknown', DEFAULT=1),
    UInt8('name_len'),
    StrLatin1("name", SIZE=".name_len"),
    )

file_fragment_locator = QStruct('file_fragment_locator',
    UInt32('first_sector'),
    UInt32('sector_count'),
    )

file_block_header = Struct("file_block_header",
    UEnum32("block_type",
        ('file_table', FILE_TABLE_SIG),
        ('file',       REGULAR_FILE_SIG),
        ),
    UInt32('data_size'),
    UInt32('sectors_used'),
    UInt8('unknown0',  DEFAULT=1),
    UEnum8('is_directory',
        ('yes', 2),
        ('no',  4),
        ),
    Pad(2),
    # NOTE: checksums are only set for regular files(not file table or dirs)
    StrHex("checksum0", SIZE=4),
    StrHex("checksum1", SIZE=4),
    Array("fragments_pri", SUB_STRUCT=file_fragment_locator, SIZE=20),
    Array("fragments_sec", SUB_STRUCT=file_fragment_locator, SIZE=20),
    Array("fragments_ter", SUB_STRUCT=file_fragment_locator, SIZE=20),
    )

arcade_hdd_def = BlockDef("arcade_hdd",
    partition_block,
    mbr_block,
    Struct("file_table_header_pri",
        INCLUDE=file_block_header,
        POINTER=lambda *a, **kw: file_table_header_pointer(*a, disc=0, **kw)
        ),
    Struct("file_table_header_sec",
        INCLUDE=file_block_header,
        POINTER=lambda *a, **kw: file_table_header_pointer(*a, disc=1, **kw)
        ),
    Struct("file_table_header_ter",
        INCLUDE=file_block_header,
        POINTER=lambda *a, **kw: file_table_header_pointer(*a, disc=2, **kw)
        ),
    # TODO: figure what to do about the multiple data copies
    endian="<"
    )

file_table_def = BlockDef("file_table",
    file_table,
    endian="<"
    )

file_block_header_def = BlockDef("file_block_header",
    file_block_header,
    endian="<"
    )
