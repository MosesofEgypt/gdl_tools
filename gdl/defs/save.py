from array import array

from supyr_struct.defs.tag_def import TagDef
from ..common_descs import *
from .objs.save import GdlXboxSaveTag, GdlPs2SaveTag, GdlNgcSaveTag

def get():
    return gdl_xbox_save_def, gdl_ps2_save_def, gdl_ngc_save_def

def levels_bool(name, count):
    bools = []
    for i in range(count):
        bools.append('wave_%s_beaten'%(i+1))
    return Bool8(name, *bools)

#The only values that seem to be in the help_disp
#array are either 0x00, 0x10, or 0x11.
#
#These might be enumerators designating the display
#status of each help hint text(invisible, visible, seen)
xbox_help_disp_default = array('B', [0]*256)
for i in (0,1,2,6,7,8,11,15,16,17,20,21,22,27,28,32,35,37,
          41,42,44,45,48,51,53,58,60,61,67,82,83,87,88,92,
          102,110,111,113,125,126,130,132,134,135,137):
    xbox_help_disp_default[i] = 0x11

def make_name_map(suffix=''):
    name_map = {}
    for i in range(len(PLAYER_TYPES)):
        name_map[PLAYER_TYPES[i]+suffix] = i
    return name_map


p_attrs = Struct('character_attrs',
    SInt32('exp', GUI_NAME='experience'),
    Float('health'),
    Float('strength_added'),
    Float('armor_added'),
    Float('magic_added'),
    Float('speed_added'),
    SIZE=24,
    )

p_stats = QStruct('character_stats',
    SInt32('enemies_killed'),
    SInt32('generals_killed'),
    SInt32('golems_killed'),
    SInt32('bosses_killed'),
    SInt32('generators_destroyed'),
    SInt32('gold_found'),
    Float('total_playtime', UNIT_SCALE=1/(30*60), SIDETIP="minutes"),
    SIZE=28,
    )

p_powerup = Struct('character_powerup',
    Float('time_left'),
    # NOTE: the type is a subset of the item_subtype enum
    #       with the invalid/unusable values removed
    SEnum32('type',
        "none",
        Pad(4),
        "weapon",
        "armor",
        "speed",
        "magic",
        "special",
        ),
    Float('add'),
    Union("flags",
        CASE='.type.enum_name',
        CASES=dict(
            none=Bool32("flags"),
            speed=Bool32("flags"),
            magic=Bool32("flags"),
            weapon=weapon_types,
            armor=armor_types,
            special=special_types,
            ),
        SIZE=4
        ),
    SIZE=16,
    )

p_stuff = (
    SInt16('potions', MIN=0, MAX=9),
    SInt16('keys', MIN=0, MAX=9),
    Bool16('shards', *BOSS_KEYS),
    Bool16('runes', *RUNESTONES),
    Bool16('legend_items', *LEGEND_ITEMS),
    SInt16('powerup_count'),

    Bool16('rune_attempts_sp', *RUNESTONES),
    Bool16('rune_attempts_mp', *RUNESTONES),
    Bool16('legend_attempts_sp', *LEGEND_ITEMS),
    Bool16('legend_attempts_mp', *LEGEND_ITEMS),
    # boss_attempts 1 and 2 are always 0 it seems
    UInt16('boss_attempts_1'),
    UInt16('boss_attempts_2'),

    QStruct('gargoyle_items',
        # a value of -1 means all that the max amount have been collected
        SInt16('fangs'),
        SInt16('feathers'),
        SInt16('claws'),
        ),
    Pad(2),#the shell3d.pdb lied about this padding. it tried to say
    #       that it's after the crystals, not before it. it isn't.
    QStruct('crystals',
        # a value of -1 means all that the max amount have been collected
        SInt16('town'),
        SInt16('mountain'),
        SInt16('castle'),
        SInt16('sky'),
        SInt16('forest'),
        SInt16('desert'),
        SInt16('ice'),
        SInt16('dream'),
        ),
    UInt32('gold'),
    )

