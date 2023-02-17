from supyr_struct.defs.tag_def import TagDef
from .objs.anim import AnimTag
from ..common_descs import *

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


def get_comp_scales_size(*args, parent=None, new_value=None, **kwargs):
    return 0 if (new_value or not parent) or parent.parent.comp_scale_pointer == 0 else 256 * 4

def texmod_case(parent=None, **kwargs):
    try:
        return "transform" if parent.type.source_index.idx < 0 else "source_index"
    except Exception:
        return "source_index"


obj_anim = Struct("obj_anim",
    StrNntLatin1("mb_desc", SIZE=32),
    SInt32("mb_index", DEFAULT=-1, VISIBLE=False), # always -1
    SInt16("frame_count"),
    SInt16("start_frame"),
    SIZE=40,
    )

anim_seq_info = Struct("anim_seq_info",
    Bool16("type",
        # these are the flags that are set across all animation files
        ("rot_x_data", 1<<0),
        ("rot_y_data", 1<<1),
        ("rot_z_data", 1<<2),

        ("pos_x_data", 1<<4),
        ("pos_y_data", 1<<5),
        ("pos_z_data", 1<<6),

        ("scale_x_data", 1<<8),
        ("scale_y_data", 1<<9),
        ("scale_z_data", 1<<10),

        # if uncompressed, framedata contains uncompressed floats. if not,
        # framedata is indices into the comp_angles/positions/scales arrays
        ("compressed_data", 1<<13),
        ("unknown", 1<<14), # seems to be completely independent of other flags
        ),
    UInt16("size"), # number of transform axis types(sum flag counts 0-9)
    UInt32("data_offset"),
    # NOTE: start of animation data is an array of bytes of length (frame_count+7)//8
    #       each bit indicates if there is framedata for that frame. If not, interpolate.
    #       framedata comes directly after bitfields array. data of all transform types
    #       is interleaved per frame(x,y,h,p,x,y,h,p,x,y,h,p...)
    SIZE=8
    )

anim_header = Struct("anim_header",
    Pointer32("comp_ang_pointer", VISIBLE=False),
    Pointer32("comp_pos_pointer", VISIBLE=False),
    Pointer32("comp_scale_pointer", VISIBLE=False),
    Pointer32("blocks_pointer", VISIBLE=False),
    Pointer32("sequence_info_pointer", VISIBLE=False),
    SInt32("sequence_count", EDITABLE=False, VISIBLE=False),
    SInt32("object_count", EDITABLE=False, VISIBLE=False),
    SIZE=28,
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
            ),
        Array("anim_seq_infos",
            SUB_STRUCT=anim_seq_info,
            SIZE=get_anim_seq_info_size,
            POINTER=lambda *a, **kw: get_atree_data_array_pointer(
                *a, pointer_field_names=[
                    ".....offset", "....anim_header_pointer", "..sequence_info_pointer"
                    ], **kw
                )
            )
        ),
        # TODO
        #UInt8Array("block_data",
        #    SIZE=get_block_data_size,
        #    POINTER=lambda *a, **kw: get_atree_data_array_pointer(
        #        *a, pointer_field_names=[
        #            ".....offset", "....anim_header_pointer", "...anim_header.blocks_pointer"
        #            ], **kw
        #        ),
        #    ),
    )

obj_anim_header = Struct("obj_anim_header",
    Pointer32("obj_anim_pointer", VISIBLE=False),
    SInt32("obj_anim_count", VISIBLE=False),
    SIZE=8,
    STEPTREE=Array("obj_anims",
        SUB_STRUCT=obj_anim, SIZE=".obj_anim_count",
        POINTER=lambda *a, **kw: get_atree_data_array_pointer(
            *a, pointer_field_names=[
                "....offset", "...obj_anim_header_pointer", ".obj_anim_pointer", 
                ], **kw
            ),
        DYN_NAME_PATH='.mb_desc', WIDGET=DynamicArrayFrame
        )
    )

atree_seq = Struct("atree_seq",
    StrNntLatin1("name", SIZE=32),
    SInt16("frame_count"),
    SInt16("frame_rate"),
    UEnum16("repeat",
        "no",
        "yes"
        ),
    SInt16("fix_pos", VISIBLE=False), # always 0
    SInt16("texmod_count"), # number of texmods starting at texmod_index to play together
    Bool16("flags",
        "play_reversed"  # applies to object and texmod animations
        ),
    SInt32("texmod_index", DEFAULT=-1),
    SIZE=48,
    )

