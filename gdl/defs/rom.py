from supyr_struct.defs.tag_def import TagDef
from .objs.rom import RomTag
from ..common_descs import *
from ..field_types import *

def get(): return rom_def


font_lump = Lump('fonts',
    SUB_STRUCT=Struct('font',
        StrLatin1('description', SIZE=16),
        UInt32('font_id'),
        )
    )

string_data_lump = Lump('string_data',
    SUB_STRUCT=StrRawLatin1('data',
        SIZE=get_lump_rawdata_size, WIDGET=TextFrame
        )
    )

string_offsets_lump = Lump('string_offsets',
    SUB_STRUCT=UInt32Array('offsets', SIZE=get_lump_rawdata_size)
    )

messages_lump = Lump('messages',
    SUB_STRUCT=QStruct('message',
        SInt32('num'),
        SInt32('first'),
        SInt32('font_id'),
        Float('scale'),
        Float('sscale'),
        )
    )

message_list_indices_lump = Lump('message_list_indices',
    SUB_STRUCT=UInt32Array('indices', SIZE=get_lump_rawdata_size)
    )

message_lists_lump = Lump('message_lists',
    SUB_STRUCT=QStruct('message_list',
        SInt32('num'),
        SInt32('first'),
        )
    )

defs_data_lump = Lump('defs_data',
    SUB_STRUCT=StrRawAscii('data',
        SIZE=get_lump_rawdata_size, WIDGET=TextFrame
        )
    )

message_def_offsets_lump = Lump('message_def_offsets',
    SUB_STRUCT=LUInt32('offset'),
    )

message_list_def_offsets_lump = Lump('message_list_def_offsets',
    SUB_STRUCT=LUInt32('offset'),
    )

rom_lump_headers = lump_headers(
    {NAME:'font', VALUE:lump_fcc('FONT'), GUI_NAME:'font'},
    {NAME:'text', VALUE:lump_fcc('TEXT'), GUI_NAME:'string data'},
    {NAME:'toff', VALUE:lump_fcc('TOFF'), GUI_NAME:'string offsets'},
    {NAME:'strs', VALUE:lump_fcc('STRS'), GUI_NAME:'messages'},
    {NAME:'loff', VALUE:lump_fcc('LOFF'), GUI_NAME:'message list indices'},
    {NAME:'list', VALUE:lump_fcc('LIST'), GUI_NAME:'message lists'},
    {NAME:'defs', VALUE:lump_fcc('DEFS'), GUI_NAME:'def data'},
    {NAME:'sdef', VALUE:lump_fcc('SDEF'), GUI_NAME:'message def offsets'},
    {NAME:'ldef', VALUE:lump_fcc('LDEF'), GUI_NAME:'message list def offsets'},
    )
rom_lumps_array = lumps_array(**{
    "font": font_lump,
    "text": string_data_lump,
    "toff": string_offsets_lump,
    "strs": messages_lump,
    "loff": message_list_indices_lump,
    "list": message_lists_lump,
    "defs": defs_data_lump,
    "sdef": message_def_offsets_lump,
    "ldef": message_list_def_offsets_lump,
    })

rom_def = TagDef("rom",
    wad_header,
    rom_lump_headers,
    rom_lumps_array,
    ext=".rom", endian="<", tag_cls=RomTag
    )
