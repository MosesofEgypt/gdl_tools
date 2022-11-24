import os
import tempfile
import zlib

from traceback import format_exc
from .ps2_wad import constants as c
from .ps2_wad import util


def _extract_files(kwargs):
    file_buffers = {}
    with open(kwargs["wad_filepath"], "rb") as fin:
        for header in kwargs["file_headers"]:
            filename = header["filename"].upper()
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

                if kwargs["to_disk"]:
                    with open(filepath, "wb") as fout:
                        fout.write(data)
                else:
                    file_buffers[filename] = data

            except Exception:
                print(format_exc())
                print(f"Failed to extract '{filepath}'")

    return file_buffers


def _compile_wad(kwargs):
    if not kwargs["overwrite"] and os.path.isfile(kwargs["wad_filepath"]):
        return

    file_headers = [
        dict(
            filename=header["filename"], filepath=header["filepath"],
            compress_level=header.get("compress_level", 0),
            data_pointer=0, uncomp_size=0, comp_size=-1,
            path_hash=util.hash_filepath(header.get("filename", "")),
            )
        for header in kwargs["file_headers"]
        ]

    with open(kwargs["wad_filepath"], "wb") as fout:
        # write the headers to allocate enough space for file index
        util.write_file_headers(file_headers, fout)

        for header in file_headers:
            print(f"Compiling file: %s" % header["filename"])
            try:
                # read the data, and update the sizes/path hash/pointer
                header["data_pointer"] = fout.tell()
                with open(header["filepath"], "rb") as fin:
                    data = fin.read()

                filename, ext = os.path.splitext(os.path.basename(header["filename"]))
                ext = ext.lower().strip(".")
                if ext == c.PS2_WAD_UNKNOWN_EXTENSION:
                    # unknown files store the path hash in the filename
                    header["path_hash"] = int(filename)
                elif ext in c.UNCOMPRESSIBLE_EXTENSIONS:
                    # do not compress
                    header["compress_level"] = 0

                # compress the data if needed, and write to file
                header["uncomp_size"]  = len(data)
                if header["compress_level"]:  # no compression if (compress_level == 0)
                    data = zlib.compress(data, header["compress_level"])
                    header["comp_size"] = len(data)
                else:
                    header["comp_size"] = -1

                fout.write(data)
            except Exception:
                print(format_exc())
                print("Failed to compile '%s'" % header["filepath"])

        fout.seek(0)
        # write the headers again after we've calculated all the offsets, hashes, and sizes
        util.write_file_headers(file_headers, fout)


class Ps2WadCompiler:
    wad_dirpath  = ""
    wad_filepath = ""

    overwrite = False
    parallel_processing = False
    use_internal_names = True
    compression_level = zlib.Z_BEST_COMPRESSION

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
            util.hash_filepath(filepath): filepath
            for filepath in c.RETAIL_NAMES
            }

        if not(use_internal_names and os.path.isfile(wad_filepath)):
            return

        try:
            internal_names_path_hash = util.hash_filepath(c.INTERNAL_NAMES_FILEPATH)
            for file_header in self.get_file_headers():
                if file_header["path_hash"] != internal_names_path_hash:
                    continue

                internal_names_data = self.extract_file(file_header)
                internal_names = util.read_internal_names(internal_names_data)

                self.filepath_hashmap.update({
                    util.hash_filepath(filepath): filepath
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

            with open(wad_filepath, "rb") as f:
                self.file_headers = util.read_file_headers(f)

        return self.file_headers

    def get_filepath_for_file(self, file_header):
        if not self.filepath_hashmap:
            self.load_filepath_hashmap()

        return self.filepath_hashmap.get(
            file_header["path_hash"],
            c.PS2_WAD_UNKNOWN_FILE_TEMPLATE % file_header["path_hash"]
            )

    def extract_file(self, file_header):
        datas = self.extract_files(file_headers=[file_header])
        return datas[0] if datas else None

    def extract_files(self, file_headers=None):
        if not file_headers:
            file_headers = self.get_file_headers()

        return _extract_files(dict(
            file_headers=file_headers, overwrite=self.overwrite, to_disk=False,
            wad_filepath=self.wad_filepath, wad_dirpath=self.wad_dirpath,
            ))

    def extract_file_to_disk(self, file_header):
        self.extract_files_to_disk(file_headers=[file_header])

    def extract_files_to_disk(self, file_headers=None):
        if not file_headers:
            file_headers = self.get_file_headers()

        files_to_extract_by_size = {}
        for header in file_headers:
            header = dict(
                filename = self.get_filepath_for_file(header).upper(),
                **header
                )
            files_to_extract_by_size.setdefault(header["uncomp_size"], []).append(header)

        files_sorted_by_size = []
        for size in sorted(files_to_extract_by_size):
            files_sorted_by_size.extend(files_to_extract_by_size[size])

        all_job_args = [
            dict(
                file_headers=[], overwrite=self.overwrite, to_disk=True,
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

    def compile_wad(self):
        files_to_compile = util.locate_ps2_wad_files(self.wad_dirpath)
        file_headers = [
            dict(
                filename=os.path.relpath(filepath, self.wad_dirpath),
                filepath=filepath,
                compress_level=self.compression_level
                )
            for filepath in files_to_compile
            ]

        all_job_args = [
            dict(
                file_headers=file_headers,
                overwrite=self.overwrite,
                wad_filepath=self.wad_filepath
                )
            #for i in range(os.cpu_count() if self.parallel_processing else 1)
            ]

        util.process_jobs(
            _compile_wad, all_job_args,
            #process_count=None if self.parallel_processing else 1
            )

        #if self.use_internal_names:
        #    names_tempfile = tempfile.TemporaryDirectory()
        #    files_to_compile.append()
