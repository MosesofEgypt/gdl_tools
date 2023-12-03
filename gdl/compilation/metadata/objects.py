from . import constants as c
from . import util


def compile_objects_metadata(data_dir=".", cache_files=False):
    return util.compile_metadata(data_dir=data_dir, cache_files=cache_files)


def decompile_objects_metadata(
        objects_tag, anim_tag=None,
        asset_types=c.METADATA_CACHE_EXTENSIONS,
        overwrite=False, data_dir=".", assets_dir=None, cache_dir=None
        ):
    object_assets, bitmap_assets = objects_tag.get_cache_names()
    exported_bitmaps = {bitm.tex_index: True for bitm in objects_tag.data.bitmap_defs}

    # decompile metadata for objects and bitmaps
    objects_metadata = {
        object_assets[i]["name"]: decompile_object_metadata(
            obj,
            asset_name=object_assets[i]["asset_name"],
            actor_name=object_assets[i].get("actor")
            )
        for i, obj in enumerate(objects_tag.data.objects)
        }

    bitmaps_metadata = {
        bitmap_assets[i]["name"]: decompile_bitmap_metadata(
            bitm,
            asset_name=bitmap_assets[i]["asset_name"],
            actor_name=bitmap_assets[i].get("actor"),
            cache_name=(i in exported_bitmaps)
            )
        for i, bitm in enumerate(objects_tag.data.bitmaps)
        }

    # move animation frames into parent and remove duplicate fields
    objects_metadata.update(_consolidate_metadata_frames(objects_metadata, False))
    bitmaps_metadata.update(_consolidate_metadata_frames(bitmaps_metadata, True))

    # filter out objects and bitmaps not assigned to a specific actor
    nonactor_bitmaps_metadata = {
        name: metadata
        for name, metadata in tuple(bitmaps_metadata.items())
        if not metadata.get("actor")
        }
    nonactor_objects_metadata = {
        name: metadata
        for name, metadata in tuple(objects_metadata.items())
        if not metadata.get("actor")
        }

    # sort remaining objects and bitmaps by what actor they're assigned to
    actor_bitmaps_metadata = {}
    for name, metadata in bitmaps_metadata.items():
        actor = metadata.pop("actor", None)
        if actor:
            actor_bitmaps_metadata.setdefault(actor, {})[name] = metadata

    actor_objects_metadata = {}
    for name, metadata in objects_metadata.items():
        actor = metadata.pop("actor", None)
        if actor:
            actor_objects_metadata.setdefault(actor, {})[name] = metadata

    # remove actor field from all metadata frames
    for metadata in (*objects_metadata.values(), *bitmaps_metadata.values()):
        for frame_metadata in metadata.get("frames", {}).values():
            frame_metadata.pop("actor", None)

    metadata_sets = {
        "_objects/_objects": dict(objects = nonactor_objects_metadata),
        "_bitmaps/_bitmaps": dict(bitmaps = nonactor_bitmaps_metadata),
        **{
            f"{actor_name}/{actor_name}_objects": dict(
                objects = actor_objects_metadata[actor_name]
                )
            for actor_name in sorted(actor_objects_metadata)
            },
        **{
            f"{actor_name}/{actor_name}_bitmaps": dict(
                bitmaps = actor_bitmaps_metadata[actor_name]
                )
            for actor_name in sorted(actor_bitmaps_metadata)
            }
        }
    util.dump_metadata_sets(
        metadata_sets, asset_types=asset_types, overwrite=overwrite,
        data_dir=data_dir, assets_dir=assets_dir, cache_dir=cache_dir,
        )


def decompile_object_metadata(obj, asset_name=None, actor_name=None):
    metadata_obj = dict(
        flags    = {},
        )

    if asset_name: metadata_obj.update(asset_name = asset_name)
    if actor_name: metadata_obj.update(actor = actor_name)

    if hasattr(obj, "lods"):
        obj_flags = obj.lods[0].flags
    else:
        obj_flags = getattr(obj, "flags", None)

    for flag in c.OBJECT_FLAG_NAMES:
        if getattr(obj_flags, flag, False):
            metadata_obj["flags"][flag] = True

    if not metadata_obj["flags"]:
        metadata_obj.pop("flags")

    return metadata_obj


