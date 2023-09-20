import concurrent.futures
import os
import traceback

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
    try:
        # do a little peek to see if the file is arcade or not
        with open(filepath, "rb") as f:
            wad_header_start = int.from_bytes(f.read(4), 'little')
            wad_header_count = int.from_bytes(f.read(4), 'little')
            # safety check in case file isn't a wad
            if wad_header_count > 50:
                return False

            for i in range(wad_header_count):
                f.seek(wad_header_start + (16 * i) + 8)
                # if the size value is present twice, its arcade
                if f.read(4) != f.read(4):
                    return False

    except Exception:
        pass

    return is_arcade


def get_is_arcade_rom(filepath):
    basename, _ = os.path.splitext(filepath)
    basename = basename.lower()
    if basename in ("anim", "objects", "textures", "worlds",
                    "dummy", "aud_data", "hstable_e", "hstable_j"):
        return True
    elif len(basename) == 9 and basename.startswith("passport"):
        return True
    elif len(basename) == 6 and basename.startswith("index"):
        return True
    return False
