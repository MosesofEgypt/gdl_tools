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

format_defs.FORMAT_X1R5G5B5 = FORMAT_X1R5G5B5 = "X1R5G5B5"

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
    (i & 0x83E0)         | # alpha and green
    ((i & 0x7C00) >> 10) | # isolate bits 10-15 and shift to 1-5
    ((i & 0x1F)   << 10)   # isolate bits 1-5 and shift to 10-15
    for i in range(0x10000)
    )


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
Arbytmap._unpack_indexing = _fixed_unpack_indexing
Arbytmap._unpack_palettized = _fixed_unpack_palettized
format_defs.register_format(FORMAT_X1R5G5B5, 1, depths=(5,5,5), bpp=16)

if png is not None:
    bitmap_io.file_readers["png"] = load_from_png_file
