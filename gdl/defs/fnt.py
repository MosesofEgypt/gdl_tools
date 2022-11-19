from supyr_struct.defs.tag_def import TagDef
from ..common_descs import *
from ..field_types import *

def get(): return font_def

def has_next_font_letter(rawdata=None, *args, **kwargs):
    try:
        data = rawdata.peek(16)
        return len(data) >= 16
    except:
        return False

font_letter = Struct('font_letter',
    SInt32('letter'),
    SInt32('width'),
    SInt32('x'),
    SInt32('y'),
    )

font_def = TagDef("fnt",
    Pointer32('name_pointer', VISIBLE=False), # unused in serialized form
    SInt32('height'),
    Pointer32('font_letters_pointer', VISIBLE=False), # unused in serialized form
    WhileArray('font_letters',
        SUB_STRUCT=font_letter,
        CASE=has_next_font_letter,
        ),
    ext=".fnt"
    )
