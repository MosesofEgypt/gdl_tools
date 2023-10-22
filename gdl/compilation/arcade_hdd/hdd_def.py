from supyr_struct.defs.block_def import BlockDef
from ...common_descs import *
from . import constants as c


def file_table_header_pointer(parent=None, new_value=None, disc=0, **kw):
    assert disc in (0, 1, 2)
    try:
        return parent.mbr_block.file_table_record[disc] * c.SECTOR_SIZE
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
    UInt32('sig', DEFAULT=c.PARTITION_HEADER_SIG),
    UInt32('unknown0', DEFAULT=5),
    Pad(4),
    ALIGN=512
    # TODO: fill this the rest of the way out
    )

mbr_block = Struct('mbr_block',
    UInt32('sig', DEFAULT=c.MBR_HEADER_SIG),
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
    UInt32('unknown13', DEFAULT=c.UNKNOWN_MBR_SIG),
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
        ('file_table', c.FILE_TABLE_SIG),
        ('file',       c.REGULAR_FILE_SIG),
        ),
    UInt32('data_size'),
    UInt32('sectors_used'),
    UInt8('unknown0',  DEFAULT=1),
    UEnum8('file_type',
        ('directory', c.FILE_BLOCK_TYPE_DIRECTORY),
        ('regular',   c.FILE_BLOCK_TYPE_REGULAR),
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


hdd_blocks = (
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
        )
    )

hdd_def = BlockDef("hdd", *hdd_blocks, endian="<")

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
