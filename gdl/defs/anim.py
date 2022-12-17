from supyr_struct.defs.tag_def import TagDef
from .objs.anim import AnimTag
from ..common_descs import *
from ..field_types import *

def get(): return anim_ps2_def


def get_atree_data_array_pointer(
        *args, node=None, parent=None, new_value=None,
        pointer_field_names=None, **kwargs
        ):
    if parent is None:
        if not node:
            return 0
        parent = node.parent

    base_pointer = 0
    for i in range(len(pointer_field_names) - 1):
        base_pointer += parent.get_neighbor(pointer_field_names[i])

    if new_value is None:
        return parent.get_neighbor(pointer_field_names[-1]) + base_pointer

    parent.set_neighbor(pointer_field_names[-1], new_value - base_pointer)


def get_anim_seq_info_size(
        *args, node=None, parent=None, new_value=None,
        pointer_field_names=None, **kwargs
    ):
    if parent is None:
        if not node:
            return 0
        parent = node.parent

    parent = parent.parent
    if new_value is None:
        return parent.sequence_count * parent.object_count

def get_block_data_size(
        *args, node=None, parent=None, new_value=None,
        pointer_field_names=None, **kwargs
    ):
    if parent is None:
        if not node:
            return 0
        parent = node.parent

    parent = parent.parent
    if new_value is None:
        return parent.sequence_count * parent.object_count

def get_comp_angles_size(*args, parent=None, new_value=None, **kwargs):
    return 0 if (new_value or not parent) or parent.parent.comp_ang_pointer == 0 else 256 * 4


def get_comp_positions_size(*args, parent=None, new_value=None, **kwargs):
    return 0 if (new_value or not parent) or parent.parent.comp_pos_pointer == 0 else 256 * 4


def get_comp_units_size(*args, parent=None, new_value=None, **kwargs):
    return 0 if (new_value or not parent) or parent.parent.comp_unit_pointer == 0 else 256 * 4


obj_anim = Struct("obj_anim",
    StrNntLatin1("mb_desc", SIZE=32),
    SInt32("mb_index"),
    SInt16("frame_count"),
    SInt16("start_frame"),
    SIZE=40,
    )

anim_seq_info = Struct("anim_seq_info",
    UInt16("type"),
    UInt16("size"),
    UInt32("anim_index"),
    SIZE=8
    )

anim_header = Struct("anim_header",
    Pointer32("comp_ang_pointer"),
    Pointer32("comp_pos_pointer"),
    Pointer32("comp_unit_pointer"),
    Pointer32("blocks_pointer"),
    Pointer32("sequence_info_pointer"),
    SInt32("sequence_count"),
    SInt32("object_count"),
    SIZE=28,
    STEPTREE=Container("data",
        FloatArray("comp_angles",
            POINTER="..comp_ang_pointer", SIZE=get_comp_angles_size
            ),
        FloatArray("comp_positions",
            POINTER="..comp_pos_pointer", SIZE=get_comp_positions_size
            ),
        FloatArray("comp_units",
            POINTER="..comp_unit_pointer", SIZE=get_comp_units_size
            ),
        Array("anim_seq_infos",
            SUB_STRUCT=anim_seq_info,
            SIZE=get_anim_seq_info_size,
            POINTER=lambda *a, **kw: get_atree_data_array_pointer(
                *a, pointer_field_names=[
                    ".....offset", "....anim_header_pointer", "..sequence_info_pointer"
                    ], **kw
                ),
            ),
        ),
    )

obj_anim_header = Struct("obj_anim_header",
    Pointer32("obj_anim_pointer"),
    SInt32("obj_anim_count"),
    SIZE=8,
    STEPTREE=Array("obj_anims",
        SUB_STRUCT=obj_anim, SIZE=".obj_anim_count",
        POINTER=lambda *a, **kw: get_atree_data_array_pointer(
            *a, pointer_field_names=[
                "....offset", "...obj_anim_header_pointer", ".obj_anim_pointer", 
                ], **kw
            ),
        )
    )

atree_seq = Struct("atree_seq",
    StrNntLatin1("name", SIZE=32),
    SInt16("frame_count"),
    SInt16("frame_rate"),
    SInt16("repeat"),
    SInt16("fix_pos"),
    SInt16("texmod_count"),
    SInt16("flags"),
    SInt32("texmod_index"),
    SIZE=48,
    # TODO
    #STEPTREE=UInt8Array("block_data",
    #    SIZE=get_block_data_size,
    #    POINTER=lambda *a, **kw: get_atree_data_array_pointer(
    #        *a, pointer_field_names=[
    #            ".....offset", "....anim_header_pointer", "...anim_header.blocks_pointer"
    #            ], **kw
    #        ),
    #    ),
    )

