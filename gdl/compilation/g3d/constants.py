from ..constants import *


ANIMATION_CACHE_EXTENSION    = "g4d"
COLLISION_CACHE_EXTENSION    = "g3c"
MODEL_CACHE_EXTENSION_NGC    = "g3n"
MODEL_CACHE_EXTENSION_PS2    = "g3p"
MODEL_CACHE_EXTENSION_XBOX   = "g3x"
TEXTURE_CACHE_EXTENSION_NGC  = "gtn"
TEXTURE_CACHE_EXTENSION_PS2  = "gtp"
TEXTURE_CACHE_EXTENSION_XBOX = "gtx"
MODEL_CACHE_EXTENSIONS = (
    MODEL_CACHE_EXTENSION_NGC,
    MODEL_CACHE_EXTENSION_PS2,
    MODEL_CACHE_EXTENSION_XBOX,
    )
TEXTURE_CACHE_EXTENSIONS = (
    TEXTURE_CACHE_EXTENSION_PS2,
    TEXTURE_CACHE_EXTENSION_NGC,
    TEXTURE_CACHE_EXTENSION_XBOX,
    )

ANIM_FOLDERNAME   = 'animations'
MOD_FOLDERNAME    = 'models'
COLL_FOLDERNAME   = 'collision'
TEX_FOLDERNAME    = 'bitmaps'

ANIMATIONS_FILENAME = 'anim'
OBJECTS_FILENAME    = 'objects'
TEXTURES_FILENAME   = 'textures'
WORLDS_FILENAME     = 'worlds'
TEXDEF_FILENAME     = 'texdef'

MISSING_ASSET_NAME = "__MISSING"
UNNAMED_ASSET_NAME = "__UNNAMED"
LIGHTMAP_NAME      = "LIGHTMAP"

# these flags map to the ones in the objects.ps2 struct
G3D_FLAG_NORMALS = 0x0002
G3D_FLAG_COLORS  = 0x0004
G3D_FLAG_MESH    = 0x0008
G3D_FLAG_LMAP    = 0x0020
G3D_FLAG_ALL     = G3D_FLAG_NORMALS | G3D_FLAG_MESH | G3D_FLAG_COLORS | G3D_FLAG_LMAP

DEFAULT_MOD_LOD_K = -90
DEFAULT_TEX_LOD_K = -64
DEFAULT_FORMAT_NAME = "ABGR_8888"

PS2_TEXTURE_BUFFER_CHUNK_SIZE = 256
DEF_TEXTURE_BUFFER_CHUNK_SIZE = 16

# these flags and format names map to the ones in the objects.ps2 struct
GTX_FLAG_HAS_ALPHA = 0x0080
GTX_FLAG_ALL       = GTX_FLAG_HAS_ALPHA


# NOTE: code looks for "IDX_8", "IDX_4", "1555", "8888", "ABGR",
#       "NGC", and/or different combinations of the above to
#       exist in the format name to indicate format properties.
#       this should probably be changed, but for now it works well.
# NOTE: MIDWAY, which one of y'all decided it'd be a good idea to
#       repurpose the ABGR_1555 format to be non-palettized
#       versions of the gamecube-exclusive ARGB_3555?
PIX_FMT_ABGR_1555 = "ABGR_1555"
PIX_FMT_XBGR_1555 = "XBGR_1555"
PIX_FMT_ABGR_8888 = "ABGR_8888"
PIX_FMT_XBGR_8888 = "XBGR_8888"
PIX_FMT_A_4_IDX_4 = "A_4_IDX_4"
PIX_FMT_I_4_IDX_4 = "I_4_IDX_4"
PIX_FMT_A_8_IDX_8 = "A_8_IDX_8"
PIX_FMT_I_8_IDX_8 = "I_8_IDX_8"
PIX_FMT_ABGR_1555_IDX_4 = "ABGR_1555_IDX_4"
PIX_FMT_XBGR_1555_IDX_4 = "XBGR_1555_IDX_4"
PIX_FMT_ABGR_8888_IDX_4 = "ABGR_8888_IDX_4"
PIX_FMT_XBGR_8888_IDX_4 = "XBGR_8888_IDX_4"
PIX_FMT_ABGR_1555_IDX_8 = "ABGR_1555_IDX_8"
PIX_FMT_XBGR_1555_IDX_8 = "XBGR_1555_IDX_8"
PIX_FMT_ABGR_8888_IDX_8 = "ABGR_8888_IDX_8"
PIX_FMT_XBGR_8888_IDX_8 = "XBGR_8888_IDX_8"
# NOTE: gamecube exclusive formats.
# NOTE: the non-indexed ones are not a format enum name used in tags
PIX_FMT_ABGR_3555_NGC = "ABGR_3555_NGC"
PIX_FMT_XBGR_3555_NGC = "XBGR_3555_NGC"
PIX_FMT_ABGR_3555_IDX_4_NGC = "ABGR_3555_IDX_4_NGC"
PIX_FMT_ABGR_3555_IDX_8_NGC = "ABGR_3555_IDX_8_NGC"


