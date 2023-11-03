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


def locate_objects_dir_files(objects_dir):
    filepaths = {
        f"{filetype}_filepath": ""
        for filetype in ("anim", "objects", "texdef", "textures", "worlds")
        }
    ngc_objects_filepath    = False
    ngc_textures_filepath   = False

    for _, __, files in os.walk(objects_dir):
        for filename in files:
            filetype, ext = os.path.splitext(filename.lower())
            filetype_key = f"{filetype}_filepath"
            ext = ext.strip(".")
            # NOTE: dreamcast uses .rom for everything like arcade, though arcade
            #       doesn't have the texdef file, whereas dreamcast does.
            #       also gamecube only uses .ngc for objects and textures.
            if ext not in (constants.PS2_EXTENSION, constants.NGC_EXTENSION,
                           constants.ARC_EXTENSION, constants.DC_EXTENSION):
                continue
            elif filetype_key not in filepaths:
                continue

            filepath = os.path.join(objects_dir, filename)
            if ext == "ngc":
                if filetype == "objects":
                    ngc_objects_filepath = filepath
                elif filetype == "textures":
                    ngc_textures_filepath = filepath
            else:
                filepaths[filetype_key] = filepath

        break

    is_ngc = bool(ngc_objects_filepath and ngc_textures_filepath)
    if is_ngc:
        # only use the gamecube filepaths if we found a matching pair
        filepaths.update(
            objects_filepath  = ngc_objects_filepath,
            textures_filepath = ngc_textures_filepath,
            )

    return dict(is_ngc=is_ngc, **filepaths)
