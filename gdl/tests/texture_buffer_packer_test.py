import os

import setup_tests

from gdl.compilation.g3d import texture_buffer_packer, constants as c


for w, h, fmt, pfmt, b_size, pal_addr, addrs, widths in (
        (256, 256, "psmt8", "psmct32", 384, 380,
         (0, 256, 320, 352, 368, 376), (2, 1, 1, 1, 1, 1)),
        (256, 256, "psmt8", "psmct32", 352, 310,
         (0, 256, 288, 304, 308, 309), (2, 2, 1, 1, 1, 1)),
        (256, 32, "psmt8", "psmct32", 64, 60,
         (0, 8, 16), (2, 1, 1)),
        (64, 128, "psmt8", "psmct32", 128, 124,
         (0, 64, 96, 112), (1, 1, 1, 1)),
        (64, 64, "psmt8", "psmct32", 64, 60,
         (0, 32, 48, 56), (1, 1, 1, 1)),
        (64, 64, "psmt8", "psmct32", 32, 22,
         (0, 16, 20, 21), (1, 1, 1, 1)),
    ):

    test = texture_buffer_packer.load_from_buffer_info(
        w, h, fmt, pfmt, b_size, pal_addr, addrs, widths,
        allow_overlap = True
        )
    print(test.get_usage_string(page_borders=True), end="")
    print(dict(
        pal_addr=test.palette_address,
        tex_addrs=test._tb_addrs,
        tex_widths=test._tb_widths,
        buffer_size=test.block_count,
        efficiency=test.efficiency,
        ), '\n')

for w, h, fmt, m, pfmt in (
        (256, 128, "psmt8", 0, "psmct32"),
        (32, 32, "psmt4", 2, "psmct32"),
        (256, 32, "psmt8", 2, "psmct32"),
        (256, 256, "psmt8", 5, "psmct32"),
        (256, 256, "psmt4", 0, None),
        (256, 32, "psmct32", 5, "psmct32"),
        (32, 256, "psmct32", 5, "psmct32"),
        (256, 64, "psmct32", 5, "psmct32"),
        (64, 256, "psmct32", 5, "psmct32"),
        (256, 128, "psmct32", 6, "psmct32"),
        (128, 256, "psmct32", 6, "psmct32"),
        (256, 256, "psmct32", 6, "psmct32"),
        (256, 256, "psmct16", 6, "psmct32"),
    ):

    test = texture_buffer_packer.TextureBufferPacker(w, h, fmt, m, pfmt)
    test.pack()
    print(test.get_usage_string(page_borders=True), end="")
    print(dict(
        pal_addr=test.palette_address,
        tex_addrs=test._tb_addrs,
        tex_widths=test._tb_widths,
        buffer_size=test.block_count,
        efficiency=test.efficiency,
        ), '\n')
