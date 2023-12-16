import pathlib

from traceback import format_exc
from ...supyr_struct_ext import FixedBytearrayBuffer
from ..metadata import objects as objects_metadata
from .serialization import halo_jm
from .serialization.animation import G3DAnimationNode
from .serialization.model import G3DModel
from .serialization.asset_cache import get_asset_checksum
from .serialization.model_cache import ModelCache, Ps2ModelCache,\
     DreamcastModelCache, ArcadeModelCache
from . import constants as c
from . import util


def compile_model(kwargs):
    name             = kwargs.pop("name")
    optimize         = kwargs.pop("optimize_strips")
    cache_type       = kwargs.pop("cache_type")
    cache_filepath   = pathlib.Path(kwargs.pop("cache_filepath"))
    asset_filepath   = pathlib.Path(kwargs.pop("asset_filepath"))

    print("Compiling model: %s" % name)
    g3d_model = G3DModel(
        optimize_for_ps2=(cache_type == c.MODEL_CACHE_EXTENSION_PS2 and optimize),
        optimize_for_ngc=(cache_type == c.MODEL_CACHE_EXTENSION_NGC and optimize),
        optimize_for_xbox=(cache_type == c.MODEL_CACHE_EXTENSION_XBOX and optimize),
        )
    asset_type = asset_filepath.suffix.strip(".")

    if asset_type == "obj":
        with open(asset_filepath, "r") as f:
            g3d_model.import_obj(f)
    else:
        raise NotImplementedError(f"Unknown asset type '{asset_type}'")

    model_cache = g3d_model.compile_g3d(cache_type)
    model_cache.source_asset_checksum = get_asset_checksum(
        filepath=asset_filepath, algorithm=model_cache.checksum_algorithm
        )
    model_cache.serialize_to_file(cache_filepath)


def decompile_model(kwargs):
    name           = kwargs["name"]
    texture_assets = kwargs["texture_assets"]
    model_caches   = kwargs["model_caches"]
    asset_type     = kwargs["asset_type"]
    filepaths      = kwargs["filepaths"]
    g3d_nodes      = kwargs.get("g3d_nodes", None)

    print("Decompiling model: %s" % name)
    if asset_type == "obj":
        for i, model_cache in enumerate(model_caches):
            g3d_model = G3DModel()
            g3d_model.import_g3d(model_cache)
            g3d_model.export_obj(
                filepaths[i], texture_assets,
                swap_lightmap_and_diffuse=kwargs["swap_lightmap_and_diffuse"]
                )
    elif asset_type == "jms":
        filepath = pathlib.Path(filepaths[0])
        if not filepath.is_file():
            g3d_models = {}
            for i, model_cache in enumerate(model_caches):
                if model_cache:
                    g3d_models[i] = G3DModel()
                    g3d_models[i].import_g3d(model_cache)

            jms = halo_jm.export_g3d_to_jms(g3d_nodes, g3d_models)
            jms.name = name
            halo_jm.halo_model.write_jms(filepath, jms)

    elif asset_type in c.MODEL_CACHE_EXTENSIONS:
        for i, model_cache in enumerate(model_caches):
            model_cache.serialize_to_file(filepaths[i])
    else:
        raise NotImplementedError(f"Unknown asset type '{asset_type}'")


