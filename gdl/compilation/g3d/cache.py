import os

from math import log
from supyr_struct.util import backup_and_rename_temp
from traceback import format_exc
from ...defs.anim import anim_def
from ...defs.objects import objects_def
from ...defs.texdef import texdef_def
from ...defs.worlds import worlds_def
from ..metadata import objects as objects_metadata
from . import animation, model, texture
from .serialization.asset_cache import verify_source_file_asset_checksum
from . import constants as c
from . import util


COMPILE_JOB_TYPE_ANIMATIONS = 'animation'
COMPILE_JOB_TYPE_TEXTURES   = 'texture'
COMPILE_JOB_TYPE_MODELS     = 'model'


def _compile_assets(
        compile_job_type, data_dir,
        force_recompile=False, parallel_processing=False,
        target_ps2=False, target_ngc=False, target_xbox=False,
        target_dreamcast=False, target_arcade=False, **kwargs
        ):
    if compile_job_type == COMPILE_JOB_TYPE_TEXTURES:
        folder          = c.TEX_FOLDERNAME
        metadata_key    = "bitmaps"
        compile_func    = texture.compile_texture
        cache_type      = (
            c.TEXTURE_CACHE_EXTENSION_PS2  if target_ps2 else
            c.TEXTURE_CACHE_EXTENSION_NGC  if target_ngc else
            c.TEXTURE_CACHE_EXTENSION_DC   if target_dreamcast else
            c.TEXTURE_CACHE_EXTENSION_ARC  if target_arcade else
            c.TEXTURE_CACHE_EXTENSION_XBOX if target_xbox else
            None
            )
    elif compile_job_type == COMPILE_JOB_TYPE_MODELS:
        folder          = c.MOD_FOLDERNAME
        metadata_key    = "objects"
        compile_func    = model.compile_model
        cache_type      = (
            c.MODEL_CACHE_EXTENSION_ARC  if target_arcade else
            c.MODEL_CACHE_EXTENSION_DC   if target_dreamcast else
            c.MODEL_CACHE_EXTENSION_XBOX if target_xbox else
            c.MODEL_CACHE_EXTENSION_NGC  if target_ngc else
            c.MODEL_CACHE_EXTENSION_PS2  if target_ps2 else
            None
            )
    elif compile_job_type == COMPILE_JOB_TYPE_ANIMATIONS:
        folder          = c.ANIM_FOLDERNAME
        metadata_key    = "animations"
        compile_func    = animation.compile_animation
        cache_type      = (
            c.ANIMATION_CACHE_EXTENSION_ARC  if target_arcade else
            c.ANIMATION_CACHE_EXTENSION_DC   if target_dreamcast else
            c.ANIMATION_CACHE_EXTENSION_XBOX if target_xbox else
            c.ANIMATION_CACHE_EXTENSION_NGC  if target_ngc else
            c.ANIMATION_CACHE_EXTENSION_PS2  if target_ps2 else
            None
            )
    else:
        raise ValueError(f"Unknown job compile type '{compile_job_type}'")

    if cache_type is None:
        raise ValueError("No target platform specified")

    asset_folder    = os.path.join(data_dir, c.EXPORT_FOLDERNAME, folder)
    cache_path_base = os.path.join(data_dir, c.IMPORT_FOLDERNAME, folder)

    # get the metadata for all assets to import and
    # key it by name to allow matching to asset files
    all_metadata = {
        m.get("name"): m
        for m in objects_metadata.compile_objects_metadata(data_dir).get(metadata_key, ())
        if isinstance(m, dict) and m.get("name")
        }

    if compile_job_type == COMPILE_JOB_TYPE_TEXTURES:
        all_assets = util.locate_textures(asset_folder, cache_files=False)
    elif compile_job_type == COMPILE_JOB_TYPE_MODELS:
        all_assets = util.locate_models(asset_folder, cache_files=False)
    elif compile_job_type == COMPILE_JOB_TYPE_ANIMATIONS:
        all_assets = util.locate_animations(asset_folder, cache_files=False)

    all_job_args = []
    for name in sorted(all_assets):
        meta = all_metadata.get(name)
        if not meta:
            # not listed in metadata. don't compile it
            continue

        try:
            asset_filepath = all_assets[name]
            rel_filepath = os.path.relpath(asset_filepath, asset_folder)
            filename, _ = os.path.splitext(rel_filepath)
            cache_filepath = os.path.join(cache_path_base, f"{filename}.{cache_type}")

            if not force_recompile and os.path.isfile(cache_filepath):
                if verify_source_file_asset_checksum(asset_filepath, cache_filepath):
                    # original asset file; don't recompile
                    continue

            all_job_args.append(dict(
                asset_filepath=asset_filepath, cache_filepath=cache_filepath,
                name=name, cache_type=cache_type, metadata=meta, **kwargs
                ))
        except Exception:
            print(format_exc())
            print(f"Error: Could not create {compile_job_type} compilation job: '{asset_filepath}'")

    print(f"Compiling %s {metadata_key} in %s" % (
        len(all_job_args), "parallel" if parallel_processing else "series"
        ))
    util.process_jobs(
        compile_func, all_job_args, process_count=None if parallel_processing else 1
        )


