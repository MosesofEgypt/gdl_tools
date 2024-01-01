from . import constants as c
from . import util


def decompile_objects_metadata(
        objects_tag, anim_tag=None,
        asset_types=c.METADATA_CACHE_EXTENSIONS,
        overwrite=False, data_dir=".", assets_dir=None, cache_dir=None
        ):
    object_assets, bitmap_assets = objects_tag.get_cache_names()
    exported_bitmaps = {i: True for i in objects_tag.get_bitmap_def_names()}

    # decompile metadata for objects and bitmaps
    objects_metadata = {
        object_assets[i]["name"]: decompile_object_metadata(
            obj,
            asset_name=object_assets[i]["asset_name"],
            actor_name=object_assets[i].get("actor"),
            bitmap_assets=bitmap_assets
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

    # remove actor field from all metadata frames and the
    # asset_name field from metadata where the name matches it
    for key, metadata in (*objects_metadata.items(), *bitmaps_metadata.items()):
        for frame_metadata in metadata.get("frames", {}).values():
            frame_metadata.pop("actor", None)

        if key == metadata.get("asset_name"):
            metadata.pop("asset_name")

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


def decompile_object_metadata(obj, asset_name=None, actor_name=None, bitmap_assets=()):
    metadata_obj = dict(
        flags    = {},
        )
    if asset_name:
        metadata_obj.update(asset_name = asset_name)

    if actor_name:
        metadata_obj.update(actor = actor_name)
    else:
        metadata_obj.update(standalone = True)                

    if hasattr(obj, "lods"):
        obj_flags = obj.lods[0].flags
    else:
        obj_flags = getattr(obj, "flags", None)

    #########################################################
    # this is temporary until lod_k can be implemented in JMS
    if bitmap_assets and hasattr(obj, "sub_object_0"):
        has_lmap = getattr(obj_flags, "lmap", False)
        metadata_obj["lod_coeffs"] = lod_coeffs = {}
        sub_objs = (obj.sub_object_0, *(getattr(obj.data, "sub_objects", ())))
        for i in range(getattr(obj, "sub_objects_count", 1)):
            tex     = bitmap_assets.get(sub_objs[i].tex_index)
            lod_k   = sub_objs[i].lod_k
            if not tex:
                # shit
                continue
            elif not has_lmap:
                lod_coeffs[tex["name"]] = lod_k
            elif lm:
                lod_coeffs.setdefault(tex["name"], {})[lm["name"]] = lod_k
    # this is temporary until lod_k can be implemented in JMS
    #########################################################

    for flag in c.OBJECT_FLAG_NAMES:
        if getattr(obj_flags, flag, False):
            metadata_obj["flags"][flag] = True

    if not metadata_obj["flags"]:
        metadata_obj.pop("flags")

    return metadata_obj


def decompile_bitmap_metadata(bitm, asset_name=None, actor_name=None, cache_name=True):
    metadata_bitm   = dict(
        flags   = {},
        format  = bitm.format.enum_name,
        )

    if asset_name:
        metadata_bitm.update(asset_name = asset_name)

    if actor_name:
        metadata_bitm.update(actor = actor_name)
    else:
        metadata_bitm.update(standalone = True)

    if bitm.frame_count == 0 and cache_name:
        metadata_bitm.update(cache_name=True)

    if bitm.frame_count > 0:
        metadata_bitm.update(animation=True)
    elif hasattr(bitm, "lod_k"): # v4 and higher
        lod_k = bitm.lod_k
        # TEST CODE BASED ON THIS FORMULA
        #   K = -log2( Z0 / h )
        #   1/(2**(-K)) = h   where Z0 is 1
        #lod_ratio = 1/(2**-lod_k)
        metadata_bitm.update(lod_k=lod_k)
        if bitm.mipmap_count:
            metadata_bitm.update(mipmap_count=bitm.mipmap_count)
    elif hasattr(bitm, "dc_sig"): # dreamcast
        image_type  = bitm.image_type.enum_name
        for name in ("twiddled", "mipmap", "small_vq", "large_vq"):
            if name in image_type:
                metadata_bitm[name] = True
    else:
        metadata_bitm.update(mipmap_count=abs(bitm.small_lod_log2_inv -
                                              bitm.large_lod_log2_inv))

    if getattr(bitm.flags, "invalid", False):
        # set to arbitrary valid value(often time set to random garbage)
        metadata_bitm["format"] = "ABGR_1555"

    has_bitm_data = (
        not getattr(bitm.flags, "invalid", False) and
        not getattr(bitm.flags, "external", False) and
        bitm.frame_count <= 0
        )

    if has_bitm_data and hasattr(bitm, "tex0") and (
        bitm.tex0.tex_width != 0 and bitm.tex0.tex_height != 0 
        ):
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

    # setup the parent texture/object animations
    for name in sorted(metadata):
        asset_name = metadata[name]["asset_name"]
        if asset_name in all_anim_metadata:
            continue
        elif ((is_bitmaps and name == asset_name and metadata[name].pop("animation", None)) or
              is_objects
              ):
            metadata_item = all_anim_metadata[asset_name] = metadata.pop(name)
            metadata_item.update(frames=({name: {}} if is_objects else {}))

    for name in sorted(metadata):
        metadata_item = metadata[name]
        asset_name    = metadata_item["asset_name"]
        anim_metadata = all_anim_metadata.get(asset_name)
        if anim_metadata is None:
            continue

        metadata.pop(name)
        frames = anim_metadata["frames"]
        if is_bitmaps and not frames:
            # for the first bitmap frame, copy all fields into the parent metadata.
            # this will allow us to reduce the duplicate fields in the metadata.
            anim_metadata.update(metadata_item)

        frames[name] = metadata_item
        for k in sorted(metadata_item):
            if metadata_item[k] == anim_metadata.get(k):
                metadata_item.pop(k)

    if is_bitmaps:
        for anim_metadata in all_anim_metadata.values():
            anim_metadata.pop("cache_name", None)
            for frame_metadata in anim_metadata.get("frames", {}).values():
                metadata_item.pop("cache_name", None)
    else:
        for k in sorted(all_anim_metadata):
            metadata_item = all_anim_metadata[k]
            if not metadata_item.get("frames") or len(metadata_item.get("frames")) == 1:
                metadata_item.pop("frames", None)
                metadata[k] = all_anim_metadata.pop(k)

    return all_anim_metadata
