import pathlib

from math import log
from supyr_struct import FieldType
from supyr_struct.util import backup_and_rename_temp
from traceback import format_exc
from ...defs.anim import anim_def
from ...defs.objects import objects_def
from ...defs.texdef import texdef_def
from ...defs.worlds import worlds_def
from ..metadata import objects as objects_metadata,\
     animations as animations_metadata, util as metadata_util
from . import animation, model, texture
from .serialization.asset_cache import verify_source_file_asset_checksum
from . import constants as c
from . import util


COMPILE_JOB_TYPE_ANIMATIONS = 'animation'
COMPILE_JOB_TYPE_TEXTURES   = 'texture'
COMPILE_JOB_TYPE_MODELS     = 'model'


def _compile_assets(
        compile_job_type,
        force_recompile=False, parallel_processing=False,
        target_ps2=False, target_ngc=False, target_xbox=False,
        target_dreamcast=False, target_arcade=False, 
        data_dir=".", assets_dir=None, cache_dir=None, **kwargs
        ):
    if not assets_dir:
        assets_dir  = pathlib.Path(data_dir, folder)
    if not cache_dir:
        cache_dir   = pathlib.Path(data_dir, c.IMPORT_FOLDERNAME, folder)

    if compile_job_type == COMPILE_JOB_TYPE_TEXTURES:
        metadata_func   = lambda: objects_metadata.\
                          compile_objects_metadata(assets_dir).get("bitmaps", ())
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
        metadata_func   = lambda: objects_metadata.\
                          compile_objects_metadata(assets_dir).get("objects", ())
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
        metadata_func   = lambda: animations_metadata.\
                          compile_animations_metadata(assets_dir).get("actors", ())
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

    if target_dreamcast:
        print("Warning: Unable to compile Dreamcast assets at this time.")
        return

    if cache_type is None:
        raise ValueError("No target platform specified")

    # get the metadata for all assets to import and
    # key it by name to allow matching to asset files
    all_metadata = metadata_func()
    if compile_job_type == COMPILE_JOB_TYPE_TEXTURES:
        all_assets = util.locate_textures(assets_dir, cache_files=False)
    elif compile_job_type == COMPILE_JOB_TYPE_MODELS:
        all_assets = util.locate_models(assets_dir, cache_files=False)
    elif compile_job_type == COMPILE_JOB_TYPE_ANIMATIONS:
        all_assets = util.locate_animations(assets_dir, cache_files=False)

    all_job_args = []
    for name in sorted(all_assets):
        meta = all_metadata.get(name)
        if not meta:
            # not listed in metadata. don't compile it
            continue

        try:
            asset_filepath = all_assets[name]
            rel_filepath   = asset_filepath.relative_to(assets_dir)
            filename       = rel_filepath.stem
            cache_filepath = cache_dir.joinpath(f"{filename}.{cache_type}")

            if not force_recompile and cache_filepath.is_file():
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


def compile_metadata(objects_dir=".", assets_dir=None, cache_dir=None):
    data_dir = pathlib.Path(objects_dir, c.DATA_FOLDERNAME)

    if not assets_dir: assets_dir  = data_dir
    if not cache_dir:  cache_dir   = data_dir.joinpath(c.IMPORT_FOLDERNAME)

    # TODO: delete any metadata files found in the folder

    metadata_sets = metadata_util.compile_metadata(assets_dir, cache_files=False)
    for set_name in metadata_sets:
        filepath = pathlib.Path(cache_dir, "{set_name}.{c.METADATA_CACHE_EXTENSION}")
        filepath.mkdir(parents=True, exist_ok=True)
        metadata_util.dump_metadata(metadata_sets[set_name], filepath, overwrite)