anode_info = Struct("anode_info",
    StrNntLatin1("mb_desc", SIZE=32),
    QStruct("init_pos", INCLUDE=xyz_float),
    SEnum16("anim_type",
        "null",  # plain, hierarchial node
        "skeletal", # same as null, except can have animation node data(only type that can actually)
        "object", # attach object animation model.
        "texture",  # plays tex_anim on objects below this on a local timer
        "particle_system",
        ),
    Bool16("flags",
        "no_object_def" # seems to indicate that there is no object def to locate for this node
        #           always set for object, particle_system, and texture
        ),
    Bool32("mb_flags",
        # these are the flags that are set across all animation files
        # its possible for no flags to be set on all node types
        ("no_z_test",       1<<6),  # 0.79% of object, skeletal, and texture
        ("no_z_write",      1<<7),  # 9.19% of all anim types
        ("sort_alpha",      1<<11), # 13.20% of all anim types(set alone in null, object, skeletal, and texture)
        ("no_shading",      1<<12), # 15.32% of all anim types
        ("add_first",       1<<13), # 0.13% of object, skeletal, and texture

        ("chrome",          1<<15), # 1.62% of null and skeletal
        ("alpha_last",      1<<19), # 8.25% of all anim types

        # all flags below not set in particle system
        ("alpha_last_2",    1<<22), # 2.32% of all anim types
        ("fb_add",          1<<23), # 2.31% of all anim types

        ("front_face",      1<<24), # 1.02% of null, skeletal, and texture
        ("camera_dir",      1<<26), # 7.41% of all anim types
        ("top_face",        1<<27), # 0.17% of skeletal, and texture

        ("harden_a",        1<<29), # 0.01% of object
        ("fb_mul",          1<<30), # 0.007% of skeletal

        # some additional flags that overlap previous flags.
        # leaving them here commented out since they don't seem
        # to be accurate, but may prove useful in the future.
        #("object_lmap",     1<<13),
        #("object_o_chrome", 1<<17),
        #("object_t_chrome", 1<<19),
        #("object_keep_a",   1<<27),

        dict(NAME="color_obj",          VALUE=1<<8,  VISIBLE=False),  # IS NEVER SET
        dict(NAME="alpha_obj",          VALUE=1<<9,  VISIBLE=False),  # IS NEVER SET
        dict(NAME="dist_alpha",         VALUE=1<<10, VISIBLE=False),  # IS NEVER SET
        dict(NAME="temp_no_shade",      VALUE=1<<14, VISIBLE=False),  # IS NEVER SET
        dict(NAME="no_alpha_z_write",   VALUE=1<<16, VISIBLE=False),  # IS NEVER SET
        dict(NAME="car_body",           VALUE=1<<17, VISIBLE=False),  # IS NEVER SET
        dict(NAME="local_light",        VALUE=1<<18, VISIBLE=False),  # IS NEVER SET
        dict(NAME="dist_alpha_2",       VALUE=1<<20, VISIBLE=False),  # IS NEVER SET
        dict(NAME="no_filter",          VALUE=1<<21, VISIBLE=False),  # IS NEVER SET
        dict(NAME="front_dir",          VALUE=1<<25, VISIBLE=False),  # IS NEVER SET
        dict(NAME="tex_shift",          VALUE=1<<28, VISIBLE=False),  # IS NEVER SET
        dict(NAME="scrn_clip",          VALUE=1<<31, VISIBLE=False),  # IS NEVER SET
        ),
    # anim_seq_info_offset is a relative pointer into one of four different
    # arrays depending on the node type(skeletal, object, texture, particle_system)
    #   skeletal:       relative to atree_data.anim_header (points to an anim_seq_info struct)
    #   object:         relative to atree_data.obj_anim_header (points to an obj_anim struct)
    #   texture:        relative to atree_data.atree_sequences (points to a texmod struct)
    #   particle_sys:   relative to atree_data.atree_sequences (points to a particle_system struct)
    #   NOTE: still not sure how particle systems are specified for worlds
    SInt32("anim_seq_info_offset"),
    Computed("anim_seq_info_index", SIZE=0),
    SInt32("parent_index", DEFAULT=-1),
    SIZE=60,
    )


