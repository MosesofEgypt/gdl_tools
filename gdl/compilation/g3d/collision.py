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

    object_mesh_indices = {
        w_obj.name.upper().strip(): dict(index=w_obj.coll_tri_index, count=w_obj.coll_tri_count)
        for w_obj in worlds_tag.data.world_objects
        if w_obj.coll_tri_index >= 0 and w_obj.coll_tri_count > 0
        }
    item_mesh_indices = {
        item.name.upper().strip(): dict(index=item.coll_tri_index, count=item.coll_tri_count)
        for item in worlds_tag.data.item_instances
        if item.coll_tri_index >= 0 and item.coll_tri_count > 0
        }

    for asset_type in asset_types:
        base_dir = cache_dir if asset_type == c.COLLISION_CACHE_EXTENSION else assets_dir
        objects_filename = "world_collision.%s" % asset_type
        items_filename   = "items_collision.%s" % asset_type

        objects_filepath = os.path.join(base_dir, objects_filename)
        items_filepath   = os.path.join(base_dir, items_filename)

        if not os.path.isfile(objects_filepath) or overwrite:
            _decompile_collision(
                coll_tris = coll_tris, mesh_indices = object_mesh_indices,
                filepath = objects_filepath, asset_type = asset_type,
                )

        if not os.path.isfile(items_filename) or overwrite:
            _decompile_collision(
                coll_tris = coll_tris, mesh_indices = item_mesh_indices,
                filepath = items_filepath, asset_type = asset_type,
                )
