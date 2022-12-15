from supyr_struct.defs.tag_def import TagDef
from .objs.anim import AnimTag
from ..common_descs import *
from ..field_types import *

def get(): return anim_ps2_def

tanim_data = Struct("tanim_data",
    FloatArray("tpyr", SIZE=4*4),
    FloatArray("tpos", SIZE=4*4),
    FloatArray("tscale", SIZE=4*4),
    )

anim_seq_info = Struct("anim_seq_info",
    UInt16("type"),
    UInt16("size"),
    UInt32("animidx"),
    )

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
    )

anim_header = Struct("anim_header",
    Pointer32("comp_ang_pointer"),
    Pointer32("comp_pos_pointer"),
    Pointer32("comp_unit_pointer"),
    Pointer32("blocks_pointer"),
    Pointer32("sequence_info_pointer"),
    SInt32("sequence_count"),
    SInt32("object_count"),
    )

atree_header = Struct("atree_header",
    Pointer32("atreeseq_pointer"),
    Pointer32("animheader_pointer"),
    Pointer32("objanimheader_pointer"),
    Pointer32("anodeinfo_pointer"),
    SInt16("node_count"),
    SInt16("seq_count"),
    StrNntLatin1("prefix", SIZE=30),
    SInt16("model"),
    )

anode = Struct("anode",
    Pointer32("mbnode_pointer"),
    Pointer32("parent_anode_pointer"),
    Pointer32("child_anode_pointer"),
    Pointer32("next_anode_pointer"),
    QStruct("initpos", INCLUDE=xyz_float),
    SInt32("type"),
    SInt32("offset"),
    )

anim_info = Struct("anim_info",
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
    )

anode_info = Struct("anode_info",
    StrNntLatin1("mbdesc", SIZE=32),
    QStruct("initpos", INCLUDE=xyz_float),
    SInt16("type"),
    SInt16("flags"),
    UInt16("mbflags"),
    SInt32("offset"),
    SInt32("parentidx"),
    )

atree = Struct("atree",
    Pointer32("root_anode_pointer"),
    Struct("anim_info", INCLUDE=anim_info),
    SInt32("anode_count"),
    Pointer32("first_anode_pointer"),
    Pointer32("anodeinfo_pointer"),
    )

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
    UInt32("texaltidx"),
    SInt16("texchangeidx"),
    UInt8("texshiftidx"),
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
    )

atree_info = Struct("atree_info",
    StrNntLatin1("name", SIZE=32),
    SInt32("offset"),
    )

texmod = Struct("texmod",
    SInt16("atree"),
    SInt16("seqidx"),
    StrNntLatin1("name", SIZE=32),
    StrNntLatin1("sourcename", SIZE=32),
    SInt32("texidx"),
    SInt32("sourceidx"),
    SInt16("frame_count"),
    SInt16("startframe"),
    SInt32("rate"),
    SInt32("frame"),
    )

world_psys_flags = Bool32("flags",
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

world_psys_flag_enables = Bool32("flag_enables",
    INCLUDE=world_psys_flags
    )

world_psys_enables = Bool32("enables",
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


world_psys = Struct("world_psys",
    UInt32("version"),
    SInt16("preset"),
    SInt8("id"),
    SInt8("dummy"),
    world_psys_flags,
    world_psys_flag_enables,
    world_psys_enables,
    SInt32("maxp"),
    UInt32("maxdir"),
    UInt32("maxpos"),
    QStruct("e_lifefade", INCLUDE=float_lower_upper),
    QStruct("p_lifefade", INCLUDE=float_lower_upper),
    Pad(4*2),
    Float("e_angle"),
    SInt32("p_texcnt"),
    StrNntLatin1("p_texname", SIZE=32),
    QStruct("e_dir", INCLUDE=ijk_float),
    QStruct("e_vol", INCLUDE=xyz_float),
    QStruct("e_rate", INCLUDE=ijkw_float),
    Float("e_rate_rand"),
    Float("p_gravity"),
    Float("p_drag"),
    Float("p_speed"),
    Array("p_colors",
        QStruct("color", SUB_STRUCT=rgba_uint8),
        SIZE=4
        ),
    FloatArray("p_widths", SIZE=4*4),
    Float("e_delay"),
    Pad(4*3 + 4*4*6 + 4*3),
    UInt32("checksum"),
    )

atree_list_header_v0 = Struct("atree_list_header",
    Pointer32("atree_infos_pointer"),
    UInt16("texmod_count"),
    UInt16("texmod_pointer"),
    )

atree_list_header_v8 = Struct("atree_list_header",
    Pointer32("atree_infos_pointer"),
    UInt16("texmod_count"),
    UInt16("texmod_pointer"),
    UInt16("psys_count"),
    UInt16("psys_pointer"),
    )

anim_ps2_def = TagDef("anim",
    UInt16("atree_count"),
    UInt16("version", DEFAULT=8),
    Switch("atree_list_header",
        CASE=".version",
        CASES={
            0: atree_list_header_v0,
            8: atree_list_header_v8
            },
        ),
    ext=".ps2", endian="<", tag_cls=AnimTag
    )
