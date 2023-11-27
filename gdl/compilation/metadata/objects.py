import os

from . import constants as c
from . import util


def compile_objects_metadata(data_dir, by_asset_name=False):
    return util.compile_metadata(data_dir, by_asset_name=by_asset_name)


def decompile_objects_metadata(
        objects_tag, data_dir, anim_tag=None,
        asset_types=c.METADATA_ASSET_EXTENSIONS[0],
        overwrite=False, individual_meta=True
        ):
    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    bitmaps_metadata = []
    objects_metadata = []

    object_assets, bitmap_assets = objects_tag.get_cache_names()
    objects = objects_tag.data.objects
    bitmaps = objects_tag.data.bitmaps
    exported_objects = {obj.obj_index:  True for obj  in objects_tag.data.object_defs}
    exported_bitmaps = {bitm.tex_index: True for bitm in objects_tag.data.bitmap_defs}
    for i, obj in enumerate(objects):
        metadata_obj = dict(
            flags={},
            name=object_assets[i]["name"],
            asset_name=object_assets[i]["asset_name"]
            )

        objects_metadata.append(metadata_obj)

        if hasattr(obj, "lods"):
            obj_flags = obj.lods[0].flags
        else:
            obj_flags = getattr(obj, "flags", None)

        for flag in c.OBJECT_FLAG_NAMES:
            if hasattr(obj_flags, flag):
                metadata_obj["flags"][flag] = bool(getattr(obj_flags, flag))

        if not metadata_obj["flags"]:
            metadata_obj.pop("flags")

    for i in range(len(bitmaps)):
        bitm = bitmaps[i]
        metadata_bitm = dict(
            flags={}, lod_k=0,
            format=bitm.format.enum_name,
            name=bitmap_assets[i]["name"],
            asset_name=bitmap_assets[i]["asset_name"],
            cache_name=exported_bitmaps.get(i, False),
            )
        if hasattr(bitm, "lod_k"): # v4 and higher
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

        bitmaps_metadata.append(metadata_bitm)

        attrs_to_write = ()
        if not has_bitm_data:
            attrs_to_write += (
                "width", "height",
                "frame_count", "tex_palette_count",
                "tex_palette_index", "tex_shift_index"
                )

        for attr in attrs_to_write:
            if hasattr(bitm, attr):
                metadata_bitm[attr] = getattr(bitm, attr)

        for flag in c.BITMAP_FLAG_NAMES:
            if hasattr(bitm.flags, flag):
                metadata_bitm["flags"][flag] = bool(getattr(bitm.flags, flag))

        if not metadata_bitm["flags"]:
            metadata_bitm.pop("flags")

    os.makedirs(data_dir, exist_ok=True)

    if individual_meta:
        metadata_sets = util.split_metadata_by_asset_name(
            group_singletons=True,
            metadata_by_type=dict(
                bitmaps=bitmaps_metadata,
                objects=objects_metadata
                )
            )
    else:
        metadata_sets = dict(
            bitmaps=dict(bitmaps=bitmaps_metadata),
            objects=dict(objects=objects_metadata),
            )

    for set_name in metadata_sets:
        for asset_type in asset_types:
            filepath = os.path.join(data_dir, "%s.%s" % (set_name, asset_type))
            util.dump_metadata(metadata_sets[set_name], filepath, overwrite)

