import os

from traceback import format_exc
from ...supyr_struct_ext import FixedBytearrayBuffer
from ..metadata import objects as objects_metadata
from .serialization.model import G3DModel
from .serialization.asset_cache import get_asset_checksum, verify_source_file_asset_checksum
from .serialization.model_cache import get_model_cache_class,\
     get_model_cache_class_from_cache_type,\
     Ps2ModelCache, DreamcastModelCache, ArcadeModelCache
from . import constants as c
from . import util


def _compile_model(kwargs):
    name             = kwargs.pop("name")
    optimize         = kwargs.pop("optimize_strips")
    cache_type       = kwargs.pop("cache_type")
    cache_filepath   = kwargs.pop("cache_filepath")
    asset_filepath   = kwargs.pop("asset_filepath")

    print("Compiling model: %s" % name)
    g3d_model = G3DModel(
        optimize_for_ps2=(cache_type == c.MODEL_CACHE_EXTENSION_PS2 and optimize),
        optimize_for_ngc=(cache_type == c.MODEL_CACHE_EXTENSION_NGC and optimize),
        optimize_for_xbox=(cache_type == c.MODEL_CACHE_EXTENSION_XBOX and optimize),
        )
    asset_type = os.path.splitext(asset_filepath)[-1].strip(".")

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


def _decompile_model(kwargs):
    name           = kwargs["name"]
    texture_assets = kwargs["texture_assets"]
    model_cache    = kwargs["model_cache"]
    asset_type     = kwargs["asset_type"]
    filepath       = kwargs["filepath"]

    print("Decompiling model: %s" % name)
    if asset_type == "obj":
        g3d_model = G3DModel()
        g3d_model.import_g3d(model_cache)
        g3d_model.export_obj(
            filepath, texture_assets,
            swap_lightmap_and_diffuse=kwargs["swap_lightmap_and_diffuse"]
            )
    elif asset_type in c.MODEL_CACHE_EXTENSIONS:
        model_cache.serialize_to_file(filepath)
    else:
        raise NotImplementedError(f"Unknown asset type '{asset_type}'")


def compile_models(
        data_dir, force_recompile=False,  parallel_processing=False,
        target_ps2=False, target_ngc=False, target_xbox=False,
        target_dreamcast=False, target_arcade=False, optimize_strips=True
        ):
    asset_folder    = os.path.join(data_dir, c.EXPORT_FOLDERNAME, c.MOD_FOLDERNAME)
    cache_path_base = os.path.join(data_dir, c.IMPORT_FOLDERNAME, c.MOD_FOLDERNAME)

    all_job_args = []
    all_assets = util.locate_models(os.path.join(asset_folder))

    cache_type = (
        c.MODEL_CACHE_EXTENSION_ARC  if target_arcade else
        c.MODEL_CACHE_EXTENSION_DC   if target_dreamcast else
        c.MODEL_CACHE_EXTENSION_XBOX if target_xbox else
        c.MODEL_CACHE_EXTENSION_NGC  if target_ngc else
        c.MODEL_CACHE_EXTENSION_PS2  if target_ps2 else
        None
        )
    if cache_type is None:
        raise ValueError("No target platform specified")

    # loop over all objs, load them, convert them, and write the g3d
    for name in sorted(all_assets):
        try:
            asset_filepath = all_assets[name]

            rel_filepath = os.path.relpath(asset_filepath, asset_folder)
            filename, _ = os.path.splitext(rel_filepath)
            cache_filepath = os.path.join(cache_path_base, "%s.%s" % (filename, cache_type))

            if not force_recompile and os.path.isfile(cache_filepath):
                if verify_source_file_asset_checksum(asset_filepath, cache_filepath):
                    # original asset file; don't recompile
                    continue

            all_job_args.append(dict(
                name=name, asset_filepath=asset_filepath, cache_filepath=cache_filepath,
                cache_type=cache_type, optimize_strips=optimize_strips,
                ))
        except Exception:
            print(format_exc())
            print("Error: Could not compile model: '%s'" % asset_filepath)

    print("Compiling %s models in %s" % (
        len(all_job_args), "parallel" if parallel_processing else "series"
        ))
    util.process_jobs(
        _compile_model, all_job_args,
        process_count=None if parallel_processing else 1
        )


def import_models(
        objects_tag, data_dir, target_ps2=False, target_ngc=False,
        target_xbox=False, target_dreamcast=False, target_arcade=False,
        ):
    _, inv_bitmap_names = objects_tag.get_cache_names(by_name=True, recache=True)

    # we uppercase everything for uniformity. do it here
    inv_bitmap_names = {n.upper(): i for n, i in inv_bitmap_names.items()}

    model_caches_by_name = {}
    all_asset_filepaths = util.locate_models(
        os.path.join(data_dir, c.IMPORT_FOLDERNAME, c.MOD_FOLDERNAME),
        cache_files=True, target_ps2=target_ps2,
        target_ngc=target_ngc, target_xbox=target_xbox,
        target_dreamcast=target_dreamcast, target_arcade=target_arcade
        )

    for name in sorted(all_asset_filepaths):
        try:
            with open(all_asset_filepaths[name], "rb") as f:
                model_cache = get_model_cache_class(f)()
                model_cache.parse(f)
                model_caches_by_name[name] = model_cache
        except Exception:
            print(format_exc())
            print("Could not load model:\n    %s" % all_asset_filepaths[name])

    objects     = objects_tag.data.objects
    object_defs = objects_tag.data.object_defs
    del objects[:]
    del object_defs[:]

    # get the metadata for all models to import
    metadata = objects_metadata.compile_objects_metadata(data_dir).get("objects", ())
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


