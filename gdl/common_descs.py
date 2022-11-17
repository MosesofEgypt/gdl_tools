from supyr_struct.defs.common_descs import *
from supyr_struct.util import fourcc_to_int
from binilla.widgets.field_widgets import *
from binilla.constants import *
from .field_types import *

def lump_fcc(value):
    return fourcc_to_int(value, 'big')    

def get_lump_type(node=None, parent=None, attr_index=None,
                  rawdata=None, new_value=None, *args, **kwargs):
    if node and parent is None:
        parent = node.parent
    if attr_index is None:
        attr_index = parent.index_by_id(node)
    return parent.get_root().data.lump_headers[attr_index].lump_id.enum_name

def lump_size(node=None, parent=None, attr_index=None,
              rawdata=None, new_value=None, *args, **kwargs):
    if node and parent is None:
        parent = node.parent
    if parent is None:
        return 0
    if attr_index is None:
        try:
            attr_index = parent.index_by_id(node)
        except ValueError:
            return 0

    try:
        header = parent.get_root().data.lump_headers[attr_index]
    except IndexError:
        return 0
    if new_value is None:
        return header.lump_array_length
    header.lump_array_length = new_value

def lump_pointer(node=None, parent=None, attr_index=None,
                 rawdata=None, new_value=None, *args, **kwargs):
    if node and parent is None:
        parent = node.parent
    if parent is None:
        return 0
    if attr_index is None:
        try:
            attr_index = parent.index_by_id(node)
        except ValueError:
            return 0
    try:
        header = parent.get_root().data.lump_headers[attr_index]
    except IndexError:
        return 0
    if new_value is None:
        return header.lump_array_pointer
    header.lump_array_pointer = new_value

# used in a lot of places
xyz_float = QStruct('xyz_float',
    Float("x"), Float("y"), Float("z"), ORIENT='h'
    )

#############################
'''individual lump structs'''
#############################

effect = Struct('effect',
    Bool32('flags',
        "unknown0",  "unknown1",  "unknown2",  "unknown3",
        "unknown4",  "unknown5",  "unknown6",  "unknown7",
        "unknown8",  "unknown9",  "unknown10", "unknown11",
        "unknown12", "unknown13", "unknown14", "unknown15",
        "unknown16", "unknown17", "unknown18", "unknown19",
        "unknown20", "unknown21", "unknown22", "unknown23",
        "unknown24", "unknown25", "unknown26", "unknown27",
        "unknown28", "unknown29", "unknown30", "unknown31"
        ),
    SInt32('next fx index'),
    SInt32('fx index'),
    SInt32('snd index'),
    StrLatin1('fx desc', SIZE=16),
    StrLatin1('snd desc', SIZE=16),
    SInt16('zmod'),
    SInt16('alpha mod'),
    QStruct('offset', INCLUDE=xyz_float),
    Float('max len'),
    Float('radius'),
    Float('scale'),
    QStruct('color',
        UInt8('b'), UInt8('g'), UInt8('r'), UInt8('a'),
        ORIENT='h', WIDGET=ColorPickerFrame,
        ),
    SIZE=80,
    )

stat = QStruct("",
    Float('min'), Float('max'), ORIENT='h'
    )

damage = Struct('damage',
    UEnum16("type"),
    Bool16("flags",
        "unknown0",  "unknown1",  "unknown2",  "unknown3",
        "unknown4",  "unknown5",  "unknown6",  "unknown7",
        "unknown8",  "unknown9",  "unknown10", "unknown11",
        "unknown12", "unknown13", "unknown14", "unknown15",
        ),
    BitStruct('damage type',
        UBitEnum('type',
            "normal",
            "fire",
            "elec",
            "light",
            "acid",
            SIZE=4,
            ),
        BitBool('flags',
            'knockback',
            'knockdown',
            'blownaway',
            'stun',
            'knockover',
            'magic',
            'explode',
            'poisongas',
            'deathstun',
            'spike',
            'grabbed',
            'thrown',
            'whirlwind',
            'arrow',
            'fball',
            'three way',
            'super',
            'reflect', 
            'five way',
            'heals',
            'nohitfx',
            'turbo',
            'sticky',
            'bosshit',
            'hammer',
            'rapid',
            'low',
            SIZE=28,
            ),
        SIZE=4,
        ),
    Float('hit rad'),
    Float('radius'),
    Float('min rad'),
    Float('delay'),
    QStruct('time', INCLUDE=stat),
    Float('angle'),
    Float('arc'),
    Float('pitch'),
    QStruct('offset', INCLUDE=xyz_float),
    Float('amount'),
    QStruct('speed', INCLUDE=stat),
    Float('weight'),
    SInt16('fx index'),
    SInt16('hit fx index'),
    SInt16('loop fx index'),
    SInt16('next'),
    SInt16('start frame'),
    SInt16('end frame'),
    SInt16('help index'),
    SInt16('dummy'),
    )


