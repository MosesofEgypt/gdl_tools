import math

from . import constants as c


class TextureBufferPacker:
    pixel_format   = ""
    palette_format = None

    height  = 0
    width   = 0
    mipmaps = 0

    check_centers = False
    overlap_error = True

    _tb_addrs  = ()
    _tb_widths = ()
    _cb_addr   = -1

    _blocks_used = ()
    _overlap_block_val = -1
    _free_block_val = 0
    _unknown_char = "?"
    _border_char_h = "-"
    _border_char_v = "|"
    _border_char_c = "+"
    _used_chars = {
        _overlap_block_val: "X",
        _free_block_val: ".",
        "T0": "0",
        "T1": "1",
        "T2": "2",
        "T3": "3",
        "T4": "4",
        "T5": "5",
        "T6": "6",
        "CB": "#",
        }

    def __init__(
            self, width, height, pixel_format,
            mipmaps=0, palette_format=None
            ):
        assert width in c.VALID_DIMS
        assert height in c.VALID_DIMS
        assert mipmaps <= c.MAX_MIP_COUNT
        assert pixel_format in c.PSM_BLOCK_ORDERS
        if pixel_format in (c.PSM_T8, c.PSM_T4):
            assert palette_format is None or palette_format in c.PSM_BLOCK_ORDERS

        self.pixel_format   = pixel_format
        self.palette_format = palette_format
        self.width   = width
        self.height  = height
        self.mipmaps = mipmaps
        self._used_chars = dict(self._used_chars) # copy in case edits are made
        self._initialize_blocks()

    def _allocate_pages(self, page_count):
        block_count = page_count * self.blocks_per_page
        self._blocks_used.extend([self._free_block_val] * block_count)
        #print("Allocated %s pages" % (page_count, ))

    def _initialize_blocks(self, allocate_required_pages=True):
        # clear existing calculations
        self._cb_addr      = 0
        self._tb_addrs     = []
        self._tb_widths    = []
        self._blocks_used  = []

        if not allocate_required_pages:
            return

        blocks_required = 0
        pixels_per_block = self.block_width * self.block_height
        for m in range(1 + self.mipmaps):
            blocks_required += self.get_mip_width(m) * self.get_mip_height(m)

        if self.has_palette:
            blocks_required += self.palette_size

        pages_required = int(math.ceil(blocks_required / self.blocks_per_page))
        self._allocate_pages(pages_required)

    def get_usage_string(self, pages_wide=None, page_borders=False):
        if not pages_wide:
            pages_wide = max(
                1, (max( [1] + self._tb_widths) * 64) // self.page_width,
                )

        page_sep_h = ""
        page_sep_v = ""
        if page_borders:
            page_sep_h = self._border_char_h*self.page_block_width + self._border_char_c
            page_sep_v = self._border_char_v

        usage_str = ""
        pages_tall = int(math.ceil(self.page_count / pages_wide))

        # nesting from hael
        for page_0 in range(0, pages_tall*pages_wide, pages_wide):
            pages_in_row = min(page_0 + pages_wide, self.page_count) - page_0

            for y in range(self.page_block_height):
                block_y_addr = y * self.page_block_width
                for page_addr in range(page_0, page_0 + pages_in_row):

                    for x in range(self.page_block_width):
                        linear_addr = (
                            self._page_to_linear_address(page_addr) +
                            block_y_addr +
                            x
                            )

                        usage_str += self._used_chars.get(
                            self._blocks_used[linear_addr],
                            self._unknown_char
                            )

                    usage_str += page_sep_v

                usage_str += "\n"

            usage_str += page_sep_h * pages_in_row + "\n"

        return usage_str

    def get_address_and_width(self, mip_level):
        if mip_level in range(min(len(self._tb_addrs), len(self._tb_widths))):
            return self._tb_addrs[mip_level], self._tb_widths[mip_level]
        return 0, 0

    def get_mip_width(self, mip_level):
        '''Returns the number of blocks wide the specified mipmap level is.'''
        return max(self.block_width, self.width >> mip_level) // self.block_width

    def get_mip_height(self, mip_level):
        '''Returns the number of blocks tall the specified mipmap level is.'''
        return max(self.block_height, self.height >> mip_level) // self.block_height

    @property
    def efficiency(self):
        return 1 - self.free_block_count / max(1, self.block_count)

    @property
    def block_count(self):
        return len(self._blocks_used)
    @property
    def free_block_count(self):
        return self._blocks_used.count(self._free_block_val)
    @property
    def page_count(self):
        return self.block_count // self.blocks_per_page

    @property
    def has_palette(self):
        return (
            self.palette_format is not None and
            (self.pixel_format == c.PSM_T8 or self.pixel_format == c.PSM_T4)
            )
    @property
    def palette_size(self):
        '''Returns the length of the palette in blocks'''
        if self.pixel_format not in (c.PSM_T8, c.PSM_T4):
            return 0
        elif self.pixel_format == c.PSM_T4:
            return 1
        elif self.palette_format in (c.PSM_CT16, c.PSM_CT16S):
            return 2
        else:
            return 4
    @property
    def palette_address(self):
        return self._cb_addr if self.palette_size else 0

    @property
    def block_width(self):
        '''Number of pixels wide each block is'''
        return c.PSM_BLOCK_WIDTHS[self.pixel_format]
    @property
    def block_height(self):
        '''Number of pixels tall each block is'''
        return c.PSM_BLOCK_HEIGHTS[self.pixel_format]
    @property
    def page_width(self):
        '''Number of pixels wide each page is'''
        return c.PSM_PAGE_WIDTHS[self.pixel_format]
    @property
    def page_height(self):
        '''Number of pixels tall each page is'''
        return c.PSM_PAGE_HEIGHTS[self.pixel_format]
    @property
    def page_block_width(self):
        '''Number of blocks wide each page is'''
        return c.PSM_PAGE_BLOCK_WIDTHS[self.pixel_format]
    @property
    def page_block_height(self):
        '''Number of blocks tall each page is'''
        return c.PSM_PAGE_BLOCK_HEIGHTS[self.pixel_format]
    @property
    def blocks_per_page(self):
        '''Number of blocks in each page'''
        return self.page_block_width * self.page_block_height

    def _linear_address_to_page(self, linear_addr):
        return linear_addr // self.blocks_per_page

    def _page_to_linear_address(self, page):
        return page * self.blocks_per_page

    def _bounds_check_address(self, page_x, page_y, linear_addr, pages_wide):
        if page_x > pages_wide:
            raise ValueError(
                "Page x=%s outside buffer width %s" % (page_x, pages_wide)
                )
        elif linear_addr >= self.block_count:
            raise ValueError(
                "Linear address i=%s outside buffer length %s" %
                (linear_addr, self.block_count)
                )

    def _linear_address_to_xy_address(self, linear_addr, pages_wide, ref_page=0):
        page   = self._linear_address_to_page(linear_addr)
        index_in_page = linear_addr - self._page_to_linear_address(page)

        page_x = page  % pages_wide
        page_y = page // pages_wide
        x0     = index_in_page  % self.page_block_width
        y0     = index_in_page // self.page_block_width

        x = x0 + page_x * self.page_block_width
        y = y0 + page_y * self.page_block_height

        self._bounds_check_address(page_x, page_y, linear_addr, pages_wide)
        return x, y

    def _xy_address_to_linear_address(self, x, y, pages_wide, ref_page=0):
        page_x = x // self.page_block_width
        page_y = y // self.page_block_height
        x0     = x  % self.page_block_width
        y0     = y  % self.page_block_height
        index_in_page = x0 + y0 * self.page_block_width

        linear_addr = (
            index_in_page +
            self._page_to_linear_address(page_x) +
            self._page_to_linear_address(page_y * pages_wide) +
            self._page_to_linear_address(ref_page)
            )

        self._bounds_check_address(page_x, page_y, linear_addr, pages_wide)
        return linear_addr

    def _block_address_to_linear_address(self, linear_addr):
        block_order = c.PSM_INVERSE_BLOCK_ORDERS[self.pixel_format]
        base_addr = self._linear_address_to_page(linear_addr) * self.blocks_per_page
        return base_addr + block_order[linear_addr % self.blocks_per_page] 

    def _linear_address_to_block_address(self, linear_addr):
        block_order = c.PSM_BLOCK_ORDERS[self.pixel_format]
        base_addr = self._linear_address_to_page(linear_addr) * self.blocks_per_page
        return base_addr + block_order[linear_addr % self.blocks_per_page]

    def _mark_allocated_indices(self, allocate, block_indices, test_only=False):
        if not allocate:
            allocate = self._free_block_val

        want_free_space = (allocate != self._free_block_val)
        for i in block_indices:
            # print("%sllocating I=%s" % ("A" if allocate else "Dea", i))
            if want_free_space and self._blocks_used[i] != self._free_block_val:
                msg = "Block already %sallocated at i=%s" % ("" if allocate else "un", i)
                if self.overlap_error:
                    raise ValueError("Error: %s" % msg)
                else:
                    print("Warning: %s" % msg)
                    self._blocks_used[i] = self._overlap_block_val

            elif not test_only:
                self._blocks_used[i] = allocate

    def _mark_allocated_block_linear(
            self, allocate, length, block_addr, ref_page=0, test_only=False
            ):
        block_addr += self._page_to_linear_address(ref_page)

        indices = (
            self._block_address_to_linear_address(b_i)
            for b_i in range(block_addr, block_addr + length)
            )
        self._mark_allocated_indices(allocate, indices, test_only)

    def _mark_allocated_xy(
            self, allocate, width, height, pages_wide, x0, y0, ref_page=0, test_only=False
            ):
        indices = (
            self._xy_address_to_linear_address(x, y, pages_wide, ref_page)
            for y in range(y0, y0 + height)
            for x in range(x0, x0 + width)
            )
        self._mark_allocated_indices(allocate, indices, test_only)

    def _get_linear_index_of_free_line_chunk(self, length):
        i = 0
        while i + length <= self.block_count:
            len_free = 0
            b_i = self._linear_address_to_block_address(i)
            for j in range(b_i, b_i + length):
                k = self._block_address_to_linear_address(j)
                len_free += not self._blocks_used[k]

            # every block is free
            if len_free == length:
                return i

            try:
                i = self._blocks_used.index(self._free_block_val, i + 1)
            except ValueError:
                # no free blocks
                break

        return None

    def _get_linear_index_of_free_2d_chunk(self, width, height):
        corner_check_coords = (
            (        0,          0), # upper left
            (width - 1, height - 1), # lower right
            (width - 1,          0), # upper right
            (        0, height - 1), # lower left
            )
        side_check_coords = (  # ignoring corners
            *tuple((0,          y) for y in range(1, height - 1)),  # left
            *tuple((width - 1,  y) for y in range(1, height - 1)),  # right
            *tuple((x,          0) for x in range(1, width  - 1)),  # top
            *tuple((x, height - 1) for x in range(1, width  - 1)),  # bottom
            )
        center_check_coords = (
            (x, y)
            for x in range(1, width  - 1)
            for y in range(1, height - 1)
            )
        max_block_x = self.blocks_wide
        max_block_y = self.blocks_tall

        # TODO: calculate pages_wide

        i = 0
        while i < self.block_count:
            x0, y0 = self._linear_address_to_xy_address(i, pages_wide)
            free = (
                x0 + width  <= max_block_x and
                y0 + height <= max_block_y
                )
            # check the corners for high certainty on block freeness
            for xa, ya in corner_check_coords:
                if not free:
                    break
                j = self._xy_address_to_linear_address(
                    x0 + xa, y0 + ya, pages_wide
                    )
                free &= j < self.block_count and not self._blocks_used[j]

            # check the sides for certainty(unless fragmentation has occurred)
            for xa, ya in side_check_coords:
                if not free:
                    break
                j = self._xy_address_to_linear_address(
                    x0 + xa, y0 + ya, pages_wide
                    )
                free &= j < self.block_count and not self._blocks_used[j]

            # check the centers(if necessary)
            if self.check_centers:
                for xa, ya in center_check_coords:
                    if not free:
                        break
                    j = self._xy_address_to_linear_address(
                        x0 + xa, y0 + ya, pages_wide
                        )
                    free &= j < self.block_count and not self._blocks_used[j]

            # every block is free
            if free:
                #print("Located free block at %s" % i)
                return i

            try:
                i = self._blocks_used.index(self._free_block_val, i + 1)
            except ValueError:
                # no more free blocks
                break

        return None

    def _get_or_allocate_block_index_of_free_chunk(self, width, height=0):
        # start off at the first free address in case we need to allocate multiple times
        allocations = 0
        block_addr = None
        while block_addr is None:
            if allocations > 50:
                raise ValueError("Could not allocate large enough buffer to fit all texture data.")

            if height > 0:
                linear_addr, pages_wide = self._get_linear_index_of_free_2d_chunk(width, height)
            else:
                linear_addr = self._get_linear_index_of_free_line_chunk(width)
                pages_wide = 0

            if linear_addr is None:
                # couldn't locate a free chunk. allocate another page
                self._allocate_pages(1)
                allocations += 1
            else:
                block_addr = self._linear_address_to_block_address(linear_addr)

        return block_addr, pages_wide

    def allocate_texture(self, mipmap_level, pages_wide, block_addr):
        linear_addr = self._block_address_to_linear_address(block_addr)
        x0, y0 = self._linear_address_to_xy_address(linear_addr, pages_wide)

        self._mark_allocated_xy(
            "T%s" % mipmap_level,
            self.get_mip_width(mipmap_level),
            self.get_mip_height(mipmap_level),
            pages_wide, x0, y0
            )
        self._tb_addrs.append(block_addr)
        self._tb_widths.append((pages_wide * self.page_width) // 64)

    def allocate_palette(self, block_addr):
        self._mark_allocated_block_linear("CB", self.palette_size, block_addr)
        self._cb_addr = block_addr

    def pack(self):
        self._initialize_blocks()

        for m in range(1 + self.mipmaps):
            addr, pages_wide = self._get_or_allocate_block_index_of_free_chunk(
                self.get_mip_width(m), self.get_mip_height(m)
                )
            self.allocate_texture(m, pages_wide, addr)

        # return if there isn't a palette to pack.
        if self.has_palette:
            # NOTE: palettes are packed linearly in block-order rather than scanline order.
            addr, _ = self._get_or_allocate_block_index_of_free_chunk(self.palette_size)
            self.allocate_palette(addr)
