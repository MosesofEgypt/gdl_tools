import os

from traceback import format_exc
from . import constants as c
from . import util


def compile_objects_metadata(data_dir, by_asset_name=False):
    all_assets = util.locate_metadata(data_dir)
    meta_type_lists = {}
    meta_type_seen  = {}

    for metadata_name in sorted(all_assets):
        asset_filepath = all_assets[metadata_name]
        try:
            metadata = util.load_metadata(asset_filepath)

            for typ in metadata:
                typ  = typ.lower()
                lst  = meta_type_lists.setdefault(typ, [])
                seen = meta_type_seen.setdefault(typ, set())
                src_lst = metadata.get(typ, ())
                for i in range(len(src_lst)):
                    name = src_lst[i].get("name")
                    if name in seen:
                        print(f"Skipping duplicate {typ} name '{name}' in '{asset_filepath}'")
                    else:
                        lst.append(src_lst[i])
                        seen.add(name)

        except Exception:
            print(format_exc())
            print(f"Could not load metadata file '{asset_filepath}'")

    if by_asset_name:
        all_metadata = util.split_metadata_by_asset_name(
            group_singletons=False,
            metadata_by_type=meta_type_lists
            )
    else:
        all_metadata = meta_type_lists

    return all_metadata


def decompile_objects_metadata(
        objects_tag, data_dir,
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
    for i in range(len(objects)):
        metadata_obj = dict(
            flags={},
            name=object_assets[i]["name"],
            asset_name=object_assets[i]["asset_name"]
            )

        objects_metadata.append(metadata_obj)

        obj_flags = getattr(objects[i], "flags", None)
        for flag in c.OBJECT_FLAG_NAMES:
            if hasattr(obj_flags, flag):
                metadata_obj["flags"][flag] = bool(getattr(obj_flags, flag))

        if not metadata_obj["flags"]:
            metadata_obj.pop("flags")

    for i in range(len(bitmaps)):
        bitm = bitmaps[i]
        metadata_bitm = dict(
            flags={},
            lod_k=bitm.lod_k,
            format=bitm.format.enum_name,
            mipmap_count=bitm.mipmap_count,
            name=bitmap_assets[i]["name"],
            asset_name=bitmap_assets[i]["asset_name"],
            cache_name=exported_bitmaps.get(i, False),
            )
        if not(bitm.frame_count or getattr(bitm.flags, "external") or not hasattr(bitm, "tex0")):
            for name, default in (
                    ("tex_cc", "rgba"),
                    ("tex_function", "decal"),
                    ("clut_smode", "csm1"),
                    ("clut_loadmode", "recache"),
                    ):
                if bitm.tex0[name].enum_name != default:
                    metadata_bitm[name] = bitm.tex0[name].enum_name

        # temporary hack 
        metadata_bitm["force_index"] = i

        bitmaps_metadata.append(metadata_bitm)

        attrs_to_write = ()
        if getattr(bitm.flags, "external", False) or bitm.frame_count > 0:
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