p_stuff_ps2 = Container('character_stuff',
    *p_stuff,
    Array('powerups', SUB_STRUCT=p_powerup, SIZE=8),
    SIZE=180,
    )

p_stuff_ngc = Container('character_stuff',
    *p_stuff,
    Array('powerups', SUB_STRUCT=p_powerup, SIZE=11),
    UInt8Array('powerup_states', SIZE=11),
    Pad(1),
    SIZE=240,
    )

p_stuff_xbox = Container('character_stuff',
    *p_stuff,
    Array('powerups', SUB_STRUCT=p_powerup, SIZE=32),
    UInt8Array('powerup_states', SIZE=32),
    SIZE=596,
    )


p_waves = Struct('levels',
    levels_bool('test_realm',3),
    levels_bool('castle_realm',6),
    levels_bool('mountain_realm',6),
    levels_bool('desert_realm',5),
    levels_bool('forest_realm',5),
    levels_bool('temple',2),
    levels_bool('underworld',2),
    levels_bool('town_realm',5),
    levels_bool('battlefields',4),
    levels_bool('ice_realm',5),
    levels_bool('dream_realm',6),
    levels_bool('sky_realm',5),
    levels_bool('secret_realm', 8),
    levels_bool('tower_realm', 3),
    SIZE=14
    )

last_character_type = SEnum16('last_character_type',
    *PLAYER_TYPES,
    "sumner",
    )
class_unlocks = Bool16('class_unlocks',
    "minotaur",
    "falconess",
    "jackal",
    "tigress",
    "ogre",
    "unicorn",
    "medusa",
    "hyena",
    "sumner",
    )
control_scheme = UEnum8('control_scheme',
    "ps2",
    "arcade",
    "robotron",
    "one_handed",
    )
rumble = UEnum8('rumble',
    "none",
    "light",
    "medium",
    "maximum",
    DEFAULT=2,
    )
auto_attack = UEnum8('auto_attack',
    "off",
    "on",
    DEFAULT=1,
    )
auto_aim = UEnum8('auto_aim',
    "off",
    "on",
    DEFAULT=1,
    )

xbox_save_data = Struct('save_data',
    StrLatin1('name', SIZE=7, DEFAULT='Empty'),
    Pad(1),
    last_character_type,
    SEnum8('last_color', *PLAYER_COLORS),
    SInt8('char_saved'),

    class_unlocks,
    UInt16('level_total'),
    
    Array('attributes',
        SUB_STRUCT=p_attrs,
        SIZE=16,
        NAME_MAP=make_name_map('_attrs')
        ),
    Array('statistics',
        SUB_STRUCT=p_stats,
        SIZE=16,
        NAME_MAP=make_name_map('_stats')
        ),
    Array('inventory',
        SUB_STRUCT=p_stuff_xbox,
        SIZE=16,
        NAME_MAP=make_name_map('_stuff')
        ),
    Array('waves',
        SUB_STRUCT=p_waves,
        SIZE=16,
        NAME_MAP=make_name_map('_waves')
        ),
    control_scheme,
    rumble,
    auto_attack,
    auto_aim,
    UInt8Array('help_disp',
        SIZE=256, DEFAULT=xbox_help_disp_default, VISIBLE=False
        ),
    )

ps2_save_data = Struct('save_data',
    StrLatin1('name', SIZE=7, DEFAULT='Empty'),
    Pad(1),
    last_character_type,
    SEnum8('last_color', *PLAYER_COLORS),
    SInt8('char_saved'),

    class_unlocks,
    UInt16('level_total'),

    Array('attributes',
        SUB_STRUCT=p_attrs,
        SIZE=16,
        NAME_MAP=make_name_map('_attrs')
        ),
    Array('statistics',
        SUB_STRUCT=p_stats,
        SIZE=16,
        NAME_MAP=make_name_map('_stats')
        ),
    Array('inventory',
        SUB_STRUCT=p_stuff_ps2,
        SIZE=16,
        NAME_MAP=make_name_map('_stuff')
        ),
    Array('waves',
        SUB_STRUCT=p_waves,
        SIZE=16,
        NAME_MAP=make_name_map('_waves')
        ),
    control_scheme,
    rumble,
    auto_attack,
    auto_aim,
    UInt8Array('help_disp', SIZE=256, VISIBLE=False),
    )

