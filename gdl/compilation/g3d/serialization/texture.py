import hashlib
import math
import numpy
import struct
import scipy

from array import array
from copy import deepcopy
from traceback import format_exc
from .. import util
from . import arbytmap_ext as arbytmap
from . import pixel_functions as pf
from . import constants as c
from . import ncc

ROMTEX_HEADER_STRUCT = struct.Struct('<HH 4x bBbB 4x 16s')
#   width
#   height
#   4_padding_bytes
#   mipmap_count
#   flags
#   lod_k
#   format
#   4_padding_bytes
#   md5_of_source_asset


def is_gamecube_format(format_name):
    return "NGC" in format_name


def is_alpha_signed(format_name):
    return "BGR" in format_name


class G3DTexture:
    palette  = None
    textures = ()
    width  = 0
    height = 0
    format_name = c.DEFAULT_FORMAT_NAME
    lod_k = 0
    flags = 0
    ncc_table = ncc.NccTable()

    source_file_hash = b'\x00'*16
    channel_map = ()

    mono_channel_map = (-1, 0, 0, 0)
    dual_channel_map = (0, 1, 1, 1)
    argb_channel_map = (0, 1, 2, 3)

    @property
    def has_alpha(self):
        return self.flags & c.GTX_FLAG_HAS_ALPHA

    @property
    def arbytmap_format(self):
        arby_format, _ = self.get_arby_format_and_channel_count(self.format_name, self.has_alpha)
        return arby_format

    @property
    def is_gamecube_format(self):
        return is_gamecube_format(self.format_name)

    @staticmethod
    def get_arby_format_and_channel_count(format_name, has_alpha):
        channel_count = 4
        if format_name == c.PIX_FMT_AI_88:
            arby_format = arbytmap.FORMAT_A8L8
            channel_count = 2
        elif format_name == c.PIX_FMT_AI_44:
            arby_format = arbytmap.FORMAT_A4L4
            channel_count = 2
        elif format_name == c.PIX_FMT_AI_44:
            arby_format = arbytmap.FORMAT_A4L4
            channel_count = 2
        elif format_name == c.PIX_FMT_RGB_565:
            arby_format = arbytmap.FORMAT_R5G6B5
        elif format_name == c.PIX_FMT_RGB_332:
            arby_format = arbytmap.FORMAT_R3G3B2
        elif format_name == c.PIX_FMT_ARGB_4444:
            arby_format = arbytmap.FORMAT_A4R4G4B4
        elif format_name == c.PIX_FMT_ARGB_8332:
            arby_format = arbytmap.FORMAT_A8R3G3B2
        elif "8888" in format_name or "3555" in format_name or format_name in (
                c.PIX_FMT_YIQ_422, c.PIX_FMT_AYIQ_8422
            ):
            arby_format = (
                arbytmap.FORMAT_A8R8G8B8 if has_alpha else
                arbytmap.FORMAT_X8R8G8B8
                )
        elif "1555" in format_name:
            arby_format = (
                arbytmap.FORMAT_A1R5G5B5 if has_alpha else
                arbytmap.FORMAT_X1R5G5B5
                )
        else:
            arby_format = arbytmap.FORMAT_L8
            channel_count = 1

        return arby_format, channel_count

    @staticmethod
    def palettize_textures(textures, max_palette_size=256, min_palette_size=None):
        if min_palette_size is None:
            min_palette_size = max_palette_size

        np_palette = None
        indexings = []

        for texture in textures:
            stride = texture.itemsize if isinstance(texture, array) else 1

            # reshaping the pixels matrix
            np_texture = numpy.reshape(
                numpy.frombuffer(texture, dtype="B"),
                ((len(texture) * stride) // 4, 4)
                ).astype(float)

            # palette calculation
            if np_palette is None:
                # calculate palette
                if len(np_texture) <= max_palette_size:
                    # entire texture will fit in palette
                    np_palette = np_texture
                else:
                    # convert to a UInt32 array to group for set comparison.
                    unique_pixels = set(array("I", np_texture.astype("B").tobytes()))
                    if len(unique_pixels) <= max_palette_size:
                        np_palette = numpy.reshape(
                            # convert back to byte buffer for reshaping
                            numpy.frombuffer(array("I", unique_pixels).tobytes(), dtype="B"),
                            (len(unique_pixels), 4)
                            ).astype(float)
                    else:
                        # NOTE: it appears that kmeans doesn't work too well if
                        #       the original image was already palettized and/or
                        #       contains exactly as many colors as is necessary.
                        #       It appears to reduce the color count a bit too
                        #       far, so we'll ONLY use it if the image contains
                        #       more unique colors than fit inside the max size.
                        np_palette, _ = scipy.cluster.vq.kmeans(
                            np_texture, max_palette_size
                            )

            # indexing calculation
            np_indexing, _ = scipy.cluster.vq.vq(
                np_texture, np_palette
                )
            indexing = np_indexing.astype("B").tobytes()
            indexings.append(bytearray(indexing))

        palette_count = max_palette_size if len(np_palette) > min_palette_size else min_palette_size
        palette = bytearray(np_palette.astype("B").tobytes())
        palette.extend(b"\x00" * (palette_count * 4 - len(palette)))

        return palette, indexings, palette_count

    def import_asset(self, input_filepath, optimize_format=False, **kwargs):
        arby = arbytmap.Arbytmap()
        arby.load_from_file(input_path=input_filepath)
        if arby.width not in c.VALID_DIMS or arby.height not in c.VALID_DIMS:
            raise ValueError("Invalid dimensions: %sx%s" % (arby.width, arby.height))

        target_format_name = kwargs.pop("target_format_name", self.format_name)
        keep_alpha         = kwargs.pop("keep_alpha", "A" in target_format_name)
        max_mip_count      = max(0, min(
            c.MAX_MIP_COUNT,
            kwargs.get("mipmap_count", c.MAX_MIP_COUNT),
            # min dimension size is 8, which is 2^3, so subtract 3
            int(math.ceil(math.log(max(1, min(arby.width, arby.height)), 2)) - 3)
            ))

        conv_settings = dict(
            target_format=arbytmap.FORMAT_L8,
            # need bitmaps unpacked and depalettized to work with
            palettize=False,
            repack=False,
            )

        source_channels = arbytmap.format_defs.CHANNEL_COUNTS[arby.format]
        target_arby_format, target_channels = self.get_arby_format_and_channel_count(
            target_format_name, keep_alpha
            )

        conv_settings.update(target_format=target_arby_format)

        # handle converting full color source bitmaps to monochrome
        if source_channels == 4:
            if target_channels == 1:
                conv_settings["channel_merge_mapping"] = arbytmap.constants.M_ARGB_TO_L
            elif target_channels == 2:
                conv_settings["channel_merge_mapping"] = arbytmap.constants.M_ARGB_TO_LA

        indexing_size = (
            None if target_format_name in c.MONOCHROME_FORMATS else
            8 if "IDX_8" in target_format_name else
            4 if "IDX_4" in target_format_name else
            None
            )

        arby.load_new_conversion_settings(**conv_settings)

        arby.unpack_all()  # unpack to depalettize
        arby.generate_mipmaps()

        if (optimize_format and target_format_name in c.DEPAL_FMT_MAP and
            arby.width * arby.height <= (1 << indexing_size)):
            # texture is small enough to not benefit from palettization.
            indexing_size = None
            target_format_name = c.DEPAL_FMT_MAP[target_format_name]

        palette = None
        textures = []
        # arbytmap stores textures in a special way.
        # collect the pixels for each mipmap
        for m in range(1 + max(0, min(arby.mipmap_count, max_mip_count))):
            i = m*arby.sub_bitmap_count
            textures.append(arby.texture_block[i])

        # NOTE: need to determine if gamecube can handle 32bit color,
        #       and if so, does the alpha need to be halved or not.

        if indexing_size:
            # palettize
            palette, textures, palette_size = self.palettize_textures(
                textures, 1 << indexing_size, 16 if optimize_format else None
                )
            # replace the indexing size in the format name with the recalculated
            # size determined from how many colors are in the palette. Do this
            # by cutting the name in half at the indexing size and replacing it
            size_str = "IDX_4" if palette_size == 16 else "IDX_8"
            name_pieces = list(target_format_name.split("IDX_"))
            name_pieces[-1] = size_str + name_pieces[-1][1:]
            target_format_name = "".join(name_pieces)

            # pack the palette
            if target_format_name in (c.PIX_FMT_ABGR_3555_IDX_4_NGC,
                                      c.PIX_FMT_ABGR_3555_IDX_8_NGC):
                palette = pf.argb_8888_to_3555(palette)
            else:
                palette = arby.pack_raw(palette)

            palette = bytearray(palette)
        elif textures:
            # pack the textures
            if target_format_name == c.PIX_FMT_ABGR_3555_NGC:
                textures = [bytearray(pf.argb_8888_to_3555(tex, False)) for tex in textures]
            elif target_format_name == c.PIX_FMT_XBGR_3555_NGC:
                textures = [bytearray(pf.argb_8888_to_3555(tex,  True)) for tex in textures]
            elif target_format_name == c.PIX_FMT_AYIQ_8422:
                self.ncc_table = ncc.NccTable()
                self.ncc_table.calculate_from_pixels(textures[0])
                textures = [bytearray(
                    pf.argb_8888_to_ayiq_8422(tex, self.ncc_table)
                    ) for tex in textures]
            elif target_format_name == c.PIX_FMT_YIQ_422:
                self.ncc_table = ncc.NccTable()
                self.ncc_table.calculate_from_pixels(textures[0])
                textures = [bytearray(
                    pf.xrgb_8888_to_yiq_422(tex, self.ncc_table)
                    ) for tex in textures]
            else:
                textures = [bytearray(arby.pack_raw(tex)) for tex in textures]

        # load the results into this G3DTexture
        self.width  = arby.width
        self.height = arby.height
        self.flags  = c.GTX_FLAG_ALL & ("A" in arby.format)
        self.channel_map = tuple(arby.channel_mapping)
        self.format_name = target_format_name
        self.lod_k = c.DEFAULT_TEX_LOD_K

        self.palette = palette
        self.textures = textures

        with open(input_filepath, "rb") as f:
            self.source_file_hash = hashlib.md5(f.read()).digest()

    def import_gtx(self, input_buffer, headerless=False, flags=0, source_md5=b'\x00'*16,
                   width=0, height=0, mipmaps=0, format_name="ABGR_8888", lod_k=0,
                   is_ngc=False, is_arcade=False, buffer_end=-1, ncc_table=None
                   ):
        if not headerless:
            header = ROMTEX_HEADER_STRUCT.unpack(
                input_buffer.read(ROMTEX_HEADER_STRUCT.size)
                )
            width, height, mipmaps, flags, lod_k, format_id, source_md5 = header

            format_name = (
                c.ARC_FORMAT_ID_TO_NAME if is_arcade else
                c.FORMAT_ID_TO_NAME
                ).get(format_id, "")
            if not format_name:
                raise TypeError("Invalid format id: '%s'" % format_id)

        # MIDWAY HACK
        if is_ngc:
            if format_name == c.PIX_FMT_ABGR_1555:
                format_name = c.PIX_FMT_ABGR_3555_NGC
            elif format_name == c.PIX_FMT_XBGR_1555:
                format_name = c.PIX_FMT_XBGR_3555_NGC

        if format_name not in c.PIXEL_SIZES:
            raise TypeError("Invalid format name: '%s'" % format_name)
        elif width not in c.VALID_DIMS or height not in c.VALID_DIMS:
            raise ValueError("Invalid dimensions: %sx%s" % (width, height))

        if headerless and "A" in format_name.split("_")[0]:
            flags |= c.GTX_FLAG_HAS_ALPHA

        is_monochrome = format_name in c.MONOCHROME_FORMATS
        palette_stride = c.PALETTE_SIZES.get(format_name, 0)
        pixel_stride   = c.PIXEL_SIZES.get(format_name, 0)
        if buffer_end < 0:
            buffer_end = 1<<63  # big buffah

        palette = None
        textures = []
        if palette_stride:
            # must be bytearray to be byteswapped(if needed)
            palette_size = (2**pixel_stride)*palette_stride
            remaining_data = buffer_end - input_buffer.tell()
            palette = bytearray(input_buffer.read(palette_size))
            if palette_size > remaining_data or len(palette) < palette_size:
                raise ValueError("Error: Detected truncated palette data. Cannot import texture.")

        mip_width  = width
        mip_height = height
        for i in range(mipmaps + 1):
            mipmap_size = (mip_width*mip_height*pixel_stride)//8
            remaining_data = buffer_end - input_buffer.tell()
                
            mipmap_data = bytearray(input_buffer.read(mipmap_size))
            if mipmap_size > remaining_data or len(mipmap_data) < mipmap_size:
                if i == 0:
                    raise ValueError("Error: Detected truncated bitmap data. Cannot import texture.")
                print("Warning: Detected truncated bitmap data. Cannot load mip %s or higher." % i)
                break

            # must be bytearray to be byteswapped(if needed)
            textures.append(mipmap_data)
            mip_width  = (mip_width + 1)//2
            mip_height = (mip_height + 1)//2

        self.width  = width
        self.height = height
        self.format_name = format_name
        self.flags = flags & c.GTX_FLAG_ALL
        self.lod_k = lod_k

        # if necessary, unshuffle the palette
        if palette:
            palette_block = []
            arbytmap.bitmap_io.bitmap_bytes_to_array(
                palette, 0, palette_block, self.arbytmap_format,
                1, 1, 1, bitmap_size=len(palette)
                )
            # convert back to bytearray to ensure everything works with it
            palette = palette_block[0] = bytearray(palette_block[0])
            if not is_ngc and not is_monochrome:
                arbytmap.gauntlet_ps2_palette_shuffle(palette, palette_stride)
            rescaler_4bpp = pf.INDEXING_4BPP_TO_8BPP
        else:
            rescaler_4bpp = pf.MONOCHROME_4BPP_TO_8BPP

        # hack for 4bpp palettized to pad it up to 8bpp
        if pixel_stride < 8:
            textures = [
                pf.rescale_4bit_array_to_8bit(texture, rescaler_4bpp)
                for texture in textures
                ]

        # if necessary, deswizzle the textures and byteswap colors
        itemsize = palette_stride if palette else (pixel_stride//8)
        if is_ngc:
            textures = arbytmap.swizzle_ngc_gauntlet_textures(
                textures, width=self.width, height=self.height,
                bits_per_pixel=pixel_stride, unswizzle=True
                )

            if itemsize > 1:
                swap_map = tuple(range(itemsize))[::-1]

                # swap from big to little endian
                for pixels in ([palette] if palette else textures):
                    arbytmap.bitmap_io.swap_array_items(pixels, swap_map)

        elif not is_monochrome and itemsize > 1 and not is_arcade:
            # swap from BGRA to RGBA for ps2/xbox
            if palette:
                pf.channel_swap_bgra_rgba_array([palette], itemsize)
            else:
                pf.channel_swap_bgra_rgba_array(textures, itemsize)

        self.channel_map = (
            self.dual_channel_map if format_name in (c.PIX_FMT_IA_8_IDX_88, c.PIX_FMT_AI_88) else
            self.mono_channel_map if is_monochrome else
            self.argb_channel_map
            )

        self.palette = palette
        self.textures = textures
        self.ncc_table = ncc_table

    def export_asset(self, output_filepath, include_mipmaps=False, **kwargs):
        arbytmap_instance = self.to_arbytmap_instance(
            include_mipmaps=include_mipmaps
            )
        # depalettize to allow images to be loaded in most programs
        arbytmap_instance.palettize = False
        arbytmap_instance.unpack_all()  # unpack to depalettize
        arbytmap_instance.pack_all()    # pack for export

        arbytmap_instance.save_to_file(
            output_path=output_filepath,
            overwrite=kwargs.get('overwrite', False),
            channel_mapping=self.channel_map, mip_levels="all",
            keep_alpha=self.has_alpha
            )

    def export_gtx(self, output_buffer, headerless=False,
                   target_ngc=False, target_ps2=False, target_arcade=False
                   ):
        is_monochrome = self.format_name in c.MONOCHROME_FORMATS
        name_to_id_map = (c.ARC_FORMAT_NAME_TO_ID if target_arcade else c.FORMAT_NAME_TO_ID)

        if not self.textures:
            return
        elif self.format_name not in name_to_id_map:
            raise TypeError("INVALID FORMAT: '%s'" % self.format_name)

        if not headerless:
            output_buffer.write(ROMTEX_HEADER_STRUCT.pack(
                self.width, self.height, len(self.textures) - 1,
                self.flags & c.GTX_FLAG_ALL, self.lod_k,
                name_to_id_map[self.format_name],
                self.source_file_hash
                ))

        palette  = deepcopy(self.palette)
        textures = deepcopy(self.textures)

        palette_stride = c.PALETTE_SIZES.get(self.format_name, 0)
        pixel_stride   = c.PIXEL_SIZES.get(self.format_name, 0)

        if palette:
            palette = deepcopy(self.palette)
            # if necessary, unshuffle the palette
            if not target_ngc and self.format_name not in c.MONOCHROME_FORMATS:
                arbytmap.gauntlet_ps2_palette_shuffle(palette, palette_stride)

        itemsize = palette_stride if palette else (pixel_stride//8)
        if target_ngc:
            # swizzle the textures and byteswap colors for gamecube
            textures = arbytmap.swizzle_ngc_gauntlet_textures(
                textures, width=self.width, height=self.height,
                bits_per_pixel=pixel_stride, unswizzle=False
                )

            if itemsize > 1:
                swap_map = tuple(range(itemsize))[::-1]

                # swap from little to big endian
                for pixels in ([palette] if palette else textures):
                    arbytmap.bitmap_io.swap_array_items(pixels, swap_map)

        elif not is_monochrome and itemsize > 1:
            # swap from BGRA to RGBA for ps2 and xbox
            if palette:
                pf.channel_swap_bgra_rgba_array([palette], itemsize)
            else:
                pf.channel_swap_bgra_rgba_array(textures, itemsize)

        # hack for 4bpp palettized to unpad from 8bpp to 4bpp
        if pixel_stride < 8:
            rescaler_4bpp = (
                pf.INDEXING_8BPP_TO_4BPP if palette else
                pf.MONOCHROME_8BPP_TO_4BPP
                )
            textures = [
                pf.rescale_8bit_array_to_4bit(texture, rescaler_4bpp)
                for texture in textures
                ]

        if palette:
            output_buffer.write(palette)

        for texture in textures:
            output_buffer.write(texture)

        if target_ps2:
            output_buffer.write(b"\x00" * util.calculate_padding(
                output_buffer.tell(), c.PS2_TEXTURE_BUFFER_CHUNK_SIZE
                ))

    def to_arbytmap_instance(self, include_mipmaps=False):
        if not self.textures:
            return arbytmap.Arbytmap()
        if self.format_name not in c.PIXEL_SIZES:
            raise ValueError("INVALID FORMAT: '%s'" % self.format_name)

        # make copies to keep originals unaffected
        palette, textures = deepcopy(self.palette), deepcopy(self.textures)
        mipmap_count = len(textures) - 1 if include_mipmaps else 0
        indexing_size = 8 if palette else None

        texture_block = []
        palette_block = []
        if palette:
            # convert the palette to an array of the correct typecode for processing
            if self.format_name in (c.PIX_FMT_ABGR_3555_IDX_4_NGC,
                                    c.PIX_FMT_ABGR_3555_IDX_8_NGC):
                # convert gamecube-exclusive format to standard A8R8G8B8
                palette_block.append(pf.argb_3555_to_8888(palette))
            else:
                # NOTE: there's a bug in arbytmap that prevents it from properly
                #       handling indexing with less than 8 bits per pixel. Arbytmap
                #       is also incapable of handling any format with less than
                #       8 bits per pixel, so for now, we pad everything up to 8bit
                arbytmap.bitmap_io.bitmap_bytes_to_array(
                    palette, 0, palette_block, self.arbytmap_format,
                    1, 1, 1, bitmap_size=len(palette)
                    )

            palette_block *= mipmap_count + 1
            texture_block[:] = textures[: mipmap_count + 1]

            if "IDX_4" in self.format_name:
                if len(palette_block[0]) < 256:
                    pf.pad_pal16_to_pal256(palette_block[0])
        else:
            palette_block = None
            # convert gamecube-exclusive format to standard A8R8G8B8
            for i in range(mipmap_count + 1):
                if self.format_name in (c.PIX_FMT_ABGR_3555_NGC,
                                        c.PIX_FMT_XBGR_3555_NGC):
                    texture_block.append(pf.argb_3555_to_8888(textures[i]))
                elif self.format_name == c.PIX_FMT_AYIQ_8422:
                    texture_block.append(pf.ayiq_8422_to_argb_8888(textures[i], self.ncc_table))
                elif self.format_name == c.PIX_FMT_YIQ_422:
                    texture_block.append(pf.yiq_422_to_xrgb_8888(textures[i], self.ncc_table))
                else:
                    arbytmap.bitmap_io.bitmap_bytes_to_array(
                        textures[i], 0, texture_block, self.arbytmap_format,
                        1, 1, 1, bitmap_size=len(textures[i])
                        )

        texture_info = dict(
            width=self.width, height=self.height, format=self.arbytmap_format,
            palette=palette_block, indexing_size=indexing_size,
            target_indexing_size=8, mipmap_count=len(texture_block) - 1,
            )

        arbytmap_instance = arbytmap.Arbytmap(
            texture_info=texture_info,
            texture_block=texture_block
            )

        return arbytmap_instance
