from . import constants as c
from . import util


def compile_objects_metadata(
        data_dir=".", assets_dir=None, cache_dir=None, by_asset_name=False
        ):
    return util.compile_metadata(
        data_dir=data_dir, assets_dir=assets_dir, cache_dir=cache_dir,
        by_asset_name=by_asset_name
        )


def decompile_objects_metadata(
        objects_tag, anim_tag=None,
        asset_types=c.METADATA_CACHE_EXTENSIONS,
        overwrite=False, data_dir=".", assets_dir=None, cache_dir=None
        ):
    bitmaps_metadata = {}
    objects_metadata = {}

    object_assets, bitmap_assets = objects_tag.get_cache_names()
    objects = objects_tag.data.objects
    bitmaps = objects_tag.data.bitmaps
    exported_objects = {obj.obj_index:  True for obj  in objects_tag.data.object_defs}
    exported_bitmaps = {bitm.tex_index: True for bitm in objects_tag.data.bitmap_defs}
    for i, obj in enumerate(objects):
        metadata_obj = dict(
            flags={},
            asset_name=object_assets[i]["asset_name"]
            )

        objects_metadata[object_assets[i]["name"]] = metadata_obj

        if hasattr(obj, "lods"):
            obj_flags = obj.lods[0].flags
        else:
            obj_flags = getattr(obj, "flags", None)

        for flag in c.OBJECT_FLAG_NAMES:
            if getattr(obj_flags, flag, False):
                metadata_obj["flags"][flag] = True

        if not metadata_obj["flags"]:
            metadata_obj.pop("flags")

    for i in range(len(bitmaps)):
        bitm = bitmaps[i]
        metadata_bitm = dict(
            flags={}, lod_k=0,
            format=bitm.format.enum_name,
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

        bitmaps_metadata[bitmap_assets[i]["name"]] = metadata_bitm

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
            if getattr(bitm.flags, flag, False):
                metadata_bitm["flags"][flag] = True

        if not metadata_bitm["flags"]:
            metadata_bitm.pop("flags")

    metadata_sets = dict(
        bitmaps = bitmaps_metadata,
        objects = objects_metadata
        )
    util.dump_metadata_sets(
        metadata_sets, asset_types=asset_types, overwrite=overwrite,
        data_dir=data_dir, assets_dir=assets_dir, cache_dir=cache_dir
        )
