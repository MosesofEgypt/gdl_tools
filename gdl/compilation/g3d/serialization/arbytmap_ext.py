'''
This module is meant to fix some bugs with arbytmap, and
add the ability to load png files into arbytmap.
'''
import os
import png

from array import array
from traceback import format_exc

from arbytmap import bitmap_io, constants, format_defs
from arbytmap.arby import *
from . import ncc

format_defs.FORMAT_X1R5G5B5 = FORMAT_X1R5G5B5 = "X1R5G5B5"
format_defs.FORMAT_A8R3G3B2 = FORMAT_A8R3G3B2 = "A8R3G3B2"


INDEXING_4BPP_TO_8BPP = tuple(
     (i & 0xF) |      # isolate bits 1-4
    ((i & 0xF0) << 4) # isolate bits 5-8 and shift to 9-12
     for i in range(0x100)
    )
INDEXING_8BPP_TO_4BPP = tuple(
     (i & 0xF) |       # isolate bits 1-4
    ((i & 0xF00) >> 4) # isolate bits 9-12 and shift to 5-8
    for i in range(0x10000)
    )
MONOCHROME_4BPP_TO_8BPP = tuple(
     ((i & 0xF) * 17) |
    (((i >> 4)  * 17) << 8)
    for i in range(0x100)
    )
MONOCHROME_8BPP_TO_4BPP = tuple(
    int(round((i & 0xFF) / 17)) |
    (int(round((i >> 8)  / 17)) << 4)
    for i in range(0x10000)
    )
BYTESWAP_5551_ARGB_AND_ABGR = tuple(
    (i & 0x83E0)         | # isolate alpha and green
    ((i & 0x7C00) >> 10) | # isolate bits 10-15 and shift to 1-5
    ((i & 0x1F)   << 10)   # isolate bits 1-5 and shift to 10-15
    for i in range(0x10000)
    )


def _upscale(src_depth, dst_depth, val, max_val=None):
    scale_ct = 2**src_depth
    if max_val is None:
        max_val  = 2**dst_depth - 1

    scale = max_val / (scale_ct - 1)
    return min(max_val, int(val * scale + 0.5))


def _rgb_888_to_yiq_422(r, g, b, ncc_table):
    y, i, q = ncc.quantize_rgb_888_to_yiq_888(r, g, b)
    y = (
        0  if y < ncc_table.y_min else
        15 if y > ncc_table.y_max else
        int((y - ncc_table.y_min) * (15 / (ncc_table.y_max - ncc_table.y_min)))
        )
    i = (
        0 if i < ncc_table.i_min else
        3 if i > ncc_table.i_max else
        int((i - ncc_table.i_min) * (3 / (ncc_table.i_max - ncc_table.i_min)))
        )
    q = (
        0 if q < ncc_table.q_min else
        3 if q > ncc_table.q_max else
        int((q - ncc_table.q_min) * (3 / (ncc_table.q_max - ncc_table.q_min)))
        )
    return y, i, q


def _yiq_422_to_rgb_888(yiq_422, ncc_table):
    y = (yiq_422 >> 4) & 0xF
    i = (yiq_422 >> 2) & 0x3
    q =  yiq_422       & 0x3
    yy = ncc_table.y[y]

    b = yy + ncc_table.a[i*3  ] + ncc_table.b[q*3  ]
    g = yy + ncc_table.a[i*3+1] + ncc_table.b[q*3+1]
    r = yy + ncc_table.a[i*3+2] + ncc_table.b[q*3+2]
    return (
        ( 0 if r <= 0 else 255 if r >= 255 else int(r)) |
        ((0 if g <= 0 else 255 if g >= 255 else int(g)) << 8) |
        ((0 if b <= 0 else 255 if b >= 255 else int(b)) << 16)
        )

def _ayiq_8422_to_argb_8888(ayiq_8422, ncc_table):
    rgb_888 = _yiq_422_to_rgb_888(ayiq_8422 & 0xFF, ncc_table)
    return rgb_888 | (((ayiq_8422 >> 8) & 0xFF) << 24)


