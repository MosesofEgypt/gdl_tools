import os
import struct
import zlib

from traceback import format_exc
from .ps2_wad import constants, util

INDEX_HEADER_STRUCT = struct.Struct("<iiIi")

class Ps2WadCompiler:
    wad_dirpath  = ""
    wad_filepath = ""

    overwrite = False
    parallel_processing = False
    use_wad_hashmap = True

    filepath_hashmap = ()
    file_headers     = ()

    def __init__(self, **kwargs):
        # simple initialization setup where kwargs are
        # copied into the attributes of this new class
        for k, v in kwargs.items():
            setattr(self, k, v)

    def load_filepath_hashmap(self, use_wad_hashmap=None):
        if use_wad_hashmap is None:
            use_wad_hashmap = self.use_wad_hashmap

        self.filepath_hashmap = {
            util.hash_filepath(filepath): filepath
            for filepath in constants.RETAIL_NAMES
            }

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

    def extract_files(self, file_headers=None):
        if file_headers is None:
            file_headers = self.get_file_headers()

        with open(self.wad_filepath, "rb") as fin:
            for header in file_headers:
                filename = self.get_filepath_for_file(header).upper()
                filepath = os.path.join(self.wad_dirpath, filename)
                print(filename)
                continue
                try:
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    with open(filepath, "wb") as fout:
                        fin.seek(header["data_pointer"])
                        if header["comp_size"] < 0:
                            data = fin.read(header["uncomp_size"])
                        else:
                            data = zlib.decompress(fin.read(header["comp_size"]))

                        fout.write(data)

                except Exception:
                    print(format_exc())
                    print(f"Failed to extract '{filepath}'")
