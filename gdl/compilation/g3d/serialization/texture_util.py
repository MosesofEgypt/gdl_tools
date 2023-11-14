import numpy
import scipy

from . import constants as c
from array import array
from arbytmap.arby import swizzler
from arbytmap import format_defs, bitmap_io


def is_alpha_signed(format_name):
    return "BGR" in format_name


def g3d_format_to_arby_format(format_name, has_alpha):
    if format_name == c.PIX_FMT_AI_88:
        arby_format = format_defs.FORMAT_A8L8
    elif format_name == c.PIX_FMT_AI_44:
        arby_format = format_defs.FORMAT_A4L4
    elif format_name == c.PIX_FMT_BGR_565:
        arby_format = format_defs.FORMAT_R5G6B5
    elif format_name == c.PIX_FMT_BGR_233:
        arby_format = format_defs.FORMAT_R3G3B2
    elif format_name == c.PIX_FMT_ABGR_4444:
        arby_format = format_defs.FORMAT_A4R4G4B4
    elif format_name == c.PIX_FMT_ABGR_8233:
        arby_format = format_defs.FORMAT_A8R3G3B2
    elif "8888" in format_name or "3555" in format_name or format_name in (
            c.PIX_FMT_YIQ_422, c.PIX_FMT_AYIQ_8422
            ):
        arby_format = (
            format_defs.FORMAT_A8R8G8B8 if has_alpha else
            format_defs.FORMAT_X8R8G8B8
            )
    elif "1555" in format_name:
        arby_format = (
            format_defs.FORMAT_A1R5G5B5 if has_alpha else
            format_defs.FORMAT_X1R5G5B5
            )
    else:
        arby_format = format_defs.FORMAT_L8

    return arby_format


def retarget_format_to_platform(target_format, cache_type, has_alpha=False):
    if cache_type not in (
        c.TEXTURE_CACHE_EXTENSION_PS2, c.TEXTURE_CACHE_EXTENSION_NGC,
        c.TEXTURE_CACHE_EXTENSION_DC,  c.TEXTURE_CACHE_EXTENSION_ARC,
        c.TEXTURE_CACHE_EXTENSION_XBOX
        ):
        raise ValueError("Unknown platform cache type '{cache_type}'")

    new_format = target_format
    
    # do some format swapping depending on the target platform
    if cache_type == c.TEXTURE_CACHE_EXTENSION_NGC:
        # retarget to the format replacements gamecube uses
        if new_format in (
                # ps2/xbox formats
                c.PIX_FMT_ABGR_8888, c.PIX_FMT_XBGR_8888,
                # arcade formats
                c.PIX_FMT_ABGR_8233, c.PIX_FMT_YIQ_422, c.PIX_FMT_AYIQ_8422,
                c.PIX_FMT_A_8, c.PIX_FMT_I_8, c.PIX_FMT_AI_44, c.PIX_FMT_AI_88,
                # arcade/dreamcast formats
                c.PIX_FMT_BGR_565, c.PIX_FMT_ABGR_4444
                ):
            new_format = c.PIX_FMT_ABGR_3555_NGC if has_alpha else c.PIX_FMT_XBGR_3555_NGC
        elif new_format == c.PIX_FMT_XBGR_8888_IDX_4:
            new_format = c.PIX_FMT_ABGR_8888_IDX_4
        elif new_format == c.PIX_FMT_XBGR_8888_IDX_8:
            new_format = c.PIX_FMT_ABGR_8888_IDX_8
    else:
        # target away from gamecube-exclusive formats
        if new_format in (c.PIX_FMT_ABGR_3555_NGC, c.PIX_FMT_XBGR_3555_NGC):
            new_format = c.PIX_FMT_ABGR_8888 if has_alpha else c.PIX_FMT_XBGR_1555
        elif new_format == c.PIX_FMT_ABGR_3555_IDX_4_NGC:
            new_format = c.PIX_FMT_ABGR_8888_IDX_4
        elif new_format == c.PIX_FMT_ABGR_3555_IDX_8_NGC:
            new_format = c.PIX_FMT_ABGR_8888_IDX_8

    if cache_type == c.TEXTURE_CACHE_EXTENSION_ARC:
        # retarget to the formats arcade uses
        if new_format in (
                # 32-bit formats with alpha
                c.PIX_FMT_ABGR_8888, c.PIX_FMT_XBGR_8888,
                c.PIX_FMT_ABGR_8888_IDX_4, c.PIX_FMT_ABGR_8888_IDX_8,
                c.PIX_FMT_XBGR_8888_IDX_4, c.PIX_FMT_XBGR_8888_IDX_8,
                ):
            # gotta compromise on alpha and color depth
            new_format = c.PIX_FMT_ABGR_4444 if has_alpha else c.PIX_FMT_BGR_565
        elif new_format in (
                # 16-bit formats
                c.PIX_FMT_XBGR_1555_IDX_4, c.PIX_FMT_ABGR_1555_IDX_4,
                c.PIX_FMT_XBGR_1555_IDX_8, c.PIX_FMT_ABGR_1555_IDX_8,
                c.PIX_FMT_XBGR_1555
                ):
            new_format = c.PIX_FMT_ABGR_1555
        elif new_format in (c.PIX_FMT_A_4_IDX_4, c.PIX_FMT_A_8_IDX_8):
            new_format = c.PIX_FMT_A_8
        elif new_format in (c.PIX_FMT_I_4_IDX_4, c.PIX_FMT_I_8_IDX_8):
            new_format = c.PIX_FMT_I_8
    else:
        # target away from arcade-exclusive formats
        if new_format == c.PIX_FMT_AI_44:
            new_format = c.PIX_FMT_ABGR_4444
        elif new_format == c.PIX_FMT_A_8:
            new_format = c.PIX_FMT_A_8_IDX_8
        elif new_format == c.PIX_FMT_I_8:
            new_format = c.PIX_FMT_I_8_IDX_8
        elif new_format in (c.PIX_FMT_YIQ_422, c.PIX_FMT_BGR_233):
            new_format = c.PIX_FMT_BGR_565
        elif new_format in (
                c.PIX_FMT_ABGR_8233, c.PIX_FMT_AYIQ_8422, c.PIX_FMT_AI_88
                ):
            new_format = c.PIX_FMT_ABGR_8888

    if cache_type == c.TEXTURE_CACHE_EXTENSION_DC:
        # retarget to the formats dreamcast uses
        if new_format in (
                # 32-bit formats with alpha
                c.PIX_FMT_ABGR_8888, c.PIX_FMT_XBGR_8888,
                c.PIX_FMT_ABGR_8888_IDX_4, c.PIX_FMT_ABGR_8888_IDX_8,
                c.PIX_FMT_XBGR_8888_IDX_4, c.PIX_FMT_XBGR_8888_IDX_8,
                # 8-bit/4-bit monochrome formats
                c.PIX_FMT_A_8_IDX_8, c.PIX_FMT_I_8_IDX_8,
                c.PIX_FMT_A_4_IDX_4, c.PIX_FMT_I_4_IDX_4,
                ):
            # gotta compromise on alpha and color depth
            new_format = c.PIX_FMT_ABGR_4444 if has_alpha else c.PIX_FMT_BGR_565
        elif new_format in (
                # 16-bit formats without alpha
                c.PIX_FMT_XBGR_1555_IDX_4, c.PIX_FMT_ABGR_1555_IDX_4,
                c.PIX_FMT_XBGR_1555_IDX_8, c.PIX_FMT_ABGR_1555_IDX_8,
                ):
            new_format = c.PIX_FMT_ABGR_1555
    else:
        # target away from dreamcast-exclusive formats
        if new_format == c.PIX_FMT_ABGR_4444:
            new_format = c.PIX_FMT_ABGR_8888
        elif new_format == c.PIX_FMT_BGR_565:
            # losing 1-bit depth in green isn't a big deal for half-size
            new_format = c.PIX_FMT_XBGR_1555

    return new_format


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


