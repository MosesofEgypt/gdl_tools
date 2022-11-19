import os
import json
import yaml

from traceback import format_exc

from . import constants as c
from . import util


def compile_metadata(data_dir, by_asset_name=False):
    all_assets = util.locate_metadata(data_dir)
    meta_type_lists = {}
    meta_type_seen  = {}

    for metadata_name in sorted(all_assets):
        asset_filepath = all_assets[metadata_name]
        try:
            asset_type = os.path.splitext(asset_filepath)[-1].strip(".").lower()
            if asset_type in ("yaml", "yml"):
                with open(asset_filepath) as f:
                    metadata = yaml.safe_load(f)
            elif asset_type == "json":
                with open(asset_filepath) as f:
                    metadata = json.load(f)
            else:
                raise ValueError("Unknown metadata asset type '%s'" % asset_type)

            for typ in metadata:
                typ  = typ.lower()
                lst  = meta_type_lists.setdefault(typ, [])
                seen = meta_type_seen.setdefault(typ, set())
                src_lst = metadata.get(typ, ())
                for i in range(len(src_lst)):
                    name = src_lst[i].get("name")
                    if name in seen:
                        print(f"Skipping duplicate {typ} name '{name}' found in '{asset_filepath}'")
                    else:
                        lst.append(src_lst[i])
                        seen.add(name)

        except Exception:
            print(format_exc())
            print(f"Could not load metadata file '{asset_filepath}'")

    if by_asset_name:
        all_metadata = _split_metadata_by_asset_name(
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

    for asset_type in asset_types:
        if asset_type not in c.METADATA_ASSET_EXTENSIONS:
            raise ValueError("Unknown metadata type '%s'" % asset_type)

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
        metadata_sets = _split_metadata_by_asset_name(
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
        filepath = os.path.join(data_dir, "%s.%s" % (set_name, asset_type))
        if os.path.isfile(filepath) and not overwrite:
            continue
        elif asset_type in ("yaml", "yml"):
            with open(filepath, 'w') as f:
                yaml.dump(metadata_sets[set_name], f)
        elif asset_type in ("json"):
            with open(filepath, 'w') as f:
                json.dump(
                    metadata_sets[set_name], f, sort_keys=True, indent=2
                    )


def _split_metadata_by_asset_name(group_singletons, metadata_by_type):
    meta_by_asset_names = {}
    for typ, metadata in metadata_by_type.items():
        for asset_metadata in metadata:
            meta_by_asset_names.setdefault(
                "%s_%s" % (typ, asset_metadata["asset_name"]), {typ: []}
                )[typ].append(asset_metadata)

    # consolidate all single-asset meta into combined files
    if group_singletons:
        for set_name in sorted(tuple(meta_by_asset_names)):
            typ = set_name.split("_")[0]
            if len(meta_by_asset_names[set_name][typ]) > 1:
                continue

            asset_meta_list = meta_by_asset_names.pop(set_name)[typ]
            combined_metadata = meta_by_asset_names.setdefault(typ, {typ: []})
            combined_metadata[typ].extend(asset_meta_list)

    return meta_by_asset_names
