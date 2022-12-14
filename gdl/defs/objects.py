from supyr_struct.defs.tag_def import TagDef
from supyr_struct.defs.common_descs import *
from ..field_types import *
from .objs.objects import ObjectsPs2Tag
from .texdef import bitmap_format as bitmap_format_v12

def get(): return objects_ps2_def

# normals are compressed as 1555 with the most significant bit
# reserved to mean whether or not the face should be created.

object_flags = Bool32("flags",
    ("alpha",     0x01),
    ("v_normals", 0x02),
    ("v_colors",  0x04),
    ("mesh",      0x08),
    ("tex2",      0x10),
    ("lmap",      0x20),

    ("sharp",  0x040),
    ("blur",   0x080),
    ("chrome", 0x100),

    ("error",  0x200),
    ("sort_a", 0x400),
    ("sort",   0x800),

    {NAME:"pre_lit",  VALUE:0x010000, DEFAULT:True},
    {NAME:"lmap_lit", VALUE:0x020000, DEFAULT:True},
    {NAME:"norm_lit", VALUE:0x030000, DEFAULT:True},
    {NAME:"dyn_lit",  VALUE:0x100000, DEFAULT:False},
    )

bitmap_format_v4 = UEnum8("format",
    #these formats are palettized
    ("ABGR_8888_IDX_8", 3),
    ("ABGR_1555_IDX_8", 5),
    )

bitmap_flags_v4 = Bool8("flags",
    ("see_alpha", 0x01),
    )

bitmap_flags_v12 = Bool16("flags",
    ("halfres",   0x0001),
    ("see_alpha", 0x0002),
    ("clamp_u",   0x0004),
    ("clamp_v",   0x0008),
    ("animation", 0x0010),
    ("external",  0x0020),
    ("tex_shift", 0x0040),
    ("has_alpha", 0x0080),
    ("invalid",   0x0100),
    ("dual_tex",  0x0200),
    )

sub_object_model = Container("sub_object_model",
    UInt16("qword_count"),
    BytesRaw("unknown", SIZE=6, DEFAULT=b'\x00\x60\x00\x00\x00\x00'),

    BytesRaw('data', SIZE=qword_size),

    ALIGN=4,
    )

v12_sub_object_block = QStruct("sub-object",
    #number of 16 byte chunks that the subobject model consists of.
    UInt16("qword_count", GUI_NAME="quadword count"),

    #tex_index is simply the texture index that the subobject uses.
    UInt16("tex_index",   GUI_NAME="texture index"),

    #Not sure about lm_index. Might be the texture index of the
    #greyscale lightmap that the object uses for the luminance.
    UInt16("lm_index",    GUI_NAME="light map index"),
    )

v4_sub_object_block = QStruct("sub_object",
    UInt16("tex_index",   GUI_NAME="texture index"),
    UInt16("lm_index",    GUI_NAME="light map index"),
    )

#Multiple sub-objects are for things where you may have multiple
#textures on one mesh. In that case each subobject would have one texture.
v13_sub_object_block = QStruct("sub_object",
    UInt16("qword_count", GUI_NAME="quadword count"),
    UInt16("tex_index",   GUI_NAME="texture index"),
    UInt16("lm_index",    GUI_NAME="light map index"),

    #Not sure how the lod_k works, but it is 0 for empty objects.
    #Maybe the higher it is, the smaller the model must be to disappear.
    #Value is definitely signed. Don't know why though
    SInt16("lod_k",       GUI_NAME="lod coefficient"),
    )

v4_object_block = Struct("object",
    Float("inv_rad"),
    Float("bnd_rad"),
    Pad(4),
    SInt32('sub_objects_count', EDITABLE=False),
    Pointer32('sub_object_models_pointer', EDITABLE=False),
    Struct("sub_object_0", INCLUDE=v4_sub_object_block),
    SInt32("vert_count"),  # exactly the number of unique verts
    SInt32("tri_count"),  # exactly the number of unique triangles
    SInt32("id_num"),
    Pad(28),

    SIZE=64,
    STEPTREE=Container("data",
        Array("sub_object_models",
              SIZE="..sub_objects_count", SUB_STRUCT=sub_object_model,
              POINTER="..sub_object_models_pointer"),
        )
    )

