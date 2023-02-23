import hashlib
import os

from traceback import format_exc
from .serialization.collision import G3DCollision
from . import constants as c
from . import util


def _decompile_collision(**kwargs):
    coll_tris    = kwargs["coll_tris"]
    mesh_indices = kwargs["mesh_indices"]
    asset_type   = kwargs["asset_type"]
    filepath     = kwargs["filepath"]

    if asset_type == "obj":
        g3c_collision = G3DCollision()
        g3c_collision.import_g3c(coll_tris, mesh_indices)
        g3c_collision.export_obj(filepath)
        return
    elif asset_type != c.COLLISION_CACHE_EXTENSION:
        return

    raise NotImplementedError("TODO")


def import_collision(worlds_tag, data_dir):
    raise NotImplementedError("TODO")


def decompile_collision(
        worlds_tag, data_dir,
        asset_types=c.COLLISION_CACHE_EXTENSION, overwrite=False,
        ):
    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    for asset_type in asset_types:
        if asset_type not in (c.COLLISION_CACHE_EXTENSION, *c.COLLISION_ASSET_EXTENSIONS):
            raise ValueError("Unknown collision type '%s'" % asset_type)

    assets_dir = os.path.join(data_dir, c.EXPORT_FOLDERNAME, c.COLL_FOLDERNAME)
    cache_dir  = os.path.join(data_dir, c.IMPORT_FOLDERNAME, c.COLL_FOLDERNAME)

    coll_tris = worlds_tag.get_collision_tris()
    raise NotImplementedError("Not implemented")