ngc_save_data = Struct('save_data',
    StrLatin1('name', SIZE=7, DEFAULT='Empty'),
    Pad(1),
    last_character_type,
    SEnum8('last_color', *PLAYER_COLORS),
    SInt8('char_saved'),

    class_unlocks,
    UInt16('level_total'),

    Array('attributes',
        SUB_STRUCT=p_attrs,
        SIZE=16,
        NAME_MAP=make_name_map('_attrs')
        ),
    Array('statistics',
        SUB_STRUCT=p_stats,
        SIZE=16,
        NAME_MAP=make_name_map('_stats')
        ),
    Array('inventory',
        SUB_STRUCT=p_stuff_ngc,
        SIZE=16,
        NAME_MAP=make_name_map('_stuff')
        ),
    Array('waves',
        SUB_STRUCT=p_waves,
        SIZE=16,
        NAME_MAP=make_name_map('_waves')
        ),
    control_scheme,
    rumble,
    auto_attack,
    auto_aim,
    UInt8Array('help_disp', SIZE=256, VISIBLE=False),
    )

ngc_icon_format = UBitEnum("icon_format",
    "none",
    "ci8_shared",
    "rgb5a3",
    "ci8_unique",
    SIZE=2, DEFAULT=2
    )

ngc_icon_speed = UBitEnum("icon_speed",
    "none",
    "four_frames",
    "eight_frames",
    "twelve_frames",
    SIZE=2, DEFAULT=2
    )

ngc_gci_header = Struct("gci_header",
    StrNntLatin1("game_code", SIZE=4, DEFAULT="GUNE"),
    StrNntLatin1("maker_code", SIZE=2, DEFAULT="5D"),
    SInt8("unused0", DEFAULT=-1, VISIBLE=False),
    BitStruct("banner_format",
        ngc_icon_format,
        SIZE=1
        ),
    StrNntLatin1("filename",
        DEFAULT="Gauntlet - Dark Legacy", SIZE=32
        ),
    UInt32("mod_time"),
    Pointer32("image_offset", DEFAULT=64),
    BitStruct("icon_formats",
        UBitEnum("icon_0_format", INCLUDE=ngc_icon_format),
        UBitEnum("icon_1_format", INCLUDE=ngc_icon_format),
        UBitEnum("icon_2_format", INCLUDE=ngc_icon_format),
        UBitEnum("icon_3_format", INCLUDE=ngc_icon_format),
        UBitEnum("icon_4_format", INCLUDE=ngc_icon_format),
        UBitEnum("icon_5_format", INCLUDE=ngc_icon_format),
        UBitEnum("icon_6_format", INCLUDE=ngc_icon_format),
        UBitEnum("icon_7_format", INCLUDE=ngc_icon_format),
        SIZE=2
        ),
    BitStruct("icon_speeds",
        UBitEnum("icon_0_speed", INCLUDE=ngc_icon_speed),
        UBitEnum("icon_1_speed", INCLUDE=ngc_icon_speed),
        UBitEnum("icon_2_speed", INCLUDE=ngc_icon_speed),
        UBitEnum("icon_3_speed", INCLUDE=ngc_icon_speed),
        UBitEnum("icon_4_speed", INCLUDE=ngc_icon_speed),
        UBitEnum("icon_5_speed", INCLUDE=ngc_icon_speed),
        UBitEnum("icon_6_speed", INCLUDE=ngc_icon_speed),
        UBitEnum("icon_7_speed", INCLUDE=ngc_icon_speed),
        SIZE=2
        ),
    Bool8("permissions",
        ("public", 0x04),
        ("no_copy", 0x08),
        ("no_move", 0x10),
        DEFAULT=0x04
        ),
    UInt8("copy_counter"),
    UInt16("first_block"),
    UInt16("block_count", DEFAULT=8),
    SInt16("unused1", DEFAULT=-1, VISIBLE=False),
    Pointer32("comments_offset"),
    SIZE=64, VISIBLE=False
    )

