import os

from traceback import format_exc

from .tag import GdlTag
from ...compilation.util import calculate_padding
from ...compilation.g3d import constants as c


class TexdefPs2Tag(GdlTag):

    def get_bitmap_names(self, by_name=False):
        name_counts = {}
        bitmap_names = []

        for bitm, bitm_def in zip(self.data.bitmaps, self.data.bitmap_defs):
            asset_name = bitm_def.name if bitm_def.name else c.UNNAMED_ASSET_NAME
            count = name_counts.setdefault(asset_name, 0)
            name_counts[asset_name] += 1

            bitmap_names.append(dict(
                index       = len(bitmap_names),
                name        = f"{asset_name}.{count:04}" if count else asset_name,
                asset_name  = asset_name
                ))

        if by_name:
            return {d['name']: d for d in bitmap_names}

        return {i: d for i, d in enumerate(bitmap_names)}