#############################
'''main wad header structs'''
#############################
wad_header = QStruct('wad header',
    UInt32('lump headers pointer'),
    UInt32('lump count'),
    Pad(8),
    VISIBLE=False,
    )

lump_header = Struct('lump header',
    UEnum32('lump id',
        #text wad lump values
        {NAME:'font', VALUE:lump_fcc('FONT'), GUI_NAME:'font'},
        {NAME:'text', VALUE:lump_fcc('TEXT'), GUI_NAME:'string text'},
        {NAME:'defs', VALUE:lump_fcc('DEFS'), GUI_NAME:'def names text'},

        {NAME:'toff', VALUE:lump_fcc('TOFF'), GUI_NAME:'string offsets'},
        {NAME:'loff', VALUE:lump_fcc('LOFF'), GUI_NAME:'list offsets'},
        {NAME:'sdef', VALUE:lump_fcc('SDEF'), GUI_NAME:'string def offsets'},
        {NAME:'ldef', VALUE:lump_fcc('LDEF'), GUI_NAME:'list def offsets'},

        {NAME:'list', VALUE:lump_fcc('LIST'), GUI_NAME:'string list'},
        {NAME:'strs', VALUE:lump_fcc('STRS'), GUI_NAME:'string message'},
        
        #pdata and critter wad lump values
        {NAME:'sfxx', VALUE:lump_fcc('SFXX'), GUI_NAME:'sound/visual fx'},
        {NAME:'damg', VALUE:lump_fcc('DAMG'), GUI_NAME:'attack damage'},
             
        #critter wad lump values
        {NAME:'desc', VALUE:lump_fcc('DESC'), GUI_NAME:'????'},
        {NAME:'adda', VALUE:lump_fcc('ADDA'), GUI_NAME:'????'},
        {NAME:'node', VALUE:lump_fcc('NODE'), GUI_NAME:'????'},
        {NAME:'move', VALUE:lump_fcc('MOVE'), GUI_NAME:'????'},
        {NAME:'ptrn', VALUE:lump_fcc('PTRN'), GUI_NAME:'????'},
        {NAME:'type', VALUE:lump_fcc('TYPE'), GUI_NAME:'????'},
             
        #pdata wad lump values
        {NAME:'pdat', VALUE:lump_fcc('PDAT'), GUI_NAME:'player data'},
             
        #wdata wad lump values
        {NAME:'enmy', VALUE:lump_fcc('ENMY'), GUI_NAME:'enemy type'},
        {NAME:'bcam', VALUE:lump_fcc('BCAM'), GUI_NAME:'boss camera'},
        {NAME:'cams', VALUE:lump_fcc('CAMS'), GUI_NAME:'cameras'},
        {NAME:'snds', VALUE:lump_fcc('SNDS'), GUI_NAME:'sounds'},
        {NAME:'auds', VALUE:lump_fcc('AUDS'), GUI_NAME:'audio streams'},
        {NAME:'maps', VALUE:lump_fcc('MAPS'), GUI_NAME:'maps'},
        {NAME:'levl', VALUE:lump_fcc('LEVL'), GUI_NAME:'level details'},
        {NAME:'wrld', VALUE:lump_fcc('WRLD'), GUI_NAME:'world description'},
             
        #shpdata wad lump values
        {NAME:'item', VALUE:lump_fcc('ITEM'), GUI_NAME:'shop items'},
        ),
    Pointer32('lump array pointer'),
    UInt32('lump array length'),
    UInt32('lump array length2'),
    )

lump_headers = Array('lump headers',
    POINTER='.wad_header.lump_headers_pointer',
    SIZE='.wad_header.lump_count', SUB_STRUCT=lump_header,
    VISIBLE=False,
    )
