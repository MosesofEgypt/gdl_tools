import multiprocessing
import os
import traceback

from supyr_struct.buffer import BytearrayBuffer

def calculate_padding(buffer_len, stride):
    return (stride-(buffer_len%stride)) % stride


class FixedBytearrayBuffer(BytearrayBuffer):
    __slots__ = ('_pos',)
    def __init__(self, *args):
        self._pos = 0
        bytearray.__init__(self, *args)


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

