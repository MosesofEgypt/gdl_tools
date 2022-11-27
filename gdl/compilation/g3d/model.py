import hashlib
import os

from traceback import format_exc
from ..metadata import objects as objects_metadata
from .serialization.model import G3DModel,\
     OBJECT_HEADER_STRUCT, SUBOBJ_HEADER_STRUCT
from . import constants as c
from . import util


def _compile_model(kwargs):
    name           = kwargs.pop("name")
    source_md5     = kwargs.pop("source_md5")
    target_ps2     = kwargs.pop("target_ps2")
    target_ngc     = kwargs.pop("target_ngc")
    target_xbox    = kwargs.pop("target_xbox")
    cache_filepath = kwargs.pop("cache_filepath")
    asset_filepath = kwargs.pop("asset_filepath")

    print("Compiling model: %s" % name)
    g3d_model = G3DModel(target_ps2=target_ps2, target_ngc=target_ngc, target_xbox=target_xbox)
    with open(asset_filepath, "r") as f:
        g3d_model.import_obj(f, source_md5)

    g3d_model.make_strips()

    os.makedirs(os.path.dirname(cache_filepath), exist_ok=True)
    with open(cache_filepath, "wb") as f:
        g3d_model.export_g3d(f)


def _decompile_model(kwargs):
    name           = kwargs["name"]
    texture_assets = kwargs["texture_assets"]
    subobj_headers = kwargs["subobj_headers"]
    subobj_models  = kwargs["subobj_models"]
    asset_type     = kwargs["asset_type"]
    filepath       = kwargs["filepath"]

    print("Decompiling model: %s" % name)
    if asset_type == "obj":
        g3d_model = G3DModel()
        # now that all the models are imported, export the obj
        for j in range(len(subobj_models)):
            g3d_model.import_g3d(
                subobj_models[j]["data"], headerless=True, **subobj_headers[j]
                )
        g3d_model.export_obj(
            filepath, texture_assets,
            swap_lightmap_and_diffuse=kwargs["swap_lightmap_and_diffuse"]
            )
        return
    elif asset_type not in c.MODEL_CACHE_EXTENSIONS:
        return

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'wb+') as out_file:
        # write the g3d header
        out_file.write(OBJECT_HEADER_STRUCT.pack(
            kwargs["bnd_rad"], kwargs["vert_count"], kwargs["tri_count"], len(subobj_models),
            c.G3D_FLAG_MESH    * bool(subobj_models) |
            c.G3D_FLAG_NORMALS * kwargs["has_normals"] |
            c.G3D_FLAG_COLORS  * kwargs["has_colors"] |
            c.G3D_FLAG_LMAP    * kwargs["has_lmap"],
            b'\x00'  # null hash
            ))

        # loop over each subobject and write them
        for j in range(len(subobj_models)):
            out_file.write(SUBOBJ_HEADER_STRUCT.pack(
                subobj_models[j]["qword_count"],
                subobj_headers[j]["lod_k"],
                subobj_headers[j]["tex_name"].encode(),
                subobj_headers[j]["lm_name"].encode()
                ))

            # write the padding for the objects-style header,
            # the model data, and pad the alignment to 16 bytes
            out_file.write(b'\x00' * 8)
            out_file.write(subobj_models[j]["data"])
            out_file.write(b'\x00'*util.calculate_padding(
                out_file.tell(), 16
                ))


