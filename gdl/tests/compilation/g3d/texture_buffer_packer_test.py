import os

from setup_tests import *

from gdl.compilation.g3d import texture_buffer_packer, constants as c


class TestTextureBufferPacker:
    def test_load_from_buffer_info(self):
        for w, h, fmt, pfmt, b_size, pal_addr, addrs, widths in (
                (256, 256, "psmt8", "psmct32", 384, 380,
                 (0, 256, 320, 352, 368, 376),
                 (2, 1, 1, 1, 1, 1)
                 ),
                (32, 32, "psmt4", "psmct32", 32, 10,
                 (0, 2, 8),
                 (2, 2, 2)
                 ),
                (256, 32, "psmt8", "psmct32", 64, 60,
                 (0, 10, 8),
                 (2, 1, 1)
                 ),
                (64, 128, "psmt8", "psmct32", 128, 124,
                 (0, 64, 96, 112),
                 (1, 1, 1, 1)
                 ),
                (64, 64, "psmt8", "psmct32", 64, 60,
                 (0, 32, 48, 56),
                 (1, 1, 1, 1)
                 ),
                (256, 256, "psmct32", "psmct32", 1376, 0,
                 (0, 1024, 1280, 1344, 1360, 1364, 1365),
                 (4, 2, 1, 1, 1, 1, 1)
                 ),
                (256, 256, "psmct16", "psmct32", 704, 0,
                 (0, 512, 640, 672, 680, 682, 683),
                 (4, 2, 1, 1, 1, 1, 1)
                 ),
            ):
            calc = texture_buffer_packer.load_from_buffer_info(
                w, h, fmt, pfmt, b_size, pal_addr, addrs, widths,
                allow_overlap = False
                )
            for m in range(len(addrs)):
                assert calc.get_address_and_width(m) == (addrs[m], c.PSM_PAGE_WIDTHS[fmt] * widths[m] // 64)
                assert calc.pixel_format == fmt

            assert calc.block_count == b_size

    def test_constants(self):
        assert len(c.MONOCHROME_FORMATS) == 4
        assert c.MAX_MIP_COUNT == 6
        assert c.PS2_TEXTURE_BUFFER_CHUNK_SIZE == 0x100
        for block_orders in (c.PSM_BLOCK_ORDERS, c.PSM_INVERSE_BLOCK_ORDERS):
            for name in block_orders:
                assert len(block_orders[name]) == 32
                assert set(block_orders[name]) == set(range(32))
                assert set(type(i) for i in block_orders[name]) == {int}

        dct_keys = {c.PSM_CT32, c.PSM_CT24, c.PSM_CT16, c.PSM_CT16S,
                    c.PSM_Z32, c.PSM_Z24, c.PSM_Z16, c.PSM_Z16S,
                    c.PSM_T8, c.PSM_T4, c.PSM_T8H, c.PSM_T4HL,
                    c.PSM_T4HH}
        for dct in (c.PSM_BLOCK_ORDERS, c.PSM_INVERSE_BLOCK_ORDERS,
                    c.PSM_PAGE_WIDTHS, c.PSM_PAGE_HEIGHTS,
                    c.PSM_BLOCK_WIDTHS, c.PSM_BLOCK_HEIGHTS,
                    c.PSM_PAGE_BLOCK_WIDTHS, c.PSM_PAGE_BLOCK_HEIGHTS,
                    ):
            assert len(dct) == 13
            assert set(dct.keys()) == dct_keys

    def test_pack(self):
        return
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
