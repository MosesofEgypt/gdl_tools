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
ijk_float = QStruct("",
    Float("i"), Float("j"), Float("k"),
    ORIENT='h'
    )
pyr_float = QStruct("",
    Float("p"), Float("y"), Float("r"),
    ORIENT='h'
    )
ijkw_float = QStruct("",
    Float("i"), Float("j"), Float("k"), Float("w"),
    ORIENT='h'
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
item_type = SEnum32("item_type",
    ("random",      -1),
    ("powerup",     0x01),
    ("container",   0x02),
    ("generator",   0x03),
    ("enemy_info",  0x04),
    ("trigger",     0x05),
    ("trap",        0x06),
    ("door",        0x07),
    ("damage_tile", 0x08),
    ("exit",        0x09),
    ("obstacle",    0x0A),
    ("transporter", 0x0B),
    ("rotator",     0x0C),
    ("sound",       0x0D),
    )

item_subtype = SEnum32("item_subtype",
    ("none",       0x00),
    ("gold",       0x01),
    ("key",        0x02),
    ("food",       0x03),
    ("potion",     0x04),
    ("weapon",     0x05),
    ("armor",      0x06),
    ("speed",      0x07),
    ("magic",      0x08),
    ("special",    0x09),
    ("runestone",  0x0A),
    ("bosskey",    0x0B),
    ("obelisk",    0x0C),
    ("quest",      0x0D),
    ("scroll",     0x0E),
    ("gemstone",   0x0F),
    ("feather",    0x10),

    ("bridge_pad",          0x14),
    ("door_pad",            0x15),
    ("bridge_switch",       0x16),
    ("door_switch",         0x17),
    ("activator_switch",    0x18),
    ("elevator_pad",        0x19),
    ("elevator_switch",     0x1A),
    ("lift_pad",            0x1B),
    ("lift_start",          0x1C),
    ("lift_end",            0x1D),
    ("no_weapon_collider",  0x1E),
    ("shoot_trigger",       0x1F),

    ("rock_fall",       0x28),
    ("safe_rock",       0x29),
    ("wall",            0x2A),
    ("barrel",          0x2B),
    ("barrel_explode",  0x2C),
    ("barrel_poison",   0x2D),
    ("chest",           0x2E),
    ("chest_gold",      0x2F),
    ("chest_silver",    0x30),
    ("leaf_fall",       0x31),
    ("secret",          0x32),
    ("rock_fly",        0x33),
    ("shoot_fall",      0x34),
    ("rock_sink",       0x35),
    )

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

# NOTE: enum size not confirmed
camera_mode = SEnum8("mode",
    "off",
    "free",
    "lock",
    "game",
    "object_eye",
    "vector_distance",
    "point",
    "dragon",
    "chimera",
    "djinn",
    "drider",
    "demon",
    "boss",
    )

# NOTE: enum size not confirmed
attention_mode = SEnum8("mode",
    "free",
    "lock",
    "target",
    "object",
    "point",
    "player",
    "enemy",
    "item",
    "milestone",
    "lookout",
    "camera",
    )

# NOTE: enum size not confirmed
boss_camera_flags = Bool8("camera_flags",
    "track_boss",
    "stay_in_front",
    "stay_in_back",
    "watch_boss",
    "track_all",
    "watch_mode_2",
    "unused0",
    "unused1",
    "zoom_in",
    "zoom_out",
    )

# NOTE: enum size not confirmed
light_type = SEnum32("preset",
    ("point",       0x01),
    ("spot",        0x02),
    ("directional", 0x03),
    )

# NOTE: enum size not confirmed
texmod_type = UEnum8("preset",
    "unknown",
    "local",
    ("mip_blend",   0xFA),
    ("fade_out",    0xFB),
    ("fade_in",     0xFC),
    ("scroll_v",    0xFD),
    ("scroll_u",    0xFE),  # also "special"
    #("special",    0xFE),
    ("external",    0xFF),
    )

particle_system = Struct("particle_system",
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
    SInt8("id"),  # always in range [65, 85] ??
    SInt8("dummy", VISIBLE=False), # always 0
    particle_system_flags,
    particle_system_flag_enables,
    particle_system_enables,
    SInt32("maxp"),
    UInt32("maxdir"),
    UInt32("maxpos"),
    QStruct("e_lifefade", INCLUDE=float_min_max),
    QStruct("p_lifefade", INCLUDE=float_min_max),
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
    Struct("p_colors",
        QStruct("c0", INCLUDE=rgba_uint8),
        QStruct("c1", INCLUDE=rgba_uint8),
        QStruct("c2", INCLUDE=rgba_uint8),
        QStruct("c3", INCLUDE=rgba_uint8),
        ),
    QStruct("p_widths",
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
cheat_weapon_types = LBitStruct("weapon_types",
    UBitEnum("weapon_type",
        "normal",
        "fire",
        "elec",
        "light",
        "acid",
        SIZE=4,
        ),
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

cheat_armor_types = Bool32("armor_types",
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
    "immune_knockback",

    ("invulnerability_silver", 0x10000),
    ("invulnerability_gold",  0x100000),

    ("antideath",        0x80000),
    ("armor_reflect",    0x20000),
    ("armor_reflect2", 0x1000000),
    ("armor_fire",      0x200000),
    ("armor_elec",      0x400000),
    ("armor_protect",   0x800000),
    )

cheat_special_types = Bool32("special_types",
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
    Pad(1),
    "turbo",
    "mikey",
    "hand_of_death",
    "health_vampire",
    )

secret_character_struct = Struct("secret_character",                         
    UEnum32("color",
        "yellow",
        "blue",
        "red",
        "green"
        ),
    UEnum32("type",
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
        "hyena",
        ),
    StrLatin1("code", SIZE=8, MAX=7),
    StrLatin1("directory", SIZE=16),
    Bool32("flags",
        "disable",
        ),
    SIZE=36, ENDIAN='<',
    )

cheat_struct = Struct("cheat",
    StrLatin1("code", SIZE=8, MAX=7),
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
            gold=Bool32("flags"),
            key=Bool32("flags"),
            potion=Bool32("flags"),
            weapon=cheat_weapon_types,
            armor=cheat_armor_types,
            special=cheat_special_types,
            )
        ),
    SIZE=20, ENDIAN='<',
    )
