from supyr_struct.defs.tag_def import TagDef
from ..common_descs import *
from ..field_types import *

def get(): return arcade_gdl_save_file_def, arcade_gleg_save_file_def


gdl_character_data = Struct('character_data',
    UInt16('level'),
    UInt16('unknown0'),
    UInt32('exp'),
    UInt16('unknown1'),
    UInt16('unknown2'),
    UInt16('strength'),
    UInt16('speed'),
    UInt16('armor'),
    UInt16('magic'),
    UInt16('unknown3'),
    UInt16('unknown4'),
    SIZE=20,
    )

gleg_character_data = Struct('character_data',
    UInt32('level'),
    UInt32('curr_exp'),
    UInt32('next_exp'),
    UInt32('unknown0'),
    UInt32('unknown1'),
    UInt32('unknown2'),
    UInt32('unknown3'),
    UInt32('unknown4'),
    UInt32('unknown5'),
    UInt32('unknown6'),
    SIZE=40,
    )

gdl_save_header = Struct('header',
    UInt16('unknown0'),
    UInt16('unknown1'),
    UInt32('health'),
    Bool32('runes', *RUNESTONES),
    UInt32('unknown3'),
    UInt32('unknown4'),
    UInt32('unknown5'),
    UInt32('unknown6'),
    UInt32('unknown7'),
    UInt32('unknown8'),
    UInt32('unknown9'),
    UInt16('unknown10'),
    UInt16('unknown11'),
    UInt32('unknown12'),
    UInt32('unknown13'),
    UInt32('unknown14'),
    UInt32('unknown15'),
    UInt32('unknown16'),
    SIZE=64,
    )

gleg_save_header = Struct('header',
    UInt16('unknown0'),
    UInt16('unknown1'),
    UInt32('health'),
    UInt32('unknown2'),
    UInt32('unknown3'),
    UInt32('unknown4'),
    UInt32('unknown5'),
    UInt32('unknown6'),
    UInt32('unknown7'),
    UInt32('unknown8'),
    UInt32('unknown9'),
    UInt16('unknown10'),
    UInt16('unknown11'),
    UInt32('unknown12'),
    UInt32('unknown13'),
    UInt32('unknown14'),
    UInt32('unknown15'),
    UInt32('unknown16'),
    SIZE=64,
    )

gdl_save_entry = Struct("save_entry",
    gdl_save_header,
    Array("characters", SUB_STRUCT=gdl_character_data, SIZE=16),
    SIZE=512
    )

gleg_save_entry = Struct("save_entry",
    gleg_save_header,
    Array("characters", SUB_STRUCT=gleg_character_data, SIZE=8),
    SIZE=512
    )

arcade_gdl_save_file_def = TagDef("arcade_gdl_save_file",
    Array('save_files', SUB_STRUCT=gdl_save_entry, SIZE=1000),
    ext=".rom", endian=">" # strangely, big endian
    )

arcade_gleg_save_file_def = TagDef("arcade_gleg_save_file",
    Array('save_files', SUB_STRUCT=gleg_save_entry, SIZE=1000),
    ext=".rom", endian=">" # strangely, big endian
    )
