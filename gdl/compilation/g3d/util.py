from . import constants as c
from ..util import *


def locate_models(
        data_dir, cache_files=False, target_xbox=False, target_ngc=False
        ):
    return locate_assets(data_dir,
        c.MODEL_ASSET_EXTENSIONS if not cache_files else
        (c.MODEL_CACHE_EXTENSION_XBOX, ) if target_xbox else
        (c.MODEL_CACHE_EXTENSION_NGC, ) if target_ngc else
        (c.MODEL_CACHE_EXTENSION_PS2, )
        )

def locate_textures(
        data_dir, cache_files=False, target_xbox=False, target_ngc=False
        ):
    return locate_assets(data_dir,
        c.TEXTURE_ASSET_EXTENSIONS if not cache_files else
        (c.TEXTURE_CACHE_EXTENSION_XBOX, ) if target_xbox else
        (c.TEXTURE_CACHE_EXTENSION_NGC, ) if target_ngc else
        (c.TEXTURE_CACHE_EXTENSION_PS2, )
        )

def locate_animations(data_dir, cache_files=False):
    return locate_assets(data_dir,
        c.ANIMATION_CACHE_EXTENSION if cache_files else
        c.ANIMATION_ASSET_EXTENSIONS
        )
