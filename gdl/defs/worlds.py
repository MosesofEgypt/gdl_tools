from supyr_struct.defs.tag_def import TagDef
from .objs.worlds import WorldsTag
from ..common_descs import *
from ..field_types import *
from .anim import anim_seq_info, anim_header, \
     get_comp_angles_size, get_comp_positions_size, get_comp_scales_size

def get(): return worlds_ps2_def


def item_info_data_case(parent=None, **kwargs):
    try:
        return "random" if parent.item_type.enum_name == "random" else "normal"
    except Exception:
        return None


def uint16_array_size(parent=None, **kwargs):
    try:
        return parent.size * 2
    except Exception:
        return 0

def dynamic_grid_object_indices_array_size(parent=None, **kwargs):
    try:
        return parent.header.size * 2
    except Exception:
        return 0


def grid_entry_size(parent=None, **kwargs):
    try:
        return max(0, (parent.last - parent.first) + 1)
    except Exception:
        return 0


def grid_entry_pointer(parent=None, **kwargs):
    try:
        return parent.parent.parent.header.grid_entry_pointer + parent.offset * 4
    except Exception:
        return 0


def grid_entry_list_pointer(parent=None, **kwargs):
    try:
        return parent.parent.parent.parent.parent.header.grid_list_pointer + parent.header.offset
    except Exception:
        return 0


def grid_list_indices_pointer(parent=None, **kwargs):
    try:
        return parent.parent.header.grid_list_pointer + parent.header.offset
    except Exception:
        return 0


coll_tri = Struct("coll_tri",
    SInt16("min_y"),  # unknown purpose(runtime optimization?)
    SInt16("max_y"),  # unknown purpose(runtime optimization?)
    Float("scale"),  # equal to 1 / sqrt(norm.i^2 + norm.k^2))
                     # can be used to normalize normal vector
                     # into a 2d unit vector in the x/z plane
    QStruct("norm", INCLUDE=ijk_float),
    QStruct("v0", INCLUDE=xyz_float),
    SInt16("v1_x"),
    SInt16("v1_z"),
    SInt16("v2_x"),
    SInt16("v2_z"),
    SIZE=40
    )

container_info = QStruct("container_info",
    SInt32("item_index"),
    SInt16("value"),
    SIZE=8
    )

trigger_info = Struct("trigger_info",
    SInt16("target_world_object_index"),
    Bool16("flags",
        # all flags below have been set on activator_switch
        ("unknown0", 1<<0),
        ("unknown1", 1<<1),  # set on lift_end, elevator_switch, shoot_trigger
        ("unknown2", 1<<2),
        ("unknown5", 1<<5),
        ("unknown6", 1<<6),
        ("unknown8", 1<<8),  # set on lift_end, elevator_switch, lift_pad
        ("unknown10", 1<<10), # set on lift_end, elevator_switch, shoot_trigger
        ("unknown12", 1<<12),
        ("unknown13", 1<<13),
        ),
    UInt8("rad"),
    SInt8("sound_id"),
    SInt8("id"),
    SInt8("next_id"),
    SInt16("start_y"),
    SInt16("end_y"),
    SIZE=12
    )

enemy_info = QStruct("enemy_info",
    SInt16("strength"), # seen set to 0, 1, 2, 3, 4, 5, 6
    #   set to 0 for red death, and 2 for black
    SInt16("ai"),  # seen set to: 0, 3, 7, 15, 16, 17, 18, 19, 23, 26, 27
    #   set to 3 for death
    Float("rad"),
    SInt16("interval"),
    SInt16("dummy"),
    SIZE=12
    )

generator_info = QStruct("generator_info",
    # NOTE: item_subtype is set to "special" for the generators
    #       that spawn every grunt enemy type in the game
    SInt16("strength"),  # set to 2 for special
    #                      otherwise always set to 1, 2, 3
    SInt16("ai"),  # set to 0 or 7 for special
    #                otherwise set to 0, 2, 4, 7, 14, 28, 29, 30
    SInt16("max_enemies"),
    SInt16("interval"),
    SIZE=8
    )

