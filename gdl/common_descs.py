import math

from supyr_struct.defs.common_descs import *
from supyr_struct.util import fourcc_to_int
from binilla.widgets.field_widgets import *
from binilla.constants import *
from .field_types import *

try:
    from binilla.widgets.field_widgets import DynamicArrayFrame, TextFrame
except Exception:
    DynamicArrayFrame = TextFrame = None


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
UNIT_SCALE_RAD_TO_DEG = 180/math.pi
xy_float = QStruct("",
    Float("x"), Float("y"),
    ORIENT='h'
    )
xyz_float = QStruct("",
    Float("x"), Float("y"), Float("z"),
    ORIENT='h'
    )
ijk_float = QStruct("",
    Float("i"), Float("j"), Float("k"),
    ORIENT='h'
    )
pyr_float = QStruct("",
    Float("p", UNIT_SCALE=UNIT_SCALE_RAD_TO_DEG),
    Float("y", UNIT_SCALE=UNIT_SCALE_RAD_TO_DEG),
    Float("r", UNIT_SCALE=UNIT_SCALE_RAD_TO_DEG),
    ORIENT='h'
    )
radian_float_min_max = QStruct("",
    Float("min", UNIT_SCALE=UNIT_SCALE_RAD_TO_DEG),
    Float("max", UNIT_SCALE=UNIT_SCALE_RAD_TO_DEG),
    ORIENT='h'
    )
ijkw_float = QStruct("",
    Float("i"), Float("j"), Float("k"), Float("w"),
    ORIENT='h'
    )
bgr_float = QStruct("",
    Float("b"), Float("g"), Float("r"),
    ORIENT='h'
    )
bgr_uint8 = QStruct("",
    UInt8("b"), UInt8("g"), UInt8("r"),
    ORIENT='h', WIDGET=ColorPickerFrame
    )
bgra_uint8 = QStruct("",
    UInt8("b"), UInt8("g"), UInt8("r"), UInt8("a"),
    ORIENT='h', WIDGET=ColorPickerFrame
    )
rgba_uint8 = QStruct("",
    UInt8("r"), UInt8("g"), UInt8("b"), UInt8("a"),
    ORIENT='h', WIDGET=ColorPickerFrame
    )
float_min_max = QStruct("",
    Float('min'), Float('max'),
    ORIENT='h'
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
#  shared lump structs
#############################
PLAYER_COLORS = (
    "yellow",
    "blue",
    "red",
    "green"
    )

PLAYER_TYPES = (
    "warrior",
    "valkyrie",
    "wizard",
    "archer",
    "dwarf",
    "knight",
    "sorceress",
    "jester",
    "minotaur",
    "falconess",
    "jackal",
    "tigress",
    "ogre",
    "unicorn",
    "medusa",
    "hyena"
    )

ENEMY_TYPES = (
    "scorp",
    "troll",
    "demon",
    "rat",
    "grunt",
    "knight",
    "snake",
    "sorcerer",
    "mummy",
    "spider",
    "lizardman",
    "treefolk",
    "maggot",
    "zombie",
    "plague",
    "wolf",
    "ice",
    "worm",
    "dog",
    "skeleton",
    "ghost",
    "acid",
    "hand",
    "imp",
    "warlock",
    "sky",
    "whirlwind",
    "garm2",
    "unused",
    "golem",
    "death",
    "it",
    "gargoyle",
    "general",
    "dragon",
    "chimera",
    "djinn",
    "drider",
    "pboss",
    "yeti",
    "wraith",
    "lich",
    "skorne1",
    "skorne2",
    "garm",
    ("none", -1),
    )

WAVE_TYPES = (
    "test",
    "castle",
    "mountain",
    "desert",
    "forest",
    "boss",
    "hell",
    "town",
    "battle",
    "ice",
    "dream",
    "sky",
    "secret",
    "tower",
    )

WEAPON_TYPES = (
    "normal",
    "fire",
    "elec",
    "light",
    "acid",
    )

ITEM_TYPES = (
    "none",
    "powerup",
    "container",
    "generator",
    "enemy",
    "trigger",
    "trap",
    "door",
    "damage_tile",
    "exit",
    "obstacle",
    "transporter",
    "rotator",
    "sound",
    ("random",      -1),
    )

ITEM_SUBTYPES = (
    "none",
    "gold",
    "key",
    "food",
    "potion",
    "weapon",
    "armor",
    "speed",
    "magic",
    "special",
    "runestone",
    "bosskey",
    "obelisk",
    "legend_item",
    "scroll",
    "crystal",
    "gargoyle_item",
    *("unused%d" % i for i in range(0x11, 0x14)),

    "bridge_pad",
    "door_pad",
    "bridge_switch",
    "door_switch",
    "activator_switch",
    "elevator_pad",
    "elevator_switch",
    "lift_pad",
    "lift_start",
    "lift_end",
    "no_weapon_collider",
    "shoot_trigger",
    *("unused%d" % i for i in range(0x20, 0x28)),

    "rock_fall",
    "safe_rock",
    "wall",
    "barrel",
    "barrel_explode",
    "barrel_poison",
    "chest",
    "chest_gold",
    "chest_silver",
    "leaf_fall",
    "secret",
    "rock_fly",
    "shoot_fall",
    "rock_sink",
    )

GARGOYLE_ITEMS = (
    "fang",
    "feather",
    "claw",
    )

CRYSTAL_TYPES = (
    "blue",
    "red",
    "yellow",
    "green",
    "orange",
    "white",
    "black",
    "purple",
    )

BOSS_KEYS = (
    'unused',
    'lich_shard',
    'dragon_shard',
    'chimera_shard',
    'plague_shard',
    'drider_shard',
    'djinn_shard',
    'yeti_shard',
    'wraith_shard',
    )

LEGEND_ITEMS = (
    'none',
    'scimitar',
    'ice_axe',
    'lamp',
    'bellows',
    'savior',
    'unused1',
    'book',
    'unused2',
    'parchment',
    'lantern',
    'javelin',
    )

RUNESTONES = (
    'blue_1',
    'blue_2',
    'blue_3',
    'red_1',
    'red_2',
    'red_3',
    'yellow_1',
    'yellow_2',
    'yellow_3',
    'green_1',
    'green_2',
    'green_3',
    'final',
    )

item_type = SEnum32("item_type", *ITEM_TYPES)

obstacle_subtype = SEnum16("obstacle_subtype", *ITEM_SUBTYPES)

item_subtype = SEnum32("item_subtype", *ITEM_SUBTYPES)

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
    DYN_NAME_PATH='.fx_desc', WIDGET=DynamicArrayFrame
    )