def compile_textures(*args, **kwargs):
    return _compile_assets(COMPILE_JOB_TYPE_TEXTURES, *args, **kwargs)


def compile_models(*args, **kwargs):
    return _compile_assets(COMPILE_JOB_TYPE_MODELS, *args, **kwargs)


def compile_cache_files(
        objects_dir,
        target_ngc=False, target_ps2=False, target_xbox=False,
        target_dreamcast=False, target_arcade=False,
        serialize_cache_files=False, build_texdef_cache=False,
        build_objects_cache=True, build_anim_cache=True
        ):
    ext = (
        c.NGC_EXTENSION if target_ngc else
        c.ARC_EXTENSION if target_arcade else
        c.DC_EXTENSION  if target_dreamcast else
        c.PS2_EXTENSION if target_ps2 or target_xbox else
        ""
        )
    anim_worlds_ext = c.PS2_EXTENSION if target_ngc else ext
    if not ext:
        raise ValueError("No build target specified")

    build_texdef_cache &= build_objects_cache

    # TODO: add support for compiling worlds
    data_dir    = os.path.join(objects_dir, c.DATA_FOLDERNAME)
    objects_tag = objects_def.build() if build_objects_cache else None
    anim_tag    = anim_def.build()    if build_anim_cache else None
    texdef_tag  = None

    if objects_tag and (target_dreamcast or target_arcade):
        # dreamcast and arcade use v1 or v0 of the objects.
        # set header to v1 and reparse header and all arrays
        # so they're the correct structure versions
        objects_tag.data.version_header.version.set_to("v1")
        objects_tag.data.parse(attr_index="header")
        objects_tag.data.parse(attr_index="objects")
        objects_tag.data.parse(attr_index="bitmaps")

    anim_tag.filepath = os.path.join(
        objects_dir, "%s.%s" % (c.ANIM_FILENAME, anim_worlds_ext)
        )
    if objects_tag:
        objects_tag.filepath = os.path.join(
            objects_dir, "%s.%s" % (c.OBJECTS_FILENAME, ext)
            )
        objects_tag.data.version_header.dir_name = (
            os.path.join(objects_dir, "").replace("\\", "/")[-32:]
            )

        print("Importing textures...")
        texture_datas = texture.import_textures(
            objects_tag, data_dir, target_ngc=target_ngc,
            target_ps2=target_ps2, target_xbox=target_xbox,
            target_dreamcast=target_dreamcast, target_arcade=target_arcade
            )
        print("Importing models...")
        model.import_models(
            objects_tag, data_dir, target_ngc=target_ngc,
            target_ps2=target_ps2, target_xbox=target_xbox,
            target_dreamcast=target_dreamcast, target_arcade=target_arcade
        )

    if anim_tag:
        print("Importing animations...")
        animation.import_animations(anim_tag, objects_tag, data_dir)

    if build_texdef_cache:
        texdef_tag = compile_texdef_cache_from_objects(objects_tag)

    if serialize_cache_files:
        print("Serializing...")
        if objects_tag:
            objects_tag.serialize(temp=False)

        if anim_tag:
            anim_tag.serialize(temp=False)

        if texdef_tag:
            texdef_tag.serialize(temp=False)

        if texture_datas:
            serialize_textures_cache(
                objects_tag, texture_datas, target_ngc=target_ngc,
                target_ps2=target_ps2, target_xbox=target_xbox,
                target_dreamcast=target_dreamcast, target_arcade=target_arcade
                )

    return dict(
        objects_tag = objects_tag,
        texture_datas = texture_datas,
        texdefs_tag = texdef_tag,
        anim_tag = anim_tag
        )


