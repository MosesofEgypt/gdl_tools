import hashlib
import math
import struct

from copy import deepcopy
from traceback import format_exc
from .. import util
from . import arbytmap_ext as arbytmap
from . import constants as c
from . import texture_util
from . import texture_conversions as tex_conv
from .texture_cache import TextureCache, Ps2TextureCache, XboxTextureCache,\
     GamecubeTextureCache, DreamcastTextureCache, ArcadeTextureCache


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

    def import_asset(self, input_filepath, target_format=None, **kwargs):
        if target_format is None:
            target_format = self.target_format

        arby = arbytmap.Arbytmap()
        arby.load_from_file(input_path=input_filepath)
        self.from_arbytmap_instance(arby, target_format, **kwargs)

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
            keep_alpha=self.has_alpha or "A" in self.format_name
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
        self.ncc_table = getattr(texture_cache, "ncc_table", None)

    def compile_g3d(self, cache_type):
        texture_cache = TextureCache.get_cache_class_from_cache_type(cache_type)()

        textures = self.textures
        # gamecube only stores the fullsize texture
        if isinstance(texture_cache, GamecubeTextureCache):
            textures = tuple(textures[:1])

        # copy the textures to the cache
        texture_cache.textures      = tuple(bytes(t) for t in textures)
        texture_cache.height        = self.width
        texture_cache.height        = self.height
        texture_cache.format_name   = self.format_name
        texture_cache.has_alpha     = self.has_alpha

        if isinstance(texture_cache, DreamcastTextureCache):
            texture_cache.twiddled  = self.twiddled
            texture_cache.large_vq  = self.large_vq
            texture_cache.small_vq  = self.small_vq
        elif isinstance(texture_cache, Ps2TextureCache):
            texture_cache.lod_k     = self.lod_k

        if texture_cache.palettized:
            texture_cache.palette   = bytes(self.palette)

        return texture_cache

    def to_arbytmap_instance(self, include_mipmaps=False):
        if not self.textures:
            return arbytmap.Arbytmap()
        elif self.format_name not in c.PIXEL_SIZES:
            raise ValueError("INVALID FORMAT: '%s'" % self.format_name)

        # make copies to keep originals unaffected
        palette, textures = deepcopy(self.palette), deepcopy(self.textures)
        mipmap_count = len(textures) - 1 if include_mipmaps else 0
        indexing_size = 8 if palette else None
        arby_format = texture_util.g3d_format_to_arby_format(
            self.format_name, self.has_alpha
            )

        texture_block = []
        palette_block = []
        if self.twiddled or self.large_vq or self.small_vq:
            # undo twiddling/vector-quantization
            raise NotImplementedError()
        elif indexing_size:
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
                    palette, 0, palette_block, arby_format,
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
                        textures[i], 0, texture_block, arby_format,
                        1, 1, 1, bitmap_size=len(textures[i])
                        )

        texture_info = dict(
            width=self.width, height=self.height, format=arby_format,
            palette=palette_block, indexing_size=indexing_size,
            target_indexing_size=8, mipmap_count=len(texture_block) - 1,
            )

        arbytmap_instance = arbytmap.Arbytmap(
            texture_info=texture_info,
            texture_block=texture_block
            )

        return arbytmap_instance

    def from_arbytmap_instance(self, arby, target_format, **kwargs):
        if target_format not in c.PIXEL_SIZES:
            raise ValueError(f"Unknown format '{target_format}'")
        elif arby.width not in c.VALID_DIMS or arby.height not in c.VALID_DIMS:
            raise ValueError(f"Invalid dimensions: {arby.width}x{arby.height}")

        keep_alpha  = kwargs.pop("keep_alpha", "A" in target_format)
        twiddled    = kwargs.pop("twiddled", False)
        large_vq    = kwargs.pop("large_vq", False)
        small_vq    = kwargs.pop("small_vq", False)
        optimize_format = kwargs.pop("optimize_format", True)
        max_mip_count   = int(math.ceil(max(0, min(
            c.MAX_MIP_COUNT,
            kwargs.get("mipmap_count", c.MAX_MIP_COUNT),
            math.log(max(1, min(arby.width, arby.height)), 2)
            ))))

        conv_settings = dict(
            target_format=arbytmap.FORMAT_L8,
            # need bitmaps unpacked and depalettized to work with
            palettize=False, repack=False,
            )

        source_channels = arbytmap.format_defs.CHANNEL_COUNTS[arby.format]
        target_arby_format = texture_util.g3d_format_to_arby_format(
            target_format, keep_alpha
            )
        target_channels = arbytmap.format_defs.CHANNEL_COUNTS[target_arby_format]

        # handle converting full color source bitmaps to monochrome
        conv_settings.update(
            target_format=target_arby_format,
            channel_merge_mapping=(
                None                            if source_channels != 4 else
                arbytmap.constants.M_ARGB_TO_LA if target_channels == 2 else
                arbytmap.constants.M_ARGB_TO_L  if target_channels == 1 else
                None
                )
            )

        indexing_size = (
            None if target_format in c.MONOCHROME_FORMATS else
            8 if "IDX_8" in target_format else
            4 if "IDX_4" in target_format else
            None
            )

        arby.load_new_conversion_settings(**conv_settings)
        arby.unpack_all()  # unpack to depalettize
        arby.generate_mipmaps()

        if (optimize_format and target_format in c.DEPAL_FMT_MAP and
            arby.width * arby.height <= (1 << indexing_size)):
            # texture is small enough to not benefit from palettization.
            indexing_size = None
            target_format = c.DEPAL_FMT_MAP[target_format]

        palette   = None
        textures  = []
        ncc_table = None

        # arbytmap stores textures in a particular way.
        # collect the pixels for each mipmap
        for m in range(1 + max(0, min(arby.mipmap_count, max_mip_count))):
            i = m*arby.sub_bitmap_count
            textures.append(arby.texture_block[i])

        # NOTE: need to determine if gamecube can handle 32bit color,
        #       and if so, does the alpha need to be halved or not.
        
        if twiddled or large_vq or small_vq:
            # apply dreamcast twiddling/vector-quantization
            if c.PIXEL_SIZES[target_format] != 16:
                raise NotImplementedError("Dreamcast does not support non-16bit textures.")

            raise NotImplementedError()
        elif indexing_size:
            # palettize
            palette, textures, palette_size = texture_util.palettize_textures(
                textures, 1 << indexing_size, 16 if optimize_format else None
                )
            # replace the indexing size in the format name with the recalculated
            # size determined from how many colors are in the palette. Do this
            # by cutting the name off at the indexing size and replacing it
            size_str      = "IDX_4" if palette_size == 16 else "IDX_8"
            target_format = target_format.split("IDX_")[0] + size_str

            # pack the palette
            if target_format in (c.PIX_FMT_ABGR_3555_IDX_4_NGC,
                                 c.PIX_FMT_ABGR_3555_IDX_8_NGC):
                palette = tex_conv.argb_8888_to_3555(palette)
            else:
                palette = arby.pack_raw(palette)

            palette = bytearray(palette)
        elif textures:
            # pack the textures
            if target_format == c.PIX_FMT_ABGR_3555_NGC:
                textures = [bytearray(tex_conv.argb_8888_to_3555(tex, False)) for tex in textures]
            elif target_format == c.PIX_FMT_XBGR_3555_NGC:
                textures = [bytearray(tex_conv.argb_8888_to_3555(tex,  True)) for tex in textures]
            elif target_format == c.PIX_FMT_AYIQ_8422:
                ncc_table = ncc.NccTable()
                ncc_table.calculate_from_pixels(textures[0])
                textures = [bytearray(
                    tex_conv.argb_8888_to_ayiq_8422(tex, ncc_table)
                    ) for tex in textures]
            elif target_format == c.PIX_FMT_YIQ_422:
                ncc_table = ncc.NccTable()
                ncc_table.calculate_from_pixels(textures[0])
                textures = [bytearray(
                    tex_conv.xrgb_8888_to_yiq_422(tex, ncc_table)
                    ) for tex in textures]
            else:
                textures = [bytearray(arby.pack_raw(tex)) for tex in textures]

        # load the results into this G3DTexture
        self.width  = arby.width
        self.height = arby.height
        self.lod_k  = c.DEFAULT_TEX_LOD_K

        self.has_alpha   = ("A" in arby.format)
        self.twiddled    = twiddled
        self.large_vq    = large_vq
        self.small_vq    = small_vq
        self.channel_map = tuple(arby.channel_mapping)
        self.format_name = target_format

        self.palette    = palette
        self.textures   = textures
        self.ncc_table  = ncc_table