exit_info = Struct("exit_info",
    # NOTES:
    #   If the "name" field is not null, it will be used as the name
    #   of the level to load if "next" is set to "no". Otherwise, the
    #   current levels name will be incremented(ex: G1 to G2) and the
    #   level with that name will be loaded.
    #   Additionally, the subtype of the secret levels will be set to "special"
    UEnum32("next",
        "no",
        "yes"
        ),
    StrNntLatin1("name", SIZE=4),
    SIZE=8
    )

teleporter_info = QStruct("teleporter_info",
    SInt32("id"),
    SInt32("dest_id"),
    SIZE=8
    )

rotator_info = QStruct("rotator_info",
    SInt32("target_world_object_index"),
    Float("speed"),
    Float("delta"),
    SIZE=12
    )

sound_info = QStruct("sound_info",
    Float("radius"),
    SInt32("music_area"), # set to 0, 1, 2, 3, 4, 5, 6, 7, 8
    SInt16("fade"),  # set to 0, 1, 2, 3
    SInt16("flags"), # always zero in serialized form
    SIZE=12
    )

obstacle_info = Struct("obstacle_info",
    obstacle_subtype,
    SInt16("strength"),
    SIZE=4
    )

powerup_info = QStruct("powerup_info",
    SInt16("value"),
    SIZE=2
    )

trap_info = QStruct("trap_info",
    SInt16("damage"),
    SInt16("interval"),
    SIZE=4
    )

item_instance = Struct("item_instance",
    SInt16("item_index"),
    SInt8("min_players"),
    Bool8("flags",
        # NOTE: might map to COLNODE_FLAG?
        # only 3 flags set across all files
        "unknown0", # settable on container, damage_tile, enemy, 
        #             generator, obstacle, powerup, and trigger
        # unknown1 seems to indicate the object is invisible until destroyed?
        # see this video and watch for the destroyed generator that appears:
        #   https://youtu.be/NFHoL4RCm60?t=83
        #   this is item instance 123 in LEVELG2
        "unknown1", # settable on generator, powerup, rotator, and trigger
        "unknown2", # settable on obstacle
        ),
    SInt16("coll_tri_index"),
    SInt16("coll_tri_count"),
    StrNntLatin1("name", SIZE=16),
    QStruct("pos", INCLUDE=xyz_float),
    QStruct("rot", INCLUDE=pyr_float),
    Union("params",
        CASES=dict(
            container_info=container_info,
            trigger_info=trigger_info,
            enemy_info=enemy_info,
            generator_info=generator_info,
            exit_info=exit_info,
            teleporter_info=teleporter_info,
            rotator_info=rotator_info,
            sound_info=sound_info,
            obstacle_info=obstacle_info,
            powerup_info=powerup_info,
            trap_info=trap_info,
            ),
        SIZE=12
        ),
    SIZE=60,
    )


item_info_data = Struct("item_info_data",
    item_subtype,
    SEnum16("coll_type",
        "none",
        "cylinder",
        "sphere",
        "box",
        "object",
        ("null", -1),
        ),
    Bool16("coll_flags",
        # yes, only one flag.
        # only set on sound, damage_tile, obstacle, trigger, and rotator types
        "unknown",  # seems to indicate colliding with the item
        #             triggers it to do something(set on sound
        #             colliders and certain proximity based traps)
        # NOTE: might map to COLNODE_FLAG
        ),
    Float("radius"),
    Float("height"),
    Float("x_dim"),
    Float("z_dim"),
    QStruct("coll_offset", INCLUDE=xyz_float),
    StrNntLatin1("name", SIZE=16),
    Bool32("mb_flags",
        # only a single flag, and only set on damage tiles
        # (specifically only FLAMEV, FLAMEH, FORCEF, and FORCEF_S)
        ("unknown", 0x8000),
        ),
    Union("properties",
        # NOTE: only used for powerups and damage tiles
        CASES=dict(
            potion=damage_type,
            damage_tile=damage_type,
            weapon=weapon_types,
            armor=armor_types,
            special=special_types,
            ),
        SIZE=4
        ),
    Union("value",
        CASES=dict(
            # NOTE: only used for powerups and damage tiles
            # NOTE: "amount" is used in the following subtypes:
            #       food, key, gold, potion, special, speed, weapon
            crystal=UEnum16("crystal", *CRYSTAL_TYPES),
            gargoyle_item=UEnum16("gargoyle_item", *GARGOYLE_ITEMS),
            legend_item=UEnum16("legend_item", *LEGEND_ITEMS),
            runestone=UEnum16("runestone", *RUNESTONES),
            amount=QStruct("amount", SInt16("value")),
            ),
        SIZE=2
        ),
    SInt16("armor"),
    SInt16("hit_points"),
    SInt16("active_type"),
    SInt16("active_off"),
    SInt16("active_on"),
    Pointer32("atree_header_pointer"),
    SIZE=76
    )