def compile_cache_files(
        target_ngc=False, target_ps2=False, target_xbox=False,
        target_dreamcast=False, target_arcade=False,
        serialize_cache_files=False, build_texdef_cache=False,
        build_objects_cache=True, build_anim_cache=True,
        objects_dir=".", cache_dir=None
        ):
    objects_dir = pathlib.Path(objects_dir)
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
    data_dir    = objects_dir.joinpath(c.DATA_FOLDERNAME)
    objects_tag = objects_def.build() if build_objects_cache else None
    anim_tag    = anim_def.build()    if build_anim_cache else None
    texdef_tag  = None

    objects_tag.anim_tag = anim_tag

    if objects_tag and (target_dreamcast or target_arcade):
        # dreamcast and arcade use v1 or v0 of the objects.
        # set header to v1 and reparse header and all arrays
        # so they're the correct structure versions
        objects_tag.data.version_header.version.set_to("v1")
        objects_tag.data.parse(attr_index="header")
        objects_tag.data.parse(attr_index="objects")
        objects_tag.data.parse(attr_index="bitmaps")

    anim_tag.filepath = objects_dir.joinpath(
        f"{c.ANIM_FILENAME}.{anim_worlds_ext}"
        )

    if objects_tag:
        objects_tag.filepath = objects_dir.joinpath(
            f"{c.OBJECTS_FILENAME}.{ext}"
            )
        objects_tag.data.version_header.dir_name = (
            str(objects_dir).replace("\\", "/")[-32:]
            )

        print("Importing textures...")
        texture_datas = texture.import_textures(
            objects_tag, target_ngc=target_ngc, target_ps2=target_ps2,
            target_xbox=target_xbox, target_dreamcast=target_dreamcast,
            target_arcade=target_arcade, data_dir=data_dir, cache_dir=cache_dir
            )
        print("Importing models...")
        model.import_models(
            objects_tag, target_ngc=target_ngc, target_ps2=target_ps2,
            target_xbox=target_xbox, target_dreamcast=target_dreamcast,
            target_arcade=target_arcade, data_dir=data_dir, cache_dir=cache_dir
            )

    if anim_tag:
        print("Importing animations...")
        animation.import_animations(
            anim_tag, objects_tag, data_dir=data_dir, cache_dir=cache_dir
            )

    if build_texdef_cache:
        texdef_tag = compile_texdef_cache_from_objects(objects_tag)
        objects_tag.texdef_tag = texdef_tag

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
        target_dir, overwrite=False,
        meta_asset_types=c.METADATA_CACHE_EXTENSIONS,
        anim_asset_types=c.ANIMATION_CACHE_EXTENSIONS,
        tex_asset_types=c.TEXTURE_CACHE_EXTENSIONS,
        mod_asset_types=c.MODEL_CACHE_EXTENSIONS,
        parallel_processing=False, swap_lightmap_and_diffuse=False,
        data_dir=None, assets_dir=None, cache_dir=None,
        **kwargs
        ):

    filepaths = util.locate_objects_dir_files(target_dir)

    # load objects, texdefs, worlds, and animations
    objects_tag = (
        objects_def.build(filepath=filepaths['objects_filepath'])
        if filepaths['objects_filepath'].is_file() else None
        )
    anim_tag = (
        anim_def.build(filepath=filepaths['anim_filepath'])
        if filepaths['anim_filepath'].is_file() else None
        )
    worlds_tag = (
        worlds_def.build(filepath=filepaths['worlds_filepath'])
        if filepaths['worlds_filepath'].is_file() else None
        )
    texdef_tag = None
    if filepaths['texdef_filepath'].is_file():
        try:
            # so strangely, some of the dreamcast texdefs are big endian
            if util.get_is_big_endian_texdef(filepaths['texdef_filepath']):
                FieldType.force_big()
            texdef_def.build(filepath=filepaths['texdef_filepath'])
        finally:
            FieldType.force_normal()

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

        try:
            objects_tag.load_objanim_sequences()
        except Exception:
            print('Could not load obj anim sequences. Object animations may be broken.')

        try:
            objects_tag.load_actor_object_assets()
        except Exception:
            print('Could not load actor object assets. Objects may not be sorted well.')

    data_dir = pathlib.Path(
        *(data_dir if data_dir else (target_dir, c.DATA_FOLDERNAME))
        )

    if meta_asset_types and objects_tag:
        objects_metadata.decompile_objects_metadata(
            objects_tag, anim_tag=anim_tag, overwrite=overwrite,
            asset_types=meta_asset_types, data_dir=data_dir,
            assets_dir=assets_dir, cache_dir=cache_dir
            )

    if meta_asset_types and anim_tag:
        animations_metadata.decompile_animations_metadata(
            anim_tag, objects_tag=objects_tag, overwrite=overwrite,
            asset_types=meta_asset_types, data_dir=data_dir,
            assets_dir=assets_dir, cache_dir=cache_dir
            )

    if tex_asset_types and (objects_tag or texdef_tag):
        texture.export_textures(
            objects_tag=objects_tag, texdef_tag=texdef_tag,
            overwrite=overwrite, parallel_processing=parallel_processing,
            asset_types=tex_asset_types, mipmaps=kwargs.get("mipmaps", False),
            textures_filepath=filepaths['textures_filepath'],
            data_dir=data_dir, assets_dir=assets_dir, cache_dir=cache_dir
            )

    if anim_asset_types and anim_tag:
        animation.export_animations(
            anim_tag, overwrite=overwrite,
            parallel_processing=parallel_processing, asset_types=anim_asset_types,
            data_dir=data_dir, assets_dir=assets_dir, cache_dir=cache_dir,
            )

    if mod_asset_types and objects_tag:
        model.export_models(
            objects_tag, anim_tag=anim_tag, overwrite=overwrite,
            parallel_processing=parallel_processing, asset_types=mod_asset_types,
            swap_lightmap_and_diffuse=swap_lightmap_and_diffuse,
            data_dir=data_dir, assets_dir=assets_dir, cache_dir=cache_dir
            )


def serialize_textures_cache(
        objects_tag, texture_datas, output_filepath=None,
        target_ngc=False, target_ps2=False, target_xbox=False,
        target_dreamcast=False, target_arcade=False
        ):
    if not output_filepath:
        objects_dir = pathlib.Path(objects_tag.filepath).parent
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

        output_filepath = objects_dir.joinpath(f"{c.TEXTURES_FILENAME}.{extension}")

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
    objects_filepath = pathlib.Path(objects_tag.filepath)
    objects_dir = objects_filepath.parent
    objects_ext = objects_filepath.suffix.strip(".")

    texdef_tag.filepath = objects_dir.joinpath("%s.%s" % (c.TEXDEF_FILENAME, objects_ext))

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
