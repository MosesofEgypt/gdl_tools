import math
import pathlib

from traceback import format_exc
from ..metadata import util as metadata_util
from .serialization.asset_cache import get_asset_checksum
from .serialization.texture import G3DTexture
from .serialization.texture_cache import TextureCache, Ps2TextureCache,\
     GamecubeTextureCache, DreamcastTextureCache, ArcadeTextureCache
from .serialization import texture_util, ncc
from . import constants as c
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


def import_texture(bitmap_block, metadata, texture_cache):
    meta, bitm   = metadata, bitmap_block
    name, flags  = meta.get("name", "<UNNAMED>"), bitm.flags
    is_invalid   = bool(meta.get("flags", {}).get("invalid"))
    is_external  = bool(meta.get("flags", {}).get("external"))
    is_animation = "frames" in meta

    texture_data  = b''
    if texture_cache:
        texture_data = texture_cache.serialize(pixel_interop_edits=False)

    if not meta:
        return texture_data

    if hasattr(flags, "animation"):
        flags.animation = is_animation

    bitm.frame_count = len(meta.get("frames", ()))
    if isinstance(texture_cache, GamecubeTextureCache):
        # gamecube autogenerates mipmaps at runtime
        mipmap_count = meta.get("mipmap_count", 0)
    else:
        mipmap_count = max(0, len(texture_cache.textures) - 1) if texture_cache else 0

    if is_animation or is_external or is_invalid:
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

        flags.data  = 0
        bitm.width  = meta.get("width", 0)
        bitm.height = meta.get("height", 0)

    elif texture_cache:
        # there is actually a texture to import
        tex_pointer += len(texture_data)

        bitm.format.data = texture_cache.format_id
        bitm.width       = texture_cache.width
        bitm.height      = texture_cache.height

        if target_dreamcast:
            bitm.size = len(texture_data)
        elif target_arcade:
            bitm.ncc_table_data = texture_cache.ncc_table.export_to_rawdata()
        elif hasattr(bitm, "lod_k"): # v4 and higher
            bitm.mipmap_count = mipmap_count
            bitm.lod_k        = meta.get("lod_k", c.DEFAULT_TEX_LOD_K)
            flags.has_alpha   = texture_cache.has_alpha or "A" in texture_cache.format_name

    else:
        print(f"Warning: Could not locate bitmap file for '{name}'")

    # copy flags from metadata
    for flag_name in meta.get("flags", {}):
        if hasattr(flags, flag_name):
            setattr(flags, flag_name, meta["flags"][flag_name])

    if hasattr(bitm, "large_lod_log2_inv"):
        # values range from 0 to 8, and they are tied to the log2 of the width or height(whichever
        # is largest). for 256, the log is 8, and for 1 the log is 0. so do 8 - log2(w_or_h)
        bitm.large_lod_log2_inv = 8 - int(math.log(max(bitm.width, bitm.height, 1), 2))
        bitm.small_lod_log2_inv = bitm.large_lod_log2_inv + mipmap_count
    elif hasattr(bitm, "image_type"):
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

    if not(is_animation or (bitm.width and bitm.height)):
        # texture size is zero(missing bitmap?).
        # set invalid flag and be done with it.
        if hasattr(flags, "invalid"):
            flags.invalid = True

    if hasattr(bitm, "tex0"):
        tex0 = bitm.tex0
        tex0.tex_cc.set_to(meta.get("tex_cc", "rgba"))
        tex0.tex_function.set_to(meta.get("tex_function", "decal"))
        tex0.clut_smode.set_to(meta.get("clut_smode", "csm1"))
        tex0.clut_loadmode.set_to(meta.get("clut_loadmode", "recache"))
        tex0.clut_pixmode.set_to(
            c.PSM_CT16 if "1555_IDX" in bitm.format.enum_name else c.PSM_CT32
            )

    return texture_data


