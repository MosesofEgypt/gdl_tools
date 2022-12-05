import hashlib
import math
import os

from traceback import format_exc
from ..metadata import objects as objects_metadata
from .serialization.texture import G3DTexture, ROMTEX_HEADER_STRUCT
from . import constants as c
from . import texture_buffer_packer
from . import util


def _compile_texture(kwargs):
    name           = kwargs.pop("name")
    target_ngc     = kwargs.pop("target_ngc")
    target_ps2     = kwargs.pop("target_ps2")
    cache_filepath = kwargs.pop("cache_filepath")
    asset_filepath = kwargs.pop("asset_filepath")

    print("Compiling texture: %s" % name)
    g3d_texture = G3DTexture()
    g3d_texture.import_asset(asset_filepath, **kwargs)
    os.makedirs(os.path.dirname(cache_filepath), exist_ok=True)
    with open(cache_filepath, "wb") as f:
        g3d_texture.export_gtx(f, target_ngc=target_ngc, target_ps2=target_ps2)


def _decompile_texture(kwargs):
    name = kwargs["name"]
    asset_type = kwargs["asset_type"]
    bitm_data = kwargs["bitm_data"]
    filepath = kwargs["filepath"]
    overwrite = kwargs["overwrite"]

    print("Decompiling texture: %s" % name)
    g3d_texture = G3DTexture()
    with open(kwargs["textures_filepath"], "rb") as f:
        # go to the start of the palette/pixel data
        f.seek(kwargs["tex_pointer"])
        g3d_texture.import_gtx(
            input_buffer=f, headerless=True, **bitm_data
            )

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if asset_type not in c.TEXTURE_CACHE_EXTENSIONS:
        g3d_texture.export_asset(
            filepath, overwrite=overwrite,
            include_mipmaps=kwargs["include_mipmaps"],
            )
    elif not os.path.isfile(filepath) or overwrite:
        with open(filepath, "wb+") as f:
            g3d_texture.export_gtx(
                f, target_ngc=(asset_type == c.TEXTURE_CACHE_EXTENSION_NGC)
                )


def compile_textures(
        data_dir,
        force_recompile=False, optimize_format=False, parallel_processing=False,
        target_ps2=False, target_ngc=False, target_xbox=False,
        ):
    asset_folder    = os.path.join(data_dir, c.EXPORT_FOLDERNAME, c.TEX_FOLDERNAME)
    cache_path_base = os.path.join(data_dir, c.IMPORT_FOLDERNAME, c.TEX_FOLDERNAME)

    # get the metadata for all bitmaps to import and
    # key it by name to allow matching to asset files
    all_metadata = objects_metadata.compile_objects_metadata(data_dir)
    bitmap_metadata = {
        m.get("name"): m
        for m in all_metadata.get("bitmaps", ())
        if isinstance(m, dict) and m.get("name")
        }

    all_job_args = []
    all_assets = util.locate_textures(os.path.join(asset_folder), cache_files=False)

    asset_type = (
        c.TEXTURE_CACHE_EXTENSION_PS2  if target_ps2 else
        c.TEXTURE_CACHE_EXTENSION_NGC  if target_ngc else
        c.TEXTURE_CACHE_EXTENSION_XBOX
        )
    for name in sorted(all_assets):
        meta = bitmap_metadata.get(name)
        asset_filepath = all_assets[name]
        if not meta:
            # texture isn't listed in metadata. don't compile it
            continue

        try:
            filename = os.path.splitext(os.path.relpath(asset_filepath, asset_folder))[0]
            cache_filepath = os.path.join(cache_path_base, "%s.%s" % (filename, asset_type))

            source_md5 = b'\x00'*16
            gtx_cached_md5 = b''
            with open(asset_filepath, "rb") as f:
                source_md5 = hashlib.md5(f.read()).digest()

            if os.path.isfile(cache_filepath):                
                with open(cache_filepath, "rb") as f:
                    data = f.read(ROMTEX_HEADER_STRUCT.size)

                if len(data) >= ROMTEX_HEADER_STRUCT.size:
                    gtx_cached_md5 = ROMTEX_HEADER_STRUCT.unpack(data)[6]

            if gtx_cached_md5 == source_md5 and not force_recompile:
                # original asset file; don't recompile
                continue

            all_job_args.append(dict(
                asset_filepath=asset_filepath, optimize_format=optimize_format,
                target_format_name=meta.get("format", c.DEFAULT_FORMAT_NAME),
                mipmap_count=max(0, 0 if target_ngc else meta.get("mipmap_count", 0)),
                name=name, cache_filepath=cache_filepath,
                target_ngc=target_ngc, target_ps2=target_ps2
                ))
        except Exception:
            print(format_exc())
            print("Error: Could not create texture compilation job: '%s'" % asset_filepath)

    print("Compiling %s textures in %s" % (
        len(all_job_args), "parallel" if parallel_processing else "series"
        ))
    util.process_jobs(
        _compile_texture, all_job_args,
        process_count=None if parallel_processing else 1
        )


