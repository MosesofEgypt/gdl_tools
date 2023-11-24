import os
import pathlib
import tempfile
import zlib

from traceback import format_exc
from .ps2_wad import constants as c
from .ps2_wad import util


def _extract_files(kwargs):
    file_buffers = {}
    wad_dirpath  = pathlib.Path(kwargs["wad_dirpath"])
    wad_filepath = pathlib.Path(kwargs["wad_filepath"])

    with wad_filepath.open("rb") as fin:
        for header in kwargs["file_headers"]:
            # convert paths to windows and then to current platform.
            # this ensures slashes are correct regardless of platform.
            filename = pathlib.Path(pathlib.PureWindowsPath(header["filename"]))
            filepath = wad_dirpath.joinpath(filename)

            if kwargs["to_disk"]:
                if not kwargs["overwrite"] and filepath.is_file():
                    continue
                print(f"Extracting file: {filename}")
            else:
                print(f"Reading file: {filename}")

            try:
                fin.seek(header["data_pointer"])
                if header["comp_size"] < 0:
                    data = fin.read(header["uncomp_size"])
                else:
                    data = zlib.decompress(fin.read(header["comp_size"]))

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


def _compile_wad(kwargs):
    wad_filepath = pathlib.Path(kwargs["wad_filepath"])
    file_headers = [
        dict(
            filename=header["filename"], filepath=pathlib.Path(header["filepath"]),
            compress_level=header.get("compress_level", 0),
            data_pointer=0, uncomp_size=0, comp_size=-1,
            path_hash=util.hash_filepath(header.get("filename", "")),
            )
        for header in kwargs["file_headers"]
        ]

    with wad_filepath.open("wb") as fout:
        # write the headers to allocate enough space for file index
        util.write_file_headers(file_headers, fout)

        for header in file_headers:
            print(f"Compiling file: %s" % header["filename"])
            try:
                # read the data, and update the sizes/path hash/pointer
                filepath = pathlib.Path(header["filepath"])
                filename = pathlib.Path(header["filename"])
                header["data_pointer"] = fout.tell()
                with filepath.open("rb") as fin:
                    data = fin.read()

                if filename.suffix.lower().strip(".") == c.PS2_WAD_UNKNOWN_EXTENSION:
                    # unknown files store the path hash in the filename
                    header["path_hash"] = int(filename.stem)

                # compress the data if needed, and write to file
                data_to_write = data
                header["uncomp_size"] = len(data)
                header["comp_size"] = -1
                if (len(data) > c.PS2_WAD_FILE_CHUNK_SIZE and header["compress_level"] and
                    util.is_compressible(header["filename"])
                    ):
                    comp_data = zlib.compress(data, header["compress_level"])
                    if len(comp_data) < len(data):
                        header["comp_size"] = len(comp_data)
                        data_to_write = comp_data

                fout.write(data_to_write)

                # write padding
                fout.write(b'\x00' * util.calculate_padding(fout.tell(), c.PS2_WAD_FILE_CHUNK_SIZE))
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
    parallel_processing = True
    use_internal_names = True
    use_compression_names = False
    compression_level = zlib.Z_NO_COMPRESSION

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

        wad_filepath = pathlib.Path(wad_filepath)
        self.filepath_hashmap = {
            util.hash_filepath(filepath): filepath
            for filepath in c.RETAIL_NAMES
            }

        if not(use_internal_names and wad_filepath.is_file()):
            return

        try:
            internal_names_path_hash = util.hash_filepath(c.INTERNAL_NAMES_FILEPATH)
            for file_header in self.get_file_headers():
                if file_header["path_hash"] != internal_names_path_hash:
                    continue

                file_header["filename"] = c.INTERNAL_NAMES_FILEPATH
                data = self.extract_file(file_header)
                internal_names = util.read_names_list(data.decode())

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

        wad_filepath = pathlib.Path(wad_filepath)
        if force_reload or not self.file_headers:
            if not wad_filepath.is_file():
                return

            with wad_filepath.open("rb") as f:
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
        return datas[tuple(datas.keys())[0]] if datas else None

    def extract_files(self, file_headers=None):
        if not file_headers:
            file_headers = self.get_file_headers()

        file_headers = [dict(h) for h in file_headers]  # copy for manipulating
        for header in file_headers:
            if "filename" not in header:
                header["filename"] = util.to_wad_filepath(self.get_filepath_for_file(header))

        return _extract_files(dict(
            file_headers=file_headers, overwrite=self.overwrite, to_disk=False,
            wad_filepath=self.wad_filepath, wad_dirpath=self.wad_dirpath,
            ))

    def extract_file_to_disk(self, file_header):
        self.extract_files_to_disk(file_headers=[file_header])

    def extract_files_to_disk(self, file_headers=None):
        if not file_headers:
            file_headers = [
                file_header for file_header in self.get_file_headers()
                if file_header["path_hash"] != c.INTERNAL_NAMES_FILEPATH_HASH
                ]

        files_to_extract_by_size = {}

        file_headers = [dict(h) for h in file_headers]  # copy for manipulating
        for header in file_headers:
            if "filename" not in header:
                header["filename"] = util.to_wad_filepath(self.get_filepath_for_file(header))

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

    def compile(self):
        files_to_compile = list(util.locate_target_platform_files(
            self.wad_dirpath, want_ps2=True
            ))
        wad_filepath = pathlib.Path(self.wad_filepath)

        if not self.overwrite and wad_filepath.is_file():
            return

        explicit_compress_level = self.compression_level
        default_compress_level  = self.compression_level
        compress = set()

        # if we're using a list of filenames to control what gets compressed, load it
        if self.use_compression_names:
            default_compress_level = zlib.Z_NO_COMPRESSION

            for filepath in files_to_compile:
                filename = filepath.relative_to(self.wad_dirpath)

                if util.hash_filepath(filename) == c.COMPRESS_NAMES_FILEPATH_HASH:
                    with filepath.open("r") as f:
                        compress.update(
                            util.hash_filepath(filename)
                            for filename in util.read_names_list(f)
                            )
                    break

        file_headers = []
        for filepath in files_to_compile:
            filename = filepath.relative_to(self.wad_dirpath)
            # don't include the extracted filepaths list
            if util.hash_filepath(filename) in (c.INTERNAL_NAMES_FILEPATH_HASH,
                                                c.COMPRESS_NAMES_FILEPATH_HASH):
                continue

            file_headers.append(dict(
                filename=filename, filepath=filepath,
                compress_level=(
                    default_compress_level if util.hash_filepath(filename) in compress else
                    explicit_compress_level
                    )
                ))

        temp_files = []
        if self.use_internal_names:
            # create a temp file to hold the filenames
            names_tempfile = tempfile.NamedTemporaryFile("w+", delete=False)
            temp_files.append(names_tempfile)

            file_headers.append(dict(
                filename=c.INTERNAL_NAMES_FILEPATH,
                filepath=names_tempfile.name,
                compress_level=explicit_compress_level
                ))

            util.write_names_list(
                [h["filename"] for h in file_headers], names_tempfile
                )
            names_tempfile.flush()

        wad_files = []
        if self.parallel_processing:
            # create temp files to write each process's wad to
            job_count = min(os.cpu_count(), len(file_headers))

            file_headers_by_job = tuple([] for i in range(job_count))
            for i in range(len(file_headers)):
                file_headers_by_job[i % len(file_headers_by_job)].append(file_headers[i])

            for i in range(job_count):
                wad_tempfile = tempfile.NamedTemporaryFile("wb+", buffering=0, delete=False)
                wad_files.append(wad_tempfile.name)
                temp_files.append(wad_tempfile)
        else:
            file_headers_by_job = [file_headers]
            wad_files.append(wad_filepath)

        all_job_args = [
            dict(
                file_headers=file_headers_by_job[i], wad_filepath=wad_files[i],
                )
            for i in range(len(wad_files))
            ]

        # process the build jobs, and concat the resulting wads
        if all_job_args:
            util.process_jobs(
                _compile_wad, all_job_args,
                process_count=len(file_headers_by_job)
                )

            if wad_files[0] != wad_filepath:
                util.concat_wad_files(wad_filepath, wad_files)

        # close and cleanup the temp files
        for file in temp_files:
            try:
                file.close()
                os.unlink(file.name)
            except Exception:
                print(format_exc())
                print(f"Could not clean up temp files '{file.name}'")
