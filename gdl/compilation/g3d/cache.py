import os

from math import log
from supyr_struct.util import backup_and_rename_temp
from traceback import format_exc
from ...defs.objects import objects_ps2_def
from ...defs.texdef import texdef_ps2_def
from ...defs.worlds import worlds_ps2_def
from ..metadata import objects as objects_metadata
from . import animation, collision, model, texture
from . import constants as c


def compile_cache_files(
        objects_dir,
        target_ngc=False, target_ps2=False, target_xbox=False, target_arcade=False,
        serialize_cache_files=False, use_force_index_hack=False,
        build_anim_cache=True, build_texdef_cache=False,
        ):
    # TODO: add support for compiling worlds
    data_dir    = os.path.join(objects_dir, c.DATA_FOLDERNAME)
    objects_tag = objects_ps2_def.build()
    anim_tag    = None
    texdef_tag  = None

    objects_tag.filepath = os.path.join(
        objects_dir, "%s.%s" % (
            c.OBJECTS_FILENAME,
            c.NGC_EXTENSION if target_ngc else
            c.ARC_EXTENSION if target_arcade else
            c.PS2_EXTENSION
            )
        )
    objects_tag.data.version_header.dir_name = (
        os.path.join(objects_dir, "").replace("\\", "/")[-32:]
        )

    gtx_textures = texture.import_textures(
        objects_tag, data_dir, target_ngc=target_ngc,
        target_ps2=target_ps2, target_xbox=target_xbox,
        use_force_index_hack=use_force_index_hack
        )
    model.import_models(
        objects_tag, data_dir, target_ngc=target_ngc,
        target_ps2=target_ps2, target_xbox=target_xbox,
        )

    if build_anim_cache:
        anim_tag = animation.import_animations(objects_tag, data_dir)

    if build_texdef_cache:
        texdef_tag = compile_texdef_cache_from_objects(objects_tag)

    if serialize_cache_files:
        objects_tag.serialize(temp=False)

        if anim_tag:
            anim_tag.serialize(temp=False)

        if texdef_tag:
            texdef_tag.serialize(temp=False)

        if gtx_textures:
            serialize_textures_cache(
                objects_tag, gtx_textures,
                target_ngc=target_ngc, target_ps2=target_ps2
                )

    return dict(
        objects_tag = objects_tag,
        gtx_textures = gtx_textures,
        texdefs_tag = texdef_tag,
        animations_tag = anim_tag
        )


def decompile_cache_files(
        target_dir, data_dir=None, overwrite=False, individual_meta=True,
        meta_asset_types=c.METADATA_ASSET_EXTENSIONS[0],
        tex_asset_types=c.TEXTURE_CACHE_EXTENSIONS,
        mod_asset_types=c.MODEL_CACHE_EXTENSIONS,
        coll_asset_types=c.COLLISION_CACHE_EXTENSION,
        parallel_processing=False, swap_lightmap_and_diffuse=False, **kwargs
        ):

    ps2_objects_filepath    = os.path.join(target_dir,  "objects.ps2")
    ngc_objects_filepath    = os.path.join(target_dir,  "objects.ngc")
    arcade_objects_filepath = os.path.join(target_dir,  "objects.rom")
    texdef_filepath         = os.path.join(target_dir,  "texdef.ps2")
    ps2_worlds_filepath     = os.path.join(target_dir,  "worlds.ps2")
    ngc_worlds_filepath     = os.path.join(target_dir,  "worlds.ngc")
    arcade_worlds_filepath  = os.path.join(target_dir,  "worlds.rom")

    objects_tag = None
    texdef_tag  = None
    worlds_tag  = None

    if os.path.isfile(ps2_objects_filepath):
        objects_tag = objects_ps2_def.build(filepath=ps2_objects_filepath)
        try:
            objects_tag.load_texdef_names()
        except Exception:
            print('Could not load texdefs. Names generated will be best guesses.')

    elif os.path.isfile(ngc_objects_filepath):
        objects_tag = objects_ps2_def.build(filepath=ngc_objects_filepath)
    elif os.path.isfile(arcade_objects_filepath):
        objects_tag = objects_ps2_def.build(filepath=arcade_objects_filepath)
    elif os.path.isfile(texdef_filepath):
        # no objects. default to texdef for trying to get texture headers
        texdef_tag = texdef_ps2_def.build(filepath=texdef_filepath)

    if os.path.isfile(ps2_worlds_filepath):
        worlds_tag = worlds_ps2_def.build(filepath=ps2_worlds_filepath)
    elif os.path.isfile(ngc_worlds_filepath):
        worlds_tag = worlds_ps2_def.build(filepath=ngc_worlds_filepath)
    elif os.path.isfile(arcade_worlds_filepath):
        worlds_tag = worlds_ps2_def.build(filepath=arcade_worlds_filepath)

    if data_dir is None:
        data_dir = os.path.join(target_dir, c.DATA_FOLDERNAME)

    if meta_asset_types and objects_tag:
        objects_metadata.decompile_objects_metadata(
            objects_tag, data_dir, overwrite=overwrite,
            asset_types=meta_asset_types, individual_meta=individual_meta,
            )

    if tex_asset_types and (objects_tag or texdef_tag):
        texture.decompile_textures(
            data_dir, objects_tag=objects_tag, texdef_tag=texdef_tag,
            overwrite=overwrite, parallel_processing=parallel_processing,
            asset_types=tex_asset_types, mipmaps=kwargs.get("mipmaps", False)
            )

    if (mod_asset_types and objects_tag and
        objects_tag.data.version_header.version.enum_name not in ("v0", "v1")
        ):
        model.decompile_models(
            objects_tag, data_dir,
            overwrite=overwrite, parallel_processing=parallel_processing,
            asset_types=mod_asset_types,
            swap_lightmap_and_diffuse=swap_lightmap_and_diffuse
            )

    if coll_asset_types and worlds_tag:
        collision.decompile_collision(
            worlds_tag, data_dir,
            overwrite=overwrite, asset_types=coll_asset_types,
            )