def import_textures(
        objects_tag, data_dir, use_force_index_hack=False,
        target_ngc=False, target_ps2=False, target_xbox=False,
        ):
    # locate and load all assets
    gtx_textures_by_name = {}
    all_asset_filepaths = util.locate_textures(
        os.path.join(data_dir, c.IMPORT_FOLDERNAME, c.TEX_FOLDERNAME),
        cache_files=True, target_ngc=target_ngc, target_xbox=target_xbox
        )
    for name in sorted(all_asset_filepaths):
        try:
            with open(all_asset_filepaths[name], "rb") as f:
                name = name.upper()
                gtx_textures_by_name[name] = G3DTexture()
                gtx_textures_by_name[name].import_gtx(f, is_ngc=target_ngc)
        except Exception:
            print(format_exc())
            print("Could not load texture:\n    %s" % all_asset_filepaths[name])

    bitmaps     = objects_tag.data.bitmaps
    bitmap_defs = objects_tag.data.bitmap_defs
    del bitmaps[:]
    del bitmap_defs[:]

    # get the metadata for all bitmaps to import
    all_metadata = objects_metadata.compile_objects_metadata(
        data_dir, by_asset_name=not use_force_index_hack
        )

    # for returning to the caller for easy iteration
    gtx_textures = []

    # we'll be saving all filenames to the texdef_names in the objects_tag.
    # this is so the model compilation can find the textures referenced, even
    # if the names aren't saved to the tag itself.
    objects_tag.texdef_names = []

    if use_force_index_hack and all_metadata:  # hack
        max_forced_bitmap_index = max(
            meta.get("force_index", -1) for meta in all_metadata["bitmaps"]
            )
        bitmaps.extend(1 + max_forced_bitmap_index)
        all_metadata = dict(combined=all_metadata)

    # for inserting the metadata into the objects tag in the correct order
    sorted_bitm_meta = [None] * len(bitmaps)
    gtx_textures     = [None] * len(bitmaps)

    tex_pointer = 0

    for type_asset_name in sorted(all_metadata):
        # type_asset_name will look like 'bitmaps_AAAWHITE', and we
        # only want the 'AAAWHITE' part. split it and unify the case
        frames_metadata = all_metadata[type_asset_name].get("bitmaps", ())

        asset_name = type_asset_name.split('_', 1)[-1].upper()
        initial_frame = not use_force_index_hack

        for meta in frames_metadata:
            g3d_texture = gtx_textures_by_name.get(meta["name"])

            # NOTE: force_index is a hack until animation decomp is a thing
            bitm_index = meta.get("force_index", -1) if use_force_index_hack else -1
            if bitm_index not in range(len(bitmaps)):
                bitmaps.append()
                gtx_textures.append(None)
                sorted_bitm_meta.append(None)
                bitm_index = len(bitmaps) - 1

            if initial_frame:
                meta["frame_count"] = max(0, len(frames_metadata) - 1)

            sorted_bitm_meta[bitm_index] = meta
            gtx_textures[bitm_index]     = g3d_texture
            initial_frame = False

    # loop over the bitmaps in the order they need to be compiled
    # into the cache file, set the pointers for the texture data,
    # and import the rest of the bitmap metadata(w/h, mips, etc).
    for i in range(len(sorted_bitm_meta)):
        bitmap      = bitmaps[i]
        meta        = sorted_bitm_meta[i]
        g3d_texture = gtx_textures[i]
        if not meta:
            continue

        bitmap.frame_count = meta.get("frame_count", 0)
        bitmap.tex_pointer = tex_pointer

        if bitmap.frame_count or bitmap.flags.external:
            # no bitmap to import; only import metadata
            try:
                bitmap.format.set_to(meta["format"])
            except Exception:
                print(format_exc())
                print("Warning: Could not set bitmap format.")

            bitmap.flags.data   = 0
            bitmap.lod_k        = meta.get("lod_k", c.DEFAULT_TEX_LOD_K)
            bitmap.width        = meta.get("width", 0)
            bitmap.height       = meta.get("height", 0)
            bitmap.mipmap_count = meta.get("mipmap_count", 0)
            bitmap.frame_count  = meta.get("frame_count", bitmap.frame_count)

            bitmap.tex_palette_index = meta.get("tex_palette_index", 0)
            bitmap.tex_palette_count = meta.get("tex_palette_count", 0)
            bitmap.tex_shift_index   = meta.get("tex_shift_index", 0)
        elif g3d_texture:
            # there is actually a texture to import
            bitmap_size = 0
            for rawdata in g3d_texture.textures:
                bitmap_size += len(rawdata) * getattr(rawdata, "itemsize", 1)

            if c.PIXEL_SIZES.get(g3d_texture.format_name) == 4:
                bitmap_size //= 2

            if g3d_texture.palette:
                bitmap_size += (
                    len(g3d_texture.palette) * getattr(g3d_texture.palette, "itemsize", 1)
                    )

            tex_pointer += bitmap_size

            bitmap.format.set_to(g3d_texture.format_name)
            bitmap.lod_k      = meta.get("lod_k", g3d_texture.lod_k)
            bitmap.flags.data = g3d_texture.flags
            bitmap.width      = g3d_texture.width
            bitmap.height     = g3d_texture.height
            if target_ngc:
                bitmap.mipmap_count = meta.get("mipmap_count", 0)
            else:
                bitmap.mipmap_count = max(0, len(g3d_texture.textures) - 1)

            bitmap.flags.has_alpha = "A" in g3d_texture.format_name
        else:
            print("Warning: Could not locate bitmap file for '%s'" % asset_name)

        # copy flags from metadata
        for flag_name in meta.get("flags", {}):
            if hasattr(bitmap.flags, flag_name):
                setattr(bitmap.flags, flag_name, meta["flags"][flag_name])

        # align after each bitmap
        tex_pointer += util.calculate_padding(tex_pointer, c.DEF_TEXTURE_BUFFER_CHUNK_SIZE)

        # add 1 to make sure we dont try to do log(0, 2)
        bitmap.log2_of_width  = int(math.log(bitmap.width + 1, 2))
        bitmap.log2_of_height = int(math.log(bitmap.height + 1, 2))
        bitmap.width_64       = max(1, (bitmap.width + 63) // 64)

        if bitmap.flags.external or meta.get("cache_name"):
            # create a bitmap def
            bitmap_defs.append()
            bitmap_defs[-1].name = meta["name"][:30]
            bitmap_defs[-1].width = bitmap.width
            bitmap_defs[-1].height = bitmap.height
            bitmap_defs[-1].tex_index = i

        if not bitmap.frame_count:
            # the only names stored to the texdef names are the non-sequence bitmaps
            objects_tag.texdef_names.append(meta["name"])

        if bitmap.flags.external:
            continue

        # populate tex0 and miptbp
        format_name = bitmap.format.enum_name
        bitmap.tex0.tex_width  = bitmap.log2_of_width
        bitmap.tex0.tex_height = bitmap.log2_of_height
        bitmap.tex0.psm.set_to(
            c.PSM_T8   if "IDX_8" in format_name else
            c.PSM_T4   if "IDX_4" in format_name else
            c.PSM_CT16 if "1555"  in format_name else
            c.PSM_CT32 if "8888"  in format_name else
            c.PSM_CT32 # should never hit this
            )
        bitmap.tex0.tex_cc.set_to(
            meta.get("tex_cc", "rgba")
            )
        bitmap.tex0.clut_pixmode.set_to(
            c.PSM_CT16 if "1555_IDX" in format_name else c.PSM_CT32
            )
        bitmap.tex0.tex_function.set_to(
            meta.get("tex_function", "decal")
            )
        bitmap.tex0.clut_smode.set_to(
            meta.get("clut_smode", "csm1")
            )
        bitmap.tex0.clut_loadmode.set_to(
            meta.get("clut_loadmode", "recache")
            )

        buffer_calc = texture_buffer_packer.TextureBufferPacker(
            width=bitmap.width, height=bitmap.height,
            mipmaps=bitmap.mipmap_count,
            pixel_format=bitmap.tex0.psm.enum_name,
            palette_format=bitmap.tex0.clut_pixmode.enum_name,
            )
        buffer_calc.calculate()

        bitmap.size          = buffer_calc.optimized_buffer_size
        bitmap.tex0.tb_addr  = buffer_calc.base_address
        bitmap.tex0.tb_width = buffer_calc.buffer_width
        bitmap.tex0.cb_addr  = buffer_calc.palette_address
        for m in range(1, 7):
            tb_addr, tb_width = buffer_calc.get_address_and_width(m)
            bitmap.mip_tbp["tb_addr%s"  % m] = tb_addr
            bitmap.mip_tbp["tb_width%s" % m] = tb_width

    return gtx_textures


def decompile_textures(
        objects_tag, data_dir,
        asset_types=c.TEXTURE_CACHE_EXTENSIONS,
        parallel_processing=False, overwrite=False, mipmaps=False
        ):
    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    for asset_type in asset_types:
        if asset_type not in (*c.TEXTURE_CACHE_EXTENSIONS, *c.TEXTURE_ASSET_EXTENSIONS):
            raise ValueError("Unknown texture type '%s'" % asset_type)

    assets_dir = os.path.join(data_dir, c.EXPORT_FOLDERNAME, c.TEX_FOLDERNAME)
    cache_dir  = os.path.join(data_dir, c.IMPORT_FOLDERNAME, c.TEX_FOLDERNAME)
    tag_dir = os.path.dirname(objects_tag.filepath)
    textures_ext = os.path.splitext(objects_tag.filepath)[-1].strip(".")

    bitmaps = objects_tag.data.bitmaps
    _, bitmap_assets = objects_tag.get_cache_names()

    is_ngc = (textures_ext.lower() == c.NGC_EXTENSION.lower())
    textures_filepath = os.path.join(
        tag_dir, "%s.%s" % (c.TEXTURES_FILENAME, textures_ext)
        )

    if not os.path.isfile(textures_filepath):
        print("No textures cache to extract from.")
        return

    all_job_args = []

    for i in range(len(bitmaps)):
        bitm  = bitmaps[i]
        asset = bitmap_assets.get(i)

        try:
            if asset is None or bitm.frame_count or getattr(bitm.flags, "external", False):
                continue
            elif bitm.format.enum_name == "<INVALID>":
                print("Invalid bitmap format detected in bitmap %s at index %s" % (asset, i))
                continue

            bitm_data = dict(
                flags = bitm.flags.data, width = bitm.width, height = bitm.height,
                lod_k=bitm.lod_k, is_ngc=is_ngc, format_name=bitm.format.enum_name,
                # regardless of what the objects says, gamecube doesnt contain mipmaps
                mipmaps=(0 if is_ngc else bitm.mipmap_count)
                )

            for asset_type in asset_types:
                filename = "%s.%s" % (asset['name'], asset_type)
                if asset['name'] != asset["asset_name"]:
                    filename = os.path.join(asset["asset_name"], filename)

                filepath = os.path.join(
                    cache_dir if asset_type in c.TEXTURE_CACHE_EXTENSIONS else assets_dir,
                    filename
                    )
                if os.path.isfile(filepath) and not overwrite:
                    continue

                all_job_args.append(dict(
                    bitm_data=bitm_data, name=asset["name"],
                    textures_filepath=textures_filepath,
                    asset_type=asset_type, filepath=filepath, overwrite=overwrite,
                    include_mipmaps=mipmaps, tex_pointer=bitm.tex_pointer,
                    ))
        except:
            print(format_exc())
            print(('The above error occurred while trying to export bitmap %s as %s. '
                   "name: '%s', asset_name: '%s'") %
                  (i, asset_type, asset.get("name"), asset.get("asset_name"))
                  )

    print("Decompiling %s textures in %s" % (
        len(all_job_args), "parallel" if parallel_processing else "series"
        ))
    util.process_jobs(
        _decompile_texture, all_job_args,
        process_count=None if parallel_processing else 1
        )