def decompile_models(
        objects_tag, data_dir,
        asset_types=c.MODEL_CACHE_EXTENSIONS,
        parallel_processing=False, overwrite=False,
        swap_lightmap_and_diffuse=False
        ):
    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    for asset_type in asset_types:
        if asset_type not in (*c.MODEL_CACHE_EXTENSIONS, *c.MODEL_ASSET_EXTENSIONS):
            raise ValueError("Unknown model type '%s'" % asset_type)

    assets_dir     = os.path.join(data_dir, c.EXPORT_FOLDERNAME, c.MOD_FOLDERNAME)
    cache_dir      = os.path.join(data_dir, c.IMPORT_FOLDERNAME, c.MOD_FOLDERNAME)
    tex_assets_dir = os.path.join(data_dir, c.EXPORT_FOLDERNAME, c.TEX_FOLDERNAME)

    texture_assets = util.locate_textures(tex_assets_dir)

    objects = objects_tag.data.objects
    object_assets, bitmap_assets = objects_tag.get_cache_names()

    all_job_args = []

    # loop over each object
    for i in range(len(object_assets)):
        asset = object_assets[i]
        obj   = objects[i]

        try:
            j = None  # initialize in case exception occurs before loop starts
            for asset_type in asset_types:
                filename = f"{asset['name']}.{asset_type}"
                if asset['name'] != asset["asset_name"]:
                    filename = os.path.join(asset["asset_name"], filename)

                filepath = os.path.join(
                    cache_dir if asset_type in c.MODEL_CACHE_EXTENSIONS else assets_dir,
                    filename
                    )
                if os.path.isfile(filepath) and not overwrite:
                    continue

                model_cache = object_to_model_cache(
                    obj, cache_type=asset_type, bitmap_assets=bitmap_assets
                    )

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
                    texture_assets=texture_assets, model_cache=model_cache,
                    name=asset['name'], asset_type=asset_type, filepath=filepath,
                    swap_lightmap_and_diffuse=swap_lightmap_and_diffuse,
                    ))

        except:
            print(format_exc())
            print(f"The above error occurred while trying to export subobj {j} "
                  f"of object {i} as {asset_type}. name: '{asset.get('name')}', "
                  f"asset_name: '{asset.get('asset_name')}'"
                  )

    print("Decompiling %s models in %s" % (
        len(all_job_args), "parallel" if parallel_processing else "series"
        ))
    util.process_jobs(
        _decompile_model, all_job_args,
        process_count=None if parallel_processing else 1
        )


def object_to_model_cache(obj, cache_type=None, bitmap_assets=()):
    if not bitmap_assets:
        bitmap_assets = {}

    is_vif = hasattr(obj, "sub_object_0")
    is_arc = hasattr(getattr(obj, "data", None), "fifo_data")
    is_dc  = hasattr(obj, "lods") and not is_arc

    texture_names = []
    geoms         = []

    if is_vif:
        default_lod_k  = getattr(obj.sub_object_0, "lod_k", c.DEFAULT_MOD_LOD_K)
        subobjs        = getattr(obj.data, "sub_objects", ())
        has_lmap       = getattr(obj.flags, "lmap",      False)
        def_name       = dict(name=c.MISSING_ASSET_NAME)
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
            get_model_cache_class_from_cache_type(cache_type)
            if cache_type in c.MODEL_CACHE_EXTENSIONS else
            Ps2ModelCache
            )()
            
        model_cache.has_lmap    = bool(getattr(obj.flags, "lmap",      False))
        model_cache.has_normals = bool(getattr(obj.flags, "v_normals", True))
        model_cache.has_colors  = bool(getattr(obj.flags, "v_colors",  True))
        model_cache.geoms       = geoms
    elif is_arc or is_dc:
        obj_lod = obj.lods[0]
        model_cache = DreamcastModelCache() if is_dc else ArcadeModelCache()

        model_cache.has_lmap    = bool(obj_lod.flags.lmap)
        model_cache.has_normals = bool(obj_lod.flags.v_normals)
        model_cache.is_fifo2    = bool(obj_lod.flags.fifo_cmds_2)

        if obj_lod.flags.fifo_cmds or model_cache.is_fifo2:
            raise NotImplementedError("hecken")
            model_cache.fifo_rawdata = obj.data.fifo_rawdata
        else:
            raise NotImplementedError("hecken")
            if model_cache.has_lmap:
                model_cache.verts_rawdata = obj.data.vert_data
                model_cache.tris_rawdata  = obj.data.tri_data
            else:
                model_cache.verts_rawdata = obj.data.vert_data
                model_cache.tris_rawdata  = obj.data.tri_data
                model_cache.norms_rawdata = obj.data.norm_data
    else:
        raise TypeError("Unknown object platform.")

    model_cache.bounding_radius = obj.bnd_rad
    model_cache.vert_count      = obj.vert_count
    model_cache.tri_count       = obj.tri_count
    model_cache.texture_names   = texture_names
    model_cache.is_extracted    = True

    return model_cache
