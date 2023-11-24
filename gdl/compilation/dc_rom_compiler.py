import os
import pathlib
import tempfile

from traceback import format_exc
from .dc_rom import constants as c
from .dc_rom import util


def _extract_files(kwargs):
    file_buffers = {}
    dirpath             = pathlib.Path(kwargs["dirpath"])
    sizes_filepath      = pathlib.Path(kwargs["sizes_filepath"])
    disk_filepath       = pathlib.Path(kwargs["disk_filepath"])
    create_fake_files   = kwargs["create_fake_files"]

    with disk_filepath.open("rb") as fin:
        for header in kwargs["file_headers"]:
            filename = header["filename"]
            filepath = dirpath.joinpath(filename)
            try:
                in_archive = header["offset"] >= 0
                if in_archive:
                    if not kwargs["to_disk"]:
                        print(f"Reading file: {filename}")
                    elif kwargs["overwrite"] or not filepath.is_file():
                        print(f"Extracting file: {filename}")
                    else:
                        continue
                elif create_fake_files and kwargs["to_disk"] and not filepath.is_file():
                    print(f"Creating fake file: {filename}")
                else:
                    continue

                if in_archive:
                    fin.seek(header["offset"])
                    data = fin.read(header["size"])
                else:
                    # NOTE: we create a fake file if it doesn't exist so the rebuilt
                    #       SIZES.ROM has the correct sizes for ALL non-archive files
                    data = b'\x00' * header["size"]

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
    dirpath         = pathlib.Path(kwargs["dirpath"])
    sizes_filepath  = pathlib.Path(kwargs["sizes_filepath"])
    disk_filepath   = pathlib.Path(kwargs["disk_filepath"])
    files_to_skip   = set(f.lower() for f in kwargs.get("files_to_not_include", ()))
    file_headers    = kwargs["file_headers"]

    print(f"Compiling {len(file_headers)} files into rom.")

    disk_filepath.parent.mkdir(parents=True, exist_ok=True)
    with disk_filepath.open("wb") as fout:
        for header in file_headers:
            filename  = header["filename"].as_posix()
            skip_file = filename.lower() in files_to_skip
            if skip_file:
                print(f"Compiling header-only: %s" % filename)
            else:
                print(f"Compiling file: %s" % filename)

            try:
                # read the data, and update the sizes/path hash/pointer
                filepath = pathlib.Path(dirpath, filename)
                with filepath.open("rb") as fin:
                    fin.seek(0, os.SEEK_END)
                    header["size"] = fin.tell()

                    if skip_file:
                        header["offset"] = -1
                        continue

                    fin.seek(0)
                    data = fin.read()

                header["offset"] = fout.tell()

                # write data and padding
                fout.write(data)
                fout.write(b'\x00' * util.calculate_padding(fout.tell(), c.DC_ROM_FILE_CHUNK_SIZE))
            except Exception:
                print(format_exc())
                print("Failed to compile '%s'" % header["filepath"])

    # write the headers after we've calculated all the offsets
    sizes_filepath.parent.mkdir(parents=True, exist_ok=True)
    with sizes_filepath.open("wb") as fout:
        util.write_file_headers(file_headers, fout)


class DcRomCompiler:
    dirpath  = ""
    sizes_filepath = ""
    disk_filepath  = ""

    overwrite = False
    parallel_processing = True
    create_fake_files = False

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
            create_fake_files=self.create_fake_files,
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
            files_to_extract_by_size.setdefault(
                header["size"] if header["offset"] > 0 else 0, []
                ).append(header)

        files_sorted_by_size = []
        for size in sorted(files_to_extract_by_size):
            files_sorted_by_size.extend(files_to_extract_by_size[size])

        all_job_args = [
            dict(
                file_headers=[], overwrite=self.overwrite, to_disk=True,
                sizes_filepath=self.sizes_filepath, dirpath=self.dirpath,
                disk_filepath=self.disk_filepath,
                create_fake_files=self.create_fake_files,
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
        self.disk_filepath  = pathlib.Path(self.disk_filepath)
        self.sizes_filepath = pathlib.Path(self.sizes_filepath)

        if self.disk_filepath.name and self.sizes_filepath.name:
            pass
        elif self.sizes_filepath.name:
            self.disk_filepath  = self.sizes_filepath.with_name("DISK.ROM")
        elif self.disk_filepath.name:
            self.sizes_filepath = self.disk_filepath.with_name("SIZES.ROM")
        else:
            self.disk_filepath  = pathlib.Path("DISK.ROM")
            self.sizes_filepath = pathlib.Path("SIZES.ROM")

        if not self.overwrite and (self.sizes_filepath.is_file() or
                                   self.disk_filepath.is_file()):
            return

        file_headers  = [
            dict(
                filename=filepath.relative_to(self.dirpath),
                size=0, offset=-1
                )
            for filepath in util.locate_target_platform_files(
                self.dirpath, want_dreamcast=True
                )
            if not (str(filepath).upper().endswith("DISK.ROM") or
                    str(filepath).upper().endswith("SIZES.ROM"))
            ]
        files_to_not_include = c.FILES_TO_EXCLUDE_FROM_ARCHIVE

        job_args = dict(
            file_headers=file_headers, dirpath=self.dirpath,
            files_to_not_include=files_to_not_include,
            sizes_filepath=self.sizes_filepath,
            disk_filepath=self.disk_filepath
            )

        util.process_jobs(_compile_rom, [job_args], process_count=1)
