import concurrent.futures
import os
import traceback

from supyr_struct.buffer import BytearrayBuffer, BytesBuffer

_processing_pool = None

# seeking is broken in supyr(can't seek to start)
BytesBuffer.seek = BytearrayBuffer.seek

class FixedBytearrayBuffer(BytearrayBuffer):
    __slots__ = ('_pos',)
    def __init__(self, *args):
        self._pos = 0
        bytearray.__init__(self, *args)


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
