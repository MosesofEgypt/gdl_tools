from . import constants as c
from ..util import *


def locate_models(
        data_dir, cache_files=False, target_ps2=False,
        target_xbox=False, target_ngc=False,
        target_dreamcast=False, target_arcade=False,
        ):
    return locate_assets(data_dir,
        c.MODEL_ASSET_EXTENSIONS if not cache_files else
        (c.MODEL_CACHE_EXTENSION_XBOX, ) if target_xbox else
        (c.MODEL_CACHE_EXTENSION_NGC, )  if target_ngc else
        (c.MODEL_CACHE_EXTENSION_DC, )   if target_dreamcast else
        (c.MODEL_CACHE_EXTENSION_ARC, )  if target_arcade else
        (c.MODEL_CACHE_EXTENSION_PS2, )  if target_ps2 else
        ()
        )

def locate_textures(
        data_dir, cache_files=False, target_ps2=False,
        target_xbox=False, target_ngc=False,
        target_dreamcast=False, target_arcade=False
        ):
    return locate_assets(data_dir,
        c.TEXTURE_ASSET_EXTENSIONS if not cache_files else
        (c.TEXTURE_CACHE_EXTENSION_XBOX, ) if target_xbox else
        (c.TEXTURE_CACHE_EXTENSION_NGC, )  if target_ngc else
        (c.TEXTURE_CACHE_EXTENSION_DC, )   if target_dreamcast else
        (c.TEXTURE_CACHE_EXTENSION_ARC, )  if target_arcade else
        (c.TEXTURE_CACHE_EXTENSION_PS2, )  if target_ps2 else
        ()
        )

def locate_animations(data_dir, cache_files=False):
    return locate_assets(data_dir,
        c.ANIMATION_CACHE_EXTENSION if cache_files else
        c.ANIMATION_ASSET_EXTENSIONS
        )

def locate_collision(data_dir, cache_files=False):
    return locate_assets(data_dir,
        c.COLLISION_CACHE_EXTENSION if cache_files else
        c.COLLISION_ASSET_EXTENSIONS
        )

def is_dreamcast_bitmaps(bitmaps):
    # arcade and dreamcast have the same extensions.
    # check the bitmap structure to tell them apart.
    for bitm in bitmaps:
        if hasattr(bitm, "dc_sig"):
            return True
    return False
