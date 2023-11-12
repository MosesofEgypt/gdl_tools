import os
import pathlib
import tempfile

from traceback import format_exc
from .arcade_hdd import constants as c
from .arcade_hdd import util


def _extract_files(kwargs):
    file_buffers = {}
    file_headers = kwargs["file_headers"]
    hdd_filepath = pathlib.Path(kwargs["hdd_filepath"])
    hdd_dirpath  = pathlib.Path(kwargs["hdd_dirpath"])

    with hdd_filepath.open("rb") as fin:
        for filename in sorted(file_headers):
            filepath = hdd_dirpath.joinpath(filename.lstrip('/'))
            if not kwargs["overwrite"] and filepath.is_file():
                continue

            if kwargs["to_disk"]:
                print(f"Extracting file: %s" % filename)
            else:
                print(f"Reading file: %s" % filename)

            try:
                file_data = util.read_file_fragments(
                    block_header=file_headers[filename],
                    rawdata=fin, disc=kwargs.get("disc", 0)
                    )
                if kwargs.get("skip_empty") and not file_data:
                    continue

                if kwargs["to_disk"]:
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    with filepath.open("wb") as fout:
                        fout.write(file_data)
                else:
                    file_buffers[filename] = file_data

            except Exception:
                print(format_exc())
                print(f"Failed to extract '{filepath}'")

    return file_buffers


def _compile_hdd(kwargs):
    # TODO: implement this
    pass


class ArcadeHddCompiler:
    hdd_dirpath  = "."
    hdd_filepath = ""
    disc = 0

    overwrite = False
    skip_empty = True
    parallel_processing = True

    file_headers = ()
    dir_tree = ()
    flat_file_list = ()

    def __init__(self, **kwargs):
        # simple initialization setup where kwargs are
        # copied into the attributes of this new class
        self.dir_tree = {}
        self.flat_file_map = {}
        self.file_headers = []
        for k, v in kwargs.items():
            setattr(self, k, v)

    def _get_file_headers_for_filenames(self, filenames=None, ignore_case=False):
        if filenames is None:
            filenames = self.flat_file_map.keys()

        file_map = self.flat_file_map
        if ignore_case:
            file_map = {k.lower(): v for k, v in file_map}
            file_headers = {
                filename: file_map[filename.lower()]
                for filename in filenames
                if filename.lower() in file_map
                }
        else:
            file_headers = {
                filename: file_map[filename]
                for filename in filenames
                if filename in file_map
                }
        return file_headers

    def load_hdd(self):
        print(self.hdd_dirpath)
        self.file_headers = util.read_file_headers(
            filepath=self.hdd_filepath, disc=self.disc
            )
        self.dir_tree = util.parse_directory_tree(
            file_headers=self.file_headers,
            filepath=self.hdd_filepath, disc=self.disc
            )
        self.flat_file_map = util.flatten_directory_tree(self.dir_tree)

    def extract_file(self, file_header):
        datas = self.extract_files(file_headers=[file_header])
        return datas[tuple(datas.keys())[0]] if datas else None

    def extract_files(self, filenames=None, ignore_case=False):
        file_headers = self._get_file_headers_for_filenames(filenames, ignore_case)

        return _extract_files(dict(
            file_headers=file_headers, overwrite=self.overwrite,
            to_disk=False, skip_empty=False, disc=self.disc,
            hdd_filepath=self.hdd_filepath, hdd_dirpath=self.hdd_dirpath,
            ))

    def extract_file_to_disk(self, filename):
        self.extract_files_to_disk(filenames=[filename])

    def extract_files_to_disk(self, filenames=None, ignore_case=False):
        file_headers = self._get_file_headers_for_filenames(filenames, ignore_case)

        all_job_args = [
            dict(
                file_headers={}, overwrite=self.overwrite,
                to_disk=True, skip_empty=self.skip_empty, disc=self.disc,
                hdd_filepath=self.hdd_filepath, hdd_dirpath=self.hdd_dirpath,
                )
            for i in range(os.cpu_count() if self.parallel_processing else 1)
            ]

        # attempt to distribute files across jobs so each job
        # extracts similar amounts of data and file counts
        names_to_extract_by_size = {}
        names_sorted_by_size = []

        for name, header in file_headers.items():
            names_to_extract_by_size.setdefault(header.data_size, []).append(name)

        for size in sorted(names_to_extract_by_size):
            names_sorted_by_size.extend(names_to_extract_by_size[size])

        for i in range(len(names_sorted_by_size)):
            name = names_sorted_by_size[i]
            all_job_args[i % len(all_job_args)]["file_headers"][name] = file_headers[name]

        util.process_jobs(
            _extract_files, all_job_args,
            process_count=None if self.parallel_processing else 1
            )

    def compile(self):
        # TODO
        pass