def decompile_cache_files(
        target_dir, data_dir=None, overwrite=False, individual_meta=True,
        meta_asset_types=c.METADATA_ASSET_EXTENSIONS[0],
        anim_asset_types=c.ANIMATION_CACHE_EXTENSIONS,
        tex_asset_types=c.TEXTURE_CACHE_EXTENSIONS,
        mod_asset_types=c.MODEL_CACHE_EXTENSIONS,\
        parallel_processing=False, swap_lightmap_and_diffuse=False, **kwargs
        ):

    filepaths = util.locate_objects_dir_files(target_dir)

    # load objects, texdefs, worlds, and animations
    objects_tag = (
        objects_def.build(filepath=filepaths['objects_filepath'])
        if os.path.isfile(filepaths['objects_filepath']) else None
        )
    texdef_tag = (
        texdef_def.build(filepath=filepaths['texdef_filepath'])
        if os.path.isfile(filepaths['texdef_filepath']) else None
        )
    anim_tag = (
        anim_def.build(filepath=filepaths['anim_filepath'])
        if os.path.isfile(filepaths['anim_filepath']) else None
        )
    worlds_tag = (
        worlds_def.build(filepath=filepaths['worlds_filepath'])
        if os.path.isfile(filepaths['worlds_filepath']) else None
        )

    if objects_tag:
        objects_tag.anim_tag   = anim_tag
        objects_tag.texdef_tag = texdef_tag
        try:
            objects_tag.load_texdef_names()
        except Exception:
            print('Could not load texdefs. Names generated will be best guesses.')

        try:
            objects_tag.load_texmod_sequences()
        except Exception:
            print('Could not load texmod sequences. Texture animations may be broken.')

    if data_dir is None:
        data_dir = os.path.join(target_dir, c.DATA_FOLDERNAME)

    if meta_asset_types and (objects_tag or anim_tag):
        objects_metadata.decompile_objects_metadata(
            objects_tag, anim_tag, data_dir, overwrite=overwrite,
            asset_types=meta_asset_types, individual_meta=individual_meta,
            )

    if tex_asset_types and (objects_tag or texdef_tag):
        texture.export_textures(
            data_dir, objects_tag=objects_tag, texdef_tag=texdef_tag,
            overwrite=overwrite, parallel_processing=parallel_processing,
            asset_types=tex_asset_types, mipmaps=kwargs.get("mipmaps", False),
            textures_filepath=filepaths['textures_filepath']
            )

    if anim_asset_types and anim_tag:
        animation.export_animations(
            anim_tag, objects_tag, data_dir, overwrite=overwrite,
            parallel_processing=parallel_processing, asset_types=anim_asset_types,
            )

    if mod_asset_types and objects_tag:
        model.export_models(
            objects_tag, data_dir, overwrite=overwrite,
            parallel_processing=parallel_processing, asset_types=mod_asset_types,
            swap_lightmap_and_diffuse=swap_lightmap_and_diffuse
            )


def serialize_textures_cache(
        objects_tag, texture_datas, output_filepath=None,
        target_ngc=False, target_ps2=False, target_xbox=False,
        target_dreamcast=False, target_arcade=False
        ):
    if not output_filepath:
        objects_dir = os.path.dirname(objects_tag.filepath)
        extension   = (
            c.PS2_EXTENSION if target_ps2 else
            c.XBOX_EXTENSION if target_xbox else
            c.NGC_EXTENSION if target_ngc else
            c.ARC_EXTENSION if target_arcade else
            c.DC_EXTENSION if target_dreamcast else
            None
            )
        if extension is None:
            raise ValueError("No target platform specified")

        output_filepath = os.path.join(
            objects_dir, f"{c.TEXTURES_FILENAME}.{extension}"
            )

    temppath = output_filepath + ".temp"
    # open the textures.ps2 file and serialize the texture data into it
    with open(temppath, 'w+b') as f:
        for texture_data, bitmap in zip(texture_datas, objects_tag.data.bitmaps):
            if bitmap.frame_count or getattr(bitmap.flags, "external", False):
                continue
            elif texture_data is None:
                continue

            f.seek(bitmap.tex_pointer)
            f.write(texture_data)

    backup_and_rename_temp(output_filepath, temppath)