random_item_info = Struct("random_item_info",
    SInt32("item_count"),
    SInt16Array("indices", SIZE=2*16),
    SIZE=36,
    )

item_info = Struct("item_info",
    item_type,
    Switch("data",
        CASES=dict(
            normal=item_info_data,
            random=random_item_info,
            ),
        CASE=item_info_data_case,
        SIZE=60,
        ),
    SIZE=80,
    )

# NOTE: it appears that non-lightmapped objects should be rendered
# in additive mode. objects without lightmaps in E1 are the ones that
# normally appear transparent(columns, light rays, door frame, etc)
world_object = Struct("world_object",
    StrNntLatin1("name", SIZE=16),
    # NOTE: seems there's such a thing as "dynamic parent" world objects
    Bool32("flags",
        # flag1: unknown purpose. set on most surfaces
        # flag2: appears to be set(mostly) on floors(walkable floor?)
        # flag4: almost never set(2 faces set in E1)
        # flag5: set on slanted walkable surfaces(walkable slope?)
        # flag6: same as flag4
        # flag9: same as flag4
        # flag11: set on invisible sconce fire(trigger collision/particle death plane?)
        # flag12: parent-relative position(possibly for animation?)
        # flag13: same as flag12
        # flag14: same as flag4
        # flag15: rarely set(set on chandalier in E1, debris in A1, gargoyle
        #         wings, carpet, and player clip in L1, some floors in D1,
        #         elevator clip in G1). seems to be animated player clip
        # flag16: same as flag4
        # flag19: same as flag4
        # flag21: same as flag4
        # flag22: same as flag4
        # flag24: rarely set(seems to be movable collision)
        # flag25: same as flag4
        # flag26: same as flag4
        # flag29: same as flag4
        # flag30: same as flag4
        *((f"unknown{i}", 1<<i) for i in range(12)),
        ("animated_collision", 1<<12),
        *((f"unknown{i}", 1<<i) for i in range(13,32))
        ),
    SEnum16("trigger_type"),
    SEnum8("trigger_state"),
    SEnum8("p_trigger_state"),

    Pointer32("parent_object_pointer"),
    QStruct("pos", INCLUDE=xyz_float),

    Pointer32("mbnode_pointer"),
    SInt16("next_index"),
    SInt16("child_index"),

    Float("radius"),
    SInt8("checked"),
    SInt8("no_collision"),
    SInt16("coll_tri_count"),
    SInt32("coll_tri_index"),
    SIZE=60
    )

grid_entry_list = Container("grid_entry_list",
    UInt16("collision_object_index"),
    UInt16("size", VISIBLE=False, EDITABLE=False),
    #Array("indices",
    #    SUB_STRUCT=QStruct("idx", UInt16("idx")),
    #    SIZE=".size"
    #    ),
    # NOTE: this is quite puzzling..... vast majority of the time this is only
    #       a few entries, and the entry values themselves don't go very high.
    #       vast majority of the time the entry values themselves are single digits.
    #       number doesn't match up with dynamic object count(sometimes higher or lower).
    #       the numbers seen seem to be contiguous, but this isn't confirmed.
    #       lower numbers more common, but number value not linearly linked to commonality
    UInt16Array("indices", SIZE=uint16_array_size)
    )

