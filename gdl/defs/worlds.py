from supyr_struct.defs.tag_def import TagDef
from .objs.worlds import WorldsTag
from ..common_descs import *
from ..field_types import *

def get(): return worlds_ps2_def

worlds_ps2_def = TagDef("worlds",
    ext=".ps2", endian="<", tag_cls=WorldsTag
    )
