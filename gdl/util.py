import concurrent.futures
import os
import traceback
import pathlib

from .compilation.constants import WAD_LUMP_TYPES
from .supyr_struct_ext import FixedBytearrayBuffer,\
     BytearrayBuffer, BytesBuffer

_processing_pool = None

def process_jobs(job_function, all_job_args=(), process_count=None):
    results = []
    if process_count is None or process_count > 1:
        global _processing_pool
        if _processing_pool is None:
            _processing_pool = concurrent.futures.ProcessPoolExecutor(process_count)

        results.extend(_processing_pool.map(job_function, all_job_args))
    else:
        for job_args in all_job_args:
            try:
                results.append(job_function(job_args))
            except Exception:
                print(traceback.format_exc())

    return results


def get_is_arcade_wad(filepath):
    is_arcade = False
    filepath = pathlib.Path(filepath)
    try:
        # do a little peek to see if the file is arcade or not
        with filepath.open("rb") as f:
            wad_header_start = int.from_bytes(f.read(4), 'little')
            wad_header_count = int.from_bytes(f.read(4), 'little')
            # safety check in case file isn't a wad
            if wad_header_count > 50:
                return False

            for i in range(wad_header_count):
                f.seek(wad_header_start + (16 * i))
                lump_type = f.read(4).decode("latin-1")[::-1]
                if lump_type not in WAD_LUMP_TYPES:
                    is_arcade = True

    except Exception:
        pass

    return is_arcade


def get_is_arcade_rom(filepath):
    name = pathlib.Path(filepath).stem.lower()
    if name in ("anim", "objects", "textures", "worlds",
                "dummy", "aud_data", "hstable_e", "hstable_j"):
        return True
    elif len(name) == 9 and name.startswith("passport"):
        return True
    elif len(name) == 6 and name.startswith("index"):
        return True
    return False

def get_is_big_endian_texdef(filepath):
    with open(filepath, "rb") as f:
        bitmaps_count       = int.from_bytes(f.read(4), 'little')
        bitmap_defs_pointer = int.from_bytes(f.read(4), 'little')
        bitmaps_pointer     = int.from_bytes(f.read(4), 'little')
        file_end            = f.seek(0, os.SEEK_END)

    if (bitmaps_pointer > file_end or
        bitmap_defs_pointer > file_end or
        bitmaps_count > 0x8000):
        return True
    return False
