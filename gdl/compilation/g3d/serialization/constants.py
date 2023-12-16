from ..constants import *

DEBUG = False

FLOAT_INFINITY = float("inf")
Y_GRID_SNAP_TOLERANCE = 0.01

# MODEL CONSTANTS
# These are the highest tested strip lengths the systems will properly load
RETAIL_MAX_STRIP_LEN = 30  # safe max length from looking at retail files
XBOX_MAX_STRIP_LEN   = 189
NGC_MAX_STRIP_LEN    = XBOX_MAX_STRIP_LEN  # haven't tested yet
PS2_MAX_STRIP_LEN    = RETAIL_MAX_STRIP_LEN  # dont change. levels might not load

COLL_SCALE  = 0x40

DEFAULT_TEX_NAME    = "__unnamed_0"
DEFAULT_LM_NAME     = "__unnamed_0"
DEFAULT_INDEX_KEY   = (DEFAULT_TEX_NAME, DEFAULT_LM_NAME)
DEFAULT_NODE_NAMES  = (
    "__NULL",
    "__UNNAMED",
    "__UNNAMED_OBJ",
    "__TEXMOD",
    "__PSYS"
    )