def compile_texdef_cache_from_objects(objects_tag):
    if objects_tag.texdef_names is None:
        try:
            objects_tag.load_texdef_names()
        except Exception:
            print('Could not load texdefs. Names generated will be best guesses.')

    _, bitmap_names = objects_tag.get_cache_names()
    named_bitmap_indices = {
        b.tex_index for b in objects_tag.data.bitmap_defs if b.name
        }

    texdef_tag = texdef_def.build()
    objects_dir = os.path.dirname(objects_tag.filepath)
    objects_ext = os.path.splitext(objects_tag.filepath)[-1].strip(".")

    texdef_tag.filepath = os.path.join(objects_dir, "%s.%s" % (c.TEXDEF_FILENAME, objects_ext))

    object_bitmaps     = objects_tag.data.bitmaps
    texdef_bitmaps     = texdef_tag.data.bitmaps
    texdef_bitmap_defs = texdef_tag.data.bitmap_defs

    texdef_index = 0
    for bitm_index in range(len(object_bitmaps)):
        object_bitmap   = object_bitmaps[bitm_index]
        is_dreamcast    = hasattr(object_bitmap, "dc_sig")
        if object_bitmap.frame_count:
            # don't save the start frame of the sequence to the texdef
            continue
        elif is_dreamcast and object_bitmap.flags.external:
            # dreamcast doesnt save external textures to texdef
            continue

        texdef_bitmaps.append(
            case = ("dreamcast" if is_dreamcast else "ps2")
            )
        texdef_bitmap_defs.append()

        texdef_bitmap     = texdef_bitmaps[-1]
        texdef_bitmap_def = texdef_bitmap_defs[-1]

        format_name = object_bitmap.format.enum_name

        # copy data over
        texdef_bitmap.tex_pointer  = object_bitmap.tex_pointer
        texdef_bitmap.width        = object_bitmap.width
        texdef_bitmap.height       = object_bitmap.height
        texdef_bitmap.format.set_to(format_name)

        texdef_bitmap.flags.clamp_u = object_bitmap.flags.clamp_u
        texdef_bitmap.flags.clamp_v = object_bitmap.flags.clamp_v
        if is_dreamcast:
            texdef_bitmap.image_type.set_to(image_type)
        else:
            texdef_bitmap.mipmap_count      = object_bitmap.mipmap_count
            texdef_bitmap.lod_k             = object_bitmap.lod_k
            texdef_bitmap.flags.halfres     = object_bitmap.flags.halfres
            texdef_bitmap.flags.has_alpha   = object_bitmap.flags.has_alpha

        texdef_bitmap_def.name = bitmap_names.get(bitm_index, {}).get("name", "")[: 30]
        texdef_bitmap_def.def_in_objects.set_to(
            "yes" if bitm_index in named_bitmap_indices else "no"
            )
        texdef_bitmap_def.width  = texdef_bitmap.width
        texdef_bitmap_def.height = texdef_bitmap.height

        if is_dreamcast:
            # copy size that was already computed
            bitmap_size = object_bitmap.size
        else:
            # calculate the size of all the bitmap data
            palette_stride = c.PALETTE_SIZES.get(format_name, 0)
            pixel_stride   = c.PIXEL_SIZES.get(format_name, 0)

            bitmap_size = (2**pixel_stride)*palette_stride
            mip_width  = texdef_bitmap.width
            mip_height = texdef_bitmap.height
            for i in range(object_bitmap.mipmap_count + 1):
                bitmap_size += (mip_width*mip_height*pixel_stride)//8
                mip_width  = (mip_width + 1)//2
                mip_height = (mip_height + 1)//2

        texdef_bitmap.size = bitmap_size

    # set the header values
    curr_ptr = texdef_tag.data.header.binsize
    texdef_tag.data.header.bitmap_defs_pointer = curr_ptr
    curr_ptr += texdef_bitmap_defs.binsize
    texdef_tag.data.header.bitmap_defs_pointer = curr_ptr

    return texdef_tag
