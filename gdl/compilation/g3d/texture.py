import math
import os

from traceback import format_exc
from ..metadata import objects as objects_metadata
from .serialization.asset_cache import get_asset_checksum, verify_source_file_asset_checksum
from .serialization.texture import G3DTexture
from .serialization.texture_cache import get_texture_cache_class,\
     get_texture_cache_class_from_cache_type, Ps2TextureCache,\
     GamecubeTextureCache, DreamcastTextureCache, ArcadeTextureCache
from .serialization import texture_util, ncc
from . import constants as c
from . import texture_buffer_packer
from . import util


def _compile_texture(kwargs):
    name            = kwargs.pop("name")
    cache_type      = kwargs.pop("cache_type")
    cache_filepath  = kwargs.pop("cache_filepath")
    asset_filepath  = kwargs.pop("asset_filepath")

    print("Compiling texture: %s" % name)
    g3d_texture = G3DTexture()
    g3d_texture.import_asset(
        asset_filepath, min_dimension=(1 if target_dreamcast else 8),
        **kwargs
        )

    texture_cache = g3d_texture.compile_g3d(cache_type)
    texture_cache.source_asset_checksum = get_asset_checksum(
        filepath=asset_filepath, algorithm=texture_cache.checksum_algorithm
        )
    texture_rawdata = texture_cache.serialize()

    os.makedirs(os.path.dirname(cache_filepath), exist_ok=True)
    with open(cache_filepath, "wb") as f:
        f.write(texture_rawdata)


def _decompile_texture(kwargs):
    name            = kwargs["name"]
    texture_cache   = kwargs["texture_cache"]
    asset_type      = kwargs["asset_type"]
    filepath        = kwargs["filepath"]
    overwrite       = kwargs["overwrite"]
    include_mipmaps = kwargs["include_mipmaps"]

    print("Decompiling texture: %s" % name)

    if asset_type in c.TEXTURE_CACHE_EXTENSIONS:
        if overwrite or not os.path.isfile(filepath):
            texture_rawdata = texture_cache.serialize()
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'wb+') as f:
                f.write(texture_rawdata)
    else:
        g3d_texture = G3DTexture()
        g3d_texture.import_g3d(texture_cache)
        g3d_texture.export_asset(
            filepath, overwrite=overwrite, include_mipmaps=include_mipmaps,
            )


