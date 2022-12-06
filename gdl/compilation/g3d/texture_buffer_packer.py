import math

from . import constants as c


class TextureBufferPacker:
    pixel_format   = ""
    palette_format = None

    height  = 0
    width   = 0
    mipmaps = 0

    check_centers = False
    max_allocations = 20

    _buffer_width = 0  # total number of pages wide the buffer is
                       # this isn't quite the same as the width of
                       # tex0, as we may end up storing the images
                       # stacked horizontally if they are taller than
                       # wide, as they'll fit better stacked sideways
    _tb_addrs  = ()
    _tb_widths = ()
    _cb_addr   = -1
    _optimized_buffer_size = None

    _blocks_used = ()
    _cull_block_val = -1
    _free_block_val = 0
    _unknown_char = "?"
    _border_char_h = "-"
    _border_char_v = "|"
    _border_char_c = "+"
    _used_chars = {
        _free_block_val: ".",
        _cull_block_val: "X",
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
        self._initialize_blocks(self.min_pages_wide, self.min_pages_tall)

    def _initialize_blocks(self, pages_wide=1, pages_tall=1):
        block_order = c.PSM_BLOCK_ORDERS[self.pixel_format]
        blocks_per_page = len(block_order[0]) * len(block_order)
        #print("Initializing %s pages wide, %s pages tall" % (pages_wide, pages_tall))

        # clear existing calculations
        self._cb_addr      = 0
        self._tb_addrs     = []
        self._tb_widths    = []
        self._blocks_used  = [0] * blocks_per_page * pages_tall * pages_wide
        self._buffer_width = pages_wide
        self._optimized_buffer_size = None

    @property
    def stack_on_y(self):
        '''
        Determines whether to grow in the Y direction or not.
        Additionally, this determines the orientation of the
        2D array when converting linear coordinates to/from xy.
        '''
        # only grow on the x axis if we're dealing with tall, thin textures
        return (self.height / self.page_height) <= (self.width / self.page_width)

    @property
    def free_block_count(self):
        return (
            self._blocks_used.count(self._free_block_val) +
            self._blocks_used.count(self._cull_block_val)
            )
    @property
    def efficiency(self):
        return 1 - self.free_block_count / max(1, self.buffer_size)
    @property
    def optimized_efficiency(self):
        delta = self.buffer_size - max(1, self.optimized_buffer_size)
        return 1 - (self.free_block_count - delta) / (self.buffer_size - delta)

    @property
    def base_address(self):
        return self._tb_addrs[0] if self._tb_addrs else 0
    @property
    def buffer_width(self):
        '''Number of pages wide the buffer is'''
        return self._buffer_width
    @property
    def buffer_size(self):
        return len(self._blocks_used)
    @property
    def optimized_buffer_size(self):
        if self._optimized_buffer_size is None:
            return self.buffer_size
        return self._optimized_buffer_size

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
        elif self.palette_format == c.PSM_CT32:
            return 4
        else:
            return 2
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
        return len(c.PSM_BLOCK_ORDERS[self.pixel_format][0])
    @property
    def page_block_height(self):
        '''Number of blocks tall each page is'''
        return len(c.PSM_BLOCK_ORDERS[self.pixel_format])

    @property
    def blocks_wide(self):
        '''Number of blocks wide the texture buffer is'''
        block_order = c.PSM_BLOCK_ORDERS[self.pixel_format]
        return len(block_order[0]) * self.buffer_width
    @property
    def blocks_tall(self):
        '''Number of blocks tall the texture buffer is'''
        return self.buffer_size // self.blocks_wide
    @property
    def pages_wide(self):
        '''Number of pages wide the texture buffer is'''
        return self.blocks_wide // self.page_block_width
    @property
    def pages_tall(self):
        '''Number of pages tall the texture buffer is'''
        return self.blocks_tall // self.page_block_height
    @property
    def min_pages_wide(self):
        '''Minimum number of pages of width are required to fit the fullsize image'''
        return int(math.ceil(max(self.page_width, self.width) / self.page_width))
    @property
    def min_pages_tall(self):
        '''Minimum number of pages of height are required to fit the fullsize image'''
        return int(math.ceil(max(self.page_height, self.height) / self.page_height))

    def _xy_address_to_linear_address(self, x, y):
        if x > self.blocks_wide:
            raise ValueError("Coordinate x=%s outside buffer width %s" % (x, self.blocks_wide))
        elif self.stack_on_y:
            return x * self.blocks_tall + y
        else:
            return y * self.blocks_wide + x

    def _linear_address_to_xy_address(self, linear_addr):
        if self.stack_on_y:
            return (linear_addr // self.blocks_tall,
                    linear_addr % self.blocks_tall)
        else:
            return (linear_addr % self.blocks_wide,
                    linear_addr // self.blocks_wide)

    def _block_address_to_xy_address(self, block_addr):
        blocks_per_page  = self.page_block_width * self.page_block_height

        page_block_addr = block_addr  % blocks_per_page
        page_index      = block_addr // blocks_per_page

        block_x = page_block_addr  % self.page_block_width
        block_y = page_block_addr // self.page_block_width
        page_x  = page_index  % self.pages_wide
        page_y  = page_index // self.pages_wide

        x0 = page_x * self.page_block_width
        y0 = page_y * self.page_block_height

        inv_block_order = c.PSM_INVERSE_BLOCK_ORDERS[self.pixel_format]
        inv_block_addr  = inv_block_order[block_y][block_x]

        xa = inv_block_addr  % self.page_block_width
        ya = inv_block_addr // self.page_block_width

        return x0 + xa, y0 + ya

    def _xy_address_to_block_address(self, x, y):
        blocks_per_page  = self.page_block_width * self.page_block_height
        page_x,  page_y  = x // self.page_block_width, y // self.page_block_height
        block_x, block_y = x  % self.page_block_width, y  % self.page_block_height

        block_order   = c.PSM_BLOCK_ORDERS[self.pixel_format]
        block_addr    = block_order[block_y][block_x]
        pages_skipped = page_y*self.buffer_width + page_x
        return block_addr + blocks_per_page*pages_skipped

    def _linear_address_to_block_address(self, linear_addr):
        return self._xy_address_to_block_address(
            *self._linear_address_to_xy_address(linear_addr)
            )

    def _mark_allocated_linear(self, allocate, b_width, b_height, linear_addr, test_only=False):
        return self._mark_allocated_xy(
            allocate, b_width, b_height,
            *self._linear_address_to_xy_address(linear_addr),
            test_only
            )

    def _mark_allocated_xy(self, allocate, b_width, b_height, x0, y0, test_only=False):
        if not allocate:
            allocate = self._free_block_val

        for y in range(y0, y0 + b_height):
            for x in range(x0, x0 + b_width):
                i = self._xy_address_to_linear_address(x, y)
                #print("%sllocating X=%s, Y=%s, I=%s" % ("A" if allocate else "Dea", x, y, i))
                if bool(self._blocks_used[i]) == bool(allocate):
                    raise ValueError("Block already %s at x=%s, y=%s" % (
                        "allocated" if allocate else "unallocated", x, y
                        ))
                if not test_only:
                    self._blocks_used[i] = allocate

        return self._xy_address_to_block_address(x0, y0)

    def _get_block_ordered_block_index_of_free_chunk(self, b_length):
        i = 0
        while i + b_length <= self.buffer_size:
            len_free = 0
            b_i = self._linear_address_to_block_address(i)
            for j in range(b_i, b_i + b_length):
                k = self._xy_address_to_linear_address(
                    *self._block_address_to_xy_address(j)
                    )
                len_free += not self._blocks_used[k]

            # every block is free
            if len_free == b_length:
                return b_i

            try:
                i = self._blocks_used.index(self._free_block_val, i + 1)
            except ValueError:
                # no free blocks
                break

        return None

    def _get_linear_index_of_free_chunk(self, b_width, b_height):
        corner_check_coords = (
            (          0,            0), # upper left
            (b_width - 1, b_height - 1), # lower right
            (b_width - 1,            0), # upper right
            (          0, b_height - 1), # lower left
            )
        side_check_coords = (  # ignoring corners
            *tuple((0,            y) for y in range(1, b_height - 1)),  # left
            *tuple((b_width - 1,  y) for y in range(1, b_height - 1)),  # right
            *tuple((x,            0) for x in range(1, b_width  - 1)),  # top
            *tuple((x, b_height - 1) for x in range(1, b_width  - 1)),  # bottom
            )
        center_check_coords = (
            (x, y)
            for x in range(1, b_width  - 1)
            for y in range(1, b_height - 1)
            )
        max_block_x = self.blocks_wide
        max_block_y = self.blocks_tall

        i = 0
        while i < self.buffer_size:
            x0, y0 = self._linear_address_to_xy_address(i)
            free = (
                x0 + b_width  <= max_block_x and
                y0 + b_height <= max_block_y
                )
            # check the corners for high certainty on block freeness
            for xa, ya in corner_check_coords:
                if not free:
                    break
                j = self._xy_address_to_linear_address(x0 + xa, y0 + ya)
                free &= j < self.buffer_size and not self._blocks_used[j]

            # check the sides for certainty(unless fragmentation has occurred)
            for xa, ya in side_check_coords:
                if not free:
                    break
                j = self._xy_address_to_linear_address(x0 + xa, y0 + ya)
                free &= j < self.buffer_size and not self._blocks_used[j]

            # check the centers(if necessary)
            if self.check_centers:
                for xa, ya in center_check_coords:
                    if not free:
                        break
                    j = self._xy_address_to_linear_address(x0 + xa, y0 + ya)
                    free &= j < self.buffer_size and not self._blocks_used[j]

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

    def get_usage_string(self, page_borders=False):
        lines_gen = (
            "".join(
                self._used_chars.get(
                    self._blocks_used[self._xy_address_to_linear_address(x, y)],
                    self._unknown_char
                    )
                for x in range(self.blocks_wide)
                )
            for y in range(self.blocks_tall)
            )
        if page_borders:
            lines = []
            border_line_h = self._border_char_c.join(
                self._border_char_h * self.page_block_width
                for p in range(self.pages_wide)
                ) + "\n"
            for line in lines_gen:
                page_line = self._border_char_v.join(
                    line[i: i + self.page_block_width]
                    for i in range(0, self.blocks_wide, self.page_block_width)
                    )
                lines.append(page_line + "\n")

            usage_str = border_line_h.join(
                "".join(lines[i: i + self.page_block_height])
                for i in range(0, len(lines), self.page_block_height)
                )
        else:
            usage_str = "\n".join(lines_gen)

        return usage_str

    def get_address_and_width(self, mip_level):
        if mip_level in range(min(len(self._tb_addrs), len(self._tb_widths))):
            return self._tb_addrs[mip_level], self._tb_widths[mip_level]
        return 0, 0

    def pack(self):
        tex_count = 1 + self.mipmaps

        pages_wide, pages_tall = self.min_pages_wide, self.min_pages_tall
        allocations = 0
        allocate = True
        m = 0

        while allocate or m < tex_count:
            if allocate:
                self._initialize_blocks(pages_wide, pages_tall)
                pack_palette = self.has_palette
                allocations += 1
                allocate = False
                m = 0

            # calculate how many blocks wide and tall are required
            mip_width  = max(self.block_width,  self.width  >> m)
            mip_height = max(self.block_height, self.height >> m)
            b_width  = mip_width  // self.block_width
            b_height = mip_height // self.block_height

            addr = self._get_linear_index_of_free_chunk(b_width, b_height)
            if addr is not None:
                mip_width   = b_width * self.block_width
                buffer_addr = self._mark_allocated_linear("T%s" % m, b_width, b_height, addr)

                # if the texture will cross into the page below, we
                # need to set the width to the overall buffer width.
                _, buffer_block_y = self._linear_address_to_xy_address(addr)
                page_y0 = buffer_block_y // self.page_block_height
                page_y1 = (buffer_block_y + b_height - 1) // self.page_block_height
                if page_y0 == page_y1:
                    # texture doesn't cross into page below
                    buffer_width = int(math.ceil(mip_width / 64))
                else:
                    buffer_width = int(math.ceil(self.buffer_width * self.page_width) / 64)

                self._tb_addrs.append(buffer_addr)
                self._tb_widths.append(buffer_width)

            m += 1

            # if there is a palette, pack it.
            # NOTE: palettes are packed linearly in block-order rather than scanline order.
            if m == tex_count and pack_palette:
                pack_palette = False
                addr = self._get_block_ordered_block_index_of_free_chunk(self.palette_size)
                if addr is not None:
                    self._cb_addr = addr
                    for i in range(self.palette_size):
                        self._mark_allocated_xy(
                            "CB", 1, 1, *self._block_address_to_xy_address(addr + i)
                            )

            if addr is None:
                # one of the addresses ended up null, indicating we need to reallocate
                if allocations >= self.max_allocations:
                    raise ValueError("Could not allocate large enough buffer to fit all texture data.")

                allocate = True
                # can't fit something. expand pages in direction of growth and restart
                pages_tall += 1

    def optimize(self):
        opt_buffer_size = self.buffer_size
        page_block_size = self.page_block_width * self.page_block_height
        # scroll backward through the end of the buffer
        # and remove any pages that have no blocks used
        x0 = (self.pages_wide - 1) * self.page_block_width
        y0 = (self.pages_tall - 1) * self.page_block_height

        # loop over every page on the last page row, and reduce the
        # opt_buffer_size by it if its completely unallocated. we are
        # going right to left as that is the order to deallocate pages.
        # We are also ignoring the first page in the row since, the row
        # was created because at least that page was deemed necessary
        while x0 >= self.page_block_width:
            allocate_args = (
                self._cull_block_val,
                self.page_block_width,
                self.page_block_height,
                self._xy_address_to_linear_address(x0, y0)
                )

            # test marking the whole page as allocated to ensure it's
            # all free before actually marking it all as cullable
            try:
                self._mark_allocated_linear(*allocate_args, test_only=True)
            except ValueError:
                break

            self._mark_allocated_linear(*allocate_args)
            opt_buffer_size -= page_block_size
            x0 -= self.page_block_width

        self._optimized_buffer_size = opt_buffer_size
