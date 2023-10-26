import struct

from . import constants
from .cache import parse_cache_header, serialize_cache_header
from .. import util

# ensure they're all no more than 4 characters since we use them as the cache_type
for ext in (constants.TEXTURE_CACHE_EXTENSION_NGC, constants.TEXTURE_CACHE_EXTENSION_PS2,
            constants.TEXTURE_CACHE_EXTENSION_XBOX, constants.TEXTURE_CACHE_EXTENSION_DC,
            constants.TEXTURE_CACHE_EXTENSION_ARC):
    assert len(ext) <= 4

TEXTURE_CACHE_VER  = 0x0001

# NOTE: the mappings below map the enum value for the format in the
#       objects/texdef bitmap block(or texture cache file) to its name
PS2_FORMAT_ID_TO_NAME = {
    0: PIX_FMT_ABGR_1555,
    1: PIX_FMT_XBGR_1555,
    2: PIX_FMT_ABGR_8888,
    3: PIX_FMT_XBGR_8888,
    # all these below formats are palettized
    16: PIX_FMT_ABGR_1555_IDX_4,
    17: PIX_FMT_XBGR_1555_IDX_4,
    34: PIX_FMT_ABGR_8888_IDX_4,
    35: PIX_FMT_XBGR_8888_IDX_4,
    48: PIX_FMT_ABGR_1555_IDX_8,
    49: PIX_FMT_XBGR_1555_IDX_8,
    66: PIX_FMT_ABGR_8888_IDX_8,
    67: PIX_FMT_XBGR_8888_IDX_8,
    56: PIX_FMT_IA_8_IDX_88,
    130: PIX_FMT_A_8_IDX_8,  # not really palettized
    131: PIX_FMT_I_8_IDX_8,  # not really palettized
    146: PIX_FMT_A_4_IDX_4,  # not really palettized
    147: PIX_FMT_I_4_IDX_4,  # not really palettized
    }
XBOX_FORMAT_ID_TO_NAME = PS2_FORMAT_ID_TO_NAME

NGC_FORMAT_ID_TO_NAME = {
    0: PIX_FMT_ABGR_3555_NGC,
    # all these below formats are palettized
    16: PIX_FMT_ABGR_1555_IDX_4,  # TODO: confirm
    18: PIX_FMT_ABGR_3555_IDX_4_NGC,
    34: PIX_FMT_ABGR_8888_IDX_4,
    48: PIX_FMT_ABGR_1555_IDX_8,  # TODO: confirm
    50: PIX_FMT_ABGR_3555_IDX_8_NGC,
    66: PIX_FMT_ABGR_8888_IDX_8,
    130: PIX_FMT_A_8_IDX_8,  # not really palettized
    146: PIX_FMT_A_4_IDX_4,  # not really palettized
    }

# dreamcast exclusive formats
DC_FORMAT_ID_TO_NAME = {
    0: PIX_FMT_ABGR_1555,
    1: PIX_FMT_ABGR_4444,
    2: PIX_FMT_BGR_565,
    }

# arcade exclusive formats
ARC_FORMAT_ID_TO_NAME = {
    0: PIX_FMT_BGR_233,
    1: PIX_FMT_YIQ_422,
    2: PIX_FMT_A_8,
    3: PIX_FMT_I_8,
    4: PIX_FMT_AI_44,
    5: PIX_FMT_P_8,
    8: PIX_FMT_ABGR_8233,
    9: PIX_FMT_AYIQ_8422,
    10: PIX_FMT_BGR_565,
    11: PIX_FMT_ABGR_1555,
    12: PIX_FMT_ABGR_4444,
    13: PIX_FMT_AI_88,
    14: PIX_FMT_AP_88,
    }

PS2_FORMAT_NAME_TO_ID  = {v: k for k, v in PS2_FORMAT_ID_TO_NAME.items()}
XBOX_FORMAT_NAME_TO_ID = {v: k for k, v in XBOX_FORMAT_ID_TO_NAME.items()}
NGC_FORMAT_NAME_TO_ID  = {v: k for k, v in NGC_FORMAT_ID_TO_NAME.items()}
DC_FORMAT_NAME_TO_ID   = {v: k for k, v in DC_FORMAT_ID_TO_NAME.items()}
ARC_FORMAT_NAME_TO_ID  = {v: k for k, v in ARC_FORMAT_ID_TO_NAME.items()}
# gamecube exclusive fuckery
NGC_FORMAT_NAME_TO_ID[PIX_FMT_XBGR_3555_NGC] = NGC_FORMAT_NAME_TO_ID[PIX_FMT_ABGR_3555_NGC]


