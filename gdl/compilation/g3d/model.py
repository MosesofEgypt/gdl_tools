import os

from traceback import format_exc
from ..metadata import objects as objects_metadata
from .serialization.model import G3DModel
from .serialization.cache import verify_source_file_asset_checksum
from .serialization import model_cache
from . import constants as c
from . import util


def _compile_model(kwargs):
    name             = kwargs.pop("name")
    source_md5       = kwargs.pop("source_md5")
    optimize         = kwargs.pop("optimize_strips")
    cache_type       = kwargs.pop("cache_type")
    asset_type       = kwargs.pop("asset_type")
    cache_filepath   = kwargs.pop("cache_filepath")
    asset_filepath   = kwargs.pop("asset_filepath")

    print("Compiling model: %s" % name)
    g3d_model = G3DModel(
        optimize_for_ps2=(cache_type == c.MODEL_CACHE_EXTENSION_PS2 and optimize),
        optimize_for_ngc=(cache_type == c.MODEL_CACHE_EXTENSION_NGC and optimize),
        optimize_for_xbox=(cache_type == c.MODEL_CACHE_EXTENSION_XBOX and optimize),
        )
    if asset_type == "obj":
        with open(asset_filepath, "r") as f:
            g3d_model.import_obj(f, source_md5)
    else:
        raise NotImplementedError(f"Unknown asset type '{asset_type}'")

    object_model = g3d_model.compile_g3d(cache_type)
    model_rawdata = model_cache.serialize_model_cache(object_model)

    os.makedirs(os.path.dirname(cache_filepath), exist_ok=True)
    with open(cache_filepath, "wb") as f:
        f.write(model_rawdata)


