import concurrent.futures
import os
import math
import string
import traceback
import pathlib


from .compilation.constants import WAD_LUMP_TYPES
from .supyr_struct_ext import FixedBytearrayBuffer,\
     BytearrayBuffer, BytesBuffer

# convert all possible byte values to the
# number of bits that are set in that value
BYTE_VALUES_TO_SET_BIT_COUNT = tuple(
    sum(bool(i & (1<<b)) for b in range(8))
    for i in range(256)
    )


def count_set_bits(byte_data):
    return sum(map(BYTE_VALUES_TO_SET_BIT_COUNT.__getitem__, byte_data))


_processing_pool = None

def process_jobs(job_function, all_job_args=(), process_count=None):
    results = []
    if process_count is None or process_count > 1:
        global _processing_pool
        if _processing_pool is None:
            _processing_pool = concurrent.futures.ProcessPoolExecutor(process_count)

        results.extend(_processing_pool.map(job_function, all_job_args))
    else:
        for job_args in all_job_args:
            try:
                results.append(job_function(job_args))
            except Exception:
                print(traceback.format_exc())

    return results


def get_is_arcade_wad(filepath):
    is_arcade = False
    filepath = pathlib.Path(filepath)
    try:
        # do a little peek to see if the file is arcade or not
        with filepath.open("rb") as f:
            wad_header_start = int.from_bytes(f.read(4), 'little')
            wad_header_count = int.from_bytes(f.read(4), 'little')
            # safety check in case file isn't a wad
            if wad_header_count > 50:
                return False

            for i in range(wad_header_count):
                f.seek(wad_header_start + (16 * i))
                lump_type = f.read(4).decode("latin-1")[::-1]
                if lump_type not in WAD_LUMP_TYPES:
                    is_arcade = True

    except Exception:
        pass

    return is_arcade


get_is_dreamcast_wad = get_is_arcade_wad


def index_count_to_string(index, count):
    return index_digits_to_string(index, int(math.ceil(math.log10(count))))


def index_digits_to_string(index, digits):
    return ("{i:0%sd}" % digits).format(i=index)


def generate_sequence_names(count, prefix, start_name="", start=0, step=1):
    if count < 1 or step < 1:
        return []

    parts  = start_name.split(prefix, 1)
    suffix = parts[1] if len(parts) == 2 else ""
    if (suffix and len(parts[0]) == 0 and set(suffix) == set(string.digits)):
        # start_name begins with prefix, and ends with a set of digits.
        # use the ending digits at the starting integer
        start = int(suffix)
    else:
        start_name = ""

    digits = int(len(suffix)-1)
    if count+start > 10**digits:
        digits = int(math.ceil(math.log10(count+start)))

    if not start_name:
        start_name = prefix + index_digits_to_string(start, digits)

    names = [
        prefix + index_digits_to_string(i, digits)
        for i in range(start, start + count*step, step)
        ]
    names[0] = start_name
    return names


def get_common_prefix(a, b):
    return (
        ""  if a[:1] != b[:1]  else
        a   if b.startswith(a) else
        b   if a.startswith(b) else
        a[:min((i for i, c in enumerate(zip(a, b)) if c[0] != c[1]))]
        )


def get_is_arcade_rom(filepath):
    name = pathlib.Path(filepath).stem.lower()
    if name in ("anim", "objects", "textures", "worlds",
                "dummy", "aud_data", "hstable_e", "hstable_j"):
        return True
    elif len(name) == 9 and name.startswith("passport"):
        return True
    elif len(name) == 6 and name.startswith("index"):
        return True
    return False


def get_is_dreamcast_rom(filepath):
    name = pathlib.Path(filepath).stem.lower()
    if name == "texdef":
        return True
    return get_is_arcade_rom(filepath)


def get_is_big_endian_texdef(filepath):
    with open(filepath, "rb") as f:
        bitmaps_count       = int.from_bytes(f.read(4), 'little')
        bitmap_defs_pointer = int.from_bytes(f.read(4), 'little')
        bitmaps_pointer     = int.from_bytes(f.read(4), 'little')
        file_end            = f.seek(0, os.SEEK_END)

    if (bitmaps_pointer > file_end or
        bitmap_defs_pointer > file_end or
        bitmaps_count > 0x8000):
        return True
    return False
