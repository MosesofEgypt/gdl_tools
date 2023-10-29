import hashlib
import math
import struct

from copy import deepcopy
from traceback import format_exc
from .. import util
from . import arbytmap_ext as arbytmap
from . import constants as c
from . import texture_conversions as tex_conv
from .texture_cache import Ps2TextureCache, XboxTextureCache,\
     GamecubeTextureCache, DreamcastTextureCache, ArcadeTextureCache,\
     get_texture_cache_class_from_cache_type


class G3DTexture:
    palette  = None
    textures = ()
    width  = 0
    height = 0
    format_name = c.DEFAULT_FORMAT_NAME
    lod_k = 0

    ncc_table   = None
    twiddled    = False
    large_vq    = False
    small_vq    = False
    has_alpha   = False

    source_file_hash = b'\x00'*16
    channel_map = ()

    mono_channel_map = (-1, 0, 0, 0)
    dual_channel_map = (0, 1, 1, 1)
    argb_channel_map = (0, 1, 2, 3)

    @property
    def arbytmap_format(self):
        texinfo = texture_util.g3d_format_to_arby_texinfo(
            self.format_name, self.has_alpha
            )
        return texinfo["format"]

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
            palettize=False, repack=False,
            )

        source_channels = arbytmap.format_defs.CHANNEL_COUNTS[arby.format]
        texinfo = texture_util.g3d_format_to_arby_texinfo(
            target_format_name, keep_alpha
            )
        target_arby_format, target_channels = texinfo["format"], texinfo["channels"]

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
            palette, textures, palette_size = texture_util.palettize_textures(
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
                palette = tex_conv.argb_8888_to_3555(palette)
            else:
                palette = arby.pack_raw(palette)

            palette = bytearray(palette)
        elif textures:
            # pack the textures
            if target_format_name == c.PIX_FMT_ABGR_3555_NGC:
                textures = [bytearray(tex_conv.argb_8888_to_3555(tex, False)) for tex in textures]
            elif target_format_name == c.PIX_FMT_XBGR_3555_NGC:
                textures = [bytearray(tex_conv.argb_8888_to_3555(tex,  True)) for tex in textures]
            elif target_format_name == c.PIX_FMT_AYIQ_8422:
                self.ncc_table = ncc.NccTable()
                self.ncc_table.calculate_from_pixels(textures[0])
                textures = [bytearray(
                    tex_conv.argb_8888_to_ayiq_8422(tex, self.ncc_table)
                    ) for tex in textures]
            elif target_format_name == c.PIX_FMT_YIQ_422:
                self.ncc_table = ncc.NccTable()
                self.ncc_table.calculate_from_pixels(textures[0])
                textures = [bytearray(
                    tex_conv.xrgb_8888_to_yiq_422(tex, self.ncc_table)
                    ) for tex in textures]
            else:
                textures = [bytearray(arby.pack_raw(tex)) for tex in textures]

        # load the results into this G3DTexture
        self.width  = arby.width
        self.height = arby.height
        self.has_alpha   = ("A" in arby.format)
        self.channel_map = tuple(arby.channel_mapping)
        self.format_name = target_format_name
        self.lod_k = c.DEFAULT_TEX_LOD_K

        self.palette = palette
        self.textures = textures

        with open(input_filepath, "rb") as f:
            self.source_file_hash = hashlib.md5(f.read()).digest()

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

    def import_g3d(self, texture_cache):
        self.width  = texture_cache.width
        self.height = texture_cache.height
        self.format_name = texture_cache.format_name
        self.lod_k = texture_cache.lod_k

        self.has_alpha = texture_cache.has_alpha
        self.twiddled = texture_cache.twiddled
        self.large_vq = texture_cache.large_vq
        self.small_vq = texture_cache.small_vq

        self.channel_map = (
            self.dual_channel_map if self.format_name in (c.PIX_FMT_IA_8_IDX_88, c.PIX_FMT_AI_88) else
            self.mono_channel_map if texture_cache.monochrome else
            self.argb_channel_map
            )

        self.palette   = texture_cache.palette
        self.textures  = texture_cache.textures
        self.ncc_table = texture_cache.ncc_table

    def compile_g3d(self, cache_type):
        cache_type = get_texture_cache_class_from_cache_type
        raise NotImplementedError()

    def to_arbytmap_instance(self, include_mipmaps=False):
        if not self.textures:
            return arbytmap.Arbytmap()
        elif self.format_name not in c.PIXEL_SIZES:
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
                palette_block.append(tex_conv.argb_3555_to_8888(palette))
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
                    tex_conv.pad_pal16_to_pal256(palette_block[0])
        else:
            palette_block = None
            # convert gamecube-exclusive format to standard A8R8G8B8
            for i in range(mipmap_count + 1):
                if self.format_name in (c.PIX_FMT_ABGR_3555_NGC,
                                        c.PIX_FMT_XBGR_3555_NGC):
                    texture_block.append(tex_conv.argb_3555_to_8888(textures[i]))
                elif self.format_name == c.PIX_FMT_AYIQ_8422:
                    texture_block.append(tex_conv.ayiq_8422_to_argb_8888(textures[i], self.ncc_table))
                elif self.format_name == c.PIX_FMT_YIQ_422:
                    texture_block.append(tex_conv.yiq_422_to_xrgb_8888(textures[i], self.ncc_table))
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
