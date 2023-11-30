import pathlib
import json
import traceback
import yaml

from . import constants as c
from ..util import *


def locate_metadata(data_dir):
    return locate_assets(data_dir, (c.METADATA_CACHE_EXTENSION, ))


def load_metadata(filepath):
    filepath    = pathlib.Path(filepath)
    asset_type  = filepath.suffix.strip(".").lower()
    if asset_type in ("yaml", "yml", c.METADATA_CACHE_EXTENSION):
        with filepath.open() as f:
            metadata = yaml.safe_load(f)
    elif asset_type == "json":
        with filepath.open() as f:
            metadata = json.load(f)
    else:
        raise ValueError("Unknown metadata asset type '%s'" % asset_type)

    return metadata


def dump_metadata_sets(metadata_sets, overwrite=False, dont_group=(),
                       asset_types=c.METADATA_CACHE_EXTENSIONS,
                       data_dir=".", assets_dir=None, cache_dir=None):
    data_dir = pathlib.Path(data_dir)
    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    if not assets_dir: assets_dir  = data_dir
    if not cache_dir:  cache_dir   = data_dir.joinpath(c.IMPORT_FOLDERNAME)

    individual_metadata_sets = split_metadata_by_asset_name(
        metadata_by_type=metadata_sets,
        group_singletons=True, dont_group=dont_group,
        )

    for asset_type in asset_types:
        if asset_type in c.METADATA_CACHE_EXTENSIONS:
            dump_dir = cache_dir
            metadata = { k: {k: v} for k, v in metadata_sets.items() }
        else:
            dump_dir = assets_dir
            metadata = individual_metadata_sets

        for set_name in metadata:
            filepath = pathlib.Path(dump_dir, "%s.%s" % (set_name, asset_type))
            filepath.parent.mkdir(parents=True, exist_ok=True)
            dump_metadata(metadata[set_name], filepath, overwrite)


def dump_metadata(metadata, filepath, overwrite=False):
    filepath    = pathlib.Path(filepath)
    asset_type  = filepath.suffix.strip(".").lower()
    if filepath.is_file() and not overwrite:
        return
    elif asset_type in ("yaml", "yml", c.METADATA_CACHE_EXTENSION):
        with filepath.open('w') as f:
            yaml.safe_dump(metadata, f)
    elif asset_type in ("json", ):
        with filepath.open('w') as f:
            json.dump(metadata, f, sort_keys=True, indent=2)


def split_metadata_by_asset_name(metadata_by_type, group_singletons=False, dont_group=()):
    meta_by_asset_names = {}
    for typ, metadata in metadata_by_type.items():
        for name, asset_metadata in metadata.items():
            asset_name = asset_metadata.get("asset_name", name)
            meta_by_asset_names.setdefault(f"{typ}/{asset_name}", {})\
                               .setdefault(typ, {})\
                               .update({name: asset_metadata})

    if group_singletons:
        for typ_name in sorted(meta_by_asset_names):
            typ, name = typ_name.split("/", 1)
            if len(meta_by_asset_names[typ_name][typ]) > 2:
                meta_by_asset_names[f"{typ}/anim_{name}"] = meta_by_asset_names.pop(typ_name)
            elif typ not in dont_group:
                meta_by_asset_names.setdefault(typ, {})\
                                   .setdefault(typ, {})\
                                   .update(meta_by_asset_names.pop(typ_name)[typ])
                

    return meta_by_asset_names


def compile_metadata(data_dir, by_asset_name=False):
    all_assets = locate_metadata(data_dir)
    meta_type_lists = {}
    meta_type_seen  = {}

    for metadata_name in sorted(all_assets):
        asset_filepath = all_assets[metadata_name]
        try:
            metadata = load_metadata(asset_filepath)

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
            print(traceback.format_exc())
            print(f"Could not load metadata file '{asset_filepath}'")

    if by_asset_name:
        all_metadata = util.split_metadata_by_asset_name(
            metadata_by_type=meta_type_lists,
            group_singletons=False,
            )
    else:
        all_metadata = meta_type_lists

    return all_metadata