def decompile_bitmap_metadata(bitm, asset_name=None, actor_name=None, cache_name=True):
    metadata_bitm   = dict(
        flags       = {},
        format      = bitm.format.enum_name,
        )

    if asset_name: metadata_bitm.update(asset_name = asset_name)
    if actor_name: metadata_bitm.update(actor = actor_name)

    if bitm.frame_count == 0 and cache_name:
        metadata_bitm.update(cache_name=True)

    if bitm.frame_count > 0:
        metadata_bitm.update(animation=True)
    elif hasattr(bitm, "lod_k"): # v4 and higher
        metadata_bitm.update(mipmap_count=bitm.mipmap_count, lod_k=bitm.lod_k)
    elif hasattr(bitm, "dc_sig"): # dreamcast
        image_type  = bitm.image_type.enum_name
        for name in ("twiddled", "mipmap", "small_vq", "large_vq"):
            if name in image_type:
                metadata_bitm[name] = True
    else:
        metadata_bitm.update(mipmap_count=abs(bitm.small_lod_log2_inv - bitm.large_lod_log2_inv))

    if getattr(bitm.flags, "invalid", False):
        # set to arbitrary valid value(often time set to random garbage)
        metadata_bitm["format"] = "ABGR_1555"

    has_bitm_data = (
        not getattr(bitm.flags, "invalid", False) and
        not getattr(bitm.flags, "external", False) and
        bitm.frame_count <= 0
        )

    if not has_bitm_data and hasattr(bitm, "tex0"):
        for name, default in (
                ("tex_cc", "rgba"),
                ("tex_function", "decal"),
                ("clut_smode", "csm1"),
                ("clut_loadmode", "recache"),
                ):
            if bitm.tex0[name].enum_name != default:
                metadata_bitm[name] = bitm.tex0[name].enum_name

    for flag in c.BITMAP_FLAG_NAMES:
        if getattr(bitm.flags, flag, False):
            metadata_bitm["flags"][flag] = True

    if not metadata_bitm["flags"]:
        metadata_bitm.pop("flags")

    return metadata_bitm


def _consolidate_metadata_frames(metadata, is_bitmaps):
    all_anim_metadata = {}
    is_objects = not is_bitmaps # for clarity

    for name in sorted(metadata):
        metadata_item = metadata[name]
        asset_name    = metadata_item["asset_name"]

        if asset_name not in all_anim_metadata:
            # NOTE: stripping off digits and then preceeding underscore
            #       for object names to match the asset name
            if ((is_objects and name.rstrip("0123456789")[:-1] == asset_name) or
                (is_bitmaps and (name != asset_name or not metadata_item.pop("animation", None)))
                 ):
                metadata.pop(name)
                all_anim_metadata[asset_name] = metadata_item
                if is_objects:
                    metadata_item.update(orig_name=name)
            continue

        anim_metadata = all_anim_metadata[asset_name]
        metadata.pop(name)
        for k in sorted(metadata_item):
            # for the first bitmap frame, copy all fields into the parent metadata.
            # this will allow us to reduce the duplicate fields in the metadata.
            if is_bitmaps and "frames" not in anim_metadata and k not in anim_metadata:
                anim_metadata[k] = metadata_item[k]

            if metadata_item[k] == anim_metadata.get(k):
                metadata_item.pop(k)

        anim_metadata.setdefault("frames", {})[name] = metadata_item

    if is_bitmaps:
        for anim_metadata in all_anim_metadata.values():
            anim_metadata.pop("cache_name", None)
            for frame_metadata in anim_metadata.get("frames", {}).values():
                metadata_item.pop("cache_name", None)
    else:
        metadata.update({
            k: all_anim_metadata.pop(k)
            for k in sorted(all_anim_metadata)
            if "frames" not in all_anim_metadata[k]
            })

    return all_anim_metadata