def _decompile_model(kwargs):
    name           = kwargs["name"]
    texture_assets = kwargs["texture_assets"]
    object_model   = kwargs["object_model"]
    asset_type     = kwargs["asset_type"]
    filepath       = kwargs["filepath"]

    print("Decompiling model: %s" % name)
    if asset_type == "obj":
        g3d_model = G3DModel()
        # import all the models are imported, export the obj
        g3d_model.import_g3d(object_model)
        g3d_model.export_obj(
            filepath, texture_assets,
            swap_lightmap_and_diffuse=kwargs["swap_lightmap_and_diffuse"]
            )
    elif asset_type in c.MODEL_CACHE_EXTENSIONS:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        model_rawdata = model_cache.serialize_model_cache(object_model)
        with open(filepath, 'wb+') as f:
            f.write(model_rawdata)
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
            asset_type = os.path.splitext(asset_filepath)[-1].strip(".").lower()

            rel_filepath = os.path.relpath(asset_filepath, asset_folder)
            cache_filepath = os.path.join(cache_path_base, "%s.%s" % (
                os.path.splitext(rel_filepath)[0], cache_type
                ))
            if not force_recompile and os.path.isfile(cache_filepath):
                if verify_source_file_asset_checksum(asset_filepath, cache_filepath):
                    # original asset file; don't recompile
                    continue

            all_job_args.append(dict(
                name=name, asset_filepath=asset_filepath, cache_filepath=cache_filepath,
                cache_type=cache_type, asset_type=asset_type, source_md5=source_md5,
                optimize_strips=optimize_strips,
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
    _, inv_bitmap_names = objects_tag.get_cache_names(by_name=True)
    # we uppercase everything for uniformity. do it here
    inv_bitmap_names = {n.upper(): inv_bitmap_names[n] for n in inv_bitmap_names}

    g3d_models_by_name = {}
    all_asset_filepaths = util.locate_models(
        os.path.join(data_dir, c.IMPORT_FOLDERNAME, c.MOD_FOLDERNAME),
        cache_files=True, target_ps2=target_ps2,
        target_ngc=target_ngc, target_xbox=target_xbox,
        target_dreamcast=target_dreamcast, target_arcade=target_arcade
        )

    for name in sorted(all_asset_filepaths):
        try:
            g3d_models_by_name[name.upper()] = model_cache.parse_model_cache(
                all_asset_filepaths[name]
                )
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
        meta   = objects_metadata_by_name[name]
        model  = g3d_models_by_name.get(name, {})
        if not model:
            print("Warning: Could not locate model file for '%s'" % name)

        cache_header    = model["cache_header"]
        model_header    = model["model_header"]
        object_models   = model["model_data"]
        model_flags     = model_header["flags"]
        cache_type      = cache_header["cache_type"]

        meta.setdefault("flags", {}).update(
            mesh       = model_flags & model_cache.MODEL_CACHE_FLAG_MESH,
            v_normals  = model_flags & model_cache.MODEL_CACHE_FLAG_NORMALS,
            v_colors   = model_flags & model_cache.MODEL_CACHE_FLAG_COLORS,
            lmap       = model_flags & model_cache.MODEL_CACHE_FLAG_LMAP
            )

        if cache_type in (c.MODEL_CACHE_EXTENSION_NGC,
                          c.MODEL_CACHE_EXTENSION_PS2,
                          c.MODEL_CACHE_EXTENSION_XBOX):
            objects.append()
            obj = objects[-1]
            obj_flags       = obj.flags
            # copy data over
            obj.bnd_rad     = model_header["bounding_radius"]
            obj.tri_count   = model_header["tri_count"]
            obj.vert_count  = model_header["vert_count"]
            obj.id_num      = len(objects)

            # loop over all the subobjects and update the headers and models
            for i, object_models in enumerate(object_models):
                obj.data.sub_object_models.append()
                subobj_model = obj.data.sub_object_models[-1]

                if i == 0:
                    subobj_header = obj.sub_object_0
                else:
                    obj.data.sub_objects.append()
                    subobj_header = obj.data.sub_objects[-1]

                tex_meta   = inv_bitmap_names.get(object_model["tex_name"], {})
                lm_meta    = inv_bitmap_names.get(object_model["lm_name"], {})
                if not tex_meta:
                    print("Warning: Texture '{tex_name}'  used in "
                          "subobject {i} of '{name}' does not exist.")

                if meta["flags"]["lmap"] and not lm_meta:
                    print("Warning: Lightmap '{lm_name}'  used in "
                          "subobject {i} of '{name}' does not exist.")

                # update the header and model data
                subobj_model.data         = object_model["vif_rawdata"]
                subobj_model.qword_count  = object_model["qword_count"]
                subobj_header.qword_count = object_model["qword_count"] + 1
                subobj_header.tex_index   = tex_meta.get("index", 0)
                subobj_header.lm_index    = lm_meta.get("index", 0)
                subobj_header.lod_k       = object_model["lod_k"]
        elif cache_type in (c.MODEL_CACHE_EXTENSION_DC, c.MODEL_CACHE_EXTENSION_ARC):
            raise NotImplementedError("hecken")

            is_fifo      = bool(object_models["fifo_rawdata"])
            is_uncomp_lm = meta["flags"]["lmap"] and not is_fifo

            objects.append(
                case=("fifo" if is_fifo else "uncomp_lm" if is_uncomp_lm else "uncomp")
                )

            obj = objects[-1]
            obj_flags           = obj.lods[0].flags
            # copy data over
            obj.bnd_rad         = model_header["bounding_radius"]
            for lod in obj.lods:
                lod.tri_count   = model_header["tri_count"]
                lod.vert_count  = model_header["vert_count"]
                lod.id_num      = len(objects)
                # NOTE: we're doing a bit of a hack to use the
                #       same flags object for each lod so we dont
                #       have to set the bits on each object
                lod.flags       = obj_flags
        else:
            raise ValueError(f"Unknown model type '{cache_type}'")

        # populate the object def
        object_defs.append()
        obj_def           = object_defs[-1]
        obj_def.bnd_rad   = model_header["bounding_radius"]
        obj_def.name      = meta.get("asset_name", name)[-16:]
        obj_def.obj_index = len(objects) - 1
        obj_def.frames    = 0 # only non-zero in DEMO objects

        # copy flags from metadata
        for name, val in meta["flags"].items():
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

    def_name = dict(name=c.MISSING_ASSET_NAME)

    all_job_args = []

    # loop over each object
    for i in range(len(object_assets)):
        asset = object_assets[i]
        obj   = objects[i]

        is_ps2_xbox_ngc = hasattr(obj, "sub_object_0")
        is_arc_or_dc    = hasattr(obj, "lods")

        texture_names = []
        if is_ps2_xbox_ngc:
            flags = dict(
                has_lmap    = bool(getattr(obj.flags, "lmap",      False)),
                has_normals = bool(getattr(obj.flags, "v_normals", True)),
                has_colors  = bool(getattr(obj.flags, "v_colors",  True)),
                )
            default_lod_k  = getattr(obj.sub_object_0, "lod_k", c.DEFAULT_MOD_LOD_K)
            subobjs        = getattr(obj.data, "sub_objects", ())
            model_data = []
            for model, head in zip(obj.data.sub_object_models, (obj.sub_object_0, *subobjs)):
                model_data.append(dict(
                    vif_rawdata = model.data,
                    lod_k       = getattr(header, 'lod_k', default_lod_k),
                    tex_name    = bitmap_assets.get(head.tex_index, def_name)['name'],
                    lm_name     = bitmap_assets.get(head.lm_index, def_name)['name'] if flags["has_lmap"] else "",
                    ))

        elif is_arc_or_dc:
            lod = obj.lods[0]
            flags = dict(
                has_lmap    = bool(lod.flags.lmap),
                has_normals = bool(lod.flags.v_normals),
                is_fifo2    = bool(lod.flags.fifo_cmds_2),
                )

            model_data = dict()
            if lod.flags.fifo_cmds or flags["is_fifo2"]:
                raise NotImplementedError("hecken")
                model_data.update(
                    fifo_rawdata = obj.data.fifo_rawdata,
                    )
            else:
                raise NotImplementedError("hecken")

                if flags["has_lmap"]:
                    raise NotImplementedError("hecken")
                    model_data.update(
                        verts_rawdata = obj.data.vert_data,
                        tris_rawdata  = obj.data.tri_data,
                        )
                else:
                    model_data.update(
                        verts_rawdata = obj.data.vert_data,
                        tris_rawdata  = obj.data.tri_data,
                        norms_rawdata = obj.data.norm_data
                        )
        else:
            raise TypeError("Unknown object platform.")

        model_flags = (
            (model_cache.MODEL_CACHE_FLAG_MESH    * bool(obj.vert_count)) |
            (model_cache.MODEL_CACHE_FLAG_NORMALS * flags.get("has_normals", 0)) |
            (model_cache.MODEL_CACHE_FLAG_COLORS  * flags.get("has_colors",  0)) |
            (model_cache.MODEL_CACHE_FLAG_LMAP    * flags.get("has_lmap",    0)) |
            (model_cache.MODEL_CACHE_FLAG_FIFO2   * flags.get("is_fifo2",    0))
            )
        model_header = dict(
            flags           = model_flags,
            bounding_radius = obj.bnd_rad,
            vert_count      = obj.vert_count,
            tri_count       = obj.tri_count
            )

        try:
            j = None  # initialize in case exception occurs before loop starts
            for asset_type in asset_types:
                filename = "%s.%s" % (asset['name'], asset_type)
                if asset['name'] != asset["asset_name"]:
                    filename = os.path.join(asset["asset_name"], filename)

                filepath = os.path.join(
                    cache_dir if asset_type in c.MODEL_CACHE_EXTENSIONS else assets_dir,
                    filename
                    )
                if os.path.isfile(filepath) and not overwrite:
                    continue

                object_model = dict(
                    cache_header  = dict(asset_type = asset_type),
                    model_header  = model_header,
                    texture_names = texture_names,
                    model_data    = model_data
                    )

                all_job_args.append(dict(
                    texture_assets=texture_assets, object_model=object_model,
                    name=asset['name'], asset_type=asset_type, filepath=filepath,
                    swap_lightmap_and_diffuse=swap_lightmap_and_diffuse,
                    ))

        except:
            print(format_exc())
            print(('The above error occurred while trying to export subobj %s of object %s as %s. '
                   "name: '%s', asset_name: '%s'") %
                  (j, i, asset_type, asset.get("name"), asset.get("asset_name"))
                  )

    print("Decompiling %s models in %s" % (
        len(all_job_args), "parallel" if parallel_processing else "series"
        ))
    util.process_jobs(
        _decompile_model, all_job_args,
        process_count=None if parallel_processing else 1
        )