def compile_models(
        data_dir, force_recompile=False,  parallel_processing=False,
        target_ps2=False, target_ngc=False, target_xbox=False
        ):
    asset_folder    = os.path.join(data_dir, c.EXPORT_FOLDERNAME, c.MOD_FOLDERNAME)
    cache_path_base = os.path.join(data_dir, c.IMPORT_FOLDERNAME, c.MOD_FOLDERNAME)

    all_job_args = []
    all_assets = util.locate_models(os.path.join(asset_folder))

    asset_type = (
        c.MODEL_CACHE_EXTENSION_PS2  if target_ps2 else
        c.MODEL_CACHE_EXTENSION_NGC  if target_ngc else
        c.MODEL_CACHE_EXTENSION_XBOX
        )

    # loop over all objs, load them, convert them, and write the g3d
    for name in sorted(all_assets):
        try:
            asset_filepath = all_assets[name]
            rel_filepath = os.path.relpath(asset_filepath, asset_folder)
            cache_filepath = os.path.join(cache_path_base, "%s.%s" % (
                os.path.splitext(rel_filepath)[0], asset_type
                ))

            source_md5 = b'\x00'*16
            g3d_cached_md5 = b''
            with open(asset_filepath, "rb") as f:
                source_md5 = hashlib.md5(f.read()).digest()

            if os.path.isfile(cache_filepath):
                with open(cache_filepath, "rb") as f:
                    data = f.read(OBJECT_HEADER_STRUCT.size)

                if len(data) >= OBJECT_HEADER_STRUCT.size:
                    g3d_cached_md5 = OBJECT_HEADER_STRUCT.unpack(data)[5]

            if g3d_cached_md5 == source_md5 and not force_recompile:
                # original asset file; don't recompile
                continue

            all_job_args.append(dict(
                asset_filepath=asset_filepath, name=name,
                target_ps2=target_ps2, target_ngc=target_ngc, target_xbox=target_xbox,
                cache_filepath=cache_filepath, source_md5=source_md5
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


def import_models(objects_tag, data_dir, target_ps2=False, target_ngc=False, target_xbox=False):
    _, inv_bitmap_names = objects_tag.get_cache_names(by_name=True)
    # we uppercase everything for uniformity. do it here
    inv_bitmap_names = {n.upper(): inv_bitmap_names[n] for n in inv_bitmap_names}

    g3d_models_by_name = {}
    all_asset_filepaths = util.locate_models(
        os.path.join(data_dir, c.IMPORT_FOLDERNAME, c.MOD_FOLDERNAME),
        cache_files=True, target_ngc=target_ngc, target_xbox=target_xbox
        )
    for name in sorted(all_asset_filepaths):
        try:
            with open(all_asset_filepaths[name], "rb") as f:
                g3d_header = OBJECT_HEADER_STRUCT.unpack(
                    f.read(OBJECT_HEADER_STRUCT.size)
                    )
                bnd_rad, vert_ct, tri_ct, subobj_ct, g3d_flags, _ = g3d_header

                model_data = dict(
                    bnd_rad=bnd_rad, vert_count=vert_ct, tri_count=tri_ct,
                    flags=(g3d_flags & c.G3D_FLAG_ALL),
                    headers=[],
                    datas=[]
                    )

                for j in range(subobj_ct):
                    qwc, lod_k, tex_name, lm_name = SUBOBJ_HEADER_STRUCT.unpack(
                        f.read(SUBOBJ_HEADER_STRUCT.size)
                        )
                    model_data["headers"].append(dict(
                        qword_count=qwc, lod_k=lod_k,
                        tex_name=tex_name.split(b"\x00")[0].decode().upper(),
                        lm_name=lm_name.split(b"\x00")[0].decode().upper(),
                        ))
                    # skip the padding header bytes
                    f.read(8)
                    # quadwords stored is always 1 + qwc. Since we've
                    # skipped the first 8 bytes, we have an extra half
                    # a quadword to read. add 8 for this
                    model_data["datas"].append(f.read(qwc * 16 + 8))

                g3d_models_by_name[name.upper()] = model_data
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
        meta = objects_metadata_by_name[name]
        if name not in g3d_models_by_name:
            print("Warning: Could not locate model file for '%s'" % name)

        g3d_model_data  = g3d_models_by_name.get(name, {})
        g3d_headers     = g3d_model_data.get("headers", ())
        g3d_datas       = g3d_model_data.get("datas", ())

        objects.append()
        object_defs.append()
        obj     = objects[-1]
        obj_def = object_defs[-1]

        # update the bounding radius, vert/tri counts, and the flags
        obj.bnd_rad    = g3d_model_data.get("bnd_rad",    0)
        obj.flags.data = g3d_model_data.get("flags",      0)
        obj.tri_count  = g3d_model_data.get("tri_count",  0)
        obj.vert_count = g3d_model_data.get("vert_count", 0)
        obj.id_num     = g3d_model_data.get("id_num",     len(objects))

        # populate the object def
        obj_def.bnd_rad   = obj.bnd_rad
        obj_def.name      = meta.get("asset_name", name)[-16:]
        obj_def.obj_index = len(objects) - 1
        obj_def.frames    = 0 # only non-zero in DEMO objects

        # copy flags from metadata
        for flag_name in meta.get("flags", {}):
            if hasattr(obj.flags, flag_name):
                setattr(obj.flags, flag_name, meta["flags"][flag_name])

        #loop over all the subobjects and update the headers and models
        for i in range(len(g3d_headers)):
            obj.data.sub_object_models.append()
            subobj_model = obj.data.sub_object_models[-1]

            if i == 0:
                subobj_header = obj.sub_object_0
            else:
                obj.data.sub_objects.append()
                subobj_header = obj.data.sub_objects[-1]

            qword_count = g3d_headers[i]["qword_count"]
            lod_k       = g3d_headers[i]["lod_k"]
            tex_name    = g3d_headers[i]["tex_name"]
            lm_name     = g3d_headers[i]["lm_name"]

            tex_meta = inv_bitmap_names.get(tex_name, {})
            lm_meta  = inv_bitmap_names.get(lm_name, {})

            if not tex_meta:
                print('Warning: Texture "%s" used in subobject %s of %s does not exist.' %
                      (tex_name, i, name))

            if obj.flags.lmap and not lm_meta:
                print('Warning: Lightmap "%s" used in subobject %s of %s does not exist.' %
                      (lm_name, i, name))

            #update the header and model data
            subobj_model.data         = g3d_datas[i]
            subobj_model.qword_count  = qword_count
            subobj_header.qword_count = qword_count + 1
            subobj_header.tex_index   = tex_meta.get("index", 0)
            subobj_header.lm_index    = lm_meta.get("index", 0)
            subobj_header.lod_k       = lod_k


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

        flags          = getattr(obj, "flags", None)
        has_lmap       = bool(getattr(flags, "lmap", False))
        has_normals    = bool(getattr(flags, "v_normals", True))
        has_colors     = bool(getattr(flags, "v_colors", True))
        default_lod_k  = getattr(obj.sub_object_0, "lod_k", c.DEFAULT_MOD_LOD_K)
        subobjs        = getattr(obj.data, "sub_objects", ())
        subobj_models  = [
            dict(data = model.data, qword_count = model.qword_count)
            for model in obj.data.sub_object_models
            ]
        subobj_headers = [
            dict(
                tex_name = bitmap_assets.get(header.tex_index, def_name)['name'],
                lm_name  = bitmap_assets.get(header.lm_index, def_name)['name'] if has_lmap else "",
                lod_k    = getattr(header, 'lod_k', default_lod_k),
                )
            for header in (obj.sub_object_0, *subobjs)
            ]

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

                all_job_args.append(dict(
                    texture_assets=texture_assets,
                    subobj_headers=subobj_headers, subobj_models=subobj_models,
                    name=asset['name'], asset_type=asset_type, filepath=filepath,
                    has_lmap=has_lmap, has_normals=has_normals, has_colors=has_colors,
                    bnd_rad=obj.bnd_rad, vert_count=obj.vert_count, tri_count=obj.tri_count,
                    swap_lightmap_and_diffuse=swap_lightmap_and_diffuse
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
