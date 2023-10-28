import os
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
    def monochrome(self):
        return self.format in constants.MONOCHROME_FORMATS
    @property
    def palettized(self):
        return self.format in constants.PALETTE_SIZES

    @property
    def format_name(self):
        return self._format_name
    @format_name.setter
    def format_name(self, val):
        if val not in self.format_name_to_id:
            raise ValueError(f"{val} is not a valid format_name in {type(self)}")
        self._format_name = val

    @property
    def palette_stride(self):
        return constants.PALETTE_SIZES.get(self.format_name, 0)
    @property
    def palette_count(self):
        return 2**self.pixel_stride if self.palettized else 0
    @property
    def pixel_stride(self):
        return constants.PIXEL_SIZES.get(self.format_name, 0)

    @property
    def palette_size(self):
        return self.palette_count*self.palette_stride

    def parse(self, rawdata):
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
        self.parse_palette(rawdata)
        self.parse_textures(rawdata)
        texture_size = rawdata.tell() - start

        # seek past the padding
        pad_size = util.calculate_padding(texture_size, self.texture_chunk_size)
        rawdata.seek(pad_size, os.SEEK_CUR)

    def serialize(self):
        self.cache_type_version = TEXTURE_CACHE_VER
        tex_flags = (
            (TEXTURE_CACHE_FLAG_HAS_ALPHA * bool(self.has_normals)) |
            (TEXTURE_CACHE_FLAG_TWIDDLED  * bool(self.has_colors))  |
            (TEXTURE_CACHE_FLAG_SMALL_VQ  * bool(self.small_vq))    |
            (TEXTURE_CACHE_FLAG_LARGE_VQ  * bool(self.large_vq))
            )

        tex_header_rawdata = TEXTURE_CACHE_HEADER_STRUCT.pack(
            tex_flags, self.format_id, max(0, self.mipmaps - 1),
            self.width, self.height
            )

        cache_header_rawdata = super().serialize()
        palette_data = self.serialize_palette()
        texture_data = self.serialize_textures()

        # pad to buffer chunk size
        padding = b'\x00' * util.calculate_padding(
            len(texture_data) + len(palette_data), self.texture_chunk_size
            )
        return (cache_header_rawdata + tex_header_rawdata +
                palette_data + texture_data + padding)

    def parse_palette(self, rawdata):
        palette = rawdata.read(self.palette_size)
        if len(palette) != self.palette_size:
            raise ValueError("Palette data is truncated. Unable to parse texture cache.")

        self.palette = palette

    def parse_textures(self, rawdata):
        mip_width       = self.width
        mip_height      = self.height
        pixel_stride    = constants.PIXEL_SIZES[self.format_name]

        textures = []
        for i in range(self.mipmaps + 1):
            mipmap_size = (mip_width*mip_height*pixel_stride)//8
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
        if constants.PIXEL_SIZES.get(self.format_name, 0) < 8:
            rescaler_4bpp = (
                tex_conv.INDEXING_8BPP_TO_4BPP if self.palettized else
                tex_conv.MONOCHROME_8BPP_TO_4BPP
                )
            textures = [
                tex_conv.rescale_4bit_array_to_8bit(texture, rescaler_4bpp)
                for texture in textures
                ]

        self.textures = textures

    def serialize_palette(self):
        palette_data = bytearray(self.palette)
        if len(palette_data) != self.palette_size:
            raise ValueError("Palette data is incorrect size. Unable to serialize texture cache.")

        return palette_data

    def serialize_textures(self):
        max_mipmaps = max(0, len(self.textures) - 1)
        if self.mipmaps > max_mipmaps:
            print(f"Warning: Reducing mipmaps from {self.mipmaps} to {max_mipmaps}")
            self.mipmaps = max_mipmaps

        texture_data = bytearray(b''.join(self.textures[i] for i in range(self.mipmaps + 1)))

        # pack 8-bit indexing/monochrome back to 4-bit
        if constants.PIXEL_SIZES.get(self.format_name, 0) < 8:
            rescaler_4bpp = (
                tex_conv.INDEXING_8BPP_TO_4BPP if self.palettized else
                tex_conv.MONOCHROME_8BPP_TO_4BPP
                )
            texture_data = tex_conv.rescale_8bit_array_to_4bit(texture_data, rescaler_4bpp)

        return texture_data


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

    def _ps2_palette_shuffle(self, palette):
        # gauntlet textures have every OTHER pair of 8 palette entries
        # swapped with each other for some reason. The exceptions to
        # to this pattern are the first and last set of 8. undo that
        w = 8 * self.pixel_stride

        # multiply by 4 instead of 2 to skip every other pair
        for i in range(w, len(palette)-w, w*4):
            temp_pixels         = palette[i: i+w]
            palette[i: i+w]     = palette[i+w: i+w*2]
            palette[i+w: i+w*2] = temp_pixels

    def parse_palette(self, rawdata):
        super().parse_palette(rawdata)
        if self.palettized:
            self.palette = bytearray(self.palette)
            self._ps2_palette_shuffle(self.palette)

    def serialize_palette(self):
        palette = super().serialize_palette()
        if self.palettized:
            self._ps2_palette_shuffle(palette)

        return palette


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

    def __init__(self):
        super().__init__()
        # gamecube exclusive fuckery(they're the same format)
        self.format_name_to_id[constants.PIX_FMT_XBGR_3555_NGC] = 0

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

    def _ngc_byteswap(self, pixel_buffers):
        # byteswap colors for gamecube
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

    def _ngc_swizzle(self, textures, unswizzle):
        # (un)swizzle the textures from gamecube
        pixel_stride = constants.PIXEL_SIZES.get(self.format_name, 0)

        texture_util.swizzle_ngc_gauntlet_textures(
            textures, width=self.width, height=self.height,
            bits_per_pixel=pixel_stride, unswizzle=unswizzle
            )

    def parse_palette(self, rawdata):
        super().parse_palette(rawdata)

        if self.palettized:
            palette = bytearray(self.palette)
            self._ngc_byteswap([palette])
            self.palette = bytes(palette)

    def serialize_palette(self):
        palette_bytes = super().serialize_palette()

        if self.palettized:
            self._ngc_byteswap([palette_bytes])

        return palette_bytes

    def parse_textures(self, rawdata):
        super().parse_textures(rawdata)
        textures = [bytearray(b) for b in self.textures]

        self._ngc_swizzle(textures, unswizzle=True)

        if not self.palettized:
            self._ngc_byteswap(textures)

        self.textures = textures

    def serialize_textures(self):
        max_mipmaps = max(0, len(self.textures) - 1)
        if self.mipmaps > max_mipmaps:
            print(f"Warning: Reducing mipmaps from {self.mipmaps} to {max_mipmaps}")
            self.mipmaps = max_mipmaps

        textures = [bytearray(self.textures[i]) for i in range(self.mipmaps + 1)]

        self._ngc_swizzle(textures, unswizzle=False)

        if not self.palettized:
            self._ngc_byteswap(textures)

        return bytearray.join(textures)


