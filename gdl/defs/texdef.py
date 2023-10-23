from supyr_struct.defs.tag_def import TagDef
from .objs.texdef import TexdefPs2Tag
from ..common_descs import *
from ..compilation.g3d.constants import *

def get(): return texdef_def

BITMAP_BLOCK_PS2_SIG = 0xF00B0017
BITMAP_BLOCK_DC_SIG  = 0x00FF


def get_bitmap_platform(rawdata=None, offset=0, root_offset=0, **kw):
    # unfortunately, arcade and dreamcast each use v1 in the version header,
    # however the bitmap blocks are completely different between the two.
    # luckily, the structs can be told apart by the first 2 or 4 bytes. arcade
    # uses these as log2 values in the range[0, 7], but dreamcast always
    # has them set to 255 for the first byte, and 0 for the second.
    try:
        rawdata.seek(root_offset + offset)
        data = rawdata.read(4)
        if int.from_bytes(data[:2], 'little') == BITMAP_BLOCK_DC_SIG:
            return 'dreamcast'
        elif int.from_bytes(data, 'little') == BITMAP_BLOCK_PS2_SIG:
            return 'ps2'
        return 'arcade'
    except Exception:
        # default to the newest version
        return 'ps2'


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
    (PIX_FMT_IA_8_IDX_88,         56), #i have no idea how this format works
    (PIX_FMT_ABGR_8888_IDX_8, 66),
    (PIX_FMT_XBGR_8888_IDX_8, 67),
    (PIX_FMT_A_8_IDX_8, 130),
    (PIX_FMT_I_8_IDX_8, 131),
    (PIX_FMT_A_4_IDX_4, 146),
    (PIX_FMT_I_4_IDX_4, 147)
    )

# dreamcast
bitmap_format_dc = UEnum8("format",
    # textures might be aligned to 16-byte boundaries?
    PIX_FMT_ABGR_1555,
    PIX_FMT_BGR_565,
    PIX_FMT_ABGR_4444,
    # NOTE: the below 4 might not be supported, but they
    #       are being documented for completeness sake
    'YUV_422',
    'BUMP',
    'P_4',
    'P_8',
    DEFAULT=1
    )

image_type_dc = UEnum8("image_type",
    # NOTES:
    #   https://segaretro.org/images/7/78/DreamcastDevBoxSystemArchitecture.pdf
    # vq stands for vector-quantized, which indicates
    #   the texture uses a codebook, whose size depends
    #   on the dimensions and if mipmapped. additionally,
    #   vq may only be used with square textures.
    # there are 2 flavors of vq: normal and small.
    #   normal contains a codebook of 256 2x2 16bit
    #   texels, whereas small contains a codebook of
    #   anywhere between 16 and 128 2x2 16bit texels.
    #   vq is used when:
    #       width >= 128 or (width == 64 and mipmapped)
    #   small vq is used otherwise, and the codebook size is:
    #       128 if width == 64 or (width == 32 and mipmapped)
    #       64  if width == 32
    #       32  width == 32 and mipmapped
    #       16  width <= 16
    # codebook entries store pixels in the following order:
    #   bottom right, top right, bottom left, top left
    # pixel data is padded to multiples of 4 bytes, so
    #   twiddled non-vq textures must store at least 2
    #   pixels. this means 1x1 textures store the single
    #   16bit pixel in bytes 2 and 3, and 0 and 1 are 0x00
    # dreamcast twiddling is swizzling in a Z-order
    #   curve, but in yxyxyx order instead of xyxyxy
    # mipmaps are stored in smallest to largest order
    # for some reason, an additional 8 bytes of 0xFF are
    #   appended to every chunk of texture data. Unable
    #   to determine a reason for this at the moment.
    # texture data pointers are 16-byte aligned.
    ("square_twiddled", 1),            # confirmed
    ("square_twiddled_and_mipmap", 2), # confirmed
    ("vq", 3),                         # confirmed
    ("vq_and_mipmap", 4),              # confirmed
    ("twiddled_8bit_clut", 5),
    ("twiddled_4bit_clut", 6),
    ("twiddled_8bit", 7),
    ("twiddled_4bit", 8),
    ("rectangle", 9),                  # confirmed
    ("rectangular_stride", 11),
    ("rectangular_twiddled", 13),
    ("small_vq", 16),                  # confirmed
    ("small_vq_and_mipmap", 17),       # confirmed
    EDITABLE=False
    )

bitmap_flags_v1_dc = Bool8("flags",
    ("clamp_u",   0x01),
    ("clamp_v",   0x02),
    ("external",  0x08),
    )

# found on dreamcast
v1_bitmap_block_dc = Struct("bitmap",
    UInt16("dc_sig", EDITABLE=False, DEFAULT=BITMAP_BLOCK_DC_SIG),
    bitmap_flags_v1_dc,
    UInt8("dc_unknown", EDITABLE=False), # set to 0, 1, 3, 4, 5, 8, 12, 13

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

v23_bitmap_block = Struct("bitmap",
    UInt32("ps2_sig", EDITABLE=False, DEFAULT=BITMAP_BLOCK_PS2_SIG),
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

texdef_def = TagDef("texdef",
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
        SUB_STRUCT=Switch("bitmap",
            CASES={
                "dreamcast":  v1_bitmap_block_dc,
                "ps2":        v23_bitmap_block,
                },
            CASE=get_bitmap_platform,
            DEFAULT=v23_bitmap_block
            ),
        ),
    endian="<", ext=".ps2", tag_cls=TexdefPs2Tag
    )