def import_textures(
        objects_tag, target_ngc=False, target_ps2=False,
        target_xbox=False, target_dreamcast=False, target_arcade=False,
        data_dir=".", cache_dir=None
        ):
    if not cache_dir:
        cache_dir = pathlib.Path(data_dir).joinpath(c.IMPORT_FOLDERNAME)

    # locate all assets
    all_asset_filepaths = util.locate_textures(
        cache_dir, cache_files=True, target_ngc=target_ngc,
        target_xbox=target_xbox, target_ps2=target_ps2,
        target_dreamcast=target_dreamcast, target_arcade=target_arcade,
        )

    bitmaps     = objects_tag.data.bitmaps
    bitmap_defs = objects_tag.data.bitmap_defs
    del bitmaps[:]
    del bitmap_defs[:]

    # we'll be saving all filenames to the texdef_names in the objects_tag.
    # this is so the model compilation can find the textures referenced, even
    # if the names aren't saved to the tag itself.
    objects_tag.texdef_names = {}

    # get the metadata for all bitmaps to import
    all_metadata    = metadata_util.compile_metadata(cache_dir, True)
    all_bitm_meta   = all_metadata.get("bitmaps", {})
    all_texmod_meta = all_metadata.get("texmods", {})

    # for returning to the caller for easy iteration
    texture_datas = []

    # tracks the next free pointer in the textures.rom
    tex_pointer = 0

    # for texmods that specify another texmod as the source of the
    # frames, we copy those frames into the referencing texmod bitmap
    for name, meta in all_texmod_meta.items():
        src_name = meta.get("source_name")
        if name in all_bitm_meta and "frames" in all_bitm_meta.get(src_name, {}):
            all_bitm_meta[name]["frames"] = all_bitm_meta[src_name]["frames"]

    # copy animation metadata into frames, and insert frames into
    # the all_metadata dict for simple iteration over everything.
    for name, meta in tuple(all_bitm_meta.items()):
        frames = meta.get("frames")
        if frames is None:
            continue

        template = dict(meta)
        for k in ("frames", "cache_name", "standalone"):
            template.pop(k, None)

        # NOTE: doing this sorted so we can set "cache_name" on the first one
        for i, frame_name in enumerate(sorted(frames)):
            # NOTE: using setdefault in case another texmod uses a frame within
            #       this sequence as the start frame and needs its name cached.
            all_bitm_meta.setdefault(frame_name, dict(template))
            all_bitm_meta[frame_name].update(frames[frame_name])
            if i == 0:
                all_bitm_meta[frame_name].update(cache_name=True)

    # loop over the bitmaps in the order they need to be compiled
    # into the cache file, set the pointers for the texture data,
    # and import the rest of the bitmap metadata(w/h, mips, etc).
    for name in sorted(all_bitm_meta):
        trimmed_name    = name[:30]
        bitm_index      = len(bitmaps)
        meta            = all_bitm_meta[name]
        asset_filepath  = all_asset_filepaths.get(name)

        if "frames" in meta:
            # animation bitmap, so no asset cache expected
            texture_cache = None
        elif asset_filepath:
            try:
                with open(asset_filepath, "rb") as f:
                    texture_cache = TextureCache.get_cache_class(f)()
                    texture_cache.parse(f, pixel_interop_edits=False)
            except Exception:
                print(format_exc())
                print(f"Error: Could not load asset cache '{asset_filepath}'")
                continue
        else:
            print(f"Warning: Could not locate asset cache for bitmap '{name}'. Skipping.")
            continue

        try:
            bitmaps.append(case=(
                "dreamcast" if target_dreamcast else
                "arcade"    if target_arcade    else
                None
                ))
            bitm = bitmaps[bitm_index]
            bitm.tex_pointer = tex_pointer

            texture_data = import_texture(bitm, meta, texture_cache)
            texture_datas.append(texture_data)

            if "frames" not in meta:
                # the only names stored to the texdef names are the non-sequence bitmaps
                objects_tag.texdef_names[tex_pointer] = trimmed_name

            if meta.get("cache_name") or getattr(bitm.flags, "external", 0):
                bitmap_defs.append()
                bitmap_def           = bitmap_defs[-1]
                bitmap_def.name      = trimmed_name
                bitmap_def.width     = bitm.width
                bitmap_def.height    = bitm.height
                bitmap_def.tex_index = bitm_index

            tex_pointer += len(texture_data)

        except Exception:
            print(format_exc())
            print(f"Error occurred while processing bitmap '{name}' at index {bitm_index}.")
            continue

    # TODO: copy dimensions from first sequence bitmap into anim bitmaps

    # populate tex0 and miptbp
    objects_tag.calculate_tex0_and_mip_tbp()

    return texture_datas


