import os

from ..util import *
from . import constants


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


def locate_target_platform_files(
        dir, want_arcade=False, want_ps2=False
        ):
    # TODO: update this to be able to locate ngc and xbox files
    filepaths = []
    for root, dirs, files in os.walk(dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            basename, ext = os.path.splitext(filename)
            basename = basename.lower()
            ext = ext.lower().lstrip(".")

            is_arcade = is_ps2 = True

            if ext not in constants.PS2_WAD_FILE_EXTENSIONS:
                is_ps2 = False
            elif ext == "wad" and get_is_arcade_wad(filepath):
                is_ps2 = False
            elif ext == "rom" and get_is_arcade_rom(filepath):
                is_ps2 = False

            if ext not in constants.ARC_HDD_FILE_EXTENSIONS:
                is_arcade = False
            elif ext == "wad" and is_ps2:
                is_arcade = False
            elif ext == "rom" and is_ps2:
                is_arcade = False

            if ((is_arcade and want_arcade) or
                (is_ps2    and want_ps2)):
                filepaths.append(filepath)

    return filepaths
