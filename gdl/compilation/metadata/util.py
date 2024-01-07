import json
import os
import pathlib
import traceback
import yaml

from . import constants as c
from ..util import *


def get_frame_count(meta):
    return 0 if not isinstance(meta, dict) else (
        meta.get("frame_count", len(meta.get("frames", ())))
        )


def locate_metadata(data_dir, cache_files=False):
    return locate_assets(data_dir,
        c.METADATA_CACHE_EXTENSIONS if cache_files else
        c.METADATA_ASSET_EXTENSIONS
        )


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


def dump_metadata_sets(metadata_sets, overwrite=False,
                       asset_types=c.METADATA_CACHE_EXTENSIONS,
                       assets_dir=".", cache_dir=None):
    assets_dir = pathlib.Path(assets_dir)
    if not cache_dir:
        cache_dir   = assets_dir.joinpath(c.IMPORT_FOLDERNAME)

    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    for asset_type in asset_types:
        if asset_type in c.METADATA_CACHE_EXTENSIONS:
            dump_dir = cache_dir
            metadata = {"metadata": merge_metadata_sets(*metadata_sets.values())}
        else:
            dump_dir = assets_dir
            metadata = metadata_sets

        for set_name in metadata:
            if not metadata[set_name]:
                continue
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


def clear_metadata_files(dir, extensions):
    if isinstance(extensions, str):
        extensions = [extensions]

    extensions = set(s.lower() for s in extensions)
    for root, dirs, files in os.walk(dir):
        for filename in files:
            ext = pathlib.Path(filename).suffix.lstrip(".")
            if ext.lower() in extensions:
                filepath = pathlib.Path(root, filename)
                try:
                    filepath.unlink(missing_ok=True)
                except Exception:
                    raise IOError(f"Could not unlink file '{filepath}'.")


def clear_cache_files(cache_dir):
    return clear_metadata_files(cache_dir, c.METADATA_CACHE_EXTENSION)


def merge_metadata_sets(*metadata_sets):
    all_metadata = {}
    for other_metadata in metadata_sets:
        if not isinstance(other_metadata, dict):
            print("Warning: Expected dict at top level of metadata, "
                  f"but got {type(other_metadata)}. Skipping.")
            continue

        for typ, meta in other_metadata.items():
            if not isinstance(meta, dict):
                print("Warning: Expected only dict under metadata key "
                      f"'{typ}', but got {type(meta)}. Skipping.")
                continue

            metadata_type = all_metadata.setdefault(typ.lower(), {})
            for name, asset_meta in meta.items():
                if not isinstance(asset_meta, dict):
                    print("Warning: Expected only dict under metadata key "
                          f"'{typ}.{name}', but got {type(asset_meta)}. Skipping.")
                    continue
                metadata_type[name.upper()] = asset_meta

    return all_metadata


def compile_metadata(data_dir, cache_files=False):
    all_assets = locate_metadata(data_dir, cache_files=cache_files)
    all_metadata = {}

    for metadata_name in sorted(all_assets):
        asset_filepath = all_assets[metadata_name]
        try:
            metadata = load_metadata(asset_filepath)
            if isinstance(metadata, dict):
                all_metadata = merge_metadata_sets(all_metadata, metadata)
        except Exception:
            print(traceback.format_exc())
            print(f"Could not load metadata file '{asset_filepath}'")

    return all_metadata