def compile_textures(
        data_dir,
        force_recompile=False, optimize_format=False, parallel_processing=False,
        target_ps2=False, target_ngc=False, target_xbox=False,
        target_dreamcast=False, target_arcade=False
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

    cache_type = (
        c.TEXTURE_CACHE_EXTENSION_PS2  if target_ps2 else
        c.TEXTURE_CACHE_EXTENSION_NGC  if target_ngc else
        c.TEXTURE_CACHE_EXTENSION_DC   if target_dreamcast else
        c.TEXTURE_CACHE_EXTENSION_ARC  if target_arcade else
        c.TEXTURE_CACHE_EXTENSION_XBOX if target_xbox else
        None
        )
    if cache_type is None:
        raise ValueError("No target platform specified")

    for name in sorted(all_assets):
        meta = bitmap_metadata.get(name)
        if not meta:
            # texture isn't listed in metadata. don't compile it
            continue

        try:
            asset_filepath = all_assets[name]

            rel_filepath = os.path.relpath(asset_filepath, asset_folder)
            filename, asset_type = os.path.splitext(rel_filepath)[0]
            cache_filepath = os.path.join(cache_path_base, "%s.%s" % (filename, cache_type))

            if not force_recompile and os.path.isfile(cache_filepath):
                if verify_source_file_asset_checksum(asset_filepath, cache_filepath):
                    # original asset file; don't recompile
                    continue

            target_format = meta.get("format", c.DEFAULT_FORMAT_NAME)
            has_alpha     = meta.get("flags", {}).get("has_alpha")
            new_format    = texture_util.retarget_format_to_platform(
                target_format, cache_type, has_alpha
                )

            if new_format != target_format:
                print(f"Retargeting {filename} from '{target_format}' to '{new_format}' to match platform.")
                target_format = new_format

            all_job_args.append(dict(
                asset_filepath=asset_filepath, cache_filepath=cache_filepath,
                optimize_format=optimize_format, name=name, target_format_name=target_format,
                mipmap_count=meta.get("mipmap_count", 0),
                keep_alpha=(has_alpha or "A" in target_format),
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
        target_dreamcast=False, target_arcade=False
        ):
    # locate and load all assets
    texture_caches_by_name = {}
    all_asset_filepaths = util.locate_textures(
        os.path.join(data_dir, c.IMPORT_FOLDERNAME, c.TEX_FOLDERNAME),
        cache_files=True, target_ngc=target_ngc,
        target_xbox=target_xbox, target_arcade=target_arcade
        )

    for name in sorted(all_asset_filepaths):
        try:
            with open(all_asset_filepaths[name], "rb") as f:
                texture_cache = get_texture_cache_class(f)()
                texture_cache.parse(f, pixel_interop_edits=False)
                texture_caches_by_name[name] = texture_cache
        except Exception:
            print(format_exc())
            print("Could not load texture:\n    %s" % all_asset_filepaths[name])

    bitmaps     = objects_tag.data.bitmaps
    bitmap_defs = objects_tag.data.bitmap_defs
    del bitmaps[:]
    del bitmap_defs[:]

    bitmap_parse_case = (
        "dreamcast" if target_dreamcast else
        "arcade"    if target_arcade    else
        None
        )

    # get the metadata for all bitmaps to import
    all_metadata = objects_metadata.compile_objects_metadata(
        data_dir, by_asset_name=not use_force_index_hack
        )

    # for returning to the caller for easy iteration
    texture_datas = []

    # we'll be saving all filenames to the texdef_names in the objects_tag.
    # this is so the model compilation can find the textures referenced, even
    # if the names aren't saved to the tag itself.
    objects_tag.texdef_names = {}

    if use_force_index_hack and all_metadata:  # hack
        max_forced_bitmap_index = max(
            meta.get("force_index", -1) for meta in all_metadata["bitmaps"]
            )
        bitmaps.extend(1 + max_forced_bitmap_index, case=bitmap_parse_case)
        all_metadata = dict(combined=all_metadata)

    # for inserting the metadata into the objects tag in the correct order
    sorted_bitm_meta = [None] * len(bitmaps)
    texture_caches   = [None] * len(bitmaps)

    for type_asset_name in sorted(all_metadata):
        # type_asset_name will look like 'bitmaps_AAAWHITE', and we
        # only want the 'AAAWHITE' part. split it and unify the case
        frames_metadata = all_metadata[type_asset_name].get("bitmaps", ())

        asset_name = type_asset_name.split('_', 1)[-1].upper()
        initial_frame = not use_force_index_hack

        for i, meta in enumerate(frames_metadata):
            texture_cache = texture_caches_by_name.get(meta["name"])

            # NOTE: force_index is a hack until animation decomp is a thing
            bitm_index = meta.get("force_index", -1) if use_force_index_hack else -1
            if bitm_index not in range(len(bitmaps)):
                bitmaps.append(case=bitmap_parse_case)
                texture_caches.append(None)
                sorted_bitm_meta.append(None)
                bitm_index = len(bitmaps) - 1

            if i == 0:
                meta["frame_count"] = max(0, len(frames_metadata) - 1)

            sorted_bitm_meta[bitm_index] = meta
            texture_caches[bitm_index]   = texture_cache

    tex_pointer = 0

    # loop over the bitmaps in the order they need to be compiled
    # into the cache file, set the pointers for the texture data,
    # and import the rest of the bitmap metadata(w/h, mips, etc).
    for i in range(len(sorted_bitm_meta)):
        bitm          = bitmaps[i]
        meta          = sorted_bitm_meta[i]
        texture_cache = texture_caches[i]
        texture_data  = b''
        if texture_cache:
            texture_data = texture_cache.serialize(pixel_interop_edits=False)

        texture_datas.append(texture_data)
        if not meta:
            continue

        bitm.frame_count = meta.get("frame_count", 0)
        bitm.tex_pointer = tex_pointer

        if not bitm.frame_count:
            # the only names stored to the texdef names are the non-sequence bitmaps
            objects_tag.texdef_names[tex_pointer] = meta["name"]

        flags = bitm.flags
        is_invalid  = bool(getattr(flags, "invalid"))
        is_external = bool(getattr(flags, "external"))

        if target_ngc:
            mipmap_count = meta.get("mipmap_count", 0)
        else:
            mipmap_count = max(0, len(texture_cache.textures) - 1) if texture_cache else 0

        if bitm.frame_count or is_external or is_invalid:
            # no bitmap to import; only import metadata
            try:
                bitm.format.set_to(meta["format"])
            except Exception:
                print(format_exc())
                print("Warning: Could not set bitmap format.")

            if hasattr(bitm, "lod_k"): # v4 and higher
                bitm.mipmap_count = meta.get("mipmap_count", 0)
                bitm.lod_k        = meta.get("lod_k", c.DEFAULT_TEX_LOD_K)

            if hasattr(bitm, "tex_palette_index"): # v12 and higher
                bitm.tex_palette_index = meta.get("tex_palette_index", 0)
                bitm.tex_palette_count = meta.get("tex_palette_count", 0)
                bitm.tex_shift_index   = meta.get("tex_shift_index", 0)

            flags.data       = 0
            bitm.width       = meta.get("width", 0)
            bitm.height      = meta.get("height", 0)
            bitm.frame_count = meta.get("frame_count", bitm.frame_count)

        elif texture_cache:
            # there is actually a texture to import
            tex_pointer += len(texture_data)

            bitm.format.set_to(texture_cache.format_id)
            bitm.width  = texture_cache.width
            bitm.height = texture_cache.height

            if target_dreamcast:
                bitm.size = len(texture_data)
            elif target_arcade:
                bitm.ncc_table_data = texture_cache.ncc_table.export_to_rawdata()
            elif hasattr(bitm, "lod_k"): # v4 and higher
                bitm.mipmap_count = mipmap_count
                bitm.lod_k        = meta.get("lod_k", texture_cache.lod_k)
                flags.has_alpha   = texture_cache.has_alpha or "A" in texture_cache.format_name

        else:
            print("Warning: Could not locate bitmap file for '%s'" % asset_name)

        # copy flags from metadata
        for flag_name in meta.get("flags", {}):
            if hasattr(flags, flag_name):
                setattr(flags, flag_name, meta["flags"][flag_name])

        if target_arcade:
            # values range from 0 to 8, and they are tied to the log2 of the width or height(whichever
            # is largest). for 256, the log is 8, and for 1 the log is 0. so do 8 - log2(w_or_h)
            bitm.large_lod_log2_inv = 8 - int(math.log(max(bitm.width, bitm.height, 1), 2))
            bitm.small_lod_log2_inv = bitm.large_lod_log2_inv + mipmap_count
        elif target_dreamcast:
            if texture_cache.large_vq:
                image_type = "large_vq"
            elif texture_cache.small_vq:
                image_type = "small_vq"
            elif bitm.width == bitm.height:
                image_type = "square"
            else:
                image_type = "rectangle"

            if texture_cache.twiddled:
                image_type += "_twiddled"

            if texture_cache.mipmaps and bitm.width == bitm.height:
                # only square textures can be mipmapped
                image_type += "_mipmap"

            bitm.image_type.set_to(image_type)
            bitm.dc_unknown = meta.get("dc_unknown", 0)
        else:
            # do max with 1 to make sure we dont try to do log(0, 2)
            bitm.log2_of_width  = int(math.log(max(bitm.width, 1), 2))
            bitm.log2_of_height = int(math.log(max(bitm.height, 1), 2))
            bitm.width_64       = max(1, (bitm.width + 63) // 64)

        if is_external or meta.get("cache_name"):
            # create a bitmap def
            bitmap_defs.append()
            bitmap_defs[-1].name = meta["name"][:30]
            bitmap_defs[-1].width = bitm.width
            bitmap_defs[-1].height = bitm.height
            bitmap_defs[-1].tex_index = i

        if is_external or is_invalid or target_arcade or target_dreamcast:
            continue

        # populate tex0 and miptbp
        format_name = bitm.format.enum_name
        bitm.tex0.tex_width  = bitm.log2_of_width
        bitm.tex0.tex_height = bitm.log2_of_height
        bitm.tex0.psm.set_to(
            c.PSM_T8   if "IDX_8" in format_name else
            c.PSM_T4   if "IDX_4" in format_name else
            c.PSM_CT16 if "1555"  in format_name else
            c.PSM_CT32 if "8888"  in format_name else
            c.PSM_CT32 # should never hit this
            )
        bitm.tex0.tex_cc.set_to(
            meta.get("tex_cc", "rgba")
            )
        bitm.tex0.clut_pixmode.set_to(
            c.PSM_CT16 if "1555_IDX" in format_name else c.PSM_CT32
            )
        bitm.tex0.tex_function.set_to(
            meta.get("tex_function", "decal")
            )
        bitm.tex0.clut_smode.set_to(
            meta.get("clut_smode", "csm1")
            )
        bitm.tex0.clut_loadmode.set_to(
            meta.get("clut_loadmode", "recache")
            )

        buffer_calc = texture_buffer_packer.TextureBufferPacker(
            width=bitm.width, height=bitm.height,
            mipmaps=bitm.mipmap_count,
            pixel_format=bitm.tex0.psm.enum_name,
            palette_format=(
                None if format_name in c.MONOCHROME_FORMATS else
                bitm.tex0.clut_pixmode.enum_name
                ),
            )
        buffer_calc.pack()

        bitm.size         = buffer_calc.block_count
        bitm.tex0.cb_addr = buffer_calc.palette_address

        bitm.tex0.tb_addr, bitm.tex0.tb_width = buffer_calc.get_address_and_width(0)
        for m in range(1, 7):
            tb_addr, tb_width = buffer_calc.get_address_and_width(m)
            bitm.mip_tbp["tb_addr%s"  % m] = tb_addr
            bitm.mip_tbp["tb_width%s" % m] = tb_width

    return texture_datas


def decompile_textures(
        data_dir, objects_tag=None, texdef_tag=None,
        asset_types=c.TEXTURE_CACHE_EXTENSIONS,
        parallel_processing=False, overwrite=False, mipmaps=False
        ):
    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    for asset_type in asset_types:
        if asset_type not in (*c.TEXTURE_CACHE_EXTENSIONS, *c.TEXTURE_ASSET_EXTENSIONS):
            raise ValueError(f"Unknown texture type '{asset_type}'")

    assets_dir = os.path.join(data_dir, c.EXPORT_FOLDERNAME, c.TEX_FOLDERNAME)
    cache_dir  = os.path.join(data_dir, c.IMPORT_FOLDERNAME, c.TEX_FOLDERNAME)
    if objects_tag:
        tag_dir          = os.path.dirname(objects_tag.filepath)
        textures_ext     = os.path.splitext(objects_tag.filepath)[-1].strip(".")
        bitmaps          = objects_tag.data.bitmaps
        _, bitmap_assets = objects_tag.get_cache_names()
    elif texdef_tag:
        tag_dir       = os.path.dirname(texdef_tag.filepath)
        textures_ext  = os.path.splitext(texdef_tag.filepath)[-1].strip(".")
        bitmaps       = texdef_tag.data.bitmaps
        bitmap_assets = texdef_tag.get_bitmap_names()
    else:
        textures_ext = tag_dir = ""

    textures_filepath = os.path.join(
        tag_dir, "%s.%s" % (c.TEXTURES_FILENAME, textures_ext)
        )

    if not os.path.isfile(textures_filepath):
        print("No textures cache to extract from.")
        return

    is_ngc = (textures_ext.lower() == c.NGC_EXTENSION.lower())
    is_arc = is_dc = False
    if textures_ext.lower() == c.ARC_EXTENSION.lower():
        is_dc  = util.is_dreamcast_bitmaps(bitmaps)
        is_arc = not is_dc

    all_job_args = []
    textures_file = open(textures_filepath, "rb")
    try:
        for i in range(len(bitmaps)):
            bitm  = bitmaps[i]
            asset = bitmap_assets.get(i)

            try:
                if (getattr(bitm, "frame_count", 0) or asset is None or
                    getattr(bitm.flags, "external", False) or
                    getattr(bitm.flags, "invalid", False)):
                    continue
                elif bitm.format.enum_name == "<INVALID>":
                    print("Invalid bitmap format detected in bitmap %s at index %s" % (asset, i))
                    continue

                for asset_type in asset_types:
                    filename = f"{asset['name']}.{asset_type}"
                    if asset['name'] != asset["asset_name"]:
                        filename = os.path.join(asset["asset_name"], filename)

                    filepath = os.path.join(
                        cache_dir if asset_type in c.TEXTURE_CACHE_EXTENSIONS else assets_dir,
                        filename
                        )
                    if os.path.isfile(filepath) and not overwrite:
                        continue

                    # create and populate texture cache
                    if is_arc:
                        texture_cache           = ArcadeTextureCache()
                        texture_cache.mipmaps   = bitm.small_lod_log2_inv - bitm.large_lod_log2_inv
                        if "YIQ" in bitm.format.enum_name:
                            texture_cache.ncc_table = ncc.NccTable()
                            texture_cache.ncc_table.import_from_rawdata(bitm.ncc_table_data)
                    elif is_dc:
                        texture_cache           = DreamcastTextureCache()
                        texture_cache.large_vq  = "large_vq" in bitm.image_type
                        texture_cache.small_vq  = "small_vq" in bitm.image_type
                        texture_cache.twiddled  = "twiddled" in bitm.image_type
                        texture_cache.mipmaps   = "mipmap" in bitm.image_type
                    elif is_ngc:
                        texture_cache           = GamecubeTextureCache()
                        texture_cache.lod_k     = bitm.lod_k
                        # regardless of what the objects says, gamecube doesnt contain mipmaps
                        texture_cache.mipmaps   = 0
                    else:
                        texture_cache = (
                            get_texture_cache_class_from_cache_type(asset_type)
                            if asset_type in c.TEXTURE_CACHE_EXTENSIONS else
                            Ps2TextureCache
                            )()
                        texture_cache.lod_k     = bitm.lod_k
                        texture_cache.mipmaps   = bitm.mipmap_count

                    texture_cache.has_alpha     = bool(getattr(bitm.flags, "has_alpha", False))
                    texture_cache.format_id     = bitm.format.data
                    texture_cache.width         = bitm.width
                    texture_cache.height        = bitm.height

                    # read texture data
                    textures_file.seek(bitm.tex_pointer)
                    texture_cache.parse_palette(textures_file)
                    texture_cache.parse_textures(textures_file)

                    all_job_args.append(dict(
                        name=asset["name"], asset_type=asset_type,
                        filepath=filepath, overwrite=overwrite,
                        include_mipmaps=mipmaps, texture_cache=texture_cache
                        ))
            except:
                print(format_exc())
                print(('The above error occurred while trying to export bitmap %s as %s. '
                       "name: '%s', asset_name: '%s'") %
                      (i, asset_type, asset.get("name"), asset.get("asset_name"))
                      )
    finally:
        textures_file.close()        

    print("Decompiling %s textures in %s" % (
        len(all_job_args), "parallel" if parallel_processing else "series"
        ))
    util.process_jobs(
        _decompile_texture, all_job_args,
        process_count=None if parallel_processing else 1
        )