damage_type = BitStruct('damage_type',
    UBitEnum('type', *WEAPON_TYPES, SIZE=4),
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
        'five_way',
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
    )

# NOTE: this is a subset of the damage_type bitstruct
#       with the invalid/unusable values removed
weapon_types = BitStruct("weapon_types",
    UBitEnum('type', *WEAPON_TYPES, SIZE=4),
    BitBool("weapon_flags",
        "knockback",
        "knockdown",
        Pad(13),
        "three_way",
        "super",
        "reflect", 
        "five_way",
        "heals",
        Pad(4),
        "hammer",
        "rapid",
        SIZE=28,
        ),
    SIZE=4,
    )

armor_types = Bool32("armor_types",
    "resist_fire",
    "resist_elec",
    "resist_light",
    "resist_acid",
    "resist_magic",
    Pad(3),
    "immune_fire",
    "immune_elec",
    "immune_light",
    "immune_acid",
    "immune_magic",
    "immune_gas",
    Pad(4),
    ("immune_knockback", 0x40000),

    ("invulnerability_silver", 0x10000),
    ("invulnerability_gold",  0x100000),

    ("antideath",        0x80000),
    ("armor_reflect",    0x20000),
    ("armor_reflect2", 0x1000000),
    ("armor_fire",      0x200000),
    ("armor_elec",      0x400000),
    ("armor_protect",   0x800000),
    )

special_types = Bool32("special_types",
    "levitate",
    "x_ray",
    "invisible",
    "stop_time",
    "fire_breath",
    "acid_breath",
    "elec_breath",
    "phoenix",
    "growth",
    "shrink",
    "pojo",
    Pad(1),
    "skorn_horns",
    "skorn_mask",
    "skorn_gauntlet_r",
    "skorn_gauntlet_l",
    "speed",
    "health",
    "dummy",
    "turbo",
    "mikey",
    "hand_of_death",
    "health_vampire",
    )

