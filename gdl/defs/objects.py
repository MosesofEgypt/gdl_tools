from supyr_struct.defs.tag_def import TagDef
from ..common_descs import *
from ..compilation.g3d.constants import *
from .objs.objects import ObjectsPs2Tag
from .texdef import bitmap_flags_v1_dc, BITMAP_BLOCK_DC_SIG,\
    bitmap_format_dc, image_type_dc, bitmap_format as bitmap_format_v12

def get(): return objects_ps2_def


def object_defs_count(*args, parent=None, new_value=None, **kwargs):
    if parent is None:
        return
    elif new_value is not None:
        parent.header.object_defs_count = new_value
    elif (parent.version_header.version.enum_name in ('v0', 'v1') and
          parent.header.object_defs_count == 0):
        # midway did some stupid shit with v0/v1 of this file
        return parent.header.objects_count
    else:
        return parent.header.object_defs_count


def bitmap_defs_count(*args, parent=None, new_value=None, **kwargs):
    if parent is None:
        return
    elif new_value is not None:
        parent.header.bitmap_defs_count = new_value
    elif (parent.version_header.version.enum_name == 'v0' and
          parent.header.bitmap_defs_count == 0):
        # midway did some stupid shit with v0 of this file
        # also YES, it only applies to v0. trying to load with v1 included
        # causes errors trying to read non-existant bitmap defs
        return parent.header.bitmaps_count
    else:
        return parent.header.bitmap_defs_count


def get_lod_type(*args, parent=None, **kwargs):
    try:
        if parent.flags.fifo_cmds or parent.flags.fifo_cmds_2:
            return "fifo"
        elif parent.flags.lightmap:
            return "uncomp_lm"
    except Exception:
        pass

    return "uncomp"


def get_arcade_lod_type(*args, parent=None, **kwargs):
    lod_type = get_lod_type(*args, parent=parent, **kwargs)
    return "uncomp" if lod_type == "uncomp_lm" else lod_type


def get_dreamcast_or_arcade_bitmap_block(
        rawdata=None, offset=0, root_offset=0, **kw
        ):
    try:
        rawdata.seek(root_offset + offset)
        if int.from_bytes(rawdata.read(2), 'little') != BITMAP_BLOCK_DC_SIG:
            return 'arcade'
    except Exception:
        pass

    return "dreamcast"


v0_object_flags = Bool32("flags",
    # confirmed these are the only flags set
    # for sst_cmds, data pointer is relative to lod struct
    # NOTE: in dreamcast, only alpha and lightmap are ever set
    ("alpha",       0x00000001),
    ("v_normals",   0x00000002),
    ("unknown2",    0x00000004), # set in ALL levelA item objects
    ("fifo_cmds",   0x00000008),
    ("lightmap",    0x00000010), # contains lightmap data?
    ("unknown10",   0x00000400),
    ("fifo_cmds_2", 0x00001000),
    ("unknown24",   0x01000000),
    ("unknown25",   0x02000000),
    ("unknown26",   0x04000000),
    )