anode_info = Struct("anode_info",
    StrNntLatin1("mb_desc", SIZE=32),
    QStruct("init_pos", INCLUDE=xyz_float),
    SInt16("type"),
    SInt16("flags"),
    UInt32("mb_flags"),
    SInt32("anim_seq_info_offset"),
    SInt32("parent_index"),
    SIZE=60,
    )

atree_data = Container("atree_data",
    Struct("anim_header",
        INCLUDE=anim_header,
        POINTER=lambda *a, **kw: get_atree_data_array_pointer(
            *a, pointer_field_names=["...offset", "..anim_header_pointer"], **kw
            ),
        ),
    Array("atree_sequences",
        SUB_STRUCT=atree_seq, SIZE="..atree_seq_count",
        POINTER=lambda *a, **kw: get_atree_data_array_pointer(
            *a, pointer_field_names=["...offset", "..atree_seq_pointer"], **kw
            ),
        ),
    Array("anode_infos",
        SUB_STRUCT=anode_info, SIZE="..anode_count",
        POINTER=lambda *a, **kw: get_atree_data_array_pointer(
            *a, pointer_field_names=["...offset", "..anode_info_pointer"], **kw
            ),
        ),
    Struct("obj_anim_header",
        INCLUDE=obj_anim_header,
        POINTER=lambda *a, **kw: get_atree_data_array_pointer(
            *a, pointer_field_names=["...offset", "..obj_anim_header_pointer"], **kw
            ),
        ),
    )

atree_header = Struct("atree_header",
    Pointer32("atree_seq_pointer"),
    Pointer32("anim_header_pointer"),
    Pointer32("obj_anim_header_pointer"),
    Pointer32("anode_info_pointer"),
    SInt32("anode_count"),
    SInt32("atree_seq_count"),
    StrNntLatin1("prefix", SIZE=30),
    SInt16("model"),
    SIZE=56, POINTER=".offset", STEPTREE=atree_data
    )

atree_info = Struct("atree_info",
    StrNntLatin1("name", SIZE=32),
    SInt32("offset"),
    SIZE=36, STEPTREE=atree_header,
    )

texmod = Struct("texmod",
    SInt16("atree"),
    SInt16("seq_index"),
    StrNntLatin1("name", SIZE=32),
    StrNntLatin1("source_name", SIZE=32),
    SInt32("tex_index"),
    SInt32("source_index"),
    SInt16("frame_count"),
    SInt16("start_frame"),
    SInt32("rate"),
    SInt32("frame"),
    SIZE=88
    )

atree_list_header_v0 = Struct("atree_list_header",
    UInt32("texmod_count"),
    UInt32("texmod_pointer"),
    SIZE=12
    )

atree_list_header_v8 = Struct("atree_list_header",
    UInt32("texmod_count"),
    UInt32("texmod_pointer"),
    UInt32("particle_system_count"),
    UInt32("particle_system_pointer"),
    SIZE=20
    )

anim_ps2_def = TagDef("anim",
    UInt16("atree_count"),
    UEnum16("version",
        ("v0", 0),
        ("v8", 8),
        DEFAULT=8
        ),
    Pointer32("atree_infos_pointer"),
    Switch("atree_list_header",
        CASE=".version.enum_name",
        CASES=dict(
            v0=atree_list_header_v0,
            v8=atree_list_header_v8
            ),
        ),
    Array("atrees",
        SUB_STRUCT=atree_info,
        SIZE=".atree_count",
        POINTER=".atree_infos_pointer"
        ),
    Array("texmods",
        SUB_STRUCT=texmod,
        SIZE=".atree_list_header.texmod_count",
        POINTER=".atree_list_header.texmod_pointer"
        ),
    Switch("particle_systems",
        CASE=".version.enum_name",
        CASES=dict(
            v8=Array("particle_systems",
                SUB_STRUCT=particle_system,
                SIZE=".atree_list_header.particle_system_count",
                POINTER=".atree_list_header.particle_system_pointer"
                ),
            )
        ),
    ext=".ps2", endian="<", tag_cls=AnimTag
    )
