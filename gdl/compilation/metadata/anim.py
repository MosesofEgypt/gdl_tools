import os

from traceback import format_exc
from . import constants as c
from . import util


def compile_anim_metadata(data_dir, by_asset_name=False):
    pass#raise NotImplementedError()


def decompile_anim_metadata(
        animations_tag, data_dir,
        asset_types=c.METADATA_ASSET_EXTENSIONS[0],
        overwrite=False, individual_meta=True
        ):
    pass#raise NotImplementedError()