PALETTE_SIZES = {
    #measured in bytes
    PIX_FMT_ABGR_1555_IDX_4:2,
    PIX_FMT_XBGR_1555_IDX_4:2,
    PIX_FMT_ABGR_1555_IDX_8:2,
    PIX_FMT_XBGR_1555_IDX_8:2,
    PIX_FMT_ABGR_8888_IDX_4:4,
    PIX_FMT_XBGR_8888_IDX_4:4,
    PIX_FMT_ABGR_8888_IDX_8:4,
    PIX_FMT_XBGR_8888_IDX_8:4,
    PIX_FMT_ABGR_3555_IDX_4_NGC:2,
    PIX_FMT_ABGR_3555_IDX_8_NGC:2,
    }

PIXEL_SIZES = {
    #measured in bits
    PIX_FMT_ABGR_1555_IDX_4:4,
    PIX_FMT_XBGR_1555_IDX_4:4,
    PIX_FMT_ABGR_8888_IDX_4:4,
    PIX_FMT_XBGR_8888_IDX_4:4,
    PIX_FMT_A_4_IDX_4:4,
    PIX_FMT_I_4_IDX_4:4,
    PIX_FMT_ABGR_1555_IDX_8:8,
    PIX_FMT_XBGR_1555_IDX_8:8,
    PIX_FMT_ABGR_8888_IDX_8:8,
    PIX_FMT_XBGR_8888_IDX_8:8,
    PIX_FMT_A_8_IDX_8:8,
    PIX_FMT_I_8_IDX_8:8,
    PIX_FMT_ABGR_1555:16,
    PIX_FMT_XBGR_1555:16,
    PIX_FMT_ABGR_8888:32,
    PIX_FMT_XBGR_8888:32,
    PIX_FMT_ABGR_3555_NGC:16,
    PIX_FMT_XBGR_3555_NGC:16,
    PIX_FMT_ABGR_3555_IDX_4_NGC:4,
    PIX_FMT_ABGR_3555_IDX_8_NGC:8,
    }

MONOCHROME_FORMATS = set(
    (PIX_FMT_A_4_IDX_4, PIX_FMT_I_4_IDX_4,
     PIX_FMT_A_8_IDX_8, PIX_FMT_I_8_IDX_8)
    )

# these limits are based on limitations of the miptbp structure
VALID_DIMS = set(1<<i for i in range(15))
MAX_MIP_COUNT = 6

# everything below relates to calculating PS2
# texture buffer addresses, sizes, and formats
PSM_CT32  = "psmct32"   # usable as palette format
PSM_CT24  = "psmct24"   # usable as palette format
PSM_CT16  = "psmct16"   # usable as palette format
PSM_CT16S = "psmct16s"  # usable as palette format
PSM_Z32   = "psmz32"
PSM_Z24   = "psmz24"
PSM_Z16   = "psmz16"
PSM_Z16S  = "psmz16s"
PSM_T8    = "psmt8"
PSM_T4    = "psmt4"
PSM_T8H   = "psmt8h"
PSM_T4HL  = "psmt4hl"
PSM_T4HH  = "psmt4hh"


PSM_BLOCK_ORDER_PSMCT32 = (
      0,  1,  4,  5,  16,  17,  20,  21,
      2,  3,  6,  7,  18,  19,  22,  23,
      8,  9, 12, 13,  24,  25,  28,  29,
     10, 11, 14, 15,  26,  27,  30,  31,
    )
PSM_BLOCK_ORDER_PSMZ32 = (
    24,  25,  28,  29,  8,  9, 12, 13,
    26,  27,  30,  31, 10, 11, 14, 15,
    16,  17,  20,  21,  0,  1,  4,  5,
    18,  19,  22,  23,  2,  3,  6,  7,
    )