# NOTE: we are doing some fucky stuff with the gamecube alpha values.
#       we're intentionally unpacking it at half brightness to ensure
#       assets are compatible between each platform(xbox/ps2/gamecube).
#       when extracted, alpha values will be no higher than 50%.
#       When imported, values higher will be properly scaled back up.
def _3Ato8(val): return _upscale(3, 8, val, 128)
def _4to8(val):  return _upscale(4, 8, val)
def _5to8(val):  return _upscale(5, 8, val)

# used to quickly convert from gamecube format to A8R8G8B8
UPSCALE_3555_TO_8888 = tuple(
    (
        _5to8(i&0x1F) | (_5to8((i>>5)&0x1F)<<8) | (_5to8((i>>10)&0x1F)<<16) | (0x80<<24)
        if i & 0x8000 else
        _4to8(i&0xF)  | (_4to8((i>>4)&0xF)<<8)  | (_4to8((i>>8)&0xF)<<16)   | (_3Ato8(i>>12)<<24)
     )
    for i in range(0x10000)
    )
# used to quickly convert to gamecube format from A8R8G8B8
DOWNSCALE_8_TO_3A = tuple(min(int((i / 128)*7  + 0.5), 7) for i in range(256))
DOWNSCALE_8_TO_4  = tuple(int((i / 255)*15 + 0.5) for i in range(256))
DOWNSCALE_8_TO_5  = tuple(int((i / 255)*31 + 0.5) for i in range(256))

# these are just for the above calculation
del _upscale
del _3Ato8
del _4to8
del _5to8


def channel_swap_bgra_rgba_array(all_pixels, pixel_stride):
    for orig_pixels in all_pixels:
        pixels = bytearray(orig_pixels) if isinstance(orig_pixels, array) else orig_pixels

        if pixel_stride == 2:
            # use a mapping to quickly swap 16 bit pixels
            uint16_pixels = array("H", pixels)
            swapped_pixels = map(BYTESWAP_5551_ARGB_AND_ABGR.__getitem__, uint16_pixels)
            pixels[:] = bytearray(array("H", swapped_pixels))
        elif pixel_stride == 4:
            # use arbytmap to quickly swap 32bit pixels
            swap_map = (2, 1, 0, 3)  # swap red and blue, but leave green and alpha alone
            bitmap_io.swap_array_items(pixels, swap_map)

        if isinstance(orig_pixels, array):
            orig_pixels[:] = array(orig_pixels.typecode, pixels)


def rescale_4bit_array_to_8bit(texture, rescale_list):
    return bytearray(array("H", map(rescale_list.__getitem__, texture)))


def rescale_8bit_array_to_4bit(texture, rescale_list):
    # NOTE: When downscaling indexing, this will break if the
    #       index value is ever higher than 15. It will take only
    #       the lower 4 bits from each byte, igoring the upper 4.
    return bytearray(map(rescale_list.__getitem__, array("H", texture)))


def pad_pal16_to_pal256(palette):
    palette.extend([palette[-1]]*(256-len(palette)))


def load_from_png_file(arby, input_path, ext, **kwargs):
    reader = png.Reader(filename="%s.%s" % (input_path, ext))

    w, h, pixels, _ = reader.asRGBA8()
    tex_info = dict(
        width = w, height = h, texture_type="2D",
        mipmap_count=0, sub_bitmap_count=1,
        format=format_defs.FORMAT_A8R8G8B8,
        filepath=input_path
        )
    pixels = bytearray().join(p for p in pixels)

    # use arbytmap to quickly swap 32bit pixels
    swap_map = (2, 1, 0, 3)  # png stores red and blue swapped from what we want
    bitmap_io.swap_array_items(pixels, swap_map)

    arby.load_new_texture(
        texture_block=[array("I", pixels)],
        texture_info=tex_info
        )


