import math

from . import constants as c


class TextureBufferPacker:
    pixel_format   = ""
    palette_format = None

    height  = 0
    width   = 0
    mipmaps = 0

    check_centers = False
    max_reallocations = 20

    _buffer_width = 0  # total number of pages wide the buffer is
                       # this isn't quite the same as the width of
                       # tex0, as we may end up storing the images
                       # stacked horizontally if they are taller than
                       # wide, as they'll fit better stacked sideways
    _tb_addrs  = ()
    _tb_widths = ()
    _cb_addr   = -1
    _blocks_free = ()
    _free_char = "-"
    _used_char = "#"

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

    @property
    def efficiency(self):
        return 1 - sum(self._blocks_free) / self.buffer_size
    @property
    def optimized_efficiency(self):
        return 1 - sum(self._blocks_free) / self.optimized_buffer_size
    @property
    def usage_string(self):
        return "\n".join(
            "".join(
                self._free_char if self._blocks_free[y*self.blocks_wide + x] else self._used_char
                for x in range(self.blocks_wide)
                )
            for y in range(self.blocks_tall)
            )
    @property
    def base_address(self):
        return self._tb_addrs[0] if self._tb_addrs else 0
    @property
    def buffer_width(self):
        '''Number of pages wide the buffer is'''
        return self._buffer_width
    @property
    def buffer_size(self):
        return len(self._blocks_free)
    @property
    def optimized_buffer_size(self):
        buffer_size = self.buffer_size
        # scroll backward through the end of the buffer
        # and remove any pages that have no blocks used
        # TODO: implement this
        return buffer_size

    @property
    def has_palette(self):
        return (
            self.palette_format is not None and
            (self.pixel_format == c.PSM_T8 or self.pixel_format == c.PSM_T4)
            )
    @property
    def palette_size(self):
        '''Returns the width and height of the palette in blocks'''
        if self.pixel_format == c.PSM_T4:
            return (1, 1)
        elif self.pixel_format != c.PSM_T8:
            return (0, 0)
        elif self.palette_format == c.PSM_CT32:
            return (2, 2)
        else:
            return (2, 1)
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
    def min_pages_wide(self):
        '''Minimum number of pages of width are required to fit the fullsize image'''
        return int(math.ceil(max(self.page_width, self.width) / self.page_width))
    @property
    def min_pages_tall(self):
        '''Minimum number of pages of height are required to fit the fullsize image'''
        return int(math.ceil(max(self.page_height, self.height) / self.page_height))

    def _xy_address_to_linear_address(self, x, y):
        block_order = c.PSM_BLOCK_ORDERS[self.pixel_format]
        blocks_wide = len(block_order[0]) * self.buffer_width
        if x > blocks_wide:
            raise ValueError("Coordinate x=%s outside buffer width %s" % (x, blocks_wide))
        return y * blocks_wide + x

    def _linear_address_to_xy_address(self, linear_addr):
        block_order = c.PSM_BLOCK_ORDERS[self.pixel_format]
        blocks_wide = len(block_order[0]) * self.buffer_width
        x = linear_addr % blocks_wide
        y = linear_addr // blocks_wide
        return x, y

    def _xy_address_to_block_address(self, x, y):
        blocks_per_page = self.page_block_width*self.page_block_height
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

    def _initialize_blocks(self, pages_wide=1, pages_tall=1):
        block_order = c.PSM_BLOCK_ORDERS[self.pixel_format]
        blocks_per_page = len(block_order[0]) * len(block_order)
        #print("Initializing %s pages wide, %s pages tall" % (pages_wide, pages_tall))

        # clear existing calculations
        self._cb_addr      = 0
        self._tb_addrs     = []
        self._tb_widths    = []
        self._blocks_free  = [True] * blocks_per_page * pages_tall * pages_wide
        self._buffer_width = pages_wide

    def _mark_allocated_linear(self, allocate, b_width, b_height, linear_addr):
        return self._mark_allocated_xy(
            allocate, b_width, b_height,
            *self._linear_address_to_xy_address(linear_addr)
            )

    def _mark_allocated_xy(self, allocate, b_width, b_height, x0, y0):
        allocate = bool(allocate)
        for y in range(y0, y0 + b_height):
            for x in range(x0, x0 + b_width):
                i = self._xy_address_to_linear_address(x, y)
                #print("%sllocating X=%s, Y=%s, I=%s" % ("A" if allocate else "Dea", x, y, i))
                if bool(self._blocks_free[i]) != allocate:
                    raise ValueError("Block already %s at x=%s, y=%s" % (
                        "allocated" if allocate else "unallocated", x, y
                        ))
                self._blocks_free[i] = not allocate

        return self._xy_address_to_block_address(x0, y0)

    def _get_linear_index_of_free_chunk(self, b_width, b_height):
        i = 0
        block_count = self.buffer_size
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
        while i < block_count:
            try:
                i = self._blocks_free.index(True, i)
            except ValueError:
                # no more free blocks
                break

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
                free &= j < block_count and self._blocks_free[j]

            # check the sides for certainty(unless fragmentation has occurred)
            for xa, ya in side_check_coords:
                if not free:
                    break
                j = self._xy_address_to_linear_address(x0 + xa, y0 + ya)
                free &= j < block_count and self._blocks_free[j]

            # check the centers(if necessary)
            if self.check_centers:
                for xa, ya in center_check_coords:
                    if not free:
                        break
                    j = self._xy_address_to_linear_address(x0 + xa, y0 + ya)
                    free &= j < block_count and self._blocks_free[j]

            # every block is free
            if free:
                #print("Located free block at %s" % i)
                return i

            i += 1

        return None

    def get_address_and_width(self, mip_level):
        if i in range(min(len(self._tb_addrs), len(self._tb_widths))):
            return self._tb_addrs[mip_level], self._tb_widths[mip_level]
        return 0, 0

    def calculate(self):
        tex_count = 1 + self.mipmaps

        # only grow on the x axis if we're dealing with tall, thin textures
        grow_on_x = (self.height / self.page_height) > (self.width / self.page_width)

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
                mip_width = b_width * self.block_width
                block_addr  = self._mark_allocated_linear(True, b_width, b_height, addr)
                block_width = int(math.ceil(mip_width / self.page_width))

                self._tb_addrs.append(block_addr)
                self._tb_widths.append(block_width)

            m += 1

            # if there is a palette, pack it no later than the 3rd texture
            if m == min(tex_count, 3) and pack_palette:
                addr = self._get_linear_index_of_free_chunk(*self.palette_size)
                if addr is not None:
                    self._cb_addr = self._mark_allocated_linear(True, *self.palette_size, addr)
                    pack_palette = False

            if addr is None:
                # one of the addresses ended up null, indicating we need to reallocate
                if allocations >= self.max_reallocations:
                    raise ValueError("Could not allocate large enough buffer to fit all texture data.")

                allocate = True
                # can't fit something. expand pages in direction of growth and restart
                if grow_on_x:
                    pages_wide += 1
                else:
                    pages_tall += 1
