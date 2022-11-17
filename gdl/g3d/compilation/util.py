import multiprocessing
import os
import traceback

from . import constants as c
from ..serialization.util import *


def locate_metadata(data_dir):
    return _locate_assets(data_dir, c.METADATA_ASSET_EXTENSIONS)

def locate_models(data_dir, cache_files=False):
    return _locate_assets(data_dir,
        c.MODEL_CACHE_EXTENSION if cache_files else
        c.MODEL_ASSET_EXTENSIONS
        )

def locate_textures(data_dir, cache_files=False, target_ngc=False):
    return _locate_assets(data_dir,
        c.TEXTURE_ASSET_EXTENSIONS if not cache_files else
        (c.TEXTURE_CACHE_EXTENSION_NGC, ) if target_ngc else
        (c.TEXTURE_CACHE_EXTENSION_PS2, )
        )

def locate_animations(data_dir, cache_files=False):
    return _locate_assets(data_dir,
        c.ANIMATION_CACHE_EXTENSION if cache_files else
        c.ANIMATION_ASSET_EXTENSIONS
        )

def _locate_assets(data_dir, extensions):
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


def process_jobs(job_function, all_job_args=(), process_count=None):
    if not process_count:
        process_count = os.cpu_count()

    if process_count > 1:
        with multiprocessing.Pool() as pool:
            pool.map(job_function, all_job_args)

        # TODO: capture stdout/stderr from jobs and redirect it to the primary process
        return

    for job_args in all_job_args:
        try:
            job_function(job_args)
        except Exception:
            print(traceback.format_exc())