grid_entry_header = BitStruct("header",
    UBitInt("offset", SIZE=22),
    UBitInt("size",  SIZE=10),
    SIZE=4, VISIBLE=False, EDITABLE=False,
    )

grid_entry = Struct("grid_entry",
    grid_entry_header,
    STEPTREE=Array("grid_entry_list",
        SUB_STRUCT=grid_entry_list,
        SIZE=".header.size", POINTER=grid_entry_list_pointer
        )
    )

# gridrows seem to be used for determining what world
# objects to consider when calculating collisions.
# NOTE: grid x and z numbers match the width and length of
#       the worlds bounds divided by the gridsize, rounded up
grid_row = QStruct("grid_row",
    # first and last are grid cell indices. if the grid row is an
    # entire row, then first and last define the first and last cell
    # in the row. A grid translates directly into 3d space using the
    # world min and max bounds defined in the world header.
    UInt16("first"),
    UInt16("last"),
    UInt32("offset", VISIBLE=False, EDITABLE=False),
    SIZE=8,
    STEPTREE=Array("grid_entries",
        SUB_STRUCT=grid_entry,
        POINTER=grid_entry_pointer,
        SIZE=grid_entry_size,
        )
    )

locator_type = SEnum8("type",
    "none",
    "camera_start",
    "camera_game",
    "camera_attract_start",
    "camera_attract",
    "milestone",
    "boss",
    "start",
    "sentry",
    "trigger_camera",
    "event",
    )

locator = Struct("locator",
    locator_type,
    UInt8("delay"),
    UInt16("next"),
    QStruct("pos", INCLUDE=xyz_float),
    QStruct("rot", INCLUDE=pyr_float),
    SIZE=28
    )

anim_header_with_data = Struct("anim_header",
    INCLUDE=anim_header,
    STEPTREE=Container("data",
        FloatArray("comp_angles",
            POINTER="..comp_ang_pointer", SIZE=get_comp_angles_size
            ),
        FloatArray("comp_positions",
            POINTER="..comp_pos_pointer", SIZE=get_comp_positions_size
            ),
        FloatArray("comp_scales",
            POINTER="..comp_scale_pointer", SIZE=get_comp_scales_size
            )
        )
    )

world_animation = Struct("world_animation",
    SInt16("world_object_index"),
    SInt16("frame_count"),
    Bool16("flags",
        *((f"unknown{i}", 1<<i) for i in range(16))
        ),
    SInt16("state"),
    Float("frame"),
    Pointer32("seq_info_pointer"),

    SIZE=16,
    STEPTREE=Struct("anim_seq_info",
        INCLUDE=anim_seq_info, POINTER=".seq_info_pointer"
        )
    )

world_anims = Container("world_anims",
    Struct("header",
        INCLUDE=anim_header_with_data,
        POINTER="..header.animation_header_offset"
        ),
    Array("animations",
        SUB_STRUCT=world_animation,
        SIZE="..header.animations_count",
        POINTER="..header.animations_pointer",
        DYN_NAME_PATH='.world_object_index', WIDGET=DynamicArrayFrame
        ),
    )

