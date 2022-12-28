from supyr_struct.defs.tag_def import TagDef
from .objs.worlds import WorldsTag
from ..common_descs import *
from ..field_types import *

def get(): return worlds_ps2_def

world_object = Struct("world_object",
    StrNntLatin1("name", SIZE=16),
    Bool32("flags",
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
    SInt16("collision_triangle_count"),
    SInt32("collision_triangle_index"),
    SIZE=60
    )

worlds_header = Struct('header',
    UInt32("world_objects_count", EDITABLE=False, VISIBLE=False),
    Pointer32("world_objects_pointer", EDITABLE=False, VISIBLE=False),

    UInt32("coll_mesh_count", EDITABLE=False, VISIBLE=False),
    Pointer32("coll_mesh_pointer", EDITABLE=False, VISIBLE=False),

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

    UInt32("anim_header_offsetcount", EDITABLE=False, VISIBLE=False),
    UInt32("world_anim_count", EDITABLE=False, VISIBLE=False),
    Pointer32("world_anim_pointer", EDITABLE=False, VISIBLE=False),

    UInt32("world_particle_systems_count", EDITABLE=False, VISIBLE=False),
    Pointer32("world_particle_systems_pointer", EDITABLE=False, VISIBLE=False),
    SIZE=120
    )

worlds_ps2_def = TagDef("worlds",
    worlds_header,
    Array("world_objects",
        SUB_STRUCT=world_object,
        SIZE=".header.world_objects_count",
        POINTER=".header.world_objects_pointer",
        ),
    ext=".ps2", endian="<", tag_cls=WorldsTag, incomplete=True
    )
