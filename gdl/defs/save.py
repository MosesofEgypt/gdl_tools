from array import array

from supyr_struct.defs.tag_def import TagDef
from ..field_types import *
from ..common_descs import *
from .objs.save import GdlSaveTag

def get(): return gdl_savemeta_def

def levels_bool(name, count):
    bools = []
    for i in range(count-1):
        bools.append('level_%s_beaten'%(i+1))
    bools.append('bos_beaten')
    return Bool8(name, *bools)

help_disp_default = array('B', [0]*256)
for i in (0,1,2,6,7,8,11,15,16,17,20,21,22,27,28,32,35,37,
          41,42,44,45,48,51,53,58,60,61,67,82,83,87,88,92,
          102,110,111,113,125,126,130,132,134,135,137):
    help_disp_default[i] = 0x11

def make_name_map(suffix=''):
    name_map = {}
    for i in range(len(PLAYER_TYPES)):
        name_map[PLAYER_TYPES[i]+suffix] = i
    return name_map


p_attrs = QStruct('character_attrs',
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
    Float('total_playtime'),  # counted in frames?
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
    Float('attribute_add'),
    Union("flags",
        CASE='.type.enum_name',
        CASES=dict(
            none=Bool32("flags"),
            speed=Bool32("flags"),
            magic=Bool32("flags"),
            weapon=weapon_types,
            armor=armor_types,
            special=special_types,
            )
        ),
    SIZE=16,
    )

p_stuff = Container('character_stuff',
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
    #boss_attempts 1 and 2 are always 0 it seems, so rather
    #than have them editable, lets just treat them as padding
    #UInt16('boss_attempts_1'),
    #UInt16('boss_attempts_2'),
    Pad(4),

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
    Array('powerups', SUB_STRUCT=p_powerup, SIZE=32),
    UInt8Array('powerup_states', SIZE=32),
    SIZE=596,
    )


p_waves = Struct('levels',
    Pad(1),
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
    Bool8('unknown',
        'unknown0',
        'unknown1',
        'unknown2',
        'unknown3',
        'unknown4',
        'unknown5',
        'unknown6',
        'unknown7',
        ),
    Pad(1),
    )

gdl_savemeta_def = TagDef("save",
    BytesRaw('hmac_sig', SIZE=20, VISIBLE=False),
    Struct('save_data',
        StrLatin1('name', SIZE=7, DEFAULT='PLAYER'),
        Pad(1),
        SEnum16('last_alt_type',
            *PLAYER_TYPES,
            "sumner",
            ),
        SEnum8('last_color', *PLAYER_COLORS),
        SInt8('char_saved'),

        Bool16('class_unlocks',
            "minotaur",
            "falconess",
            "jackal",
            "tigress",
            "ogre",
            "unicorn",
            "medusa",
            "hyena",
            "sumner",
            ),
        UInt16('level_total'),
        
        Array('character_attrs',  SUB_STRUCT=p_attrs,
            SIZE=16, NAME_MAP=make_name_map('_attrs')),
        Array('character_stats',  SUB_STRUCT=p_stats,
            SIZE=16, NAME_MAP=make_name_map('_stats')),
        Array('character_stuff',  SUB_STRUCT=p_stuff,
            SIZE=16, NAME_MAP=make_name_map('_stuff')),
        Array('character_levels', SUB_STRUCT=p_waves,
            SIZE=16, NAME_MAP=make_name_map('_levels')),
        
        UEnum8('control_scheme',
            "ps2",
            "arcade",
            "robotron",
            "one_handed",
            ),
        UEnum8('rumble',
            "none",
            "light",
            "medium",
            "maximum",
            DEFAULT=2,
            ),
        UEnum8('auto_attack',
            "off",
            "on",
            DEFAULT=1,
            ),
        UEnum8('auto_aim',
            "off",
            "on",
            DEFAULT=1,
            ),
        #The only values that seem to be in the help_disp
        #array are either 0x00, 0x10, or 0x11.
        #
        #These might be enumerators designating the display
        #status of each help hint text(invisible, visible, seen)
        UInt8Array('help_disp', SIZE=256, DEFAULT=help_disp_default),
        ),

    ext=".xsv", endian='<', tag_cls=GdlSaveTag,
    )