class DreamcastTextureCache(TextureCache):
    # dreamcast exclusive formats
    format_id_to_name = {
        0: constants.PIX_FMT_ABGR_1555,
        1: constants.PIX_FMT_ABGR_4444,
        2: constants.PIX_FMT_BGR_565,
        }

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
        # TODO: test this logic
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

    def parse_textures(self, rawdata):
        is_square = (self.width == self.height)
        if (self.large_vq or self.small_vq) and not is_square:
            raise ValueError("Vector-quantized textures must be square.")

        if self.mipmaps:
            if not is_square:
                raise ValueError("Mipmap count non-zero in rectangular Dreamcast texture.")
            elif self.width != 2**(self.mipmaps + 1):
                raise ValueError(f"Mipmap count({self.mipmaps}) does not match expected value.")

            # mips stored in reverse
            mip_dims = [(2**d, 2**d) for d in range(self.mipmaps, -1, -1)]
        else:
            mip_dims = [(self.width, self.height)]

        textures = []
        for w, h in mip_dims:
            # vector quantized textures store a palette of 2x2 textures
            if self.large_vq or self.small_vq:
                mipmap_size = (w*h)//4
            else:
                pixel_stride = constants.PIXEL_SIZES[self.format_name]//8
                mipmap_size = w*h*pixel_stride

                if pixel_stride > 1 and mipmap_size < 4:
                    # non-palettized textures each take up at least 4 bytes
                    mipmap_size = 4

            mipmap_data = rawdata.read(mipmap_size)

            if len(mipmap_data) < mipmap_size:
                if w == self.width:
                    raise ValueError("Texture data is truncated. Unable to parse texture cache.")
                print(f"Warning: Detected truncated bitmap data. Cannot load mip {i} or higher.")
                break

            textures.append(mipmap_data)

        # skip past the 8 bytes of 0xFF
        rawdata.seek(8, os.SEEK_CUR)
        self.textures = textures

    def serialize_textures(self):
        if (self.width == self.height and self.mipmaps and
            self.width != 2**(self.mipmaps + 1)):
            raise ValueError(f"Mipmap count({self.mipmaps}) does not match expected value.")
        elif not self.textures:
            return b''

        textures = list(self.textures)
        if not self.mipmaps or self.width != self.height:
            # no mipmaps, or rectangular texture(can't have mipmaps)
            # use highest resolution texture only
            textures = textures[:1]
        else:
            minsize_mipmap = bytes(textures.pop(-1))
            if len(minsize_mipmap) < 4:
                # textures must be at least 4 bytes. pad with 0x00
                minsize_mipmap = b'\x00' * (4 - len(minsize_mipmap)) + minsize_mipmap

            textures.append(minsize_mipmap)

        # mips stored in reverse
        texture_data = b''.join(self.textures[::-1])
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
            ncc_table_rawdata = b''

        return texture_cache_rawdata + ncc_table_rawdata