def export_textures(
        objects_tag=None, texdef_tag=None,
        asset_types=c.TEXTURE_CACHE_EXTENSIONS, textures_filepath="",
        parallel_processing=False, overwrite=False, mipmaps=False,
        data_dir=".", assets_dir=None, cache_dir=None,
        ):
    data_dir = pathlib.Path(data_dir)
    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    for asset_type in asset_types:
        if asset_type not in (*c.TEXTURE_CACHE_EXTENSIONS, *c.TEXTURE_ASSET_EXTENSIONS):
            raise ValueError(f"Unknown texture type '{asset_type}'")

    if not assets_dir: assets_dir  = data_dir
    if not cache_dir:  cache_dir   = data_dir.joinpath(c.IMPORT_FOLDERNAME)

    if objects_tag:
        tag_dir         = pathlib.Path(objects_tag.filepath).parent
        bitmaps         = objects_tag.data.bitmaps
        objects         = objects_tag.data.objects
        bitmap_assets   = objects_tag.get_cache_names()[1]
        obj_ver  = objects_tag.data.version_header.version.enum_name
    elif texdef_tag:
        tag_dir         = pathlib.Path(texdef_tag.filepath).parent
        bitmaps         = texdef_tag.data.bitmaps
        objects         = ()
        bitmap_assets   = texdef_tag.get_bitmap_names()
        obj_ver  = ""
    else:
        raise ValueError("Must supply either texdef tag or objects tag.")

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
        bitmap_blocks = {i: b for i, b in enumerate(bitmaps)}
        for i, obj in enumerate(objects):
            if obj_ver not in ("v0", "v1"):
                break

            try:
                lm_header = getattr(obj.model_data, "lightmap_header", None)
                if (obj_ver == "v1" or (
                    getattr(lm_header, "dc_lm_sig1", None) == c.DC_LM_HEADER_SIG1 and
                    getattr(lm_header, "dc_lm_sig2", None) == c.DC_LM_HEADER_SIG2
                    )):
                    # NOTE: we use negative indices in the bitmap_assets to indicate
                    #       that the name was taken from a dreamcast lightmap, and
                    #       doesn't actually have a bitmap block tied to this bitmap.
                    bitmap_blocks[-(i+1)] = lm_header
            except Exception:
                continue

        for i in sorted(bitmap_blocks.keys()):
            asset = bitmap_assets.get(i)
            bitm  = bitmap_blocks[i]

            try:
                flags = getattr(bitm, "flags", None)
                if (getattr(bitm, "frame_count", 0) or asset is None or
                    getattr(flags, "external", False) or
                    getattr(flags, "invalid", False)):
                    continue
                elif hasattr(bitm, "format") and bitm.format.enum_name == "<INVALID>":
                    print(f"Invalid bitmap format detected in bitmap {asset} at index {i}")
                    continue

                for asset_type in asset_types:
                    filename = f"{asset['name']}.{asset_type}"
                    if asset['name'] != asset["asset_name"]:
                        filename = pathlib.PurePath(asset["asset_name"], filename)

                    filepath = pathlib.Path(
                        cache_dir if asset_type in c.TEXTURE_CACHE_EXTENSIONS else assets_dir,
                        asset.get("actor", "_bitmaps"), filename
                        )
                    if filepath.is_file() and not overwrite:
                        continue

                    # create and populate texture cache
                    texture_cache = bitmap_to_texture_cache(
                        bitm, textures_file, is_ngc=is_ngc, cache_type=asset_type
                        )
                    if texture_cache:
                        all_job_args.append(dict(
                            name=asset["name"], asset_type=asset_type,
                            filepath=filepath, overwrite=overwrite,
                            include_mipmaps=mipmaps, texture_cache=texture_cache
                            ))
            except:
                print(format_exc())
                print(f"The above error occurred while trying to export bitmap {i} as {asset_type}. "
                      f"name: '{asset.get('name')}', asset_name: '{asset.get('asset_name')}'"
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


def bitmap_to_texture_cache(bitmap_or_lm_block, textures_file, is_ngc=False, cache_type=None):
    is_arcade   = is_dreamcast_lm = is_dreamcast = False
    is_ps2_xbox = hasattr(bitmap_or_lm_block, "lod_k") and not is_ngc
    if not is_ps2_xbox and not is_ngc:
        is_dreamcast_lm = hasattr(bitmap_or_lm_block, "dc_lm_sig1")
        is_dreamcast    = hasattr(bitmap_or_lm_block, "image_type")
        is_arcade       = not (is_dreamcast_lm or is_dreamcast)

    if cache_type in c.TEXTURE_CACHE_EXTENSIONS:
        if is_ps2_xbox and cache_type not in (
                c.TEXTURE_CACHE_EXTENSION_PS2, c.TEXTURE_CACHE_EXTENSION_XBOX
                ):
            print("Cannot export PS2/XBOX texture to non-PS2/XBOX cache file.")
            return
        elif is_ngc and cache_type != c.TEXTURE_CACHE_EXTENSION_NGC:
            print("Cannot export Gamecube texture to non-Gamecube cache file.")
            return
        elif (is_dreamcast or is_dreamcast_lm) and cache_type != c.TEXTURE_CACHE_EXTENSION_DC:
            print("Cannot export Dreamcast texture to non-Dreamcast cache file.")
            return
        elif is_arcade and cache_type != c.TEXTURE_CACHE_EXTENSION_ARC:
            print("Cannot export Arcade texture to non-Arcade cache file.")
            return

    flags = getattr(bitmap_or_lm_block, "flags", None)
    # create and populate texture cache
    if is_arcade:
        texture_cache           = ArcadeTextureCache()
        texture_cache.mipmaps   = (bitmap_or_lm_block.small_lod_log2_inv -
                                   bitmap_or_lm_block.large_lod_log2_inv)
        texture_cache.format_id = bitmap_or_lm_block.format.data
        if "YIQ" in bitmap_or_lm_block.format.enum_name:
            texture_cache.ncc_table = ncc.NccTable()
            texture_cache.ncc_table.import_from_rawdata(bitmap_or_lm_block.ncc_table_data)
    elif is_dreamcast_lm:
        texture_cache           = DreamcastTextureCache()
        # the dreamcast v0 files have what appear to be broken lightmap data
        # structures that don't seem to contain all the data we would expect,
        # OR the expected data is supposed to be hardcoded like we're doing.
        texture_cache.width     = 256
        texture_cache.height    = 256
        texture_cache.format_id = 1 # R5G6B5
    elif is_dreamcast:
        texture_cache           = DreamcastTextureCache()
        image_type              = bitmap_or_lm_block.image_type.enum_name
        texture_cache.large_vq  = "large_vq" in image_type
        texture_cache.small_vq  = "small_vq" in image_type
        texture_cache.twiddled  = "twiddled" in image_type
        texture_cache.mipmaps   = "mipmap" in image_type
        texture_cache.format_id = bitmap_or_lm_block.format.data
    elif is_ngc:
        texture_cache           = GamecubeTextureCache()
        # regardless of what the objects says, gamecube doesnt contain mipmaps
        texture_cache.mipmaps   = 0
        texture_cache.format_id = bitmap_or_lm_block.format.data
    elif is_ps2_xbox:
        texture_cache = (
            TextureCache.get_cache_class_from_cache_type(cache_type)
            if cache_type in c.TEXTURE_CACHE_EXTENSIONS else
            Ps2TextureCache
            )()
        texture_cache.lod_k     = bitmap_or_lm_block.lod_k
        texture_cache.mipmaps   = bitmap_or_lm_block.mipmap_count
        # NOTE: we're doing enum_name here instead of using the integer enum
        #       because the v4 bitmap format is has a different mapping
        texture_cache.format_name   = bitmap_or_lm_block.format.enum_name
    else:
        raise ValueError("Cannot determine bitmap block type.")

    if not is_dreamcast_lm:
        # read the note above about dreamcast lightmaps
        texture_cache.width         = bitmap_or_lm_block.width
        texture_cache.height        = bitmap_or_lm_block.height

    texture_cache.has_alpha     = (bool(getattr(flags, "has_alpha", False)) or
                                   "A" in texture_cache.format_name)
    texture_cache.is_extracted  = True

    # read texture data
    textures_file.seek(bitmap_or_lm_block.tex_pointer)
    texture_cache.parse_palette(textures_file)
    texture_cache.parse_textures(textures_file)

    return texture_cache