worlds_header = Struct('header',
    UInt32("world_objects_count", EDITABLE=False, VISIBLE=False),
    Pointer32("world_objects_pointer", EDITABLE=False, VISIBLE=False),

    UInt32("coll_tri_count", EDITABLE=False, VISIBLE=False),
    Pointer32("coll_tri_pointer", EDITABLE=False, VISIBLE=False),

    UInt32("grid_entry_count", EDITABLE=False, VISIBLE=False),
    Pointer32("grid_entry_pointer", EDITABLE=False, VISIBLE=False),

    UInt32("grid_list_value_count", EDITABLE=False, VISIBLE=False),  # always 0
    Pointer32("grid_list_pointer", EDITABLE=False, VISIBLE=False),
    Pointer32("grid_row_pointer", EDITABLE=False, VISIBLE=False),

    QStruct("world_min_bounds", INCLUDE=xyz_float),
    QStruct("world_max_bounds", INCLUDE=xyz_float),

    Float("grid_size", VISIBLE=False),
    UInt32("grid_number_x", EDITABLE=False),
    UInt32("grid_number_z", EDITABLE=False),

    UInt32("item_info_count", EDITABLE=False, VISIBLE=False),
    Pointer32("item_info_pointer", EDITABLE=False, VISIBLE=False),

    UInt32("item_instance_count", EDITABLE=False, VISIBLE=False),
    Pointer32("item_instance_pointer", EDITABLE=False, VISIBLE=False),

    UInt32("locator_count", EDITABLE=False, VISIBLE=False),
    Pointer32("locator_pointer", EDITABLE=False, VISIBLE=False),

    UEnum32("world_format",
        ("v2", 0xF00BAB02),
        DEFAULT=0xF00BAB02, EDITABLE=False
        ),

    UInt32("animation_header_offset", EDITABLE=False, VISIBLE=False),
    UInt32("animations_count", EDITABLE=False, VISIBLE=False),
    Pointer32("animations_pointer", EDITABLE=False, VISIBLE=False),

    UInt32("particle_systems_count", EDITABLE=False, VISIBLE=False),
    Pointer32("particle_systems_pointer", EDITABLE=False, VISIBLE=False),
    SIZE=120
    )

worlds_ps2_def = TagDef("worlds",
    worlds_header,
    Array("world_objects",
        SUB_STRUCT=world_object,
        SIZE=".header.world_objects_count",
        POINTER=".header.world_objects_pointer",
        DYN_NAME_PATH='.name', WIDGET=DynamicArrayFrame
        ),
    Struct("dynamic_grid_objects",
        grid_entry_header,
        # indices of world objects that can move
        POINTER=".header.grid_entry_pointer",
        STEPTREE=UInt16Array("world_object_indices",
            SIZE=dynamic_grid_object_indices_array_size,
            POINTER=grid_list_indices_pointer
            ),
        #STEPTREE=Array("world_object_indices",
        #    SUB_STRUCT=QStruct("idx", UInt16("idx")),
        #    SIZE=".header.size",
        #    POINTER=grid_list_indices_pointer
        #    ),
        ),
    Array("grid_rows",
        SUB_STRUCT=grid_row,
        SIZE=".header.grid_number_z",
        POINTER=".header.grid_row_pointer",
        ),
    Array("coll_tris",
        SUB_STRUCT=coll_tri,
        SIZE=".header.coll_tri_count",
        POINTER=".header.coll_tri_pointer",
        ),
    Array("item_infos",
        SUB_STRUCT=item_info,
        SIZE=".header.item_info_count",
        POINTER=".header.item_info_pointer",
        DYN_NAME_PATH='.item_type.enum_name', WIDGET=DynamicArrayFrame
        ),
    Array("item_instances",
        SUB_STRUCT=item_instance,
        SIZE=".header.item_instance_count",
        POINTER=".header.item_instance_pointer",
        DYN_NAME_PATH='.item_index', WIDGET=DynamicArrayFrame
        ),
    Array("locators",
        SUB_STRUCT=locator,
        SIZE=".header.locator_count",
        POINTER=".header.locator_pointer",
        DYN_NAME_PATH='.type.enum_name', WIDGET=DynamicArrayFrame
        ),
    Array("particle_systems",
        SUB_STRUCT=particle_system,
        SIZE=".header.particle_systems_count",
        POINTER=".header.particle_systems_pointer",
        DYN_NAME_PATH='.p_texname', WIDGET=DynamicArrayFrame
        ),
    Switch("world_anims",
        CASE=".header.animations_count",
        CASES={ 0: Void("world_anims") },
        DEFAULT=world_anims
        ),
    ext=".ps2", endian="<", tag_cls=WorldsTag, incomplete=True
    )
