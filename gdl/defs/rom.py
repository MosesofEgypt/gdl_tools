from supyr_struct.defs.tag_def import TagDef
from binilla.widgets.field_widgets import TextFrame
from ..common_descs import *
from ..field_types import *

def get(): return rom_def

def get_text_lump_size(node=None, parent=None, attr_index=None,
                       rawdata=None, new_value=None, *args, **kwargs):
    if node and parent is None:
        parent = node.parent
    if attr_index is None:
        try:
            attr_index = parent.index(node)
        except ValueError:
            return 0
    if parent is None or attr_index is None:
        return 0
    if new_value is not None:
        return
    lump_headers = parent.get_root().data.lump_headers
    start = end = lump_headers[attr_index].lump_array_pointer
    
    try:
        end = lump_headers[attr_index+1].lump_array_pointer
    except IndexError:
        if hasattr(rawdata, 'len'):
            end = len(rawdata)
    return end - start

def get_oe_offs_lump_size(node=None, parent=None, attr_index=None,
                          rawdata=None, new_value=None, *args, **kwargs):
    if node and parent is None:
        parent = node.parent
    if attr_index is None:
        try:
            attr_index = parent.index(node)
        except ValueError:
            return 0
    if parent is None or attr_index is None:
        return 0
    if new_value is not None:
        return
    lump_headers = parent.get_root().data.lump_headers
    start = end = lump_headers[attr_index].lump_array_pointer
    
    try:
        end = lump_headers[attr_index+1].lump_array_pointer
    except IndexError:
        if hasattr(rawdata, 'len'):
            end = len(rawdata)
    return (end - start)//4

lump_kw      = {SIZE: lump_size, POINTER: lump_pointer}
text_lump_kw = {SIZE: get_text_lump_size, POINTER: lump_pointer,
                WIDGET: TextFrame}
oe_offs_lump_kw = {SIZE: get_oe_offs_lump_size, POINTER: lump_pointer}

#############################
'''individual lump structs'''
#############################

string_message = QStruct('string message',
    #These define which strings(specified by TOFF) are grouped into messages.

    #For example, all of a single boss's hints are in one STRS block.

    #"first" specifies which string the grouping starts at.

    #Font is the numerical ID of the font to use
    #which should match a FONT block "fontid"
    SInt32('num',   GUI_NAME='number of strings'),
    SInt32('first', GUI_NAME='first string index'),
    SInt32('font id'),
    Float('scale'),
    Float('sscale'),
    )

string_list = QStruct('string list',
    #These define which string offsets are grouped together into lists.

    #For example, all of the rune hints are in one
    #string list, all of the boss hints are in another,
    #list, and all of the general hints are in another.

    #"first" specifies which string offset the list starts at.
    SInt32('num',   GUI_NAME='number of strings'),
    SInt32('first', GUI_NAME='first string index'),
    )

font = Struct('font',
    StrLatin1('description', SIZE=16),
    UInt32('font id', GUI_NAME='id of this font'),
    )

text_data      = StrRawAscii('text data',      **text_lump_kw)
def_names_data = StrRawAscii('def names data', **text_lump_kw)


'''lump block arrays'''
font_array = Lump('fonts',
    SUB_STRUCT=font, **lump_kw
    )
string_offsets = Lump('string offsets',
    #An array of UInt32 offsets to the null
    #terminated strings within the TEXT lump
    SUB_STRUCT=UInt32('offset'),
    **oe_offs_lump_kw
    )
string_message_array = Lump('string messages',
    SUB_STRUCT=string_message, **lump_kw
    )
list_offsets   = Lump('list offsets',
    #These are less like offsets, and more of an ordering.
    #This is a list how the string messages should be ordered.

    #For example, the first 13 offsets in HINTS_E.ROM are:
    #11, 7, 1, 0, 4, 3, 2, 5, 6, 8, 9, 10, and 11
    #Using this to reorder the first 13 string lists
    #gives the string lists in this ordering:

    #NOBOSSHINT
    #LICHHINTS
    #DRAGONHINTS
    #CHIMERAHINTS
    #PLAGUEHINTS
    #DRIDERHINTS
    #DJINNHINTS
    #YETIHINTS
    #WRAITHHINTS
    #SKORNE1HINTS
    #SKORNE2HINTS
    #GARMHINTS
    #NOBOSSHINT

    #which is the order that the boss hints would be given ingame
    SUB_STRUCT=LUInt32('offset'), **oe_offs_lump_kw
    )
string_list_array = Lump('string lists',
    SUB_STRUCT=string_list, **lump_kw
    )
list_def_offsets   = Lump('list def offsets',
    #These offsets point to the start of each
    #string list defs name in the DEFS lump
    SUB_STRUCT=LUInt32('offset'), **lump_kw
    )
string_def_offsets = Lump('string def offsets',
    #These offsets point to the start of each
    #string defs name in the DEFS lump
    SUB_STRUCT=LUInt32('offset'), **lump_kw
    )


rom_def = TagDef("rom",
    QStruct('wad header',
        UInt32('lump headers pointer'),
        UInt32('lump count', DEFAULT=9),
        Pad(8),
        VISIBLE=False,
        ),
    lump_headers,

    #these need to be in a container to have the same index
    #ordering as their headers in the lump_headers array
    Container('lumps',
        font_array,
        text_data,
        string_offsets,
        string_message_array,
        list_offsets,
        string_list_array,
        def_names_data,
        string_def_offsets,
        list_def_offsets,
        ),
    
    ext=".rom"
    )