def argb_8888_to_ayiq_8422(source_pixels, ncc_table):
    # converts packed/unpacked pixels to packed pixels
    if isinstance(source_pixels, array):
        source_pixels = source_pixels.tobytes()

    packed_pixels = array("H", b'\x00\x00'*(len(source_pixels) // 4))
    for i in range(len(source_pixels)//4):
        a, r, g, b = source_pixels[i*4: i*4+4]
        y, i, q = _rgb_888_to_yiq_422(r, g, b, ncc_table)

        packed_pixels[i] = q | (i << 2) | (y << 4) | (a << 8)

    return array("H", packed_pixels)


def xrgb_8888_to_yiq_422(source_pixels, ncc_table):
    # converts packed/unpacked pixels to packed pixels
    if isinstance(source_pixels, array):
        source_pixels = source_pixels.tobytes()

    packed_pixels = array("B", b'\x00'*(len(source_pixels) // 4))
    for i in range(len(source_pixels)//4):
        _, r, g, b = source_pixels[i*4: i*4+4]
        y, i, q = _rgb_888_to_yiq_422(r, g, b, ncc_table)

        packed_pixels[i] = q | (i << 2) | (y << 4)

    return array("B", packed_pixels)


def ayiq_8422_to_argb_8888(source_pixels, ncc_table):
    # converts packed pixels to packed pixels
    if not isinstance(source_pixels, array):
        source_pixels = array("H", source_pixels)

    return array("I", (_ayiq_8422_to_argb_8888(p, ncc_table) for p in source_pixels))


def yiq_422_to_xrgb_8888(source_pixels, ncc_table):
    # converts packed pixels to packed pixels
    if not isinstance(source_pixels, array):
        source_pixels = array("B", source_pixels)

    return array("I", (_yiq_422_to_rgb_888(p, ncc_table) for p in source_pixels))


def argb_8888_to_3555(source_pixels, no_alpha=False):
    # converts packed/unpacked pixels to packed pixels
    if isinstance(source_pixels, array):
        source_pixels = source_pixels.tobytes()

    packed_pixels = array("H", b'\x00\x00'*(len(source_pixels) // 4))
    alpha_cutoff = DOWNSCALE_8_TO_3A[255]
    for i in range(len(source_pixels)//4):
        a, r, g, b = source_pixels[i*4: i*4+4]

        if no_alpha or DOWNSCALE_8_TO_3A[a] == alpha_cutoff:
            # full opaque alpha
            packed_pixels[i] = (
                DOWNSCALE_8_TO_5[b] |
                (DOWNSCALE_8_TO_5[g] << 5) |
                (DOWNSCALE_8_TO_5[r] << 10) |
                0x8000
                )
        else:
            # transparent alpha
            packed_pixels[i] = (
                DOWNSCALE_8_TO_4[b] |
                (DOWNSCALE_8_TO_4[g] << 4) |
                (DOWNSCALE_8_TO_4[r] << 8) |
                (DOWNSCALE_8_TO_3A[a] << 12)
                )

    return array("H", packed_pixels)


def argb_3555_to_8888(source_pixels):
    # converts packed pixels to packed pixels
    if not isinstance(source_pixels, array):
        source_pixels = array("H", source_pixels)

    return array("I", map(UPSCALE_3555_TO_8888.__getitem__, source_pixels))


def _fixed_unpack_palettized(self, packed_pal, packed_idx):
    '''
    Fixed replacement for Arbytmap's _unpack_palettized method.
    '''
    unpacked_pal = self.palette_unpacker(packed_pal) if self.palette_packed else packed_pal
    unpacked_idx = self.indexing_unpacker(packed_idx) if self.packed else packed_idx

    if not self.palettize:
        unpacked_idx = self.depalettize_bitmap(unpacked_pal, unpacked_idx)
        unpacked_pal = None

    return unpacked_pal, unpacked_idx


def _fixed_unpack_indexing(self, packed_indexing):
    '''
    Fixed(somewhat) replacement for Arbytmap's _unpack_indexing method.
    Does not support unpacking 1 or 2 bit indexing
    '''
    if self.indexing_size == 4:
        return rescale_4bit_array_to_8bit(packed_indexing, INDEXING_4BPP_TO_8BPP)
    elif self.indexing_size == 8:
        return array("B", packed_indexing)
    else:
        raise TypeError("Cannot unpack indexing from sizes other than 4 or 8 bit")


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


def swizzle_ngc_gauntlet_textures(
        textures, width, height, bits_per_pixel, unswizzle=True
        ):
    '''
    Swizzles or unswizzles Gamecube Gauntlet textures.
    Swizzle pattern used depends on the bits-per-pixel.
    '''

    deswizzler = swizzler.Swizzler(
        mask_type=(
            "NGC_GAUNTLET_4BPP"  if bits_per_pixel == 4  else
            "NGC_GAUNTLET_8BPP"  if bits_per_pixel == 8  else
            "NGC_GAUNTLET_16BPP" if bits_per_pixel == 16 else
            "NGC_GAUNTLET_32BPP"
            )
        )
    channel_count = 1 if bits_per_pixel <= 8 else bits_per_pixel // 8

    swizzled_textures = []
    for i in range(len(textures)):
        texture = textures[i]

        if bits_per_pixel == 4 and not unswizzle:
            # hack to fix each pair of pixels per byte unpacking swapped
            bitmap_io.swap_array_items(texture, (1, 0))

        texture = deswizzler.swizzle_single_array(
            texture, not unswizzle, channel_count, width, height, 1,
            )

        if bits_per_pixel == 4 and unswizzle:
            # hack to fix each pair of pixels needing to be packed swapped
            bitmap_io.swap_array_items(texture, (1, 0))

        swizzled_textures.append(texture)

        width  = (width + 1) // 2
        height = (height + 1) // 2

    return swizzled_textures


# just a guess on the 32bpp one
def _ngc_gauntlet_swizzle_32bpp_mask_set(*args, **kwargs):
    return _ngc_gauntlet_swizzle_mask_set(*args, **kwargs, ngc_mask_start="xxy")

def _ngc_gauntlet_swizzle_16bpp_mask_set(*args, **kwargs):
    return _ngc_gauntlet_swizzle_mask_set(*args, **kwargs, ngc_mask_start="xxyy")

def _ngc_gauntlet_swizzle_8bpp_mask_set(*args, **kwargs):
    return _ngc_gauntlet_swizzle_mask_set(*args, **kwargs, ngc_mask_start="xxxyy")

def _ngc_gauntlet_swizzle_4bpp_mask_set(*args, **kwargs):
    return _ngc_gauntlet_swizzle_mask_set(*args, **kwargs, ngc_mask_start="xxxyyy")


def _ngc_gauntlet_swizzle_mask_set(
        swizzler_mask,
        log_c,  log_x,  log_y,  log_z,
        c_mask, x_mask, y_mask, z_mask,
        ngc_mask_start=""
        ):
    '''
    Sets up bit shift amounts for the Swizzler class to utilize.
    The shift amounts are how many positions to shift each bit per axis.
    '''

    log_sizes = dict(c=log_c, x=log_x, y=log_y, z=log_z)
    masks = dict(c=c_mask, x=x_mask, y=y_mask, z=z_mask)

    axis_bits = (
        "c" * log_c +
        ngc_mask_start +
        "x" * max(0, log_x - ngc_mask_start.count("x")) +
        "y" * max(0, log_y - ngc_mask_start.count("y")) +
        "z" * log_z
        )

    i = 0
    for axis in axis_bits:
        if axis in masks:
            mask = masks[axis]
            bits = max(0, min(log_sizes[axis] - len(mask), 1))
            mask.extend([i - len(mask)]*bits)
            i += bits


swizzler.SwizzlerMask.add_mask("NGC_GAUNTLET_32BPP", _ngc_gauntlet_swizzle_32bpp_mask_set)
swizzler.SwizzlerMask.add_mask("NGC_GAUNTLET_16BPP", _ngc_gauntlet_swizzle_16bpp_mask_set)
swizzler.SwizzlerMask.add_mask("NGC_GAUNTLET_8BPP",  _ngc_gauntlet_swizzle_8bpp_mask_set)
swizzler.SwizzlerMask.add_mask("NGC_GAUNTLET_4BPP",  _ngc_gauntlet_swizzle_4bpp_mask_set)
Arbytmap._unpack_indexing   = _fixed_unpack_indexing
Arbytmap._unpack_palettized = _fixed_unpack_palettized

format_defs.register_format(FORMAT_X1R5G5B5, 1, depths=(5,5,5), bpp=16)
format_defs.register_format(FORMAT_A8R3G3B2, 1, depths=(8,3,3,2), bpp=16)

if png is not None:
    bitmap_io.file_readers["png"] = load_from_png_file
