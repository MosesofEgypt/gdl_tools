from supyr_struct.defs.tag_def import TagDef
from .objs.worlds import WorldsTag
from ..common_descs import *
from ..field_types import *

def get(): return worlds_ps2_def


def grid_entry_size(parent=None, **kwargs):
    try:
        return parent.header.grid_entry_count * 4
    except Exception:
        return 0

def item_info_data_case(parent=None, **kwargs):
    try:
        return "random" if parent.item_type.enum_name == "" else "normal"
    except Exception:
        return None

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

trigger_info = QStruct("trigger_info",
    SInt16("target_world_object_index"),
    SInt16("flags"),
    UInt8("rad"),
    SInt8("sound_id"),
    SInt8("id"),
    SInt8("next_id"),
    SInt16("start_y"),
    SInt16("end_y"),
    SIZE=12
    )

enemy_info = QStruct("enemy_info",
    SInt16("strength"),
    SInt16("ai"),
    Float("rad"),
    SInt16("interval"),
    SInt16("dummy"),
    SIZE=12
    )

generator_info = QStruct("generator_info",
    SInt16("strength"),
    SInt16("ai"),
    SInt16("max_enemies"),
    SInt16("interval"),
    SIZE=8
    )

exit_info = Struct("exit_info",
    SInt32("next"),
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
    SInt32("music_area"),
    SInt16("fade"),
    SInt16("flags"),
    SIZE=12
    )

obstacle_info = QStruct("obstacle_info",
    SInt16("subtype"),
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
    SInt8("flags"),
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
    SEnum16("col_type",
        "none",
        "cylinder",
        "sphere",
        "box",
        "object",
        ("null", -1),
        ),
    SInt16("col_flags"),
    Float("radius"),
    Float("height"),
    Float("x_dim"),
    Float("z_dim"),
    QStruct("col_offset", INCLUDE=xyz_float),
    StrNntLatin1("name", SIZE=16),
    Bool32("mb_flags",
        *(("unknown%s" % i, 1 << i) for i in range(32))
        ),
    UInt32("properties"),
    SInt16("value"),
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
        *((f"unknown{i}", 1<<i) for i in range(32))
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

# related to pathfinding and item placement?
grid_row = Struct("grid_row",
    # debug symbols say first and last are unsigned, but i've seen -1 and -2 as values
    SInt16("first"),
    SInt16("last"),
    UInt32("offset"),
    SIZE=8
    )

grid_list = Struct("grid_entry",
    )

locator_type = SEnum8("type",
    ("camera_start",    0x01),
    ("camera_game",     0x02),
    ("camera_attract_start", 0x03),
    ("camera_attract",  0x04),
    ("milestone",       0x05),
    ("boss",            0x06),
    ("start",           0x07),
    ("sentry",          0x08),
    ("trigger_camera",  0x09),
    ("event",           0x0A),
    )

locator = Struct("locator",
    locator_type,
    UInt8("unknown0"),
    UInt16("unknown1"),
    QStruct("pos", INCLUDE=xyz_float),
    QStruct("rot", INCLUDE=pyr_float),
    SIZE=28
    )

worlds_header = Struct('header',
    UInt32("world_objects_count", EDITABLE=False, VISIBLE=False),
    Pointer32("world_objects_pointer", EDITABLE=False, VISIBLE=False),

    UInt32("coll_tri_count", EDITABLE=False, VISIBLE=False),
    Pointer32("coll_tri_pointer", EDITABLE=False, VISIBLE=False),

    UInt32("grid_entry_count", EDITABLE=False, VISIBLE=False),
    Pointer32("grid_entry_pointer", EDITABLE=False, VISIBLE=False),

    UInt32("grid_list_entry_count", EDITABLE=False, VISIBLE=False),
    Pointer32("grid_list_pointer", EDITABLE=False, VISIBLE=False),
    Pointer32("grid_row_pointer", EDITABLE=False, VISIBLE=False),

    QStruct("world_min_bounds", INCLUDE=xyz_float),
    QStruct("world_max_bounds", INCLUDE=xyz_float),

    Float("grid_size", VISIBLE=False),
    UInt32("grid_number_x", EDITABLE=False),
    UInt32("grid_number_y", EDITABLE=False),

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

    UInt32("animation_headers_offset", EDITABLE=False, VISIBLE=False),
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
        ),
    # each grid_entry is a count offset
    #UInt32Array("grid_entries",
    #    SIZE=grid_entry_size,
    #    POINTER=".header.grid_entry_pointer",
    #    ),
    Array("grid_rows",
        SUB_STRUCT=grid_row,
        SIZE=".header.grid_number_y",
        POINTER=".header.grid_row_pointer",
        ),
    Array("coll_tris",
        SUB_STRUCT=coll_tri,
        SIZE=".header.coll_tri_count",
        POINTER=".header.coll_tri_pointer",
        ),
    Array("items_infos",
        SUB_STRUCT=item_info,
        SIZE=".header.item_info_count",
        POINTER=".header.item_info_pointer",
        ),
    Array("item_instances",
        SUB_STRUCT=item_instance,
        SIZE=".header.item_instance_count",
        POINTER=".header.item_instance_pointer",
        ),
    Array("locators",
        SUB_STRUCT=locator,
        SIZE=".header.locator_count",
        POINTER=".header.locator_pointer",
        ),
    #Array("animations",
    #    SUB_STRUCT=????,
    #    SIZE=".header.animations_count",
    #    POINTER=".header.animations_pointer",
    #    ),
    Array("particle_systems",
        SUB_STRUCT=particle_system,
        SIZE=".header.particle_systems_count",
        POINTER=".header.particle_systems_pointer",
        ),
    ext=".ps2", endian="<", tag_cls=WorldsTag, incomplete=True
    )
