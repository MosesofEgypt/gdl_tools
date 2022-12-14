from ..constants import *

DEBUG = False

# MODEL CONSTANTS
# These are the highest tested strip lengths the systems will properly load
RETAIL_MAX_STRIP_LEN = 30  # safe max length from looking at retail files
XBOX_MAX_STRIP_LEN   = 189
NGC_MAX_STRIP_LEN    = XBOX_MAX_STRIP_LEN  # haven't tested yet
PS2_MAX_STRIP_LEN    = RETAIL_MAX_STRIP_LEN  # dont change. levels might not load

POS_SCALE   = 0x80
UV_SCALE    = 0x80
LM_UV_SCALE = 0x8000

DEFAULT_TEX_NAME  = "__unnamed_0"
DEFAULT_LM_NAME   = "__unnamed_0"
DEFAULT_INDEX_KEY = (DEFAULT_TEX_NAME, DEFAULT_LM_NAME)

STREAM_FLAGS_DEFAULT    = 0x80
STREAM_FLAGS_UV_DEFAULT = 0xC0

UNKNOWN_GEOM_DATA = b'\x00\x00\x00\x2D'

DATA_TYPE_GEOM  = 0x00
DATA_TYPE_POS   = 0x01
DATA_TYPE_NORM  = 0x02
DATA_TYPE_COLOR = 0x03
DATA_TYPE_UV    = 0x04

STORAGE_TYPE_NULL             = 0x00
STORAGE_TYPE_UNKNOWN          = 0x01
STORAGE_TYPE_STRIP_0_END      = 0x14
STORAGE_TYPE_STRIP_N_END      = 0x17
STORAGE_TYPE_UINT32_UV        = 0x64
STORAGE_TYPE_UINT16_UV        = 0x65
STORAGE_TYPE_UINT8_UV         = 0x66
STORAGE_TYPE_SINT32_XYZ       = 0x68
STORAGE_TYPE_SINT16_XYZ       = 0x69
STORAGE_TYPE_SINT8_XYZ        = 0x6A
STORAGE_TYPE_FLOAT32          = 0x6C
STORAGE_TYPE_UINT16_LMUV      = 0x6D
STORAGE_TYPE_UINT16_BITPACKED = 0x6F


# TEXTURE CONSTANTS
FORMAT_ID_TO_NAME = {
    0: "ABGR_1555",
    1: "XBGR_1555",
    2: "ABGR_8888",
    3: "XBGR_8888",
    #all these below formats are palettized
    16: "ABGR_1555_IDX_4",
    17: "XBGR_1555_IDX_4",
    18: "ABGR_1555_IDX_4_NGC",
    34: "ABGR_8888_IDX_4",
    35: "XBGR_8888_IDX_4",
    48: "ABGR_1555_IDX_8",
    49: "XBGR_1555_IDX_8",
    50: "XBGR_1555_IDX_8_NGC",
    66: "ABGR_8888_IDX_8",
    67: "XBGR_8888_IDX_8",
    130: "A_8_IDX_8",  # not really palettized
    131: "I_8_IDX_8",  # not really palettized
    146: "A_4_IDX_4",  # not really palettized
    147: "I_4_IDX_4",  # not really palettized
    }
FORMAT_NAME_TO_ID = {v: k for k, v in FORMAT_ID_TO_NAME.items()}
