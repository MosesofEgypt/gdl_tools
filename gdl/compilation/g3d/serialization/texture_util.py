import arbytmap
import numpy
import scipy

from . import constants
from array import array
from arbytmap.arby import swizzler


def is_gamecube_format(format_name):
    return "NGC" in format_name


def is_alpha_signed(format_name):
    return "BGR" in format_name


def g3d_format_to_arby_texinfo(format_name, has_alpha):
    channel_count = 4
    if format_name == constants.PIX_FMT_AI_88:
        arby_format = arbytmap.FORMAT_A8L8
        channel_count = 2
    elif format_name == constants.PIX_FMT_AI_44:
        arby_format = arbytmap.FORMAT_A4L4
        channel_count = 2
    elif format_name == constants.PIX_FMT_BGR_565:
        arby_format = arbytmap.FORMAT_R5G6B5
    elif format_name == constants.PIX_FMT_BGR_233:
        arby_format = arbytmap.FORMAT_R3G3B2
    elif format_name == constants.PIX_FMT_ABGR_4444:
        arby_format = arbytmap.FORMAT_A4R4G4B4
    elif format_name == constants.PIX_FMT_ABGR_8233:
        arby_format = arbytmap.FORMAT_A8R3G3B2
    elif "8888" in format_name or "3555" in format_name or format_name in (
            constants.PIX_FMT_YIQ_422, constants.PIX_FMT_AYIQ_8422
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

    return dict(
        format=arby_format, channels=channel_count
        )


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


def gauntlet_ps2_palette_shuffle(palette, pixel_stride):
    # gauntlet textures have every OTHER pair of 8 palette entries
    # swapped with each other for some reason. The exceptions to
    # to this pattern are the first and last set of 8. undo that
    w = 8 * pixel_stride

    # multiply by 4 instead of 2 to skip every other pair
    for i in range(w, len(palette)-w, w*4):
        temp_pixels         = palette[i: i+w]
        palette[i: i+w]     = palette[i+w: i+w*2]
        palette[i+w: i+w*2] = temp_pixels


def swizzle_dc_gauntlet_textures(
        textures, width, height, bits_per_pixel, unswizzle=True
        ):
    return _swizzle_gauntlet_textures(
        textures, width, height, bits_per_pixel, "dc", unswizzle
        )

def swizzle_ngc_gauntlet_textures(
        textures, width, height, bits_per_pixel, unswizzle=True
        ):
    return _swizzle_gauntlet_textures(
        textures, width, height, bits_per_pixel, "ngc", unswizzle
        )
    
def _swizzle_gauntlet_textures(
        textures, width, height, bits_per_pixel, platform, unswizzle
        ):
    '''
    Swizzles or unswizzles Gamecube/Dreamcast Gauntlet textures.
    Swizzle pattern used depends on the bits-per-pixel.
    '''
    is_ngc = platform == "ngc"
    is_dc  = platform == "dc"
    assert is_ngc or is_dc

    mask_type = (
        "DC_GAUNTLET"        if is_dc  else
        "NGC_GAUNTLET_4BPP"  if bits_per_pixel == 4  else
        "NGC_GAUNTLET_8BPP"  if bits_per_pixel == 8  else
        "NGC_GAUNTLET_16BPP" if bits_per_pixel == 16 else
        "NGC_GAUNTLET_32BPP"
        )
    swizz = swizzler.Swizzler(mask_type = mask_type)

    # ngc 4bpp hack to fix each pair of pixels per byte unpacking swapped
    ngc_4bpp = is_ngc and bits_per_pixel == 4
    channel_count = 1 if bits_per_pixel <= 8 else bits_per_pixel // 8
    
    if ngc_4bpp and not unswizzle:
        [arbytmap.bitmap_io.swap_array_items(t, (1, 0)) for t in textures]

    swizzled = [
        swizz.swizzle_single_array(
            texture, not unswizzle, channel_count,
            max(width >> i, 1), max(height >> i, 1), 1,
            )
        for i, texture in enumerate(textures)
        ]

    if ngc_4bpp and unswizzle:
        [arbytmap.bitmap_io.swap_array_items(t, (1, 0)) for t in swizzled]

    return swizzled
