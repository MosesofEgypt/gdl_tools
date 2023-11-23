import os
import struct
import pathlib

from supyr_struct.buffer import get_rawdata_context
from ..util import *
from . import constants as c
from . import rom_def

INDEX_HEADER_STRUCT = struct.Struct("<IIhhhh")


def is_dc_sizes_rom(filepath):
    unpacker = INDEX_HEADER_STRUCT.unpack_from
    try:
        with open(filepath, "rb") as f:
            entry_count = int.from_bytes(f.read(4), 'little')
            # check there's no way too many files, or way too few
            if (entry_count > c.DC_ROM_MAX_FILE_COUNT or
                entry_count < 100):
                return False

            entry_data = f.read(entry_count * 16)
            path_strings_start = f.tell()
            f.seek(0, os.SEEK_END)
            path_strings_len = f.tell() - path_strings_start

        # check every entry and ensure the path strings are appropriate
        for i in range(0, 16*entry_count, 16):
            struct_data = unpacker(entry_data, i)
            size, off, p0_off, p1_off, p2_off, p3_off = struct_data
            if p0_off == -1: p1_off = p0_off
            if p1_off == -1: p2_off = p1_off
            if p2_off == -1: p3_off = p2_off

            if ((p0_off != -1 and p0_off < 0) or p0_off > path_strings_len or
                (p1_off != -1 and p1_off < 0) or p1_off > path_strings_len or
                (p2_off != -1 and p2_off < 0) or p2_off > path_strings_len or
                (p3_off != -1 and p3_off < 0) or p3_off > path_strings_len):
                return False

        return True
    except Exception:
        pass

    return False


def locate_dreamcast_rom_files(wad_dir):
    return locate_target_platform_files(wad_dir, want_dreamcast=True)


def read_file_headers(filepath):
    dc_rom = rom_def.dc_rom_def.build(filepath=filepath)
    rawdata = dc_rom.path_string_data

    file_headers = []
    for file_header in dc_rom.file_headers:
        path_parts = []
        for off in file_header.path_part_offsets:
            if off < 0: break
            end = rawdata.find(b"\x00", off)
            if end < 0: str_end = len(rawdata)
            path_parts.append(rawdata[off: end].decode("latin-1"))

        file_headers.append(dict(
            filename    = pathlib.Path(*path_parts),
            size        = file_header.size,
            offset      = file_header.offset,
            ))

    return file_headers


def write_file_headers(file_headers):
    dc_rom = rom_def.dc_rom_def.build()
    dc_rom_headers = dc_rom.file_headers

    path_string_offsets = {}
    str_data_len = 0

    for header in file_headers:
        path_parts = pathlib.Path(header["filename"]).parts
        if len(path_parts) > 4:
            raise ValueError("Cannot nest files deeper than 3 directories.")

        dc_rom_headers.append()
        dc_rom_header = dc_rom_headers[-1]
        dc_rom_header.size   = header["size"]
        dc_rom_header.offset = header["offset"]
        path_part_offsets    = dc_rom_header.path_part_offsets

        for i, part in enumerate(path_parts):
            part = part.lower() + "\x00"
            if part not in path_string_offsets:
                path_string_offsets[part] = str_data_len
                str_data_len += len(part)

            path_part_offsets[i] = path_string_offsets[part]

        if i < 3:
            path_part_offsets[i + 1] = -1

    path_string_offsets_inv = {v: k for k, v in path_string_offsets.items()}
    dc_rom.path_string_data = b''.join(
        path_string_offsets_inv[k].encode("latin-1")
        for k in sorted(path_string_offsets_inv)
        )
    return dc_rom.serialize()