def swizzle_dc_vq_gauntlet_textures(
        textures, width, height, bits_per_pixel, unswizzle=True
        ):
    return _swizzle_gauntlet_textures(
        textures, width, height, bits_per_pixel, "dc_vq",
        unswizzle, min_width=2, min_height=2
        )

def twiddle_gauntlet_textures(
        textures, width, height, bits_per_pixel, unswizzle=True, is_vq=False
        ):
    if is_vq:
        width   = width // 2
        height  = height // 2

    return _swizzle_gauntlet_textures(
        textures, width, height, bits_per_pixel, "twiddled", unswizzle
        )

def swizzle_ngc_gauntlet_textures(
        textures, width, height, bits_per_pixel, unswizzle=True
        ):
    return _swizzle_gauntlet_textures(
        textures, width, height, bits_per_pixel, "ngc", unswizzle
        )
    
def _swizzle_gauntlet_textures(
        textures, width, height, bits_per_pixel, platform, unswizzle,
        min_width=1, min_height=1
        ):
    '''
    Swizzles or unswizzles Gamecube/Dreamcast Gauntlet textures.
    Swizzle pattern used depends on the bits-per-pixel.
    '''
    is_ngc      = platform == "ngc"
    is_dc_vq    = platform == "dc_vq"
    is_twiddled = platform == "twiddled"
    assert is_ngc or is_dc_vq or is_twiddled

    mask_type = (
        "DC_GAUNTLET_TWIDDLED"  if is_twiddled          else
        "DC_GAUNTLET_VQ"        if is_dc_vq             else
        "NGC_GAUNTLET_4BPP"     if bits_per_pixel == 4  else
        "NGC_GAUNTLET_8BPP"     if bits_per_pixel == 8  else
        "NGC_GAUNTLET_16BPP"    if bits_per_pixel == 16 else
        "NGC_GAUNTLET_32BPP"
        )
    swizz = swizzler.Swizzler(mask_type = mask_type)

    # ngc 4bpp hack to fix each pair of pixels per byte unpacking swapped
    ngc_4bpp = is_ngc and bits_per_pixel == 4
    channel_count = 1 if bits_per_pixel <= 8 else bits_per_pixel // 8
    
    if ngc_4bpp and not unswizzle:
        [bitmap_io.swap_array_items(t, (1, 0)) for t in textures]

    swizzled = [
        swizz.swizzle_single_array(
            texture, not unswizzle, channel_count,
            max(width  >> i, min_width),
            max(height >> i, min_height),
            1,
            )
        for i, texture in enumerate(textures)
        ]

    if ngc_4bpp and unswizzle:
        [bitmap_io.swap_array_items(t, (1, 0)) for t in swizzled]

    return swizzled