damages_lump = Lump('damages',
    SUB_STRUCT=Struct('damage',
        UEnum16("type",
            # TODO: verify these
            "none",
            "node",
            "fireball",
            "arc",
            "stomp",
            "cone",
            "spout",
            "spout2",
            "fountain",
            "shoot_weapon",
            ),
        Bool16("flags",
            *("unknown%s" % i for i in range(16))
            ),
        damage_type,
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

particle_system_flags = Bool32("flags",
    ("dynamic",  0x1),
    ("oneshot",  0x2),
    ("forever",  0x4),
    ("gravity",  0x8),
    ("drag",     0x10),
    ("notexrgb", 0x20),
    ("notexa",   0x40),
    ("fb_add",   0x80),
    ("fb_mul",   0x100),
    ("sort",     0x200),
    ("nozcmp",   0x400),
    ("nozwrite", 0x800),
    )

particle_system_flag_enables = Bool32("flag_enables",
    INCLUDE=particle_system_flags
    )

particle_system_enables = Bool32("enables",
    ("preset",  0x1),
    ("maxp",    0x2),
    ("maxdir",  0x4),
    ("maxpos",  0x8),
    ("e_life",  0x10),
    ("p_life",  0x20),
    ("e_angle", 0x40),
    ("e_dir",   0x80),
    ("e_vol",   0x100),
    ("e_rate",  0x200),
    ("e_rate_rand", 0x400),
    ("p_gravity", 0x800),
    ("p_drag",    0x1000),
    ("p_speed",   0x2000),
    ("p_texname", 0x4000),
    ("p_texcnt",  0x8000),
    ("p_rgb",   0x10000),
    ("p_alpha", 0x20000),
    ("p_width", 0x40000),
    ("e_delay", 0x80000),
    )

particle_system = Struct("particle_system",
    # NOTE: "e" means emitter? "p" means phase?
    UEnum32("version",
        ("v257", 257),
        DEFAULT=257
        ),
    SEnum16("preset",
        "firework",
        "cannon",
        "spray",
        "smoke",
        "firework_g",
        "cannon_g",
        "spray_g",
        "smoke_g",
        ),
    StrAsciiEnum("id",
        # NOTE: insert this id into the following template:
        #   "%sPSYS%c" % (level_id, psys_id)
        # this serves as a prefix matcher to determin if this particle system
        # should be attached to a given world object. if it matches, attach.
        *((c, c) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        SIZE=1
        ),
    SInt8("dummy", VISIBLE=False), # always 0
    particle_system_flags,
    particle_system_flag_enables,
    particle_system_enables,
    SInt32("maxp"),
    UInt32("maxdir"),
    UInt32("maxpos"),
    QStruct("e_life", INCLUDE=float_min_max),
    QStruct("p_life", INCLUDE=float_min_max),
    Pad(4*2),
    Float("e_angle"),
    SInt32("p_texcnt"),
    StrNntLatin1("p_texname", SIZE=32),
    QStruct("e_dir", INCLUDE=ijk_float),
    QStruct("e_vol", INCLUDE=xyz_float),
    QStruct("e_rate",
        Float("r0"),
        Float("r1"),
        Float("r2"),
        Float("r3"),
        ),
    Float("e_rate_rand"),
    Float("p_gravity"),
    Float("p_drag"),
    Float("p_speed"),
    Struct("p_color",
        QStruct("c0", INCLUDE=rgba_uint8),
        QStruct("c1", INCLUDE=rgba_uint8),
        QStruct("c2", INCLUDE=rgba_uint8),
        QStruct("c3", INCLUDE=rgba_uint8),
        ),
    QStruct("p_width",
        Float("w0"),
        Float("w1"),
        Float("w2"),
        Float("w3"),
        ),
    Float("e_delay"),
    Pad(4*3 + 4*4*6 + 4*3),
    UInt32("checksum"),  # TODO: figure out how this is calculated if necessary
    SIZE=312
    )

#############################
#  shared executable
#############################
secret_character_struct = Struct("secret_character",                         
    UEnum32("color", *PLAYER_COLORS),
    UEnum32("type", *PLAYER_TYPES),
    StrLatin1("code", SIZE=8, MAX=7),
    StrLatin1("directory", SIZE=16),
    Bool32("flags",
        "disable",
        ),
    SIZE=36, ENDIAN='<',
    )

cheat_struct = Struct("cheat",
    StrLatin1("code", SIZE=8, MAX=7),
    # NOTE: the type is a subset of the item_subtype enum
    #       with the invalid/unusable values removed
    UEnum32("type",
        Pad(1),
        "gold",
        "key",
        Pad(1),
        "potion",

        # these 3 utilize the below flags
        "weapon",
        "armor",
        Pad(2),
        "special",
        ),
    Float("add"),
    Union("flags",
        CASE='.type.enum_name',
        CASES=dict(
            gold=Void("flags"),
            key=Void("flags"),
            potion=Void("flags"),
            weapon=weapon_types,
            armor=armor_types,
            special=special_types,
            )
        ),
    SIZE=20, ENDIAN='<',
    )
