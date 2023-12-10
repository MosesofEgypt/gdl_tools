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
        c.ANIMATION_CACHE_EXTENSIONS if cache_files else
        c.ANIMATION_ASSET_EXTENSIONS
        )

def locate_metadata(data_dir, cache_files=False):
    return locate_assets(data_dir,
        c.METADATA_CACHE_EXTENSIONS if cache_files else
        c.METADATA_ASSET_EXTENSIONS
        )

def invert_map(mapping):
    if isinstance(mapping, dict):
        return {v: k for k, v in values.items()}
    elif isinstance(mapping, (list, tuple)):
        return {v: k for k, v in enumerate(values)}

    raise ValueError(f"Cannot invert mapping for type {type(mapping)}")

def dereference_indexed_values(indices, value_map):
    '''
    NOTE: This function returns a map iterator. To ensure
    the values it generates are concrete, you must pass it
    to a concrete iterable constructor(i.e. a list or tuple)
    '''
    return map(value_map.__getitem__, indices)
