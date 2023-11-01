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
from . import constants as c
from . import util


def compile_cache_files(
        objects_dir,
        target_ngc=False, target_ps2=False, target_xbox=False,
        target_dreamcast=False, target_arcade=False,
        serialize_cache_files=False, use_force_index_hack=False,
        build_texdef_cache=False,
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

    # TODO: add support for compiling worlds
    data_dir    = os.path.join(objects_dir, c.DATA_FOLDERNAME)
    objects_tag = objects_def.build()
    anim_tag    = anim_def.build()
    texdef_tag  = None

    if target_dreamcast or target_arcade:
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
        target_dreamcast=target_dreamcast, target_arcade=target_arcade,
        use_force_index_hack=use_force_index_hack
        )
    print("Importing models...")
    model.import_models(
        objects_tag, data_dir, target_ngc=target_ngc,
        target_ps2=target_ps2, target_xbox=target_xbox,
        target_dreamcast=target_dreamcast, target_arcade=target_arcade
        )
    print("Importing animations...")
    animation.import_animations(anim_tag, data_dir)

    if build_texdef_cache:
        texdef_tag = compile_texdef_cache_from_objects(objects_tag)

    if serialize_cache_files:
        print("Serializing...")
        objects_tag.serialize(temp=False)
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
        animations_tag = anim_tag
        )


def decompile_cache_files(
        target_dir, data_dir=None, overwrite=False, individual_meta=True,
        meta_asset_types=c.METADATA_ASSET_EXTENSIONS[0],
        anim_asset_types=(c.ANIMATION_CACHE_EXTENSION,),
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

    if meta_asset_types:
        if objects_tag:
            objects_metadata.decompile_objects_metadata(
                objects_tag, data_dir, overwrite=overwrite,
                asset_types=meta_asset_types, individual_meta=individual_meta,
                )

        if anim_tag:
            anim_metadata.decompile_anim_metadata(
                anim_tag, data_dir, overwrite=overwrite,
                asset_types=meta_asset_types, individual_meta=individual_meta,
                )

    if tex_asset_types and (objects_tag or texdef_tag):
        texture.decompile_textures(
            data_dir, objects_tag=objects_tag, texdef_tag=texdef_tag,
            overwrite=overwrite, parallel_processing=parallel_processing,
            asset_types=tex_asset_types, mipmaps=kwargs.get("mipmaps", False),
            textures_filepath=filepaths['textures_filepath']
            )

    if mod_asset_types and objects_tag:
        model.decompile_models(
            objects_tag, data_dir, overwrite=overwrite,
            parallel_processing=parallel_processing, asset_types=mod_asset_types,
            swap_lightmap_and_diffuse=swap_lightmap_and_diffuse
            )

    if anim_asset_types and anim_tag:
        animation.decompile_animations(
            anim_tag, data_dir, overwrite=overwrite,
            parallel_processing=parallel_processing, asset_types=anim_asset_types,
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
