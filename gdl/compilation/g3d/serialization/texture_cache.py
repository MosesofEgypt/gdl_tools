import struct

from . import constants
from .asset_cache import AssetCache
from .. import util

# ensure they're all no more than 4 characters since we use them as the cache_type
for ext in (constants.TEXTURE_CACHE_EXTENSION_NGC, constants.TEXTURE_CACHE_EXTENSION_PS2,
            constants.TEXTURE_CACHE_EXTENSION_XBOX, constants.TEXTURE_CACHE_EXTENSION_DC,
            constants.TEXTURE_CACHE_EXTENSION_ARC):
    assert len(ext) <= 4

TEXTURE_CACHE_VER  = 0x0001

# flags
TEXTURE_CACHE_FLAG_HAS_ALPHA = 1 << 0
# dreamcast
TEXTURE_CACHE_FLAG_TWIDDLED  = 1 << 1
TEXTURE_CACHE_FLAG_SMALL_VQ  = 1 << 2
TEXTURE_CACHE_FLAG_LARGE_VQ  = 1 << 3


TEXTURE_CACHE_HEADER_STRUCT = struct.Struct('<HBB HH')
#   flags
#   format_id
#   mipmaps
#   width
#   height


class TextureCache(AssetCache):
    format_id_to_name = {}
    format_name_to_id = {}
    has_alpha   = False
    twiddled    = False
    large_vq    = False
    small_vq    = False
    format_name = ""
    width       = 0
    height      = 0
    mipmaps     = 0

    def parse(self, rawdata):
        super().parse(rawdata)

        tex_flags, format_id, mipmaps, width, height = \
           TEXTURE_CACHE_HEADER_STRUCT.unpack(
               rawdata.read(TEXTURE_CACHE_HEADER_STRUCT.size)
               )

        format_name = self.format_id_to_name\
                      .get(self.cache_type, {})\
                      .get(format_id)
        if format_name is None:
            raise ValueError(f"Cannot determine format name for id '{format_id}'")

        self.format_name = format_name
        self.width       = width
        self.height      = height

        self.has_alpha  = bool(tex_flags & TEXTURE_CACHE_FLAG_HAS_ALPHA)
        self.twiddled   = bool(tex_flags & TEXTURE_CACHE_FLAG_TWIDDLED)
        self.large_vq   = bool(tex_flags & TEXTURE_CACHE_FLAG_SMALL_VQ)
        self.small_vq   = bool(tex_flags & TEXTURE_CACHE_FLAG_LARGE_VQ)

    def serialize(self):
        self.cache_type_version = TEXTURE_CACHE_VER
        format_id = self.format_name_to_id\
                    .get(self.cache_type, {})\
                    .get(self.format_name)
        if format_id is None:
            raise ValueError(f"Cannot determine format id for '{self.format_name}'")

        tex_flags = (
            (TEXTURE_CACHE_FLAG_HAS_ALPHA * bool(self.has_normals)) |
            (TEXTURE_CACHE_FLAG_TWIDDLED  * bool(self.has_colors))  |
            (TEXTURE_CACHE_FLAG_SMALL_VQ  * bool(self.small_vq))    |
            (TEXTURE_CACHE_FLAG_LARGE_VQ  * bool(self.large_vq))
            )
        tex_header_rawdata = TEXTURE_CACHE_HEADER_STRUCT.pack(
            tex_flags, format_id, self.mipmaps, self.width, self.height
            )

        cache_header_rawdata = super().serialize()
        return cache_header_rawdata + tex_header_rawdata


class Ps2TextureCache(TextureCache):
    format_id_to_name = {
        0: constants.PIX_FMT_ABGR_1555,
        1: constants.PIX_FMT_XBGR_1555,
        2: constants.PIX_FMT_ABGR_8888,
        3: constants.PIX_FMT_XBGR_8888,
        # all these below formats are palettized
        16: constants.PIX_FMT_ABGR_1555_IDX_4,
        17: constants.PIX_FMT_XBGR_1555_IDX_4,
        34: constants.PIX_FMT_ABGR_8888_IDX_4,
        35: constants.PIX_FMT_XBGR_8888_IDX_4,
        48: constants.PIX_FMT_ABGR_1555_IDX_8,
        49: constants.PIX_FMT_XBGR_1555_IDX_8,
        66: constants.PIX_FMT_ABGR_8888_IDX_8,
        67: constants.PIX_FMT_XBGR_8888_IDX_8,
        56: constants.PIX_FMT_IA_8_IDX_88,
        130: constants.PIX_FMT_A_8_IDX_8,  # not really palettized
        131: constants.PIX_FMT_I_8_IDX_8,  # not really palettized
        146: constants.PIX_FMT_A_4_IDX_4,  # not really palettized
        147: constants.PIX_FMT_I_4_IDX_4,  # not really palettized
        }
    format_name_to_id = {v: k for k, v in format_name_to_id.items()}

    def parse(self, rawdata):
        super().parse(rawdata)

    def serialize(self):
        tex_header_rawdata = super().serialize()
        return tex_header_rawdata


class GamecubeTextureCache(Ps2TextureCache):
    format_id_to_name = {
        0: constants.PIX_FMT_ABGR_3555_NGC,
        # all these below formats are palettized
        16: constants.PIX_FMT_ABGR_1555_IDX_4,  # TODO: confirm
        18: constants.PIX_FMT_ABGR_3555_IDX_4_NGC,
        34: constants.PIX_FMT_ABGR_8888_IDX_4,
        48: constants.PIX_FMT_ABGR_1555_IDX_8,  # TODO: confirm
        50: constants.PIX_FMT_ABGR_3555_IDX_8_NGC,
        66: constants.PIX_FMT_ABGR_8888_IDX_8,
        130: constants.PIX_FMT_A_8_IDX_8,  # not really palettized
        146: constants.PIX_FMT_A_4_IDX_4,  # not really palettized
        }
    format_name_to_id = {v: k for k, v in format_name_to_id.items()}
    # gamecube exclusive fuckery(they're the same format)
    format_name_to_id[constants.PIX_FMT_XBGR_3555_NGC] = 0


class ArcadeTextureCache(TextureCache):
    # dreamcast exclusive formats
    format_id_to_name = {
        0: constants.PIX_FMT_ABGR_1555,
        1: constants.PIX_FMT_ABGR_4444,
        2: constants.PIX_FMT_BGR_565,
        }
    format_name_to_id = {v: k for k, v in format_name_to_id.items()}

    def parse(self, rawdata):
        super().parse(rawdata)

    def serialize(self):
        tex_header_rawdata = super().serialize()
        return tex_header_rawdata


class DreamcastTextureCache(TextureCache):
    # arcade exclusive formats
    format_id_to_name = {
        0: constants.PIX_FMT_BGR_233,
        1: constants.PIX_FMT_YIQ_422,
        2: constants.PIX_FMT_A_8,
        3: constants.PIX_FMT_I_8,
        4: constants.PIX_FMT_AI_44,
        5: constants.PIX_FMT_P_8,
        8: constants.PIX_FMT_ABGR_8233,
        9: constants.PIX_FMT_AYIQ_8422,
        10: constants.PIX_FMT_BGR_565,
        11: constants.PIX_FMT_ABGR_1555,
        12: constants.PIX_FMT_ABGR_4444,
        13: constants.PIX_FMT_AI_88,
        14: constants.PIX_FMT_AP_88,
        }
    format_name_to_id = {v: k for k, v in format_name_to_id.items()}

    def parse(self, rawdata):
        super().parse(rawdata)

    def serialize(self):
        tex_header_rawdata = super().serialize()
        return tex_header_rawdata
