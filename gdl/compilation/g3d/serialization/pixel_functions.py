'''
This module is meant to fix some bugs with arbytmap, and
add the ability to load png files into arbytmap.
'''
from array import array
from traceback import format_exc
from arbytmap import bitmap_io

from . import ncc


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
