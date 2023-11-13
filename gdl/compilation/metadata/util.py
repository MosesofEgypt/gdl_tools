import pathlib
import json
import yaml

from . import constants as c
from ..util import *


def locate_metadata(data_dir):
    return locate_assets(data_dir, c.METADATA_ASSET_EXTENSIONS)


def load_metadata(filepath):
    filepath    = pathlib.Path(filepath)
    asset_type  = filepath.suffix.strip(".").lower()
    if asset_type in ("yaml", "yml"):
        with filepath.open() as f:
            metadata = yaml.safe_load(f)
    elif asset_type == "json":
        with filepath.open() as f:
            metadata = json.load(f)
    else:
        raise ValueError("Unknown metadata asset type '%s'" % asset_type)

    return metadata


def dump_metadata(metadata, filepath, overwrite=False):
    filepath    = pathlib.Path(filepath)
    asset_type  = filepath.suffix.strip(".").lower()
    if filepath.is_file() and not overwrite:
        return
    elif asset_type in ("yaml", "yml"):
        with filepath.open('w') as f:
            yaml.safe_dump(metadata, f)
    elif asset_type in ("json", ):
        with filepath.open('w') as f:
            json.dump(metadata, f, sort_keys=True, indent=2)


def split_metadata_by_asset_name(group_singletons, metadata_by_type):
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
