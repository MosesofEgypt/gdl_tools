from supyr_struct.field_types import *
from supyr_struct.defs.tag_def import TagDef
from ..common_descs import secret_character_struct, cheat_struct

def get(): return GdlPs2Def


GdlPs2Def = TagDef('slus',
    Array("secret_characters",
        SIZE=27, POINTER=1187880,
        SUB_STRUCT=secret_character_struct
        ),
    Array("cheats",
        SIZE=18, POINTER=1188856,
        SUB_STRUCT=cheat_struct
        ),
    ext='.47', incomplete=True, endian='<'
    )
