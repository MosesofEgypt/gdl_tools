from supyr_struct.defs.common_descs import *
from supyr_struct.util import fourcc_to_int
from binilla.widgets.field_widgets import *
from binilla.constants import *
from .field_types import *

def lump_fcc(value):
    return fourcc_to_int(value, 'big')


def _get_lump_context(
        *args, node=None, parent=None, attr_index=None, rawdata=None,
        new_value=None, **kwargs):
    if node and parent is None:
        parent = node.parent

    if attr_index is None:
        try:
            attr_index = parent.index_by_id(node)
        except:
            attr_index = None

    try:
        headers = parent.get_root().data.lump_headers
    except:
        headers = None

    return attr_index, headers


def get_lump_type(*args, **kwargs):
    i, lump_headers = _get_lump_context(*args, **kwargs)
    return lump_headers[i].lump_id.enum_name


def get_lump_size(*args, new_value=None, **kwargs):
    i, lump_headers = _get_lump_context(*args, **kwargs)
    if None in (i, lump_headers):
        return 0
    elif new_value is None:
        return lump_headers[i].lump_size

    lump_headers[i].lump_size  = new_value
    if hasattr(lump_headers[i], "lump_size2"):
        lump_headers[i].lump_size2 = new_value


def get_lump_rawdata_size(
        *args, parent=None, attr_index=None, rawdata=None,
        new_value=None, **kwargs
        ):
    if new_value is not None:
        # open-ended lump data doesnt have its size stored anywhere
        return None
    elif None in (parent, attr_index) or parent[attr_index] is None:
        # need to check the parent of the parent to determine the size
        kwargs["node"] = parent
        parent = parent.parent
        attr_index = None
    else:
        # lumps rawdata exists, so return its size
        node = parent[attr_index]
        return getattr(node, 'itemsize', 1) * len(node)

    i, lump_headers = _get_lump_context(*args, **kwargs)
    if None in (i, lump_headers):
        return 0

    start = lump_headers[i].lump_array_pointer
    if start == lump_headers.parent.wad_header.lump_headers_pointer:
        # weird edge case for lumps without data
        return 0

    end   = 0x100000000 # use a high start value to reduce from that'll get
    #                     masked off to 0 if no lumps end after this one
    for lump_header in lump_headers:
        # find the lump that starts closest AFTER this one
        if lump_header.lump_array_pointer in range(start + 1, end):
            end = lump_header.lump_array_pointer

    if hasattr(rawdata, '__len__'):
        end = min(len(rawdata), end)

    end &= 0xFFffFFff  # mask off to cap size
    return end - start


def get_lump_pointer(*args, new_value=None, **kwargs):
    i, lump_headers = _get_lump_context(*args, **kwargs)
    if None in (i, lump_headers):
        return 0
    elif new_value is None:
        return lump_headers[i].lump_array_pointer

    lump_headers[i].lump_array_pointer = new_value


# shared structs
xyz_float = QStruct("",
    Float("x"), Float("y"), Float("z"),
    ORIENT='h'
    )
bgra_uint8 = QStruct("",
    UInt8("b"), UInt8("g"), UInt8("r"), UInt8("a"),
    ORIENT='h', WIDGET=ColorPickerFrame
    )
stat_range = QStruct("",
    Float('min'), Float('max'),
    ORIENT='h'
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

def lump_headers(*lump_ids, extra_size_field=True):
    header_fields = (
        UEnum32('lump_id', *lump_ids),
        Pointer32('lump_array_pointer'),
        UInt32('lump_size'),
        )
    if extra_size_field:
        header_fields += (UInt32('lump_size2'), )

    return Array('lump_headers',
        POINTER='.wad_header.lump_headers_pointer',
        SIZE='.wad_header.lump_count', VISIBLE=False,
        SUB_STRUCT=Struct('lump_header', *header_fields)
        )

def lumps_array(**cases):
    lump_switch = Switch("lump",
        CASE=get_lump_type, CASES=cases,
        )
    return Array('lumps',
        POINTER='.wad_header.lump_headers_pointer',
        SIZE='.wad_header.lump_count',
        SUB_STRUCT=lump_switch,
        )

def Lump(*args, **kwargs):
    kwargs.setdefault("SIZE", get_lump_size)
    kwargs.setdefault("POINTER", get_lump_pointer)
    return LumpArray(*args, **kwargs)


#############################
'''shared lump structs'''
#############################

effects_lump = Lump('effects',
    SUB_STRUCT=Struct('effect',
        Bool32('flags',
            *("unknown%s" % i for i in range(32))
            ),
        SInt32('next_fx_index'),
        SInt32('fx_index'),
        SInt32('snd_index'),
        StrLatin1('fx_desc', SIZE=16),
        StrLatin1('snd_desc', SIZE=16),
        SInt16('zmod'),
        SInt16('alpha_mod'),
        QStruct('offset', INCLUDE=xyz_float),
        Float('max_len'),
        Float('radius'),
        Float('scale'),
        QStruct('color', INCLUDE=bgra_uint8),
        SIZE=80,
        ),
    )

damages_lump = Lump('damages',
    SUB_STRUCT=Struct('damage',
        UEnum16("type"),
        Bool16("flags",
            *("unknown%s" % i for i in range(16))
            ),
        BitStruct('damage_type',
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
                'three_way',
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
        Float('hit_rad'),
        Float('radius'),
        Float('min_rad'),
        Float('delay'),
        QStruct('time', INCLUDE=stat_range),
        Float('angle'),
        Float('arc'),
        Float('pitch'),
        QStruct('offset', INCLUDE=xyz_float),
        Float('amount'),
        QStruct('speed', INCLUDE=stat_range),
        Float('weight'),
        SInt16('fx_index'),
        SInt16('hit_fx_index'),
        SInt16('loop_fx_index'),
        SInt16('next'),
        SInt16('start_frame'),
        SInt16('end_frame'),
        SInt16('help_index'),
        SInt16('dummy'),
        ),
    )
