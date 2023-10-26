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