# flags
TEXTURE_CACHE_FLAG_HAS_ALPHA = 1 << 0


TEXTURE_CACHE_HEADER_STRUCT = struct.Struct('<HH 4x bBbB 4x 16s')
#   flags
#   format
#   width
#   height


def parse_texture_cache_header(rawdata):
    cache_header = read_cache_header(rawdata)
    asdf = \
           TEXTURE_CACHE_HEADER_STRUCT.unpack(
               rawdata.read(TEXTURE_CACHE_HEADER_STRUCT.size)
               )
    texture_header = dict(
        )

    return cache_header, texture_header


def serialize_texture_cache_header(cache_header, texture_header):
    cache_header.setdefault("cache_type_version", TEXTURE_CACHE_VER)
    cache_header_rawdata = write_cache_header(**cache_header)
    texture_header_rawdata = TEXTURE_CACHE_HEADER_STRUCT.pack(
        )

    return cache_header_rawdata + texture_header_rawdata
    

def parse_texture_cache(filepath=None, rawdata=None):
    rawdata = get_readable_rawdata(filepath, rawdata)
    try:
        cache_header, texture_header = parse_texture_cache_header(rawdata)

        # determine what parser to use
        cache_type      = cache_header["cache_type"]
        cache_type_ver  = cache_header["cache_type_version"]
        parser          = _data_parsers.get((cache_type, cache_type_version))
        if parser is None:
            raise NotImplementedError(
                f"No parser implemented for version '{cache_type_ver}' of '{cache_type}'."
                )

        # parse the rest of the data
        texture_data = parser(rawdata, cache_header, texture_header)

        return dict(
            cache_header=cache_header,
            texture_header=texture_header,
            texture_data=texture_data,
            )
    finally:
        if hasattr(rawdata, "close"):
            rawdata.close()
    

def serialize_texture_cache(texture_cache):
    pass


def _parse_ngc_texture_data(rawdata, cache_header, texture_header):
    pass

def _parse_xbox_texture_data(rawdata, cache_header, texture_header):
    pass

def _parse_ps2_texture_data(rawdata, cache_header, texture_header):
    pass

def _parse_dreamcast_texture_data(rawdata, cache_header, texture_header):
    pass

def _parse_arcade_texture_data(rawdata, cache_header, texture_header):
    pass


def _serialize_ngc_texture_data(cache_header, texture_header, texture_data):
    pass

def _serialize_xbox_texture_data(cache_header, texture_header, texture_data):
    pass

def _serialize_ps2_texture_data(cache_header, texture_header, texture_data):
    pass

def _serialize_dreamcast_texture_data(cache_header, texture_header, texture_data):
    pass

def _serialize_arcade_texture_data(cache_header, texture_header, texture_data):
    pass


_data_parsers = {
    (constants.TEXTURE_CACHE_EXTENSION_NGC,  TEXTURE_CACHE_VER): _parse_ngc_texture_data,
    (constants.TEXTURE_CACHE_EXTENSION_XBOX, TEXTURE_CACHE_VER): _parse_xbox_texture_data,
    (constants.TEXTURE_CACHE_EXTENSION_PS2,  TEXTURE_CACHE_VER): _parse_ps2_texture_data,
    (constants.TEXTURE_CACHE_EXTENSION_DC,   TEXTURE_CACHE_VER): _parse_dreamcast_texture_data,
    (constants.TEXTURE_CACHE_EXTENSION_ARC,  TEXTURE_CACHE_VER): _parse_arcade_texture_data,
    }


_data_serializers = {
    (constants.TEXTURE_CACHE_EXTENSION_NGC,  TEXTURE_CACHE_VER): _serialize_ngc_texture_data,
    (constants.TEXTURE_CACHE_EXTENSION_XBOX, TEXTURE_CACHE_VER): _serialize_xbox_texture_data,
    (constants.TEXTURE_CACHE_EXTENSION_PS2,  TEXTURE_CACHE_VER): _serialize_ps2_texture_data,
    (constants.TEXTURE_CACHE_EXTENSION_DC,   TEXTURE_CACHE_VER): _serialize_dreamcast_texture_data,
    (constants.TEXTURE_CACHE_EXTENSION_ARC,  TEXTURE_CACHE_VER): _serialize_arcade_texture_data,
    }