v12_object_flags = Bool32("flags",
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

bitmap_format_v0 = UEnum8("format",
    PIX_FMT_BGR_233,
    PIX_FMT_YIQ_422,
    PIX_FMT_A_8,
    PIX_FMT_I_8,
    PIX_FMT_AI_44,
    PIX_FMT_P_8,
    "RSVD0", # reserved
    "RSVD1", # reserved
    PIX_FMT_ABGR_8233,
    PIX_FMT_AYIQ_8422,
    PIX_FMT_BGR_565,
    PIX_FMT_ABGR_1555,
    PIX_FMT_ABGR_4444,
    PIX_FMT_AI_88,
    PIX_FMT_AP_88,
    "RSVD2", # reserved
    )

bitmap_format_v4 = UEnum8("format",
    #these formats are palettized
    (PIX_FMT_ABGR_8888_IDX_8, 3),
    (PIX_FMT_ABGR_1555_IDX_4, 5),
    )

bitmap_flags_v0 = Bool8("flags",
    # confirmed these are the only flags set
    ("halfres",    0x01), # confirmed
    ("force_tmu1", 0x02), # ???
    ("force_tmu0", 0x04), # ???
    ("unknown",    0x08), # ???
    )

bitmap_flags_v4 = Bool8("flags",
    ("see_alpha", 0x01), # confirmed
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

v4_sub_object_block = QStruct("sub_object",
    UInt16("tex_index",   GUI_NAME="texture index"),
    UInt16("lm_index",    GUI_NAME="light map index"),
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

v0_lod_fifo_data = QStruct("lod_fifo_data",
    SInt32("vert_count"),
    # NOTE: this pointer is relative to the start of this
    #       lod_struct in the file.
    SInt32("unknown_pointer"),
    # NOTE: this pointer is relative to the start of this
    #       lod_struct in the file, AND sometimes seems
    #       to point to the beginning of the file.
    SInt32("unknown_pointer_2"),
    # NOTE: this pointer is relative to the start of this
    #       lod_struct in the file.
    SInt32("fifo_pointer"),
    SInt32("id_num"),
    # is one of the following:
    #   2, 5, 7, 9, 10, 11, 12, 13
    SInt32("unknown"),
    SIZE=24
    )

v0_lod_uncomp_data = QStruct("lod_uncomp_data",
    SInt32("vert_count"),
    # XYZ floats, followed by UVW floats
    # uv coords are 0-256 range floats(divide by 256 to get 0-1)
    SInt32("verts_pointer"),
    SInt32("tri_count"),
    # set of 3 uint16 for vert/norm indices, then uint16 texture index
    SInt32("tris_pointer"),
    SInt32("id_num"),
    # IJK floats (count is equal to vert_count)
    SInt32("norms_pointer"),
    SIZE=24,
    )

v1_lod_uncomp_lm_data = QStruct("lod_uncomp_lm_data",
    SInt32("vert_count"),
    # XYZ floats, then sint16s UVs, then uint16 lm UVs
    SInt32("verts_pointer"),
    SInt32("tri_count"),
    # set of 3 uint16 for vert indices, followed by uint16 texture index
    SInt32("tris_pointer"),
    SInt32("id_num"),
    SInt32("lm_header_pointer"),
    SIZE=24,

    STEPTREE=Struct("lightmap_header",
        Pointer32("tex_pointer", EDITABLE=False),
        # lightmaps are always R5G6B5, and this value is set to 1 in
        # all files, and that matches the pixel format for R5G6B5 in
        # the dreamcast PVR header, so this appears to be "format"
        bitmap_format_dc,
        image_type_dc,
        Pad(2),
        UInt16("width", EDITABLE=False),
        UInt16("height", EDITABLE=False),
        POINTER=".lm_header_pointer"
        )
    )


v0_lod_block = Struct("lod",
    UInt32("unknown"),
    v0_object_flags,
    Switch("data",
        CASES={
            "fifo":   v0_lod_fifo_data,
            "uncomp": v0_lod_uncomp_data,
            },
        CASE=get_arcade_lod_type,
        SIZE=24
        ),
    SIZE=32
    )

v1_lod_block = Struct("lod",
    UInt32("unknown"),
    v0_object_flags,
    Switch("data",
        CASES={
            "fifo":      v0_lod_fifo_data,
            "uncomp":    v0_lod_uncomp_data,
            "uncomp_lm": v1_lod_uncomp_lm_data,
            },
        CASE=get_lod_type,
        SIZE=24
        ),
    SIZE=32
    )

v0_object_block = Struct("object",
    Float("inv_rad"), # always 0?
    Float("bnd_rad"),
    UInt32("unknown", DEFAULT=1, VISIBLE=False), # always 1
    Array("lods", SUB_STRUCT=v0_lod_block, SIZE=4),
    SIZE=140,
    )

v1_object_block = Struct("object",
    Float("inv_rad"), # always 0?
    Float("bnd_rad"),
    UInt32("unknown", DEFAULT=1, VISIBLE=False), # always 1
    Array("lods", SUB_STRUCT=v1_lod_block, SIZE=4),
    SIZE=140,
    )

v4_object_block = Struct("object",
    Float("inv_rad"),
    Float("bnd_rad"),
    UInt32("unknown"), # always 0?
    SInt32('sub_objects_count', EDITABLE=False), # name is a guess. always 1?
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
    v12_object_flags,

    SInt32('sub_objects_count', EDITABLE=False),
    Struct("sub_object_0", INCLUDE=v13_sub_object_block),

    Pointer32('sub_objects_pointer', EDITABLE=False),
    Pointer32('sub_object_models_pointer', EDITABLE=False),

    SInt32("vert_count"),  # exactly the number of unique verts
    SInt32("tri_count"),  # exactly the number of unique triangles
    SInt32("id_num"),

    # pointer to the obj def that this model uses
    # always 0 in serialized form, but keeping this for documentation
    Pointer32("obj_def"),
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

v0_bitmap_block = Struct("bitmap",
    UInt8("large_lod_log2_inv", EDITABLE=False),
    UInt8("small_lod_log2_inv", EDITABLE=False),
    bitmap_format_v0,
    bitmap_flags_v0,

    UInt16("width", EDITABLE=False),
    UInt16("height", EDITABLE=False),
    Pointer32("tex_pointer", EDITABLE=False),

    # NOTE: adr, mod, lod, and pkt are runtime values
    UInt16("unknown0"),
    SInt16("unknown1"),
    UInt16("unknown2"),
    UInt16("unknown3"),
    UInt16("unknown4"),
    UInt16("unknown5"),
    #SInt32("adr", EDITABLE=False, VISIBLE=False),
    #SInt32("mod", EDITABLE=False, VISIBLE=False),
    #SInt32("lod", EDITABLE=False, VISIBLE=False),
    SInt16("frame_count"),
    Pad(2),
    SInt32("pkt", EDITABLE=False, VISIBLE=False),
    # a and b are actually 9-bit signed ints packed into
    # a uint32 to preserve a large enough range for them.
    # they are packed like so:
    #     a[i][0] = (ncc_table_a[i] >> 18) & 0x1FF
    #     a[i][1] = (ncc_table_a[i] >>  9) & 0x1FF
    #     a[i][2] = (ncc_table_a[i] >>  0) & 0x1FF
    # since they are twos-signed, if 0x100 is set, subtract 0x200
    #UInt8Array("ncc_table_y", SIZE=16, EDITABLE=False, VISIBLE=False),
    #UInt32Array("ncc_table_a", SIZE=16, EDITABLE=False, VISIBLE=False),
    #UInt32Array("ncc_table_b", SIZE=16, EDITABLE=False, VISIBLE=False),
    BytesRaw("ncc_table_data", SIZE=48),
    SIZE=80
    )

v1_bitmap_block_dc = Struct("bitmap",
    UInt16("sig", EDITABLE=False, DEFAULT=BITMAP_BLOCK_DC_SIG),
    bitmap_flags_v1_dc,
    UInt8("unknown1", EDITABLE=False), # set to 0, 1, 3, 4, 5, 8, 12, 13

    UInt16("width", EDITABLE=False),
    UInt16("height", EDITABLE=False),
    Pointer32("tex_pointer", EDITABLE=False),

    Pad(4),
    bitmap_format_dc,
    image_type_dc,
    Pad(2),
    # size of all pixel data
    SInt32("size", EDITABLE=False, VISIBLE=False),
    SInt16("frame_count"),
    Pad(54),
    SIZE=80
    )

# unfortunately, arcade and dreamcast each use v1 in the version header,
# however the bitmap blocks are completely different between the two.
# luckily, the structs can be told apart by the first 2 bytes. arcade
# uses these as log2 values in the range[0, 7], but dreamcast always
# has them set to 255 for the first byte, and 0 for the second.
v1_bitmap_block = Switch("bitmap",
    CASES={
        "arcade":    v0_bitmap_block,
        "dreamcast": v1_bitmap_block_dc,
        },
    CASE=get_dreamcast_or_arcade_bitmap_block,
    DEFAULT=v1_bitmap_block_dc,
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
    SInt16("frame_count"),
    Pad(54),
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
        # fuck you midway games
        ("v0",  0x00000000),
        ("v1",  0xF00B0001),
        ("v4",  0xF00B0004),
        ("v12", 0xF00B000C),
        ("v13", 0xF00B000D),
        DEFAULT=0xF00B000D, EDITABLE=False
        ),
    SIZE=68
    )

v0_objects_header = Struct('header',
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

v0_objects_array = Array("objects",
    SIZE='.header.objects_count',
    SUB_STRUCT=v0_object_block,
    )
v1_objects_array = Array("objects",
    SIZE='.header.objects_count',
    SUB_STRUCT=v1_object_block,
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

v0_bitmaps_array = Array("bitmaps",
    SIZE='.header.bitmaps_count',
    SUB_STRUCT=v0_bitmap_block
    )
v1_bitmaps_array = Array("bitmaps",
    SIZE='.header.bitmaps_count',
    SUB_STRUCT=v1_bitmap_block
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
            "v0":  v0_objects_header,
            "v1":  v0_objects_header,
            "v4":  v0_objects_header,
            "v12": v12_objects_header,
            "v13": v12_objects_header,
            },
        CASE=".version_header.version.enum_name"
        ),
    Switch("objects",
        CASES={
            "v0":  v0_objects_array,
            "v1":  v1_objects_array,
            "v4":  v4_objects_array,
            "v12": v12_objects_array,
            "v13": v13_objects_array,
            },
        CASE=".version_header.version.enum_name"
        ),
    Switch("bitmaps",
        CASES={
            "v0":  v0_bitmaps_array,
            "v1":  v1_bitmaps_array,
            "v4":  v4_bitmaps_array,
            "v12": v12_bitmaps_array,
            "v13": v12_bitmaps_array,
            },
        CASE=".version_header.version.enum_name"
        ),
    Array("object_defs",
        SIZE=object_defs_count,
        POINTER='.header.object_defs_pointer',
        SUB_STRUCT=object_def,
        DYN_NAME_PATH='.name', WIDGET=DynamicArrayFrame
        ),
    Array("bitmap_defs",
        SIZE=bitmap_defs_count,
        POINTER='.header.bitmap_defs_pointer',
        SUB_STRUCT=bitmap_def,
        DYN_NAME_PATH='.name', WIDGET=DynamicArrayFrame
        ),

    endian="<", ext=".ps2", tag_cls=ObjectsPs2Tag
    )
