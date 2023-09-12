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
    # TODO: fix this to work if the wad header is at the start of the file
    try:
        # do a little peek to see if the file is arcade or not
        with open(filepath, "rb") as f:
            wad_header_start = int.from_bytes(f.read(4), 'little')
            wad_header_count = int.from_bytes(f.read(4), 'little')
            f.seek(2, 2)
            wad_header_size = (f.tell() - wad_header_start) // wad_header_count

        # arcade size is 12, console size is 16
        return wad_header_size == 12
    except Exception:
        return False