# used in gamecube and ps2(is separate file for PS2)
game_options = Struct("game_options",
    # WHAT ARE THOSE?!?!?!?!
    UInt32("unknown0", DEFAULT=128),
    UInt32("unknown1", DEFAULT=128),
    UInt32("unknown2", DEFAULT=1),
    UInt32("unknown3", DEFAULT=0),
    UInt32("unknown4", DEFAULT=0),
    UInt32("unknown5", DEFAULT=1),
    UInt32("unknown6", DEFAULT=0),
    UInt32("unknown7", DEFAULT=0),
    SIZE=32, VISIBLE=False
    )

integrity_header = Container("integrity_header",
    UInt16("zero", SIZE=2, DEFAULT=0),
    UInt16("checksum", SIZE=2),
    StrNntLatin1("integrity", SIZE=4, DEFAULT="OKAY"),
    SIZE=8, VISIBLE=False
    )

dir_info = Struct("dir_info",
    SInt32("level_total"),
    SEnum32('last_character_type',
        *PLAYER_TYPES,
        "sumner",
        ),
    StrNntLatin1("name", SIZE=8),
    SIZE=16
    )

ngc_comments = Container("comments",
    StrNntLatin1("comment_1",
        DEFAULT="Gauntlet Dark Legacy", SIZE=32
        ),
    StrNntLatin1("comment_2",
        DEFAULT="Gauntlet Save Data", SIZE=32
        ),
    VISIBLE=False,
    )

ngc_banner_data = BytesRaw("banner_data",
    SIZE=96*32*2, VISIBLE=False, # TEMPORARY SIZE HACK
    )

ngc_icon_data = Container("icon_data",
    # TEMPORARY SIZE HACKS
    BytesRaw("icon_0_data", SIZE=32*32*2),
    BytesRaw("icon_1_data", SIZE=32*32*2),
    BytesRaw("icon_2_data", SIZE=32*32*2),
    BytesRaw("icon_3_data", SIZE=32*32*2),
    BytesRaw("icon_4_data", SIZE=32*32*2),
    BytesRaw("icon_5_data", SIZE=32*32*2),
    BytesRaw("icon_6_data", SIZE=32*32*2),
    BytesRaw("icon_7_data", SIZE=32*32*2),
    VISIBLE=False,
    )

gdl_xbox_save_def = TagDef("xbox_save",
    BytesRaw('hmac_sig', SIZE=20, VISIBLE=False),
    xbox_save_data,
    ext=".xsv", endian='<', tag_cls=GdlXboxSaveTag,
    )

gdl_ps2_save_def = TagDef("ps2_save",
    ps2_save_data,
    ext="", endian='<', tag_cls=GdlPs2SaveTag,
    )

gdl_ngc_save_def = TagDef("ngc_save",
    ngc_gci_header,
    Container("gci_block_data",
        ngc_comments,
        ngc_banner_data,
        ngc_icon_data,
        Container("save_data",
            integrity_header,
            game_options,
            Array("saves",
                SUB_STRUCT=ngc_save_data,
                SIZE=8, DYN_NAME_PATH='.name', WIDGET=DynamicArrayFrame
                ),
            Array("dir_infos",
                SUB_STRUCT=dir_info, VISIBLE=False,
                SIZE=8, DYN_NAME_PATH='.name', WIDGET=DynamicArrayFrame
                ),
            ),
        Pad(1400),
        ),
    ext=".gci", endian='>', tag_cls=GdlNgcSaveTag,
    )
