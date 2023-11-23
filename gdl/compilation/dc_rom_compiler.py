import os
import pathlib
import tempfile

from traceback import format_exc
from .dc_rom import util


def _extract_files(kwargs):
    file_buffers = {}
    dirpath         = pathlib.Path(kwargs["dirpath"])
    sizes_filepath  = pathlib.Path(kwargs["sizes_filepath"])
    disk_filepath   = pathlib.Path(kwargs["disk_filepath"])

    with disk_filepath.open("rb") as fin:
        for header in kwargs["file_headers"]:
            filename = header["filename"]
            filepath = dirpath.joinpath(filename)
            try:
                if header["offset"] < 0 or (not kwargs["overwrite"] and filepath.is_file()):
                    continue

                if kwargs["to_disk"]:
                    print(f"Extracting file: {filename}")
                else:
                    print(f"Reading file: {filename}")

                fin.seek(header["offset"])
                data = fin.read(header["size"])

                if kwargs["to_disk"]:
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    with filepath.open("wb") as fout:
                        fout.write(data)
                else:
                    file_buffers[filename] = data

            except Exception:
                print(format_exc())
                print(f"Failed to extract '{filepath}'")

    return file_buffers


def _compile_rom(kwargs):
    raise NotImplementedError()


class DcRomCompiler:
    dirpath  = ""
    sizes_filepath = ""
    disk_filepath  = ""

    overwrite = False
    parallel_processing = True

    file_headers     = ()

    def __init__(self, **kwargs):
        # simple initialization setup where kwargs are
        # copied into the attributes of this new class
        for k, v in kwargs.items():
            setattr(self, k, v)

    def locate_disk_file(self):
        sizes_filepath = pathlib.Path(self.sizes_filepath)
        for root, _, files in os.walk(sizes_filepath.parent):
            for filename in files:
                if filename.lower() == "disk.rom":
                    return sizes_filepath.with_name(filename)
            break

        raise FileNotFoundError("Cannot locate DISK.ROM file.")

    def get_file_headers(self, force_reload=False):
        sizes_filepath = pathlib.Path(self.sizes_filepath)
        if force_reload or not self.file_headers:
            if not sizes_filepath.is_file():
                return

            self.file_headers = util.read_file_headers(sizes_filepath)

        return self.file_headers

    def extract_files(self, file_headers=None):
        if not file_headers:
            file_headers = self.get_file_headers()

        if not self.disk_filepath:
            self.disk_filepath = self.locate_disk_file()

        return _extract_files(dict(
            file_headers=file_headers, overwrite=self.overwrite, to_disk=False,
            sizes_filepath=self.sizes_filepath, dirpath=self.dirpath,
            disk_filepath=self.disk_filepath,
            ))

    def extract_file(self, file_header):
        datas = self.extract_files(file_headers=[file_header])
        return datas[tuple(datas.keys())[0]] if datas else None

    def extract_file_to_disk(self, file_header):
        self.extract_files_to_disk(file_headers=[file_header])

    def extract_files_to_disk(self, file_headers=None):
        if not file_headers:
            file_headers = self.get_file_headers()

        if not self.disk_filepath:
            self.disk_filepath = self.locate_disk_file()

        files_to_extract_by_size = {}

        for header in file_headers:
            files_to_extract_by_size.setdefault(header["size"], []).append(header)

        files_sorted_by_size = []
        for size in sorted(files_to_extract_by_size):
            files_sorted_by_size.extend(files_to_extract_by_size[size])

        all_job_args = [
            dict(
                file_headers=[], overwrite=self.overwrite, to_disk=True,
                sizes_filepath=self.sizes_filepath, dirpath=self.dirpath,
                disk_filepath=self.disk_filepath,
                )
            for i in range(os.cpu_count() if self.parallel_processing else 1)
            ]
        for i in range(len(files_sorted_by_size)):
            all_job_args[i % len(all_job_args)]["file_headers"].append(files_sorted_by_size[i])

        util.process_jobs(
            _extract_files, all_job_args,
            process_count=None if self.parallel_processing else 1
            )

    def compile(self):
        raise NotImplementedError()
