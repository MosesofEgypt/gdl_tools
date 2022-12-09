import os
import pprint

import setup_tests

from gdl.compilation.g3d import texture_buffer_packer, constants as c


test = texture_buffer_packer.TextureBufferPacker(
    256, 256, "psmt8", 5, "psmct32"
    )
test.initialize_blocks(allocate_required_pages=False)
test.allocate_pages(384 // 32)
test.allocate_texture(0, 2, 0)
test.allocate_texture(1, 1, 256)
test.allocate_texture(2, 1, 320)
test.allocate_texture(3, 1, 352)
test.allocate_texture(4, 1, 368)
test.allocate_texture(5, 1, 376)
test.allocate_palette(380)
print(test.get_usage_string(page_borders=True))

test = texture_buffer_packer.TextureBufferPacker(
    256, 256, "psmt8", 5, "psmct32"
    )
#test.initialize_blocks(allocate_required_pages=False)
#test.allocate_pages(352 // 32)
test.allocate_texture(0, 2, 0)
test.allocate_texture(1, 2, 256)
test.allocate_texture(2, 1, 288)
test.allocate_texture(3, 1, 304)
test.allocate_texture(4, 1, 308)
test.allocate_texture(5, 1, 309)
test.allocate_palette(310)

print(test.get_usage_string(page_borders=True))

test = texture_buffer_packer.TextureBufferPacker(
    256, 32, "psmt8", 5, "psmct32"
    )
test.overlap_error = False
#test.initialize_blocks(allocate_required_pages=False)
#test.allocate_pages(64 // 32)
test.allocate_texture(0, 2, 0)
test.allocate_texture(1, 1, 8)
test.allocate_texture(2, 1, 16)
test.allocate_palette(60)

print(test.get_usage_string(page_borders=True))

test = texture_buffer_packer.TextureBufferPacker(
    64, 128, "psmt8", 5, "psmct32"
    )
test.overlap_error = False
test.initialize_blocks(allocate_required_pages=False)
test.allocate_pages(128 // 32)
test.allocate_texture(0, 1, 0)
test.allocate_texture(1, 1, 64)
test.allocate_texture(2, 1, 96)
test.allocate_texture(3, 1, 112)
test.allocate_palette(124)

print(test.get_usage_string(page_borders=True))

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
    print(dict(
        pal_addr=test.palette_address,
        tex_addrs=test._tb_addrs,
        tex_widths=test._tb_widths,
        buffer_size=test.block_count,
        efficiency=test.efficiency,
        ))
    print(test.get_usage_string(page_borders=True))
