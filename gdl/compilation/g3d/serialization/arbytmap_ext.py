'''
This module is meant to fix some bugs with arbytmap, add some more texture
formats/swizzler masks, and add the ability to load png files into arbytmap.
'''
import png

from array import array
from traceback import format_exc

from arbytmap import arby, bitmap_io, constants, format_defs
from arbytmap.arby import *
from . import texture_conversions

FORMAT_X1R5G5B5 = format_defs.FORMAT_X1R5G5B5 = "X1R5G5B5"
FORMAT_A8R3G3B2 = format_defs.FORMAT_A8R3G3B2 = "A8R3G3B2"



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
        return texture_conversions.rescale_4bit_array_to_8bit(
            packed_indexing, texture_conversions.INDEXING_4BPP_TO_8BPP
            )
    elif self.indexing_size == 8:
        return array("B", packed_indexing)
    else:
        raise TypeError("Cannot unpack indexing from sizes other than 4 or 8 bit")


# just a guess on the 32bpp one
def _ngc_gauntlet_swizzle_32bpp_mask_set(*args, **kwargs):
    return _ngc_gauntlet_swizzle_mask_set(*args, **kwargs, ngc_mask_start="xxy")

def _ngc_gauntlet_swizzle_16bpp_mask_set(*args, **kwargs):
    return _ngc_gauntlet_swizzle_mask_set(*args, **kwargs, ngc_mask_start="xxyy")

def _ngc_gauntlet_swizzle_8bpp_mask_set(*args, **kwargs):
    return _ngc_gauntlet_swizzle_mask_set(*args, **kwargs, ngc_mask_start="xxxyy")

def _ngc_gauntlet_swizzle_4bpp_mask_set(*args, **kwargs):
    return _ngc_gauntlet_swizzle_mask_set(*args, **kwargs, ngc_mask_start="xxxyyy")

def _swizzle_axis_bits(axis_bits, masks, log_sizes):
    '''
    Sets up bit shift amounts for the Swizzler class to utilize.
    The shift amounts are how many positions to shift each bit per axis.
    '''
    i = 0
    for axis in axis_bits:
        if axis in masks:
            mask = masks[axis]
            bits = max(0, min(log_sizes[axis] - len(mask), 1))
            mask.extend([i - len(mask)]*bits)
            i += bits

def _ngc_gauntlet_swizzle_mask_set(
        swizzler_mask,
        log_c,  log_x,  log_y,  log_z,
        c_mask, x_mask, y_mask, z_mask,
        ngc_mask_start=""
        ):
    log_sizes = dict(c=log_c, x=log_x, y=log_y, z=log_z)
    masks = dict(c=c_mask, x=x_mask, y=y_mask, z=z_mask)

    axis_bits = (
        "c" * log_c +
        ngc_mask_start +
        "x" * max(0, log_x - ngc_mask_start.count("x")) +
        "y" * max(0, log_y - ngc_mask_start.count("y")) +
        "z" * log_z
        )
    _swizzle_axis_bits(axis_bits, masks, log_sizes)

def _dc_gauntlet_swizzle_mask_set(
        swizzler_mask,
        log_c,  log_x,  log_y,  log_z,
        c_mask, x_mask, y_mask, z_mask
        ):
    log_sizes = dict(c=log_c, x=log_x, y=log_y, z=log_z)
    masks = dict(c=c_mask, x=x_mask, y=y_mask, z=z_mask)

    axis_bits = "c" * log_c
    while log_y or log_x:
        if log_y > 0: axis_bits += "y"
        if log_x > 0: axis_bits += "x"

        log_y -= 1
        log_x -= 1

    axis_bits += "z" * log_z
    _swizzle_axis_bits(axis_bits, masks, log_sizes)


swizzler.SwizzlerMask.add_mask("NGC_GAUNTLET_32BPP", _ngc_gauntlet_swizzle_32bpp_mask_set)
swizzler.SwizzlerMask.add_mask("NGC_GAUNTLET_16BPP", _ngc_gauntlet_swizzle_16bpp_mask_set)
swizzler.SwizzlerMask.add_mask("NGC_GAUNTLET_8BPP",  _ngc_gauntlet_swizzle_8bpp_mask_set)
swizzler.SwizzlerMask.add_mask("NGC_GAUNTLET_4BPP",  _ngc_gauntlet_swizzle_4bpp_mask_set)
swizzler.SwizzlerMask.add_mask("DC_GAUNTLET",        _dc_gauntlet_swizzle_mask_set)
Arbytmap._unpack_indexing   = _fixed_unpack_indexing
Arbytmap._unpack_palettized = _fixed_unpack_palettized

format_defs.register_format(FORMAT_X1R5G5B5, 1, depths=(5,5,5), bpp=16)
format_defs.register_format(FORMAT_A8R3G3B2, 1, depths=(8,3,3,2), bpp=16)

if png is not None:
    bitmap_io.file_readers["png"] = load_from_png_file
