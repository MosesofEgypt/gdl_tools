from supyr_struct.defs.tag_def import TagDef
from .objs.wad import WadTag
from ..common_descs import *

def get(): return shop_def

item_type = UEnum32('type',
    ('exit',   0),
    ('key',    1),
    ('potion', 3),
    ('food',  17),

    ('ten_strength', 5),
    ('ten_speed', 6),
    ('ten_armor', 7),
    ('ten_magic', 8),

    ('phoenix',        10),
    ('rapid_fire',     11),
    ('hammer',         13),
    ('three_way_shot', 12),
    ('five_way_shot',  34),
    ('super_shot',     24),

    ('reflect_shield', 9),
    ('elec_shield',   14),
    ('fire_shield',   15),

    ('levitate', 18),
    ('growth',   19),
    ('growth2',   4),
    ('shrink',   29),
    ('speed',    28),

    ('fire_amulet',  20),
    ('elec_amulet',  21),
    ('light_amulet', 22),
    ('acid_amulet',  23),

    ('fire_breath',      25),
    ('lightning_breath', 26),
    ('acid_breath',      27),

    ('invisibility', 30),
    ('invulnerable', 31),
    ('gold_invulnerable', 16),
    ('x_ray',    32),
    ('gas_mask', 33),

    ('anti_death',     35),
    ('hand_of_death',  36),
    ('health_vampire', 37),
    ('mikey_dummy',    38),
    #the next 20 items after 38 act like exit,
    #so im assuming all other values do as well
    )

item_lump = Lump('items',
    SUB_STRUCT=Struct('item',
        StrLatin1('icon_id',     SIZE=32),
        StrLatin1('description', SIZE=32, WIDGET=TextFrame),
        Float('scale', DEFAULT=1.0),
        item_type,
        UInt32('price'),
        UInt32('amount'),
        SIZE=80,
        ),
    DYN_NAME_PATH='.item_type.enum_name', WIDGET=DynamicArrayFrame
    )

shop_lump_headers = lump_headers(
    {NAME:'item', VALUE:lump_fcc('ITEM'), GUI_NAME:'shop items'},
    )
shop_lumps_array = lumps_array(
    item = item_lump,
    )

shop_def = TagDef("shop",
    wad_header,
    shop_lump_headers,
    shop_lumps_array,
    ext=".wad", endian="<", tag_cls=WadTag
    )