def import_models(
        objects_tag, target_ps2=False, target_ngc=False,
        target_xbox=False, target_dreamcast=False, target_arcade=False,
        data_dir=".", cache_dir=None
        ):
    if not cache_dir:
        cache_dir = pathlib.Path(data_dir).joinpath(c.IMPORT_FOLDERNAME)

    model_caches_by_name = {}
    all_asset_filepaths = util.locate_models(
        cache_dir, cache_files=True, target_ps2=target_ps2,
        target_ngc=target_ngc, target_xbox=target_xbox,
        target_dreamcast=target_dreamcast, target_arcade=target_arcade
        )

    for name in sorted(all_asset_filepaths):
        try:
            with open(all_asset_filepaths[name], "rb") as f:
                model_cache = ModelCache.get_cache_class(f)()
                model_cache.parse(f)
                model_caches_by_name[name] = model_cache
        except Exception:
            print(format_exc())
            print("Could not load model:\n    %s" % all_asset_filepaths[name])

    # we uppercase everything for uniformity. do it here
    _, inv_bitmap_names = objects_tag.get_cache_names(by_name=True, recache=True)
    inv_bitmap_names = {n.upper(): i for n, i in inv_bitmap_names.items()}

    objects     = objects_tag.data.objects
    object_defs = objects_tag.data.object_defs
    del objects[:]
    del object_defs[:]

    # get the metadata for all models to import
    metadata = objects_metadata.compile_objects_metadata(
        cache_dir
        ).get("objects", ())
    objects_metadata_by_name = {
        meta["name"]: meta for meta in metadata if "name" in meta
        }

    for name in sorted(objects_metadata_by_name):
        meta        = objects_metadata_by_name[name]
        model_cache = model_caches_by_name.get(name)

        # append object and object_def in case model is missing. this should
        # keep the number of objects intact, and thus animation frame counts
        is_fifo      = bool(getattr(model_cache, "fifo_rawdata", None))
        is_uncomp_lm = model_cache.has_lmap and not is_fifo

        objects.append(
            case=("fifo" if is_fifo else "uncomp_lm" if is_uncomp_lm else "uncomp")
            )

        object_defs.append()
        obj     = objects[-1]
        obj_def = object_defs[-1]

        if not model_cache:
            print(f"Warning: Could not locate model file for '{name}'")
            continue

        meta_flags = dict(meta.setdefault("flags", {}))
        meta_flags.update(
            mesh       = model_cache.has_mesh,
            v_normals  = model_cache.has_normals,
            v_colors   = model_cache.has_colors,
            lmap       = model_cache.has_lmap,
            )

        if isinstance(model_cache, Ps2ModelCache):
            obj_flags       = obj.flags
            # copy data over
            obj.bnd_rad     = model_cache.bounding_radius
            obj.tri_count   = model_cache.tri_count
            obj.vert_count  = model_cache.vert_count
            obj.id_num      = len(objects)

            # loop over all the subobjects and update the headers and models
            for i, geom in enumerate(model_cache.geoms):
                subobj_model = obj.data.sub_object_models[-1]

                if i == 0:
                    subobj_header = obj.sub_object_0
                else:
                    obj.data.sub_objects.append()
                    subobj_header = obj.data.sub_objects[-1]

                tex_meta   = inv_bitmap_names.get(geom["tex_name"], {})
                lm_meta    = inv_bitmap_names.get(geom["lm_name"], {})
                if not tex_meta:
                    print(f"Warning: Texture '{geom['tex_name']}' used in "
                          f"subobject {i} of '{name}' does not exist.")

                if model_cache.has_lmap and not lm_meta:
                    print(f"Warning: Lightmap '{geom['lm_name']}' used in "
                          f"subobject {i} of '{name}' does not exist.")

                # update the header and model data
                subobj_model.data         = geom["vif_rawdata"]
                subobj_model.qword_count  = geom["qword_count"]
                subobj_header.qword_count = geom["qword_count"] + 1
                subobj_header.lod_k       = geom["lod_k"]
                subobj_header.tex_index   = tex_meta.get("index", 0)
                subobj_header.lm_index    = lm_meta.get("index", 0)
        elif isinstance(model_cache, (DreamcastModelCache, ArcadeModelCache)):
            raise NotImplementedError("hecken")

            # copy data over
            obj         = objects[-1]
            obj_flags   = obj.lods[0].flags
            obj.bnd_rad = model_cache.bounding_radius
            for lod in obj.lods:
                lod.tri_count   = model_cache.tri_count
                lod.vert_count  = model_cache.vert_count
                lod.id_num      = len(objects)
                # NOTE: we're doing a bit of a hack to use the
                #       same flags object for each lod so we dont
                #       have to set the bits on each object
                lod.flags       = obj_flags
        else:
            raise ValueError(f"Unknown model type '{type(model_cache)}'")

        # populate the object def
        obj_def.bnd_rad   = model_cache.bounding_radius
        obj_def.name      = meta.get("asset_name", name)[-16:]
        obj_def.obj_index = len(objects) - 1
        obj_def.frames    = 0 # only non-zero in DEMO objects

        # copy flags from metadata
        for name, val in meta_flags.items():
            if hasattr(obj_flags, name):
                setattr(obj_flags, name, bool(val))


