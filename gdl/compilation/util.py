import os

from ..util import *

def calculate_padding(buffer_len, stride):
    return (stride-(buffer_len%stride)) % stride

def locate_assets(data_dir, extensions):
    assets = {}
    for root, dirs, files in os.walk(data_dir):
        for filename in sorted(files):
            asset_name, ext = os.path.splitext(filename)
            asset_name = asset_name.upper()
            if ext.lower().lstrip(".") not in extensions:
                continue

            if asset_name in assets:
                print(f"Warning: Found duplicate asset named '{asset_name}'")

            assets[asset_name] = os.path.join(root, filename)

    return assets