v12_object_block = Struct("object",
    Float("inv_rad"),
    Float("bnd_rad"),
    object_flags,

    SInt32('sub_objects_count', EDITABLE=False),
    Struct("sub_object_0", INCLUDE=v13_sub_object_block),

    Pointer32('sub_objects_pointer', EDITABLE=False),
    Pointer32('sub_object_models_pointer', EDITABLE=False),

    SInt32("vert_count"),  # exactly the number of unique verts
    SInt32("tri_count"),  # exactly the number of unique triangles
    SInt32("id_num"),

    #pointer to the obj def that this model uses
    #doesnt seem to be used, so ignore it
    Pad(4),#LPointer32("obj_def"),
    Pad(16),

    SIZE=64,
    STEPTREE=Container("data",
        Array("sub_objects",
              SIZE=sub_objects_size, SUB_STRUCT=v12_sub_object_block,
              POINTER="..sub_objects_pointer"),
        Array("sub_object_models",
              SIZE="..sub_objects_count", SUB_STRUCT=sub_object_model,
              POINTER="..sub_object_models_pointer"),
        )
    )


v13_object_block = Struct("object",
    INCLUDE=v12_object_block,
    STEPTREE=Container("data",
        Array("sub_objects",
              SIZE=sub_objects_size, SUB_STRUCT=v13_sub_object_block,
              POINTER="..sub_objects_pointer"),
        Array("sub_object_models",
              SIZE="..sub_objects_count", SUB_STRUCT=sub_object_model,
              POINTER="..sub_object_models_pointer"),
        )
    )

# For tex0_struct and mip_tbp_struct, the following references were used:
#   https://openkh.dev/common/tm2.html
#   https://psi-rockin.github.io/ps2tek/
pixel_storage_modes = (
    ("psmct32",   0), #  RGBA32
    ("psmct24",   1), #  RGB24
    ("psmct16",   2), #  RGBA16
    ("psmct16s", 10), #  RGBA16 signed
    )

tex0_struct = BitStruct("tex0",
    UBitInt("tb_addr",  SIZE=14),  # base pointer in words/64(i.e. 256-byte chunks)
    UBitInt("tb_width", SIZE=6),   # texture buffer width in pixels/64
    UBitEnum("psm",
        *pixel_storage_modes,
        ("psmt8",    19), #  8-bit indexed(4 pixels per 32 bits)
        ("psmt4",    20), #  4-bit indexed(8 pixels per 32 bits)
        ("psmt8h",   27), #  like PSMT8, but upper 24 bits unused
        ("psmt4hl",  26), #  like PSMT4, but upper 24 bits are discarded
        ("psmt4hh",  44), #  like PSMT4, but lower 4 and upper 24 bits are discarded
        ("psmz32",   48), #  32-bit Z buffer
        ("psmz24",   49), #  24-bit Z buffer in 32-bit(upper 8-bit unused)
        ("psmz16",   50), #  16-bit Z buffer in 32-bit(2 pixels)
        ("psmz16s",  58), #  16-bit signed Z buffer in 32-bit(2 pixels)
        SIZE=6
        ),
    UBitInt("tex_width",  SIZE=4),  # log2 of width
    UBitInt("tex_height", SIZE=4),  # log2 of height
    UBitEnum("tex_cc",
        "rgb",
        "rgba",
        SIZE=1
        ),
    UBitEnum("tex_function",
        "modulate",
        "decal",
        "hilight",
        "hilight_2",
        SIZE=2
        ),
    UBitInt("cb_addr", SIZE=14),  # palette pointer in words/64(i.e. 256-byte chunks)
    UBitEnum("clut_pixmode",
        *pixel_storage_modes,
        SIZE=4
        ),
    UBitEnum("clut_smode",
        "csm1",  # swizzled every 32 bytes
        "csm2",  # unswizzled
        SIZE=1
        ),
    UBitInt("clut_offset", SIZE=5), # offset/16
    UBitEnum("clut_loadmode",
        "dont_recache",
        "recache",
        "recache_and_copy_clut_to_cbp0",
        "recache_and_copy_clut_to_cbp1",
        "recache_and_copy_clut_to_cbp0_if_cb_addr_changed",
        "recache_and_copy_clut_to_cbp1_if_cb_addr_changed",
        SIZE=3, DEFAULT=1
        ),
    SIZE=8, VISIBLE=False
    )

