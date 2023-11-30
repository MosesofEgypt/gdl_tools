import os

from traceback import format_exc
from .serialization.animation import G3DAnimation
from .serialization.asset_cache import get_asset_checksum, verify_source_file_asset_checksum
from .serialization.animation_cache import AnimationCache
from . import constants as c
from . import util

def compile_animation(kwargs):
    name             = kwargs.pop("name")
    cache_type       = kwargs.pop("cache_type")
    cache_filepath   = kwargs.pop("cache_filepath")
    asset_filepath   = kwargs.pop("asset_filepath")

    print("Compiling animation: %s" % name)
    g3d_animation = G3DAnimation()
    asset_type    = os.path.splitext(asset_filepath)[-1].strip(".")

    if asset_type == "jmm":
        g3d_animation.import_jmm(asset_filepath)
    else:
        raise NotImplementedError(f"Unknown asset type '{asset_type}'")

    animation_cache = g3d_animation.compile_g3d(cache_type)
    animation_cache.source_asset_checksum = get_asset_checksum(
        filepath=asset_filepath, algorithm=animation_cache.checksum_algorithm
        )
    animation_cache.serialize_to_file(cache_filepath)


def decompile_animation(kwargs):
    name            = kwargs["name"]
    animation_cache = kwargs["animation_cache"]
    asset_type      = kwargs["asset_type"]
    filepath        = kwargs["filepath"]

    print("Decompiling animation: %s" % name)
    if asset_type == "jmm":
        g3d_animation = G3DAnimation()
        g3d_animation.import_g3d(animation_cache)
        g3d_animation.export_jmm(asset_filepath)
    elif asset_type in c.ANIMATION_CACHE_EXTENSIONS:
        animation_cache.serialize_to_file(filepath)
    else:
        raise NotImplementedError(f"Unknown asset type '{asset_type}'")


def import_animations(
        anim_tag, objects_tag,
        data_dir=".", cache_dir=None
        ):
    # TODO: implement this
    pass


def export_animations(
        anim_tag, asset_types=c.ANIMATION_CACHE_EXTENSIONS,
        overwrite=False, parallel_processing=True,
        data_dir=".", assets_dir=None, cache_dir=None
        ):
    data_dir = pathlib.Path(data_dir)
    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    for asset_type in asset_types:
        if asset_type not in (*c.ANIMATION_CACHE_EXTENSIONS,
                              *c.ANIMATION_ASSET_EXTENSIONS):
            raise ValueError("Unknown model type '%s'" % asset_type)

    if not assets_dir:
        assets_dir  = data_dir.joinpath(c.EXPORT_FOLDERNAME, c.ANIM_FOLDERNAME)
    if not cache_dir:
        cache_dir   = data_dir.joinpath(c.IMPORT_FOLDERNAME, c.ANIM_FOLDERNAME)

    atrees = anim_tag.data.atrees
    object_assets, bitmap_assets = objects_tag.get_cache_names()

    all_job_args = []


def atree_to_animation_caches(atree, cache_type=None):
    pass