atree_data = Container("atree_data",
    Struct("anim_header",
        INCLUDE=anim_header_with_data,
        POINTER=lambda *a, **kw: get_atree_data_array_pointer(
            *a, pointer_field_names=["...offset", "..anim_header_pointer"], **kw
            ),
        ),
    Array("atree_sequences",
        SUB_STRUCT=atree_seq, SIZE="..atree_seq_count",
        POINTER=lambda *a, **kw: get_atree_data_array_pointer(
            *a, pointer_field_names=["...offset", "..atree_seq_pointer"], **kw
            ),
        DYN_NAME_PATH='.name', WIDGET=DynamicArrayFrame
        ),
    Array("anode_infos",
        SUB_STRUCT=anode_info, SIZE="..anode_count",
        POINTER=lambda *a, **kw: get_atree_data_array_pointer(
            *a, pointer_field_names=["...offset", "..anode_info_pointer"], **kw
            ),
        DYN_NAME_PATH='.mb_desc', WIDGET=DynamicArrayFrame
        ),
    Struct("obj_anim_header",
        INCLUDE=obj_anim_header,
        POINTER=lambda *a, **kw: get_atree_data_array_pointer(
            *a, pointer_field_names=["...offset", "..obj_anim_header_pointer"], **kw
            )
        ),
    )

atree_header = Struct("atree_header",
    Pointer32("atree_seq_pointer", VISIBLE=False),
    Pointer32("anim_header_pointer", VISIBLE=False),
    Pointer32("obj_anim_header_pointer", VISIBLE=False),
    Pointer32("anode_info_pointer", VISIBLE=False),
    SInt32("anode_count", VISIBLE=False),
    SInt32("atree_seq_count", VISIBLE=False),
    StrNntLatin1("prefix", SIZE=30),
    SInt16("model", VISIBLE=False), # always 0
    SIZE=56, POINTER=".offset", STEPTREE=atree_data
    )

atree_info = Struct("atree_info",
    StrNntLatin1("name", SIZE=32),
    SInt32("offset", VISIBLE=False),
    SIZE=36, STEPTREE=atree_header,
    )

texmod = Struct("texmod",
    SInt16("atree"),
    SInt16("seq_index"),
    StrNntLatin1("name", SIZE=32),
    StrNntLatin1("source_name", SIZE=32),
    SInt32("tex_index"),  # index of animated texture(empty nub)
    Union("type",
        CASES=dict(
            transform=SEnum32("transform",
                ("mip_blend",   -6),
                ("fade_out",    -5),
                ("fade_in",     -4),
                ("scroll_v",    -3),
                ("scroll_u",    -2),  # also "special"
                #("special",    -2),
                ("external",    -1),
                ),
            source_index=QStruct("source_index",
                SInt32("idx"), # index of the first texture in the sequence
                ),
            ),
        CASE=texmod_case
        ),
    SInt16("frame_count"),  # number of texture swap frames, or
                            # number of frames to complete one scroll.
                            # values < 0 mean scroll in opposite direction
    SInt16("start_frame"),  # unused?
    SInt32("frames_per_tex"),   # number of frames to display each texture before swap
                                # must be nonzero if texture swap animation
    SInt32("tex_start_frame"),  # texture swap frame to start on
    SIZE=88
    )

atree_list_header_v0 = Struct("atree_list_header",
    UInt32("texmod_count", VISIBLE=False),
    UInt32("texmod_pointer", VISIBLE=False),
    SIZE=12
    )

atree_list_header_v8 = Struct("atree_list_header",
    UInt32("texmod_count", VISIBLE=False),
    UInt32("texmod_pointer", VISIBLE=False),
    UInt32("particle_system_count", VISIBLE=False),
    UInt32("particle_system_pointer", VISIBLE=False),
    SIZE=20
    )

anim_ps2_def = TagDef("anim",
    UInt16("atree_count", VISIBLE=False),
    UEnum16("version",
        ("v0", 0),
        ("v8", 8),
        DEFAULT=8, EDITABLE=False
        ),
    Pointer32("atree_infos_pointer", VISIBLE=False),
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
        POINTER=".atree_infos_pointer",
        DYN_NAME_PATH='.name', WIDGET=DynamicArrayFrame
        ),
    Array("texmods",
        SUB_STRUCT=texmod,
        SIZE=".atree_list_header.texmod_count",
        POINTER=".atree_list_header.texmod_pointer",
        DYN_NAME_PATH='.name', WIDGET=DynamicArrayFrame
        ),
    Switch("particle_systems",
        CASE=".version.enum_name",
        CASES=dict(
            v8=Array("particle_systems",
                SUB_STRUCT=particle_system,
                SIZE=".atree_list_header.particle_system_count",
                POINTER=".atree_list_header.particle_system_pointer",
                DYN_NAME_PATH='.p_texname', WIDGET=DynamicArrayFrame
                ),
            )
        ),
    ext=".ps2", endian="<", tag_cls=AnimTag
    )
