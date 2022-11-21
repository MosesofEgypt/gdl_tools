from supyr_struct.defs.tag_def import TagDef
from .objs.wad import WadTag
from ..common_descs import *
from ..field_types import *

def get(): return critter_def

critter_lump_headers = lump_headers(
    {NAME:'sfxx', VALUE:lump_fcc('SFXX'), GUI_NAME:'sound/visual fx'},
    {NAME:'damg', VALUE:lump_fcc('DAMG'), GUI_NAME:'attack damage'},
    {NAME:'desc', VALUE:lump_fcc('DESC'), GUI_NAME:'????'},
    {NAME:'adda', VALUE:lump_fcc('ADDA'), GUI_NAME:'????'},
    {NAME:'node', VALUE:lump_fcc('NODE'), GUI_NAME:'????'},
    {NAME:'move', VALUE:lump_fcc('MOVE'), GUI_NAME:'????'},
    {NAME:'ptrn', VALUE:lump_fcc('PTRN'), GUI_NAME:'????'},
    {NAME:'type', VALUE:lump_fcc('TYPE'), GUI_NAME:'????'},
    )
critter_lumps_array = lumps_array(
    sfxx = effects_lump,
    damg = damages_lump,
    )

critter_def = TagDef("critter",
    wad_header,
    critter_lump_headers,
    critter_lumps_array,
    ext=".wad", endian="<", tag_cls=WadTag
    )