mip_tbp_struct = BitStruct("mip_tbp",
    UBitInt("tb_addr1",  SIZE=14),
    UBitInt("tb_width1", SIZE=6),
    UBitInt("tb_addr2",  SIZE=14),
    UBitInt("tb_width2", SIZE=6),
    UBitInt("tb_addr3",  SIZE=14),
    UBitInt("tb_width3", SIZE=6),
    Pad(4),
    UBitInt("tb_addr4",  SIZE=14),
    UBitInt("tb_width4", SIZE=6),
    UBitInt("tb_addr5",  SIZE=14),
    UBitInt("tb_width5", SIZE=6),
    UBitInt("tb_addr6",  SIZE=14),
    UBitInt("tb_width6", SIZE=6),
    Pad(4),
    SIZE=16, VISIBLE=False
    )

v4_bitmap_block = Struct("bitmap",
    UInt8("mipmap_count", EDITABLE=False),
    SInt8("lod_k"),
    bitmap_format_v4,
    bitmap_flags_v4,

    UInt16("width", EDITABLE=False),
    UInt16("height", EDITABLE=False),
    Pointer32("tex_pointer", EDITABLE=False),

    Pad(4),
    UInt16("unknown", EDITABLE=False),
    Pad(6),
    UInt16("frame_count"),
    Pad(2),

    Pad(52),
    SIZE=80
    )

v12_bitmap_block = Struct("bitmap",
    # palletized textures are in either 16 or 256 color format
    #   if a texture has a 16 color palette then each byte counts as
    #   2 pixels with the least significant 4 bits being the left pixel
    # color data is stored in RGBA order
    # 8x8 seems to be the smallest a texture is allowed to be
    bitmap_format_v12,
    SInt8("lod_k"),
    # mipmap_count does not include the largest size.
    # this means a texture without mipmaps will have a mipmap_count of 0
    UInt8("mipmap_count", EDITABLE=False),

    # Width-64 == (width+63)//64
    UInt8("width_64", EDITABLE=False),
    UInt16("log2_of_width", EDITABLE=False),
    UInt16("log2_of_height", EDITABLE=False),

    bitmap_flags_v12,

    UInt16("tex_palette_index", EDITABLE=False),  # unused while serialized

    #pointer to the texture in the BITMAPS.ps2
    #where the pixel texture data is located
    Pointer32("tex_pointer", EDITABLE=False),

    UInt16("tex_palette_count"),  # unused while serialized
    UInt16("tex_shift_index"),    # unused while serialized
    UInt16("frame_count"),

    UInt16("width", EDITABLE=False),
    UInt16("height", EDITABLE=False),

    # size of all pixel data defined by tex0 and miptbp
    UInt16("size"),

    # points to the bitmap def that this bitmap uses
    # this seems to be the same pointer for each texture in
    # an animation, except for ones of a different format
    # doesnt seem to be used, so ignore it
    LPointer32("bitmap_def", VISIBLE=False),

    tex0_struct,
    mip_tbp_struct,

    # unused while serialized
    LUInt16Array("vram_address", SIZE=4, VISIBLE=False),
    LUInt16Array("clut_address", SIZE=4, VISIBLE=False),

    SIZE=64
    )

version_header = Struct('version_header',
    StrNntLatin1("dir_name",   SIZE=32),
    StrNntLatin1("model_name", SIZE=32),
    UEnum32("version",
        ("v4",  0xF00B0004),
        ("v12", 0xF00B000C),
        ("v13", 0xF00B000D),
        DEFAULT=0xF00B000D, EDITABLE=False
        ),
    SIZE=68
    )