PSM_BLOCK_ORDER_PSMCT16 = (
     0,  2,  8, 10,
     1,  3,  9, 11,
     4,  6, 12, 14,
     5,  7, 13, 15,
    16, 18, 24, 26,
    17, 19, 25, 27,
    20, 22, 28, 30,
    21, 23, 29, 31,
    )
PSM_BLOCK_ORDER_PSMCT16S = (
     0,  2, 16, 18,
     1,  3, 17, 19,
     8, 10, 24, 26,
     9, 11, 25, 27,
     4,  6, 20, 22,
     5,  7, 21, 23,
    12, 14, 28, 30,
    13, 15, 29, 31,
    )
PSM_BLOCK_ORDER_PSMZ16 = (
    24, 26, 16, 18,
    25, 27, 17, 19,
    28, 30, 20, 22,
    29, 31, 21, 23,
     8, 10,  0,  2,
     9, 11,  1,  3,
    12, 14,  4,  6,
    13, 15,  5,  7,
    )
PSM_BLOCK_ORDER_PSMZ16S = (
    24, 26,  8, 10,
    25, 27,  9, 11,
    16, 18,  0,  2,
    17, 19,  1,  3,
    28, 30, 12, 14,
    29, 31, 13, 15,
    20, 22,  4,  6,
    21, 23,  5,  7,
    )

# NOTE: several of these block structures are shared across formats
PSM_BLOCK_ORDERS = {
    PSM_CT32:  PSM_BLOCK_ORDER_PSMCT32,
    PSM_CT24:  PSM_BLOCK_ORDER_PSMCT32,
    PSM_CT16:  PSM_BLOCK_ORDER_PSMCT16,
    PSM_CT16S: PSM_BLOCK_ORDER_PSMCT16S,
    PSM_Z32:   PSM_BLOCK_ORDER_PSMZ32,
    PSM_Z24:   PSM_BLOCK_ORDER_PSMZ32,
    PSM_Z16:   PSM_BLOCK_ORDER_PSMZ16,
    PSM_Z16S:  PSM_BLOCK_ORDER_PSMZ16S,
    PSM_T8:    PSM_BLOCK_ORDER_PSMCT32,
    PSM_T4:    PSM_BLOCK_ORDER_PSMCT16,
    PSM_T8H:   PSM_BLOCK_ORDER_PSMCT32,
    PSM_T4HL:  PSM_BLOCK_ORDER_PSMCT32,
    PSM_T4HH:  PSM_BLOCK_ORDER_PSMCT32,
    }

def invert_block_map(block_map):
    inv_block_map = [ -1 ] * len(block_map)
    for i in range(len(block_map)):
        inv_block_map[block_map[i]] = i
    return tuple(inv_block_map)

PSM_INVERSE_BLOCK_ORDERS = {
    name: invert_block_map(PSM_BLOCK_ORDERS[name])
    for name in PSM_BLOCK_ORDERS
    }

PSM_PAGE_BLOCK_WIDTHS = {
    psm: (8 if psm in (PSM_T8, PSM_CT32, PSM_CT24, PSM_Z32, PSM_Z24) else 4)
    for psm in PSM_BLOCK_ORDERS.keys()
    }

PSM_PAGE_BLOCK_HEIGHTS = {
    psm: (4 if psm in (PSM_T8, PSM_CT32, PSM_CT24, PSM_Z32, PSM_Z24) else 8)
    for psm in PSM_BLOCK_ORDERS.keys()
    }

PSM_PAGE_WIDTHS = {
    psm: (128 if psm in (PSM_T8, PSM_T4) else 64)
    for psm in PSM_BLOCK_ORDERS.keys()
    }
PSM_PAGE_HEIGHTS = {
    psm: (
        128 if psm == PSM_T4 else
        64 if psm in (PSM_T8, PSM_CT16, PSM_CT16S, PSM_Z16, PSM_Z16S) else
        32
        )
    for psm in PSM_BLOCK_ORDERS.keys()
    }
PSM_BLOCK_WIDTHS = {
    psm: (
        32 if psm == PSM_T4 else
        16 if psm in (PSM_T8, PSM_CT16, PSM_CT16S, PSM_Z16, PSM_Z16S) else
        8
        )
    for psm in PSM_BLOCK_ORDERS.keys()
    }
PSM_BLOCK_HEIGHTS = {
    psm: (16 if psm in (PSM_T8, PSM_T4) else 8)
    for psm in PSM_BLOCK_ORDERS.keys()
    }
