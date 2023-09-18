import concurrent.futures
import os
import traceback

from .supyr_struct_ext import FixedBytearrayBuffer,\
     BytearrayBuffer, BytesBuffer
from .defs import arcade_hdd

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
            if wad_header_count:
                f.seek(wad_header_start + 8)
                # if the size value is present twice, its arcade
                is_arcade = (f.read(4) == f.read(4))

    except Exception:
        pass

    return is_arcade


def get_is_arcade_hdd(filepath):
    is_hdd = False
    try:
        # check for a couple header signatures
        with open(filepath, "rb") as f:
            f.seek(512)
            if int.from_bytes(f.read(4), 'little') != arcade_hdd.MBR_HEADER_SIG:
                return False

            f.seek(512 + 56)
            if int.from_bytes(f.read(4), 'little') != arcade_hdd.UNKNOWN_MBR_SIG:
                return False

            return True

    except Exception:
        pass

    return is_hdd
