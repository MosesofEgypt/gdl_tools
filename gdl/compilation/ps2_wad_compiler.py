import os
import struct
import zlib

from traceback import format_exc
from .ps2_wad import constants, util as ps2_wad_util
from . import util 

INDEX_HEADER_STRUCT = struct.Struct("<iiIi")


def _extract_files(kwargs):
    file_buffers = {}
    with open(kwargs["wad_filepath"], "rb") as fin:
        for header in kwargs["file_headers"]:
            filename = header["filepath"].upper()
            filepath = os.path.join(kwargs["wad_dirpath"], filename)
            if not kwargs["overwrite"] and os.path.isfile(filepath):
                continue

            print(f"Extracting file: %s" % filename)
            try:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                fin.seek(header["data_pointer"])
                if header["comp_size"] < 0:
                    data = fin.read(header["uncomp_size"])
                else:
                    data = zlib.decompress(fin.read(header["comp_size"]))

                if kwargs["to_file"]:
                    with open(filepath, "wb") as fout:
                        fout.write(data)
                else:
                    file_buffers[filename] = data

            except Exception:
                print(format_exc())
                print(f"Failed to extract '{filepath}'")

    return file_buffers


class Ps2WadCompiler:
    wad_dirpath  = ""
    wad_filepath = ""

    overwrite = False
    parallel_processing = False
    use_internal_names = True

    filepath_hashmap = ()
    file_headers     = ()

    def __init__(self, **kwargs):
        # simple initialization setup where kwargs are
        # copied into the attributes of this new class
        for k, v in kwargs.items():
            setattr(self, k, v)

    def load_filepath_hashmap(self, wad_filepath=None, use_internal_names=None):
        if use_internal_names is None:
            use_internal_names = self.use_internal_names

        if not wad_filepath:
            wad_filepath = self.wad_filepath

        self.filepath_hashmap = {
            ps2_wad_util.hash_filepath(filepath): filepath
            for filepath in constants.RETAIL_NAMES
            }

        if not(use_internal_names and os.path.isfile(wad_filepath)):
            return

        try:
            internal_names_path_hash = ps2_wad_util.hash_filepath(constants.INTERNAL_NAMES_FILEPATH)
            for file_header in self.get_file_headers():
                if file_header["path_hash"] != internal_names_path_hash:
                    continue

                internal_names_data = self.extract_file(file_header)
                internal_names = ps2_wad_util.read_internal_names(internal_names_data)

                self.filepath_hashmap.update({
                    ps2_wad_util.hash_filepath(filepath): filepath
                    for filepath in internal_names
                    })
                break
        except Exception:
            print(format_exc())
            print("Could not load internal filepath names list.")

    def get_file_headers(self, wad_filepath=None, force_reload=False):
        if not wad_filepath:
            wad_filepath = self.wad_filepath

        if force_reload or not self.file_headers:
            if not os.path.isfile(wad_filepath):
                return

            file_headers = []
            with open(wad_filepath, "rb") as f:
                file_count = struct.unpack('<I', f.read(4))[0]
                for i in range(file_count):
                    header = INDEX_HEADER_STRUCT.unpack(f.read(16))
                    uncomp_size, data_pointer, path_hash, comp_size = header
                    file_headers.append(dict(
                        uncomp_size  = uncomp_size,
                        data_pointer = data_pointer,
                        path_hash    = path_hash,
                        comp_size    = comp_size
                        ))

            self.file_headers = file_headers

        return self.file_headers

    def get_filepath_for_file(self, file_header):
        if not self.filepath_hashmap:
            self.load_filepath_hashmap()

        return self.filepath_hashmap.get(
            file_header["path_hash"],
            "UNKNOWN/%s" % file_header["path_hash"]
            )

    def extract_file(self, file_header, overwrite=False):
        datas = self.extract_files(file_headers=[file_header], overwrite=overwrite)
        return datas[0] if datas else None

    def extract_files(self, file_headers=None, overwrite=False):
        if not file_headers:
            file_headers = self.get_file_headers()

        return _extract_files(dict(
            file_headers=file_headers, overwrite=overwrite, to_file=False,
            wad_filepath=self.wad_filepath, wad_dirpath=self.wad_dirpath,
            ))

    def extract_file_to_disk(self, file_header, overwrite=False):
        self.extract_files_to_disk(file_headers=[file_header], overwrite=overwrite)

    def extract_files_to_disk(self, file_headers=None, overwrite=False):
        if not file_headers:
            file_headers = self.get_file_headers()

        files_to_extract_by_size = {}
        for header in file_headers:
            header = dict(
                filepath = self.get_filepath_for_file(header).upper(),
                **header
                )
            files_to_extract_by_size.setdefault(header["uncomp_size"], []).append(header)

        files_sorted_by_size = []
        for size in sorted(files_to_extract_by_size):
            files_sorted_by_size.extend(files_to_extract_by_size[size])

        all_job_args = [
            dict(
                file_headers=[], overwrite=overwrite, to_file=True,
                wad_filepath=self.wad_filepath, wad_dirpath=self.wad_dirpath,
                )
            for i in range(os.cpu_count() if self.parallel_processing else 1)
            ]
        for i in range(len(files_sorted_by_size)):
            all_job_args[i % len(all_job_args)]["file_headers"].append(files_sorted_by_size[i])

        util.process_jobs(
            _extract_files, all_job_args,
            process_count=None if self.parallel_processing else 1
            )
