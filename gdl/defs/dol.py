from supyr_struct.field_types import *
from supyr_struct.defs.tag_def import TagDef
from ..common_descs import *

def get(): return GdlPs2Def


GdlPs2Def = TagDef('dol',
    Array("secret_characters",
        SIZE=27, POINTER=1168920,
        SUB_STRUCT=secret_character_struct,
        DYN_NAME_PATH='.code', WIDGET=DynamicArrayFrame
        ),
    Array("cheats",
        SIZE=18, POINTER=1169892,
        SUB_STRUCT=cheat_struct,
        DYN_NAME_PATH='.code', WIDGET=DynamicArrayFrame
        ),
    # NOTE: the STATIC/ANIM.PS2, STATIC/OBJECTS.NGC, and
    #       STATIC/TEXTURES.NGC are all present in the dol.
    #       we have an idea that it's to ensure the textures
    #       for fonts are available ASAP, but its just a hunch
    Container("static_resource",
        # NOTE: using an empty struct to force the pointer.
        Struct("pointer_fixup", POINTER=1206080, VISIBLE=False),
        BytesRaw("objects_data",  SIZE=23040),  # file is padded to 256 bytes
        BytesRaw("textures_data", SIZE=1084000),
        BytesRaw("anim_data",     SIZE=192),
        ),
    ext='.dol', incomplete=True, endian='>'
    )