def export_models(
        objects_tag, anim_tag=None, asset_types=c.MODEL_CACHE_EXTENSIONS,
        parallel_processing=False, overwrite=False,
        swap_lightmap_and_diffuse=False,
        data_dir=".", assets_dir=None, cache_dir=None
        ):
    data_dir = pathlib.Path(data_dir)
    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    for asset_type in asset_types:
        if asset_type not in (*c.MODEL_CACHE_EXTENSIONS,
                              *c.MODEL_ASSET_EXTENSIONS,
                              *c.ACTOR_ASSET_EXTENSIONS):
            raise ValueError("Unknown model type '%s'" % asset_type)

    if not assets_dir: assets_dir  = data_dir
    if not cache_dir:  cache_dir   = data_dir.joinpath(c.IMPORT_FOLDERNAME)

    is_arcade   = False
    for bitm in objects_tag.data.bitmaps:
        is_arcade   = hasattr(bitm, "ncc_table_data")
        break

    texture_assets = util.locate_textures(assets_dir)

    objects = {i: obj for i, obj in enumerate(objects_tag.data.objects)}
    object_assets, bitmap_assets = objects_tag.get_cache_names()

    all_job_args = []
    model_caches_by_index = {}

    actor_asset_types = tuple(s for s in asset_types if s in c.ACTOR_ASSET_EXTENSIONS)
    model_asset_types = tuple(s for s in asset_types if s not in actor_asset_types)

    # loop over each object
    for asset_type in model_asset_types:
        for i in range(len(object_assets)):
            if i not in object_assets or i not in objects:
                continue

            asset = object_assets[i]
            filename = f"{asset['name']}.{asset_type}"
            if asset['name'] != asset["asset_name"]:
                filename = pathlib.PurePath(asset["asset_name"], filename)

            filepath = pathlib.Path(
                cache_dir if asset_type in c.MODEL_CACHE_EXTENSIONS else assets_dir,
                asset.get("actor", "_objects"), filename
                )
            if filepath.is_file() and not overwrite:
                continue

            try:
                model_cache = object_to_model_cache(
                    objects[i], cache_type=asset_type, obj_index=i,
                    bitmap_assets=bitmap_assets, is_arcade=is_arcade
                    )
                model_caches_by_index[i] = model_cache

                if asset_type in c.MODEL_CACHE_EXTENSIONS:
                    if isinstance(model_cache, Ps2ModelCache) and asset_type not in (
                            c.MODEL_CACHE_EXTENSION_PS2, c.MODEL_CACHE_EXTENSION_XBOX,
                            c.MODEL_CACHE_EXTENSION_NGC
                            ):
                        print("Cannot export PS2/XBOX/NGC model to non-PS2/XBOX/NGC cache file.")
                        continue
                    elif (isinstance(model_cache, DreamcastModelCache) and
                          asset_type != c.MODEL_CACHE_EXTENSION_DC):
                        print("Cannot export Dreamcast model to non-Dreamcast cache file.")
                        continue
                    elif (isinstance(model_cache, ArcadeModelCache) and
                          asset_type != c.MODEL_CACHE_EXTENSION_ARC):
                        print("Cannot export Arcade model to non-Arcade cache file.")
                        continue

                all_job_args.append(dict(
                    texture_assets=texture_assets, model_caches=[model_cache],
                    name=asset['name'], asset_type=asset_type, filepaths=[filepath],
                    swap_lightmap_and_diffuse=swap_lightmap_and_diffuse,
                    ))

            except:
                print(format_exc())
                print(f"The above error occurred while trying to export object {i} as {asset_type}. "
                      f"name: '{asset.get('name')}', asset_name: '{asset.get('asset_name')}'"
                      )

    object_indices_by_name = {object_assets[k]["name"]: k for k in object_assets}
    # loop over each actor
    for asset_type in actor_asset_types:
        for atree in anim_tag.data.atrees:
            name    = atree.name.upper()
            prefix  = atree.atree_header.prefix.upper()

            filepath = pathlib.Path(assets_dir, name, f"{name}.{asset_type}")
            if filepath.is_file() and not overwrite:
                continue

            try:
                nodes        = atree_to_g3d_nodes(atree)
                model_caches = []

                for node in nodes:
                    obj_index   = object_indices_by_name.get(prefix + node.name)
                    model_cache = model_caches_by_index.get(obj_index)
                    if model_cache is None:
                        obj         = objects.get(obj_index)
                        model_cache = None if obj is None else object_to_model_cache(
                            obj, cache_type=asset_type, obj_index=obj_index,
                            bitmap_assets=bitmap_assets, is_arcade=is_arcade
                            )

                    model_caches.append(model_cache)

                all_job_args.append(dict(
                    texture_assets=texture_assets, asset_type=asset_type,
                    g3d_nodes=nodes, model_caches=model_caches, filepaths=[filepath],
                    name=name, swap_lightmap_and_diffuse=swap_lightmap_and_diffuse,
                    ))
            except:
                print(format_exc())

    print("Decompiling %s models in %s" % (
        len(all_job_args), "parallel" if parallel_processing else "series"
        ))
    util.process_jobs(
        decompile_model, all_job_args,
        process_count=None if parallel_processing else 1
        )


