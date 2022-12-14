from supyr_struct.defs.executables.xbe import xbe_image_header,\
     xbe_certificate, xbe_sec_headers, xbe_lib_ver_headers
from ..common_descs import secret_character_struct, cheat_struct
from supyr_struct.field_types import *
from supyr_struct.defs.tag_def import TagDef

def get(): return GdlXbeDef

GdlXbeDef = TagDef('xbe',
    Struct("xbe_image_header", INCLUDE=xbe_image_header, VISIBLE=False),
    Struct("xbe_certificate", INCLUDE=xbe_certificate, VISIBLE=False),
    Array("xbe_sec_headers", INCLUDE=xbe_sec_headers, VISIBLE=False),
    Array("lib_ver_headers", INCLUDE=xbe_lib_ver_headers, VISIBLE=False),
    Array("secret_characters",
        SIZE=27, POINTER=1135088,
        SUB_STRUCT=secret_character_struct
        ),
    Array("cheats",
        SIZE=18, POINTER=1136064,
        SUB_STRUCT=cheat_struct
        ),

    ext='.xbe', incomplete=True, endian='<'
    )
