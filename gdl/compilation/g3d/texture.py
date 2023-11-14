import math
import pathlib

from traceback import format_exc
from ..metadata import objects as objects_metadata
from .serialization.asset_cache import get_asset_checksum
from .serialization.texture import G3DTexture
from .serialization.texture_cache import TextureCache, Ps2TextureCache,\
     GamecubeTextureCache, DreamcastTextureCache, ArcadeTextureCache
from .serialization import texture_util, ncc
from . import constants as c
from . import texture_buffer_packer
from . import util


def compile_texture(kwargs):
    name            = kwargs.pop("name")
    metadata        = kwargs.pop("metadata")
    cache_type      = kwargs.pop("cache_type")
    cache_filepath  = kwargs.pop("cache_filepath")
    asset_filepath  = kwargs.pop("asset_filepath")

    print("Compiling texture: %s" % name)

    flags           = metadata.get("flags", {})
    target_format   = metadata.get("format", c.DEFAULT_FORMAT_NAME)
    is_dreamcast    = (cache_type == c.TEXTURE_CACHE_EXTENSION_DC)
    has_alpha       = flags.get("has_alpha", False) or "A" in target_format
    new_format      = texture_util.retarget_format_to_platform(
        target_format, cache_type, has_alpha
        )
    if new_format != target_format:
        print(f"Retargeting {asset_filepath} from '{target_format}' to '{new_format}' to match platform.")
        target_format = new_format

    import_kwargs = dict(
        target_format   = target_format,
        mipmap_count    = metadata.get("mipmap_count", 0), 
        has_alpha       = has_alpha,
        keep_alpha      = has_alpha,
        twiddled        = flags.get("twiddled") and is_dreamcast,
        large_vq        = flags.get("large_vq") and is_dreamcast,
        small_vq        = flags.get("small_vq") and is_dreamcast,
        min_dimension   = (1 if is_dreamcast else 8),
        )

    g3d_texture = G3DTexture()
    g3d_texture.import_asset(asset_filepath, **import_kwargs)

    texture_cache = g3d_texture.compile_g3d(cache_type)
    texture_cache.source_asset_checksum = get_asset_checksum(
        filepath=asset_filepath, algorithm=texture_cache.checksum_algorithm
        )
    texture_cache.serialize_to_file(cache_filepath)


def decompile_texture(kwargs):
    name            = kwargs["name"]
    texture_cache   = kwargs["texture_cache"]
    asset_type      = kwargs["asset_type"]
    filepath        = kwargs["filepath"]
    overwrite       = kwargs["overwrite"]
    include_mipmaps = kwargs["include_mipmaps"]

    print("Decompiling texture: %s" % name)

    if asset_type in c.TEXTURE_CACHE_EXTENSIONS:
        texture_cache.serialize_to_file(filepath)
    else:
        g3d_texture = G3DTexture()
        g3d_texture.import_g3d(texture_cache)
        g3d_texture.export_asset(
            filepath, overwrite=overwrite, include_mipmaps=include_mipmaps,
            )


