import os

from supyr_struct.defs.block_def import BlockDef
from ...common_descs import *
from . import constants as c


def has_next_path_part(root_offset=0, offset=0, rawdata=None, **kwargs):
    if rawdata is None:
        return False

    rawdata.seek(0, os.SEEK_END)
    return offset + root_offset < rawdata.tell()


file_entry = Struct("file_entry",
    SInt32("size"),
    SInt32("offset", DEFAULT=-1), # if -1, file isn't in disk.rom
    SInt16Array("path_part_offsets",
        # NOTE: these are offsets to the cstrings in the path_string_data
        #       blob. they are relative to the start of the block, which is
        #       why we're parsing it as a blob instead of a cstring array.
        SIZE=8
        ),
    SIZE=16
    )

header = QStruct("header",
    SInt32("file_count"),
    SIZE=4
    )

dc_rom_def = BlockDef("dreamcast_rom",
    header,
    Array("file_headers",
        SUB_STRUCT=file_entry,
        SIZE=".header.file_count"
        ),
    BytesRaw("path_string_data", SIZE=remaining_data_length),
    #WhileArray("path_parts",
    #    SUB_STRUCT=Container("path_part",
    #        CStrLatin1("path_part")
    #        ),
    #    CASE=has_next_path_part
    #    ),
    endian="<"
    )
