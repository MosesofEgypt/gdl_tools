from supyr_struct.defs.tag_def import TagDef
from .objs.wad import WadTag
from ..common_descs import *
from ..field_types import *

def get(): return wdata_def

wdata_lump_headers = lump_headers(
    {NAME:'enmy', VALUE:lump_fcc('ENMY'), GUI_NAME:'enemy type'},
    {NAME:'bcam', VALUE:lump_fcc('BCAM'), GUI_NAME:'boss camera'},
    {NAME:'cams', VALUE:lump_fcc('CAMS'), GUI_NAME:'cameras'},
    {NAME:'snds', VALUE:lump_fcc('SNDS'), GUI_NAME:'sounds'},
    {NAME:'auds', VALUE:lump_fcc('AUDS'), GUI_NAME:'audio streams'},
    {NAME:'maps', VALUE:lump_fcc('MAPS'), GUI_NAME:'maps'},
    {NAME:'levl', VALUE:lump_fcc('LEVL'), GUI_NAME:'level details'},
    {NAME:'wrld', VALUE:lump_fcc('WRLD'), GUI_NAME:'world description'},
    )
wdata_lumps_array = lumps_array(
    SUB_STRUCT=Void("empty"),
    )

wdata_def = TagDef("wdata",
    wad_header,
    wdata_lump_headers,
    wdata_lumps_array,
    ext=".wad", endian="<", tag_cls=WadTag
    )
