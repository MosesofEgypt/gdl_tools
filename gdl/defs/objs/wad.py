from .tag import GdlTag
from ...compilation.util import calculate_padding


class WadTag(GdlTag):

    def get_lump_of_type(self, typ):
        for lump_header, lump in zip(
                self.data.lump_headers, self.data.lumps
                ):
            if lump_header.lump_id.enum_name.lower() == typ.lower():
                return lump
        return None

    def _add_lump_of_type(self, typ):
        self.data.lump_headers.append()
        try:
            self.data.lump_headers[-1].lump_id.set_to(typ)
        except Exception as e:
            self.data.lump_headers.pop(-1)
            raise e

        self.data.lumps.append()
        return self.data.lumps[-1]

    def get_or_add_lump_of_type(self, typ):
        lump = self.get_lump_of_type(typ)
        if lump is None:
            lump = self._add_lump_of_type(typ)

        return lump

    def set_pointers(self, offset=0):
        offset += self.data.wad_header.binsize
        self.data.wad_header.lump_headers_pointer = offset

        offset += self.data.lump_headers.binsize

        for lump_header, lump in zip(self.data.lump_headers, self.data.lumps):
            lump_header.lump_array_pointer = offset
            offset += lump.binsize
            offset += calculate_padding(offset, 4)