def object_to_model_cache(obj, cache_type=None, obj_index=0, is_arcade=False,
                          bitmap_assets=()):
    if not bitmap_assets:
        bitmap_assets = {}

    is_vif = hasattr(obj, "sub_object_0")
    is_arc = hasattr(getattr(obj, "data", None), "fifo_data") or is_arcade
    is_dc  = hasattr(obj, "lods") and not is_arc

    texture_names   = []
    geoms           = []
    def_name        = dict(name=c.MISSING_ASSET_NAME)

    if is_vif:
        default_lod_k   = getattr(obj.sub_object_0, "lod_k", c.DEFAULT_MOD_LOD_K)
        subobjs         = getattr(obj.data, "sub_objects", ())
        has_lmap        = getattr(obj.flags, "lmap",      False)
        for model, head in zip(obj.data.sub_object_models,
                               (obj.sub_object_0, *subobjs)):
            geoms.append(dict(
                vif_rawdata = FixedBytearrayBuffer(model.data),
                lod_k       = getattr(head, 'lod_k', default_lod_k),
                tex_name    = bitmap_assets.get(
                    head.tex_index, def_name)['name'],
                lm_name     = bitmap_assets.get(
                    head.lm_index, def_name)['name'] if has_lmap else "",
                ))

        model_cache = (
            ModelCache.get_cache_class_from_cache_type(cache_type)
            if cache_type in c.MODEL_CACHE_EXTENSIONS else
            Ps2ModelCache
            )()
            
        model_cache.has_lmap    = bool(getattr(obj.flags, "lmap",      False))
        model_cache.has_normals = bool(getattr(obj.flags, "v_normals", True))
        model_cache.has_colors  = bool(getattr(obj.flags, "v_colors",  True))
        model_cache.vert_count  = obj.vert_count
        model_cache.tri_count   = obj.tri_count
        model_cache.geoms       = geoms
    elif is_arc or is_dc:
        obj_lod = obj.lods[0]
        model_cache = DreamcastModelCache() if is_dc else ArcadeModelCache()

        model_cache.has_lmap        = bool(obj_lod.flags.lmap)
        model_cache.has_normals     = bool(obj_lod.flags.v_normals)
        model_cache.is_fifo2        = bool(obj_lod.flags.fifo_cmds_2)
        model_cache.is_compressed   = bool(obj_lod.flags.compressed)

        if obj_lod.flags.fifo_cmds or model_cache.is_fifo2:
            #raise NotImplementedError("hecken")
            pass
        else:
            model_cache.vert_count  = obj_lod.data.vert_count
            model_cache.tri_count   = obj_lod.data.tri_count
            if model_cache.has_lmap:
                model_cache.verts_rawdata = obj.model_data.vert_data
                model_cache.tris_rawdata  = obj.model_data.tri_data
                for i in range(obj_index+1, 0, -1):
                    # NOTE: check gdl.compilation.g3d.texture.export_textures
                    #       to see why we increment and negate "i" here. 
                    if (-i) in bitmap_assets:
                        model_cache.lightmap_name = bitmap_assets[-i]['name']
                        break
            else:
                model_cache.verts_rawdata = obj.model_data.vert_data
                model_cache.tris_rawdata  = obj.model_data.tri_data
                model_cache.norms_rawdata = obj.model_data.norm_data

            tex_index_map = {}
            for i in sorted(model_cache.get_texture_indices()):
                tex_index_map[i] = len(texture_names)
                texture_names.append(bitmap_assets.get(i, def_name)['name'])

            model_cache.replace_texture_indices(tex_index_map)
    else:
        raise TypeError("Unknown object platform.")

    model_cache.bounding_radius = obj.bnd_rad
    model_cache.texture_names   = texture_names
    model_cache.is_extracted    = True

    return model_cache


def atree_to_g3d_nodes(atree):
    g3d_nodes   = []
    for anode_info in atree.atree_header.atree_data.anode_infos:
        g3d_nodes.append(G3DAnimationNode())
        g3d_nodes[-1].name      = anode_info.mb_desc.upper()
        g3d_nodes[-1].parent    = anode_info.parent_index
        g3d_nodes[-1].init_pos  = anode_info.init_pos
        g3d_nodes[-1].type_name = anode_info.anim_type.enum_name

    return g3d_nodes
