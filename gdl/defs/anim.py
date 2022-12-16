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
        if node:
            parent = node.parent
        else:
            return 0

    base_pointer = 0
    for i in range(len(pointer_field_names) - 1):
        base_pointer += parent.get_neighbor(pointer_field_names[i])

    if new_value is None:
        return parent.get_neighbor(pointer_field_names[-1]) + base_pointer

    parent.set_neighbor(pointer_field_names[-1], new_value - base_pointer)


def get_comp_angles_size(*args, parent=None, new_value=None, **kwargs):
    return 0 if (new_value or not parent) or parent.parent.comp_ang_pointer == 0 else 256 * 4


def get_comp_positions_size(*args, parent=None, new_value=None, **kwargs):
    return 0 if (new_value or not parent) or parent.parent.comp_pos_pointer == 0 else 256 * 4


def get_comp_units_size(*args, parent=None, new_value=None, **kwargs):
    return 0 if (new_value or not parent) or parent.parent.comp_unit_pointer == 0 else 256 * 4
    


# necessary?
mbnode = Struct("mbnode",
    Array("mats",
        SUB_STRUCT=QStruct("mat", INCLUDE=ijkw_float),
        SIZE=4
        ),
    QStruct("scale", INCLUDE=ijkw_float),
    UInt16("id"),
    SInt8("type"),
    UInt8("alpha"),
    Float("zsort_add"),
    UInt32("tex_alt_index"),
    SInt16("tex_change_index"),
    UInt8("tex_shift_index"),
    UInt8("extra_byte"),
    UInt32("flags"),
    UInt32("color"),
    SInt16("zmod"),
    SInt16("ambient_add"),
    UInt32("index"),
    QStruct("data",
        Pointer32("romobject_pointer"),
        Pointer32("polyheader_pointer"),
        Pointer32("blitinst_pointer"),
        Pointer32("psys_pointer"),
        ),
    Pointer32("parent_mbnode_pointer"),
    Pointer32("child_mbnode_pointer"),
    Pointer32("next_mbnode_pointer"),
    SIZE=128
    )

# necessary?
tanim_data = Struct("tanim_data",
    FloatArray("tpyr", SIZE=4*4),
    FloatArray("tpos", SIZE=4*4),
    FloatArray("tscale", SIZE=4*4),
    SIZE=48
    )

# necessary?
anim_data = Struct("anim_data",
    Pointer32("anim_seq_info_pointer"),
    SInt32("used"),
    SInt16("pidx"),
    SInt16("nidx"),
    SInt32("keycount"),
    FloatArray("ppyr",   SIZE=4*4),
    FloatArray("npyr",   SIZE=4*4),
    FloatArray("xpyr",   SIZE=4*4),
    FloatArray("ppos",   SIZE=4*4),
    FloatArray("npos",   SIZE=4*4),
    FloatArray("xpos",   SIZE=4*4),
    FloatArray("pscale", SIZE=4*4),
    FloatArray("nscale", SIZE=4*4),
    FloatArray("xscale", SIZE=4*4),
    SIZE=160
    )

# necessary?
anim_info = QStruct("anim_info",
    Pointer32("atreeseq_pointer"),
    Pointer32("animheader_pointer"),
    Pointer32("objanimheader_pointer"),
    SInt16("seq_count"),
    SInt16("anim_seq"),
    SInt16("frame_count"),
    SInt8("setp_anim"),
    UInt8("flags"),
    Float("trans_frac"),
    Float("frame"),
    SInt16("animseq0"),
    SInt16("active"),
    Float("start_time"),
    Float("trans_time"),
    Float("anim_scale"),
    Float("seq_scale"),
    Float("atime"),
    SInt16("repeat"),
    UInt16("stage"),
    SIZE=56
    )

# necessary?
atree = Struct("atree",
    Pointer32("root_anode_pointer"),
    QStruct("anim_info", INCLUDE=anim_info),
    SInt32("anode_count"),
    Pointer32("first_anode_pointer"),
    Pointer32("anodeinfo_pointer"),
    SIZE=76
    )

anode = Struct("anode",
    Pointer32("mb_node_pointer"),
    Pointer32("parent_anode_pointer"),
    Pointer32("child_anode_pointer"),
    Pointer32("next_anode_pointer"),
    QStruct("init_pos", INCLUDE=xyz_float),
    SInt32("type"),
    SInt32("offset"),  # TODO
    SIZE=36
    )



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
    Pointer32("blocks_pointer"),  # TODO
    Pointer32("sequence_info_pointer"),
    SInt32("sequence_count"),
    SInt32("object_count"),  # TODO
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
        # TODO
        #Array("sequences",
        #    SUB_STRUCT=anim_seq_info, SIZE="..sequence_count",
        #    POINTER=lambda *a, **kw: get_atree_data_array_pointer(
        #        *a, pointer_field_names=[
        #            ".....offset", "....anim_header_pointer", "..sequence_info_pointer"
        #            ], **kw
        #        ),
        #    ),
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
    SInt16("texmod_count"),  # TODO
    SInt16("flags"),
    SInt32("texmod_pointer"),  # TODO
    SIZE=48
    )

anode_info = Struct("anode_info",
    StrNntLatin1("mb_desc", SIZE=32),
    QStruct("init_pos", INCLUDE=xyz_float),
    SInt16("type"),
    SInt16("flags"),
    UInt32("mb_flags"),
    SInt32("offset"),  # add to anim_header.blocks_pointer maybe?
    SInt32("parent_index"),
    SIZE=60,
    # TODO
    #STEPTREE=Struct("anode",
    #    INCLUDE=anode,
    #    POINTER=lambda *a, **kw: get_atree_data_array_pointer(
    #        *a, pointer_field_names=[
    #            "..anim_header_pointer", ".offset",
    #            ], **kw
    #        ),
    #    ),
    )

atree_data = Container("atree_data",
    Struct("anim_header",
        INCLUDE=anim_header,
        POINTER=lambda *a, **kw: get_atree_data_array_pointer(
            *a, pointer_field_names=["...offset", "..anim_header_pointer"], **kw
            ),
        ),
    Struct("obj_anim_header",
        INCLUDE=obj_anim_header,
        POINTER=lambda *a, **kw: get_atree_data_array_pointer(
            *a, pointer_field_names=["...offset", "..obj_anim_header_pointer"], **kw
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
    UInt32("psys_count"),
    UInt32("psys_pointer"),
    SIZE=20
    )

anim_ps2_def = TagDef("anim",
    UInt16("atree_count"),
    UInt16("version", DEFAULT=8),
    Pointer32("atree_infos_pointer"),
    Switch("atree_list_header",
        CASE=".version",
        CASES={
            0: atree_list_header_v0,
            8: atree_list_header_v8
            },
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
    Switch("psys",
        CASE=".version",
        CASES={
            8: Array("psys",
                SUB_STRUCT=psys_struct,
                SIZE=".atree_list_header.psys_count",
                POINTER=".atree_list_header.psys_pointer"
                ),
            }
        ),
    ext=".ps2", endian="<", tag_cls=AnimTag
    )
