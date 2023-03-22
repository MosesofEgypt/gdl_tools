from supyr_struct.defs.tag_def import TagDef
from .objs.texdef import TexdefPs2Tag
from ..common_descs import *
from ..compilation.g3d.constants import *

def get(): return texdef_ps2_def

bitmap_format = UEnum8("format",
    # NOTE: the NGC formats are some custom format that swaps
    #       between A1R5G5B5 and A4R4G4B4, depending on if the
    #       high bit is set. If set, it's A1; otherwise its A4
    (PIX_FMT_ABGR_1555, 0),
    (PIX_FMT_XBGR_1555, 1),
    (PIX_FMT_ABGR_8888, 2),
    (PIX_FMT_XBGR_8888, 3),
    #all these below formats are palettized
    (PIX_FMT_ABGR_1555_IDX_4, 16),
    (PIX_FMT_XBGR_1555_IDX_4, 17),
    (PIX_FMT_ABGR_3555_IDX_4_NGC, 18),
    (PIX_FMT_ABGR_8888_IDX_4, 34),
    (PIX_FMT_XBGR_8888_IDX_4, 35),
    (PIX_FMT_ABGR_1555_IDX_8, 48),
    (PIX_FMT_XBGR_1555_IDX_8, 49),
    (PIX_FMT_ABGR_3555_IDX_8_NGC, 50),
    #(PIX_FMT_IDXA_88,         56), #i have no idea how this format works
    (PIX_FMT_ABGR_8888_IDX_8, 66),
    (PIX_FMT_XBGR_8888_IDX_8, 67),
    (PIX_FMT_A_8_IDX_8, 130),
    (PIX_FMT_I_8_IDX_8, 131),
    (PIX_FMT_A_4_IDX_4, 146),
    (PIX_FMT_I_4_IDX_4, 147)
    )

bitmap_block = Struct("bitmap",
    UEnum32("version",
        ("v23", 0xF00B0017),
        DEFAULT=0xF00B0017, EDITABLE=False
        ),
    Bool16("flags",
        # checked every other bit in every texdef in
        # in the ps2 game files, and no other flag
        # is set. this is all of them that are used
        ("halfres",   0x0001),
        ("clamp_u",   0x0040),
        ("clamp_v",   0x0080),
        ("has_alpha", 0x0100),
        EDITABLE=False
        ),
    Pad(2),

    bitmap_format,
    Pad(1),
    UInt8("mipmap_count", EDITABLE=False),
    SInt8("lod_k"),
    UInt16("width", EDITABLE=False),
    UInt16("height", EDITABLE=False),

    Pointer32("tex_pointer", EDITABLE=False),
    UInt32("size"),
    Pad(40),

    SIZE=64
    )

header = Struct('header',
    UInt32("bitmaps_count", EDITABLE=False, VISIBLE=False),
    Pointer32("bitmap_defs_pointer", VISIBLE=False),
    Pointer32("bitmaps_pointer", VISIBLE=False),
    SIZE=12
    )
   
bitmap_def = Struct("bitmap_def",
    StrNntLatin1("name", SIZE=30),
    SEnum16("def_in_objects",
        # Whether or not there is a matching bitmap_def struct
        # in the bitmap_defs array in the objects tag.
        ("yes",  0),
        ("no",  -1),
        ),
    UInt16("width"),
    UInt16("height"),
    SIZE=36
    )

texdef_ps2_def = TagDef("texdef",
    header,
    Array("bitmap_defs",
        SIZE='.header.bitmaps_count',
        POINTER='.header.bitmap_defs_pointer',
        SUB_STRUCT=bitmap_def,
        DYN_NAME_PATH='.name', WIDGET=DynamicArrayFrame
        ),
    Array("bitmaps",
        SIZE='.header.bitmaps_count',
        POINTER='.header.bitmaps_pointer',
        SUB_STRUCT=bitmap_block
        ),

    endian="<", ext=".ps2", tag_cls=TexdefPs2Tag
    )
