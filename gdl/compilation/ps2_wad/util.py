import os
import struct

from ..util import *
from . import constants as c

INDEX_HEADER_STRUCT = struct.Struct("<iiIi")


def sanitize_filename(filename):
    return filename.upper().replace("/", "\\")


def is_compressible(filename):
    filename = sanitize_filename(filename)
    ext = os.path.splitext(filename)[-1].strip(".")
    if ext in c.PS2_WAD_UNCOMPRESSIBLE_EXTENSIONS:
        return False
    elif filename in c.PS2_WAD_UNCOMPRESSIBLE_FILEPATHS:
        return False
    return True


def locate_ps2_wad_files(wad_dir):
    wad_files = []
    for root, dirs, files in os.walk(wad_dir):
        for filename in files:
            ext = os.path.splitext(filename)[-1]
            if ext.lower().lstrip(".") in c.PS2_WAD_FILE_EXTENSIONS:
                wad_files.append(os.path.join(root, filename))
    return wad_files


def read_internal_names(input_buffer):
    filenames = []
    filename_count = struct.unpack('<I', input_buffer.read(4))[0]
    for i in range(filename_count):
        name_len = struct.unpack('<I', input_buffer.read(4))[0]
        filenames.append(input_buffer.read(name_len).decode("utf8"))

    return filenames


def write_internal_names(filenames, output_buffer):
    output_buffer.write(struct.pack('<I', len(filenames)))
    for filename in sorted(filenames):
        encoded_filename = filename.encode("utf8")
        output_buffer.write(struct.pack('<I', len(encoded_filename)))
        output_buffer.write(encoded_filename)


def read_file_headers(input_buffer):
    file_headers = []
    file_count = struct.unpack('<I', input_buffer.read(4))[0]
    for i in range(file_count):
        header = INDEX_HEADER_STRUCT.unpack(input_buffer.read(16))
        uncomp_size, data_pointer, path_hash, comp_size = header
        file_headers.append(dict(
            uncomp_size  = uncomp_size,
            data_pointer = data_pointer,
            path_hash    = path_hash,
            comp_size    = comp_size
            ))

    return file_headers


def concat_wad_files(wad_filepath, temp_wad_filepaths):
    # combine mini wads into final wad
    all_file_headers = []
    wad_concat_data = []
    for filepath in temp_wad_filepaths:
        with open(filepath, "rb") as f:
            file_headers = read_file_headers(f)

        all_file_headers.extend(file_headers)

        # calculate the start of the wad data
        base_pointer = 4 + 16*len(file_headers)
        base_pointer += calculate_padding(base_pointer, c.PS2_WAD_FILE_CHUNK_SIZE)

        # adjust pointers to start of data, and add up all file sizes
        wad_data_size = 0
        for file_header in file_headers:
            file_header["data_pointer"] -= base_pointer

            file_data_size = file_header[
                "uncomp_size" if file_header["comp_size"] < 0 else "comp_size"
                ]
            file_data_end = file_header["data_pointer"] + calculate_padding(
                file_data_size, c.PS2_WAD_FILE_CHUNK_SIZE)

            wad_data_size = max(wad_data_size, file_data_end)

        wad_concat_data.append(dict(
            filepath       = filepath,
            wad_data_start = base_pointer,
            wad_data_size  = wad_data_size,
            ))

    with open(wad_filepath, "wb") as fout:
        base_pointer = 4 + 16 * len(all_file_headers)
        base_pointer += calculate_padding(base_pointer, c.PS2_WAD_FILE_CHUNK_SIZE)

        # adjust pointers to start of wad
        for file_header in all_file_headers:
            file_header["data_pointer"] += base_pointer

        # write the file headers
        write_file_headers(all_file_headers, fout)

        # read the data section from each temp file and write it to the final wad
        for concat_data in wad_concat_data:
            data_remaining = concat_data["wad_data_size"]

            with open(concat_data["filepath"], "rb") as fin:
                fin.seek(concat_data["wad_data_start"])
                while data_remaining > 0:
                    data = fin.read(8 * 1024**2) # read and write in 8MB chunks
                    data_remaining -= len(data)
                    fout.write(data)


def write_file_headers(file_headers, output_buffer):
    output_buffer.write(struct.pack('<I', len(file_headers)))
    for header in file_headers:
        output_buffer.write(INDEX_HEADER_STRUCT.pack(
            header["uncomp_size"],
            header["data_pointer"],
            header["path_hash"],
            header["comp_size"],
            ))

    output_buffer.write(
        b'\x00' * calculate_padding(
            output_buffer.tell(), c.PS2_WAD_FILE_CHUNK_SIZE
            )
        )


def _mix_filepath_hash_values(x, y, z):
    vals = [v & 0xFFffFFff for v in (x, y, z)]

    # loop over the x, y, z values and mix them in 3 passes
    for i, shift in [
            (0, 13), (1,  8), (2, 13),
            (0, 12), (1, 16), (2,  5),
            (0,  3), (1, 10), (2, 15),
            ]:
        v = (vals[(i+2)%3] << shift if i % 2 else
             vals[(i+2)%3] >> shift)

        vals[i] = (v ^ (vals[i] - vals[(i+1)%3] - vals[(i+2)%3])) & 0xFFffFFff

    return vals


def hash_filepath(filepath):
    filepath = sanitize_filename(filepath)
    str_len = len(filepath)

    x = c.PS2_WAD_PATHHASH_SEED
    y = c.PS2_WAD_PATHHASH_SEED
    z = c.PS2_WAD_PATHHASH_CHUNK_SIZE + 1
    
    mix_length_at_end = str_len % c.PS2_WAD_PATHHASH_CHUNK_SIZE == 0

    # hash the filepath string
    for i in range(0, str_len, c.PS2_WAD_PATHHASH_CHUNK_SIZE):
        remainder = max(0, min(str_len - i, 12))

        # the first 2 sets of 4 bytes are always mixed the same, but the
        # third set of 4 changes depending on the remaining filepath length
        a = 1 if remainder < 12 else 0

        x += sum(ord(filepath[i + j    ]) << (8*j    ) for j in range(max(0, min(remainder,     4))))
        y += sum(ord(filepath[i + j + 4]) << (8*j    ) for j in range(max(0, min(remainder - 4, 4))))
        z += sum(ord(filepath[i + j + 8]) << (8*(j+a)) for j in range(max(0, min(remainder - 8, 4))))

        # mix the length into the hash on the last iteration
        if not mix_length_at_end and i + c.PS2_WAD_PATHHASH_CHUNK_SIZE > str_len:
            z += str_len

        x, y, z = _mix_filepath_hash_values(x, y, z)

    if mix_length_at_end:
        # one last mix round
        z += str_len
        x, y, z = _mix_filepath_hash_values(x, y, z)

    return z