v4_objects_header = Struct('header',
    UInt32("bitmap_defs_count", EDITABLE=False, VISIBLE=False),
    Pad(8),
    UInt32("object_defs_count", EDITABLE=False, VISIBLE=False),
    Pad(4),

    Pointer32("object_defs_pointer", VISIBLE=False),
    Pointer32("bitmap_defs_pointer", VISIBLE=False),

    UInt32("objects_count", EDITABLE=False, VISIBLE=False),
    UInt32("bitmaps_count", EDITABLE=False, VISIBLE=False),
    SIZE=36
    )

v12_objects_header = Struct('header',
    UInt32("objects_count", EDITABLE=False, VISIBLE=False),
    UInt32("bitmaps_count", EDITABLE=False, VISIBLE=False),
    UInt32("object_defs_count", EDITABLE=False, VISIBLE=False),
    UInt32("bitmap_defs_count", EDITABLE=False, VISIBLE=False),

    Pointer32("objects_pointer", VISIBLE=False),
    Pointer32("bitmaps_pointer", VISIBLE=False),
    Pointer32("object_defs_pointer", VISIBLE=False),
    Pointer32("bitmap_defs_pointer", VISIBLE=False),

    Pointer32("sub_objects_pointer", VISIBLE=False),
    Pointer32("sub_objects_end", VISIBLE=False),

    UInt32("obj_end", EDITABLE=False),

    UInt32("tex_start", EDITABLE=False),
    UInt32("tex_end", EDITABLE=False),
    
    UInt32("tex_bits", EDITABLE=False),

    UInt16("lm_tex_first"),
    UInt16("lm_tex_num"),
    UInt32("tex_info"),
    Pad(28),
    SIZE=92
    )


object_def = Struct("object_def",
    StrNntLatin1("name", SIZE=16),
    Float("bnd_rad", GUI_NAME="bounding_radius"),
    SInt16("obj_index"),
    SInt16("frames"), # NOTE: only used in demo objects file
    SIZE=24
    )
   
bitmap_def = Struct("bitmap_def",
    StrNntLatin1("name", SIZE=30),
    UInt16("tex_index"),
    UInt16("width"),
    UInt16("height"),
    SIZE=36
    )

v4_objects_array = Array("objects",
    SIZE='.header.objects_count',
    SUB_STRUCT=v4_object_block,
    )
v12_objects_array = Array("objects",
    SIZE='.header.objects_count',
    POINTER='.header.objects_pointer',
    SUB_STRUCT=v12_object_block,
    )
v13_objects_array = Array("objects",
    SIZE='.header.objects_count',
    POINTER='.header.objects_pointer',
    SUB_STRUCT=v13_object_block,
    )

v4_bitmaps_array = Array("bitmaps",
    SIZE='.header.bitmaps_count',
    SUB_STRUCT=v4_bitmap_block
    )
v12_bitmaps_array = Array("bitmaps",
    SIZE='.header.bitmaps_count',
    POINTER='.header.bitmaps_pointer',
    SUB_STRUCT=v12_bitmap_block
    )

objects_ps2_def = TagDef("objects",
    version_header,
    Switch("header",
        CASES={
            "v4":  v4_objects_header,
            "v12": v12_objects_header,
            "v13": v12_objects_header,
            },
        CASE=".version_header.version.enum_name"
        ),
    Switch("objects",
        CASES={
            "v4":  v4_objects_array,
            "v12": v12_objects_array,
            "v13": v13_objects_array,
            },
        CASE=".version_header.version.enum_name"
        ),
    Switch("bitmaps",
        CASES={
            "v4":  v4_bitmaps_array,
            "v12": v12_bitmaps_array,
            "v13": v12_bitmaps_array,
            },
        CASE=".version_header.version.enum_name"
        ),
    Array("object_defs",
        SIZE='.header.object_defs_count',
        POINTER='.header.object_defs_pointer',
        SUB_STRUCT=object_def
        ),
    Array("bitmap_defs",
        SIZE='.header.bitmap_defs_count',
        POINTER='.header.bitmap_defs_pointer',
        SUB_STRUCT=bitmap_def
        ),

    endian="<", ext=".ps2", tag_cls=ObjectsPs2Tag
    )
