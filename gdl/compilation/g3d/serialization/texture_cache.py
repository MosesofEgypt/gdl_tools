import os
import math
import struct

from . import constants
from . import texture_util
from . import arbytmap_ext as arbytmap
from . import texture_conversions as tex_conv
from .asset_cache import AssetCache
from .ncc import NccTable
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
    format_id_to_name   = {}
    format_name_to_id   = {}
    has_alpha       = False
    twiddled        = False
    large_vq        = False
    small_vq        = False
    lod_k           = constants.DEFAULT_TEX_LOD_K
    width           = 0
    height          = 0
    mipmaps         = 0

    _format_name    = ""
    palette         = b''
    textures        = ()
    texture_chunk_size = constants.DEF_TEXTURE_BUFFER_CHUNK_SIZE

    def __init__(self):
        self.format_name_to_id = {
            v: k for k, v in self.format_id_to_name.items()
            }

    @property
    def format_id(self):
        return self.format_name_to_id.get(self._format_name)
    @format_id.setter
    def format_id(self, val):
        if val not in self.format_id_to_name:
            raise ValueError(f"{val} is not a valid format_id in {type(self)}")
        self.format_name = self.format_id_to_name[val]

    @property
    def format_name(self):
        return self._format_name
    @format_name.setter
    def format_name(self, val):
        if val not in self.format_name_to_id:
            raise ValueError(f"{val} is not a valid format_name in {type(self)}")
        self._format_name = val

    @property
    def monochrome(self): return self.format_name in constants.MONOCHROME_FORMATS
    @property
    def dualchrome(self): return self.format_name in constants.DUALCHROME_FORMATS
    @property
    def rgb_format(self): return self.format_name in constants.RGB_FORMATS
    @property
    def palettized(self): return self.format_name in constants.PALETTE_SIZES

    @property
    def palette_stride(self): return constants.PALETTE_SIZES.get(self.format_name, 0)
    @property
    def palette_count(self): return 2**self.pixel_stride if self.palettized else 0
    @property
    def pixel_stride(self): return constants.PIXEL_SIZES.get(self.format_name, 0)
    @property
    def palette_size(self): return self.palette_count*self.palette_stride

    def parse(self, rawdata, *, pixel_interop_edits=True):
        super().parse(rawdata)

        tex_flags, format_id, mipmaps, width, height = \
           TEXTURE_CACHE_HEADER_STRUCT.unpack(
               rawdata.read(TEXTURE_CACHE_HEADER_STRUCT.size)
               )

        self.format_id = format_id
        self.width     = width
        self.height    = height

        self.has_alpha  = bool(tex_flags & TEXTURE_CACHE_FLAG_HAS_ALPHA)
        self.twiddled   = bool(tex_flags & TEXTURE_CACHE_FLAG_TWIDDLED)
        self.large_vq   = bool(tex_flags & TEXTURE_CACHE_FLAG_SMALL_VQ)
        self.small_vq   = bool(tex_flags & TEXTURE_CACHE_FLAG_LARGE_VQ)

        start = rawdata.tell()
        self.parse_palette(rawdata, pixel_interop_edits=pixel_interop_edits)
        self.parse_textures(rawdata, pixel_interop_edits=pixel_interop_edits)
        texture_size = rawdata.tell() - start

        # seek past the padding
        pad_size = util.calculate_padding(texture_size, self.texture_chunk_size)
        rawdata.seek(pad_size, os.SEEK_CUR)

    def serialize(self, *, pixel_interop_edits=True):
        self.cache_type_version = TEXTURE_CACHE_VER
        tex_flags = (
            (TEXTURE_CACHE_FLAG_HAS_ALPHA * bool(self.has_alpha)) |
            (TEXTURE_CACHE_FLAG_TWIDDLED  * bool(self.twiddled))  |
            (TEXTURE_CACHE_FLAG_SMALL_VQ  * bool(self.small_vq))  |
            (TEXTURE_CACHE_FLAG_LARGE_VQ  * bool(self.large_vq))
            )

        tex_header_rawdata = TEXTURE_CACHE_HEADER_STRUCT.pack(
            tex_flags, self.format_id, max(0, self.mipmaps - 1),
            self.width, self.height
            )

        cache_header_rawdata = super().serialize()
        palette_data = self.serialize_palette(pixel_interop_edits=pixel_interop_edits)
        texture_data = self.serialize_textures(pixel_interop_edits=pixel_interop_edits)

        # pad to buffer chunk size
        padding = b'\x00' * util.calculate_padding(
            len(texture_data) + len(palette_data), self.texture_chunk_size
            )
        return (cache_header_rawdata + tex_header_rawdata +
                palette_data + texture_data + padding)

    def parse_palette(self, rawdata, *, pixel_interop_edits=True):
        palette = rawdata.read(self.palette_size)
        if len(palette) != self.palette_size:
            raise ValueError("Palette data is truncated. Unable to parse texture cache.")

        self.palette = palette

    def parse_textures(self, rawdata, *, pixel_interop_edits=True):
        mip_width  = self.width
        mip_height = self.height

        textures = []
        for i in range(self.mipmaps + 1):
            mipmap_size = (mip_width*mip_height*self.pixel_stride)//8
            mipmap_data = rawdata.read(mipmap_size)

            if len(mipmap_data) < mipmap_size:
                if i == 0:
                    raise ValueError("Texture data is truncated. Unable to parse texture cache.")
                print(f"Warning: Detected truncated bitmap data. Cannot load mip {i} or higher.")
                break

            textures.append(mipmap_data)
            mip_width  = (mip_width + 1)//2
            mip_height = (mip_height + 1)//2

        # make 4-bit indexing/monochrome into 8-bit for easy manipulation
        if pixel_interop_edits and self.pixel_stride < 8:
            rescaler = (
                tex_conv.INDEXING_4BPP_TO_8BPP if self.palettized else
                tex_conv.MONOCHROME_4BPP_TO_8BPP
                )
            textures = [
                tex_conv.rescale_4bit_array_to_8bit(texture, rescaler)
                for texture in textures
                ]

        self.textures = textures

    def serialize_palette(self, *, pixel_interop_edits=True):
        palette_data = bytearray(self.palette)
        if len(palette_data) != self.palette_size:
            raise ValueError("Palette data is incorrect size. Unable to serialize texture cache.")

        return palette_data

    def serialize_textures(self, *, pixel_interop_edits=True):
        max_mipmaps = max(0, len(self.textures) - 1)
        if self.mipmaps > max_mipmaps:
            print(f"Warning: Reducing mipmaps from {self.mipmaps} to {max_mipmaps}")
            self.mipmaps = max_mipmaps

        texture_data = bytearray().join(self.textures[i] for i in range(self.mipmaps + 1))

        # pack 8-bit indexing/monochrome back to 4-bit
        if pixel_interop_edits and self.pixel_stride < 8:
            rescaler = (
                tex_conv.INDEXING_8BPP_TO_4BPP if self.palettized else
                tex_conv.MONOCHROME_8BPP_TO_4BPP
                )
            texture_data = tex_conv.rescale_8bit_array_to_4bit(texture_data, rescaler)

        return texture_data

    def _buffer_byteswap(self, pixel_buffers):
        itemsize = (
            self.palette_stride
            if self.palettized else
            (self.pixel_stride//8)
            )
        if itemsize <= 1:
            return

        swap_map = tuple(range(itemsize))[::-1]

        # swap from little to big endian
        for pixels in pixel_buffers:
            arbytmap.bitmap_io.swap_array_items(pixels, swap_map)


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
    texture_chunk_size = constants.PS2_TEXTURE_BUFFER_CHUNK_SIZE

    cache_type = constants.TEXTURE_CACHE_EXTENSION_PS2

    def _ps2_palette_shuffle(self, palette):
        # gauntlet textures have every OTHER pair of 8 palette entries
        # swapped with each other for some reason. The exceptions to
        # to this pattern are the first and last set of 8. undo that
        stride = 8 * self.palette_stride

        # multiply by 4 instead of 2 to skip every other pair
        for i in range(stride, len(palette)-stride, stride*4):
            temp_pixels                   = palette[i:        i+stride]
            palette[i:        i+stride]   = palette[i+stride: i+stride*2]
            palette[i+stride: i+stride*2] = temp_pixels

    def parse_palette(self, rawdata, *, pixel_interop_edits=True):
        super().parse_palette(rawdata, pixel_interop_edits=pixel_interop_edits)
        if pixel_interop_edits and self.palettized:
            self.palette = bytearray(self.palette)
            self._ps2_palette_shuffle(self.palette)
            tex_conv.channel_swap_bgra_rgba_array([self.palette], self.palette_stride)

    def parse_textures(self, rawdata, *, pixel_interop_edits=True):
        super().parse_textures(rawdata, pixel_interop_edits=pixel_interop_edits)
        if pixel_interop_edits and self.rgb_format and not self.palettized:
            self.textures = [bytearray(t) for t in self.textures]
            tex_conv.channel_swap_bgra_rgba_array(self.textures, self.pixel_stride // 8)

    def serialize_palette(self, *, pixel_interop_edits=True):
        palette = super().serialize_palette(pixel_interop_edits=pixel_interop_edits)
        if pixel_interop_edits and self.palettized:
            self._ps2_palette_shuffle(palette)
            tex_conv.channel_swap_bgra_rgba_array([palette], self.palette_stride)

        return palette

    def serialize_textures(self, *, pixel_interop_edits=True):
        texture_data = super().serialize_textures(pixel_interop_edits=pixel_interop_edits)
        if pixel_interop_edits and self.rgb_format and not self.palettized:
            tex_conv.channel_swap_bgra_rgba_array([texture_data], self.pixel_stride // 8)

        return texture_data


class XboxTextureCache(Ps2TextureCache):
    # same in every way
    cache_type = constants.TEXTURE_CACHE_EXTENSION_XBOX


class GamecubeTextureCache(TextureCache):
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
    cache_type = constants.TEXTURE_CACHE_EXTENSION_NGC

    def __init__(self):
        super().__init__()
        # gamecube exclusive fuckery(they're the same format)
        for fmt in (constants.PIX_FMT_XBGR_1555,
                    constants.PIX_FMT_ABGR_1555,
                    constants.PIX_FMT_XBGR_3555_NGC):
            self.format_name_to_id[fmt] = 0

    @property
    def format_name(self):
        return self._format_name
    @format_name.setter
    def format_name(self, val):
        # MIDWAY HACK
        if val == constants.PIX_FMT_ABGR_1555:
            val = constants.PIX_FMT_ABGR_3555_NGC
        elif val == constants.PIX_FMT_XBGR_1555:
            val = constants.PIX_FMT_XBGR_3555_NGC
        elif val not in self.format_name_to_id:
            raise ValueError(f"{val} is not a valid format_name in {type(self)}")

        self._format_name = val

    def _ngc_swizzle(self, textures, unswizzle):
        # (un)swizzle the textures from gamecube
        return texture_util.swizzle_ngc_gauntlet_textures(
            textures, width=self.width, height=self.height,
            bits_per_pixel=self.pixel_stride, unswizzle=unswizzle
            )

    def parse_palette(self, rawdata, *, pixel_interop_edits=True):
        super().parse_palette(rawdata, pixel_interop_edits=pixel_interop_edits)

        if pixel_interop_edits and self.palettized:
            palette = bytearray(self.palette)
            self._buffer_byteswap([palette]) # byteswap colors
            self.palette = palette

    def parse_textures(self, rawdata, *, pixel_interop_edits=True):
        super().parse_textures(rawdata, pixel_interop_edits=pixel_interop_edits)
        textures = [bytearray(b) for b in self.textures]

        if pixel_interop_edits:
            textures = self._ngc_swizzle(textures, unswizzle=True)
            if not self.palettized:
                self._buffer_byteswap(textures) # byteswap colors

        self.textures = textures

    def serialize_palette(self, *, pixel_interop_edits=True):
        palette_bytes = super().serialize_palette(pixel_interop_edits=pixel_interop_edits)

        if pixel_interop_edits and self.palettized:
            self._buffer_byteswap([palette_bytes]) # byteswap colors

        return palette_bytes

    def serialize_textures(self, *, pixel_interop_edits=True):
        max_mipmaps = max(0, len(self.textures) - 1)
        if self.mipmaps > max_mipmaps:
            print(f"Warning: Reducing mipmaps from {self.mipmaps} to {max_mipmaps}")
            self.mipmaps = max_mipmaps

        orig_textures = self.textures
        try:
            self.textures = [bytearray(t) for t in self.textures[:self.mipmaps + 1]]

            if pixel_interop_edits:
                self.textures = self._ngc_swizzle(self.textures, unswizzle=False)
                if not self.palettized:
                    self._buffer_byteswap(self.textures) # byteswap colors

            texture_data = super().serialize_textures(pixel_interop_edits=pixel_interop_edits)
        finally:
            self.textures = orig_textures

        return texture_data


class DreamcastTextureCache(TextureCache):
    # dreamcast exclusive formats
    format_id_to_name = {
        0: constants.PIX_FMT_ABGR_1555,
        1: constants.PIX_FMT_BGR_565,
        2: constants.PIX_FMT_ABGR_4444,
        }
    cache_type = constants.TEXTURE_CACHE_EXTENSION_DC

    @property
    def palettized(self):
        # only handling vq palettized
        return (self.large_vq or self.small_vq)
    @property
    def palette_stride(self):
        # always 4 pixels per vq entry, with 2 bytes per pixel.
        return 8 if self.palettized else 0
    @property
    def palette_count(self):
        if not self.palettized:
            palette_count = 0
        elif self.large_vq or (self.small_vq and self.width > 64):
            palette_count = 256
        elif self.width == 64:
            palette_count = 128
        elif self.width == 32 and self.mipmaps:
            palette_count = 64
        elif self.width == 32:
            palette_count = 32
        elif self.width <= 16:
            palette_count = 16

        return palette_count
    @property
    def pixel_stride(self):
        # always 8-bit indexing for palettized
        return 8 if self.palettized else constants.PIXEL_SIZES.get(self.format_name, 0)

    def _dc_twiddle(self, textures, untwiddle):
        # (un)twiddle the textures from dreamcast
        return texture_util.twiddle_gauntlet_textures(
            textures, width=self.width, height=self.height,
            bits_per_pixel=self.pixel_stride,
            is_vq=(self.large_vq or self.small_vq), unswizzle=untwiddle,
            )

    def parse_textures(self, rawdata, *, pixel_interop_edits=True):
        is_square = (self.width == self.height)
        if (self.large_vq or self.small_vq) and not is_square:
            raise ValueError("Vector-quantized textures must be square.")

        mip_dims = []
        if self.mipmaps:
            if not is_square:
                raise ValueError("Mipmap count non-zero in rectangular Dreamcast texture.")

            # don't bother using the mipmaps count. for dreamcast, there are always
            # mipmaps starting from 1 x 1 all the way up to width x height
            mipmaps = int(math.ceil(math.log(self.width, 2)))
            # mips stored in reverse
            mip_dims = [(2**d, 2**d) for d in range(mipmaps)]

        mip_dims.append((self.width, self.height))

        textures = []
        for i in range(len(mip_dims)):
            w, h = mip_dims[i]
            # vector quantized textures store a palette of 2x2 textures
            if self.large_vq or self.small_vq:
                mipmap_size = max((w*h)//4, 1)
            else:
                mipmap_size = (w*h*self.pixel_stride)//8
                if w == 1 and h == 1 and mipmap_size == 2:
                    # pixels are stored in at least 4 bytes. skip first 2
                    rawdata.read(2)

            mipmap_data = rawdata.read(mipmap_size)

            if len(mipmap_data) < mipmap_size:
                if w == self.width:
                    raise ValueError("Texture data is truncated. Unable to parse texture cache.")
                print(f"Warning: Detected truncated bitmap data. Cannot load mip {i} or higher.")
                self.width  = w
                self.height = h
                break

            textures.append(mipmap_data)

        # since mips are stored in reverse, reverse them to match our standard(big to small)
        textures = textures[::-1]

        if pixel_interop_edits and self.twiddled:
            textures = self._dc_twiddle([bytearray(t) for t in textures], untwiddle=True)

        # skip past the 8 bytes of 0xFF
        rawdata.seek(8, os.SEEK_CUR)
        self.textures = textures

    def serialize_textures(self, *, pixel_interop_edits=True):
        mip_count = (len(self.textures) - 1)
        if (self.width == self.height and self.mipmaps and
            self.width != 2**mip_count):
            raise ValueError(
                f"Mipmap count({mip_count}) does not match expected "
                f"value({int(math.log2(max(1, self.width)))})."
                )
        elif not self.textures:
            return bytearray()

        textures = list(self.textures)
        if not self.mipmaps or self.width != self.height:
            # no mipmaps, or rectangular texture(can't have mipmaps)
            # use highest resolution texture only
            textures = textures[:1]

        if pixel_interop_edits and self.twiddled:
            textures = self._dc_twiddle([bytearray(t) for t in textures], untwiddle=False)

        # mips stored in reverse
        texture_data = bytearray().join(textures[::-1])

        if self.mipmaps and self.width == self.height:
            # textures must be at least 4 bytes, but the first will be
            # a 1x1 which is 2 bytes. pad it on the beginning of the data
            texture_data = bytearray(2) + texture_data

        # for some reason the texture data always stores an extra 8 bytes of 0xFF
        texture_data += b'\xFF' * 8

        return texture_data


class ArcadeTextureCache(TextureCache):
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
    ncc_table = None
    cache_type = constants.TEXTURE_CACHE_EXTENSION_ARC

    def parse(self, rawdata):
        super().parse(rawdata)
        if self.format_name in (constants.PIX_FMT_YIQ_422,
                                constants.PIX_FMT_AYIQ_8422):
            ncc_rawdata = rawdata.read(48)
            if len(ncc_rawdata) != 48:
                raise ValueError("Cannot read NCC table data. Unable to parse texture cache.")

            ncc_table = NccTable()
            ncc_table.import_from_rawdata(ncc_rawdata)
        else:
            ncc_table = None

        self.ncc_table = ncc_table

    def serialize(self):
        texture_cache_rawdata = super().serialize()
        if self.format_name in (constants.PIX_FMT_YIQ_422,
                                constants.PIX_FMT_AYIQ_8422):
            ncc_table_rawdata = self.ncc_table.export_to_rawdata()
        else:
            ncc_table_rawdata = bytearray()

        return texture_cache_rawdata + ncc_table_rawdata


TextureCache._sub_classes = {
    cls.cache_type: cls for cls in (
        Ps2TextureCache, XboxTextureCache, GamecubeTextureCache,
        DreamcastTextureCache, ArcadeTextureCache
        )
    }
