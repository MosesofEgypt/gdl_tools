from supyr_struct.field_types import *
from supyr_struct.defs.tag_def import TagDef
from ..common_descs import *

def get(): return gdl_slus_def


gdl_slus_def = TagDef('slus',
    Array("secret_characters",
        SIZE=27, POINTER=1187880,
        SUB_STRUCT=secret_character_struct,
        DYN_NAME_PATH='.code', WIDGET=DynamicArrayFrame
        ),
    Array("cheats",
        SIZE=18, POINTER=1188856,
        SUB_STRUCT=cheat_struct,
        DYN_NAME_PATH='.code', WIDGET=DynamicArrayFrame
        ),
    ext='.47', incomplete=True, endian='<'
    )