def import_textures(
        objects_tag, data_dir, use_force_index_hack=False,
        target_ngc=False, target_ps2=False, target_xbox=False,
        target_dreamcast=False, target_arcade=False
        ):
    # locate and load all assets
    texture_caches_by_name = {}
    all_asset_filepaths = util.locate_textures(
        pathlib.Path(data_dir, c.IMPORT_FOLDERNAME, c.TEX_FOLDERNAME),
        target_ngc=target_ngc, target_xbox=target_xbox, target_ps2=target_ps2,
        target_dreamcast=target_dreamcast, target_arcade=target_arcade,
        cache_files=True,
        )

    for name in sorted(all_asset_filepaths):
        try:
            with open(all_asset_filepaths[name], "rb") as f:
                texture_cache = TextureCache.get_cache_class(f)()
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
        data_dir, by_asset_name=False
        )

    # for returning to the caller for easy iteration
    texture_datas = []

    # we'll be saving all filenames to the texdef_names in the objects_tag.
    # this is so the model compilation can find the textures referenced, even
    # if the names aren't saved to the tag itself.
    objects_tag.texdef_names = {}

    # for inserting the metadata into the objects tag in the correct order
    sorted_bitm_meta = []
    texture_caches   = []

    for type_asset_name in sorted(all_metadata):
        # type_asset_name will look like 'bitmaps_AAAWHITE', and we
        # only want the 'AAAWHITE' part. split it and unify the case
        frames_metadata = all_metadata[type_asset_name].get("bitmaps", ())

        asset_name = type_asset_name.split('_', 1)[-1].upper()
        initial_frame = True

        for i, meta in enumerate(frames_metadata):
            bitmaps.append(case=bitmap_parse_case)

            texture_caches.append(texture_caches_by_name.get(meta["name"]))
            sorted_bitm_meta.append(meta)

            if i == 0:
                meta["frame_count"] = max(0, len(frames_metadata) - 1)

    tex_pointer = 0

    # loop over the bitmaps in the order they need to be compiled
    # into the cache file, set the pointers for the texture data,
    # and import the rest of the bitmap metadata(w/h, mips, etc).
    for i in range(len(sorted_bitm_meta)):
        bitm    = bitmaps[i]
        meta    = sorted_bitm_meta[i]
        name    = meta.get("name", "<UNNAMED>")[:30]
        try:
            flags = bitm.flags
            is_invalid  = bool(getattr(flags, "invalid"))
            is_external = bool(getattr(flags, "external"))

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
                objects_tag.texdef_names[tex_pointer] = name

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

                bitm.format.data = texture_cache.format_id
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
                print(f"Warning: Could not locate bitmap file for '{name}'")

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
                if bitm.width == bitm.height:
                    # only square textures can be twiddled/vector-compressed/mipmapped
                    image_type = (
                        "large_vq" if texture_cache.large_vq else
                        "small_vq" if texture_cache.small_vq else
                        "square"
                        )
                    image_type += (
                        ""                     if not texture_cache.twiddled else
                        "_twiddled_and_mipmap" if texture_cache.mipmaps else
                        "_twiddled"
                        )
                else:
                    image_type = "rectangle"

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
                bitmap_defs[-1].name   = name
                bitmap_defs[-1].width  = bitm.width
                bitmap_defs[-1].height = bitm.height
                bitmap_defs[-1].tex_index = i

            if not(bitm.width and bitm.height):
                # texture size is zero(missing bitmap?).
                # set invalid flag and be done with it.
                if hasattr(flags, "invalid"):
                    flags.invalid = True

                continue

            if is_external or is_invalid or target_arcade or target_dreamcast:
                continue

            # populate tex0 and miptbp
            format_name             = bitm.format.enum_name
            bitm.tex0.tex_width     = bitm.log2_of_width
            bitm.tex0.tex_height    = bitm.log2_of_height
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

        except Exception:
            print(format_exc())
            print(f"Error occurred while processing bitmap '{name}' at index {i}.")
            continue

    return texture_datas