def serialize_textures_cache(
        objects_tag, gtx_textures, output_filepath=None,
        target_ngc=False, target_ps2=False
        ):
    if not output_filepath:
        objects_dir     = os.path.dirname(objects_tag.filepath)
        textures_filename = "%s.%s" % (
            c.TEXTURES_FILENAME,
            c.NGC_EXTENSION if target_ngc else c.PS2_EXTENSION
            )
        output_filepath = os.path.join(objects_dir, textures_filename)

    temppath = output_filepath + ".temp"
    # open the textures.ps2 file and serialize the texture data into it
    with open(temppath, 'w+b') as f:
        for g3d_texture, bitmap in zip(gtx_textures, objects_tag.data.bitmaps):
            if bitmap.frame_count or bitmap.flags.external:
                continue
            elif g3d_texture is None:
                continue

            f.seek(bitmap.tex_pointer)
            g3d_texture.export_gtx(
                f, headerless=True,
                target_ngc=target_ngc, target_ps2=target_ps2,
                )

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

    texdef_tag = texdef_ps2_def.build()
    objects_dir         = os.path.dirname(objects_tag.filepath)
    texdef_tag.filepath = os.path.join(objects_dir, "%s.%s" % (c.TEXDEF_FILENAME, c.PS2_EXTENSION))

    object_bitmaps     = objects_tag.data.bitmaps
    texdef_bitmaps     = texdef_tag.data.bitmaps
    texdef_bitmap_defs = texdef_tag.data.bitmap_defs

    texdef_index = 0
    for bitm_index in range(len(object_bitmaps)):
        object_bitmap     = object_bitmaps[bitm_index]
        if object_bitmap.frame_count:
            # don't save the start frame of the sequence to the texdef
            continue
        
        texdef_bitmaps.append()
        texdef_bitmap_defs.append()

        texdef_bitmap     = texdef_bitmaps[-1]
        texdef_bitmap_def = texdef_bitmap_defs[-1]

        format_name = object_bitmap.format.enum_name

        # copy data over
        texdef_bitmap.tex_pointer  = object_bitmap.tex_pointer
        texdef_bitmap.mipmap_count = object_bitmap.mipmap_count
        texdef_bitmap.lod_k        = object_bitmap.lod_k
        texdef_bitmap.width        = object_bitmap.width
        texdef_bitmap.height       = object_bitmap.height
        texdef_bitmap.format.set_to(format_name)

        texdef_bitmap_def.name = bitmap_names.get(bitm_index, {}).get("name", "")[: 30]
        texdef_bitmap_def.def_in_objects.set_to(
            "yes" if bitm_index in named_bitmap_indices else "no"
            )
        texdef_bitmap_def.width  = texdef_bitmap.width
        texdef_bitmap_def.height = texdef_bitmap.height

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

        # copy the flags
        texdef_bitmap.flags.halfres   = object_bitmap.flags.halfres
        texdef_bitmap.flags.clamp_u   = object_bitmap.flags.clamp_u
        texdef_bitmap.flags.clamp_v   = object_bitmap.flags.clamp_v
        texdef_bitmap.flags.has_alpha = object_bitmap.flags.has_alpha

    # set the header values
    curr_ptr = texdef_tag.data.header.binsize
    texdef_tag.data.header.bitmap_defs_pointer = curr_ptr
    curr_ptr += texdef_bitmap_defs.binsize
    texdef_tag.data.header.bitmap_defs_pointer = curr_ptr

    return texdef_tag
