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
        all_metadata = util.split_metadata_by_asset_name(
            group_singletons=False,
            metadata_by_type=meta_type_lists
            )
    else:
        all_metadata = meta_type_lists

    return all_metadata