def export_textures(
        data_dir, objects_tag=None, texdef_tag=None,
        asset_types=c.TEXTURE_CACHE_EXTENSIONS, textures_filepath="",
        parallel_processing=False, overwrite=False, mipmaps=False
        ):
    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    for asset_type in asset_types:
        if asset_type not in (*c.TEXTURE_CACHE_EXTENSIONS, *c.TEXTURE_ASSET_EXTENSIONS):
            raise ValueError(f"Unknown texture type '{asset_type}'")

    assets_dir = pathlib.Path(data_dir, c.EXPORT_FOLDERNAME, c.TEX_FOLDERNAME)
    cache_dir  = pathlib.Path(data_dir, c.IMPORT_FOLDERNAME, c.TEX_FOLDERNAME)
    if objects_tag:
        tag_dir          = pathlib.Path(objects_tag.filepath).parent
        bitmaps          = objects_tag.data.bitmaps
        _, bitmap_assets = objects_tag.get_cache_names()
    elif texdef_tag:
        tag_dir       = pathlib.Path(texdef_tag.filepath).parent
        bitmaps       = texdef_tag.data.bitmaps
        bitmap_assets = texdef_tag.get_bitmap_names()
    else:
        tag_dir = ""

    textures_filepath = pathlib.Path(
        textures_filepath if textures_filepath else
        util.locate_objects_dir_files(tag_dir)['textures_filepath']
        )

    is_ngc = textures_filepath.name.lower().endswith(c.NGC_EXTENSION)
    if not textures_filepath.is_file():
        print("No textures cache to extract from.")
        return

    all_job_args = []
    textures_file = open(textures_filepath, "rb")
    try:
        for i in range(len(bitmaps)):
            asset = bitmap_assets.get(i)
            bitm  = bitmaps[i]

            try:
                if (getattr(bitm, "frame_count", 0) or asset is None or
                    getattr(bitm.flags, "external", False) or
                    getattr(bitm.flags, "invalid", False)):
                    continue
                elif bitm.format.enum_name == "<INVALID>":
                    print(f"Invalid bitmap format detected in bitmap {asset} at index {i}")
                    continue

                for asset_type in asset_types:
                    filename = f"{asset['name']}.{asset_type}"
                    if asset['name'] != asset["asset_name"]:
                        filename = pathlib.PurePath(asset["asset_name"], filename)

                    filepath = pathlib.Path(
                        cache_dir if asset_type in c.TEXTURE_CACHE_EXTENSIONS else assets_dir,
                        filename
                        )
                    if filepath.is_file() and not overwrite:
                        continue

                    # create and populate texture cache
                    texture_cache = bitmap_to_texture_cache(
                        bitm, textures_file, is_ngc=is_ngc, cache_type=asset_type
                        )

                    all_job_args.append(dict(
                        name=asset["name"], asset_type=asset_type,
                        filepath=filepath, overwrite=overwrite,
                        include_mipmaps=mipmaps, texture_cache=texture_cache
                        ))
            except:
                print(format_exc())
                print("The above error occurred while trying to export bitmap {i} as {asset_type}. "
                      "name: '%s', asset_name: '%s'" % (asset.get("name"), asset.get("asset_name"))
                      )
    finally:
        textures_file.close()

    print("Decompiling %s textures in %s" % (
        len(all_job_args), "parallel" if parallel_processing else "series"
        ))
    util.process_jobs(
        decompile_texture, all_job_args,
        process_count=None if parallel_processing else 1
        )


def bitmap_to_texture_cache(bitmap_block, textures_file, is_ngc=False, cache_type=None):
    is_arcade   = is_dreamcast = False
    is_ps2_xbox = hasattr(bitmap_block, "lod_k")
    if not is_ps2_xbox and not is_ngc:
        is_dreamcast = hasattr(bitmap_block, "dc_sig")
        is_arcade    = not is_dreamcast

    # create and populate texture cache
    if is_arcade:
        texture_cache           = ArcadeTextureCache()
        texture_cache.mipmaps   = bitmap_block.small_lod_log2_inv - bitmap_block.large_lod_log2_inv
        if "YIQ" in bitmap_block.format.enum_name:
            texture_cache.ncc_table = ncc.NccTable()
            texture_cache.ncc_table.import_from_rawdata(bitmap_block.ncc_table_data)
    elif is_dreamcast:
        texture_cache           = DreamcastTextureCache()
        image_type              = bitmap_block.image_type.enum_name
        texture_cache.large_vq  = "large_vq" in image_type
        texture_cache.small_vq  = "small_vq" in image_type
        texture_cache.twiddled  = "twiddled" in image_type
        texture_cache.mipmaps   = "mipmap" in image_type
    elif is_ngc:
        texture_cache           = GamecubeTextureCache()
        texture_cache.lod_k     = bitmap_block.lod_k
        # regardless of what the objects says, gamecube doesnt contain mipmaps
        texture_cache.mipmaps   = 0
    elif is_ps2_xbox:
        texture_cache = (
            TextureCache.get_cache_class_from_cache_type(cache_type)
            if cache_type in c.TEXTURE_CACHE_EXTENSIONS else
            Ps2TextureCache
            )()
        texture_cache.lod_k     = bitmap_block.lod_k
        texture_cache.mipmaps   = bitmap_block.mipmap_count
    else:
        raise ValueError("Cannot determine bitmap block type.")

    texture_cache.format_id     = bitmap_block.format.data
    texture_cache.has_alpha     = (bool(getattr(bitmap_block.flags, "has_alpha", False)) or
                                   "A" in texture_cache.format_name)
    texture_cache.width         = bitmap_block.width
    texture_cache.height        = bitmap_block.height
    texture_cache.is_extracted  = True

    # read texture data
    textures_file.seek(bitmap_block.tex_pointer)
    texture_cache.parse_palette(textures_file)
    texture_cache.parse_textures(textures_file)

    return texture_cache
