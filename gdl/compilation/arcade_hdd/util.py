import os

from supyr_struct.buffer import get_rawdata_context
from ..util import *
from . import constants as c
from . import hdd_def


class BlockHeader:
    '''
    This utility class exists to hold all important information contained
    in a BlockHeader struct. This class is serializable, so it works with
    parallel processing, while supyr_struct objects do not.
    '''
    block_type = c.REGULAR_FILE_SIG
    file_type  = c.FILE_BLOCK_TYPE_REGULAR
    data_size = 0
    sectors_used = 0
    checksum  = '00'*4
    fragments_pri = (0, 0) * 20
    fragments_sec = (0, 0) * 20
    fragments_ter = (0, 0) * 20

    def __init__(self, **kwargs):
        self.block_type     = int(kwargs.get("block_type", self.block_type))
        self.file_type      = int(kwargs.get("file_type", self.file_type))
        self.data_size      = int(kwargs.get("data_size", self.data_size))
        self.sectors_used   = int(kwargs.get("sectors_used", self.sectors_used))
        self.checksum       = str(kwargs.get("checksum", self.checksum))
        self.fragments_pri = tuple(kwargs.get("fragments_pri", self.fragments_pri))
        self.fragments_sec = tuple(kwargs.get("fragments_sec", self.fragments_sec))
        self.fragments_ter = tuple(kwargs.get("fragments_ter", self.fragments_ter))


def is_arcade_hdd(filepath):
    try:
        # check for a couple header signatures
        with open(filepath, "rb") as f:
            f.seek(512)
            if int.from_bytes(f.read(4), 'little') != c.MBR_HEADER_SIG:
                return False

            f.seek(512 + 56)
            if int.from_bytes(f.read(4), 'little') != c.UNKNOWN_MBR_SIG:
                return False

            return True

    except Exception:
        pass

    return False


def is_arcade_chd(filepath):
    try:
        # check for a couple header signatures
        with open(filepath, "rb") as f:
            signature  = f.read(8)
            header_len = int.from_bytes(f.read(4), 'big')
            version    = int.from_bytes(f.read(4), 'big')
            if signature != c.CHD_SIGNATURE:
                return False

            # current version is v5, with a header length of 124 bytes.
            # future-proof a little by giving the format room to grow
            if header_len > 256 or version > 16:
                return False

            return True

    except Exception:
        pass

    return False


def read_file_fragments(*, block_header, rawdata, disc=0):
    fragments = (
        block_header.fragments_ter if disc == 2 else
        block_header.fragments_sec if disc == 1 else
        block_header.fragments_pri
        )

    data_remaining = block_header.data_size
    ft_data = b''

    for i in range(0, len(fragments), 2):
        # read in and concatenate all fragments of the file
        read_size = min(data_remaining, fragments[i+1] * c.SECTOR_SIZE)
        if read_size <= 0:
            break

        rawdata.seek(fragments[i]*c.SECTOR_SIZE)
        ft_data += rawdata.read(read_size)
        data_remaining = max(0, data_remaining - read_size)

    return ft_data


def read_file_table(*, filepath=None, rawdata=None, disc=0):
    assert disc in (0, 1, 2)
    with get_rawdata_context(filepath=filepath, rawdata=rawdata) as fin:
        hdd_block = hdd_def.hdd_def.build(rawdata=fin)
        ft_header = (
            hdd_block.file_table_header_ter if disc == 2 else
            hdd_block.file_table_header_sec if disc == 1 else
            hdd_block.file_table_header_pri
            )
        ft_data = read_file_fragments(
            block_header=ft_header, rawdata=fin, disc=disc
            )

    file_table = hdd_def.file_table_def.build(rawdata=ft_data)
    return file_table.file_table


def read_file_headers(*, file_table=None, filepath=None, rawdata=None, disc=0):
    assert disc in (0, 1, 2)

    if file_table is None:
        file_table = read_file_table(
            filepath=filepath, rawdata=rawdata, disc=disc
            )

    headers = []
    with get_rawdata_context(filepath=filepath, rawdata=rawdata) as fin:
        for record in file_table:
            header = hdd_def.block_header_def.build(
                rawdata=fin, offset=record[disc] * c.SECTOR_SIZE
                ).block_header

            headers.append(
                BlockHeader(
                    block_type=header.block_type.data,
                    file_type=header.file_type.data,
                    data_size=header.data_size,
                    sectors_used=header.sectors_used,
                    checksum=header.checksum0,
                    fragments_pri=header.fragments_pri,
                    fragments_sec=header.fragments_sec,
                    fragments_ter=header.fragments_ter,
                    )
                )

    return headers


def parse_directory_tree(*, file_headers=None, filepath=None, rawdata=None, disc=0):
    if file_headers is None:
        file_headers = read_file_headers(
            filepath=filepath, rawdata=rawdata, disc=disc
            )

    dir_tree = {
        'unknown': file_headers[c.UNKNOWN_FILE_INDEX]
        }
    dir_flat = {
        c.ROOT_DIR_INDEX: dir_tree,
        c.UNKNOWN_FILE_INDEX: file_headers[c.UNKNOWN_FILE_INDEX]
        }

    dir_blocks = {
        c.ROOT_DIR_INDEX: file_headers[c.ROOT_DIR_INDEX]
        }
    with get_rawdata_context(filepath=filepath, rawdata=rawdata) as fin:
        while dir_blocks:
            next_dir_blocks = {}
            for dir_idx, dir_block in dir_blocks.items():
                if dir_block.file_type != c.FILE_BLOCK_TYPE_DIRECTORY:
                    continue

                dir_data = read_file_fragments(
                    block_header=dir_block, rawdata=fin, disc=disc
                    )
                dir_list = hdd_def.dir_entry_list_def.build(rawdata=dir_data).dir_entry_list

                parent_dir_dict = dir_flat[dir_idx]
                for dir_entry in dir_list:
                    if dir_entry.table_index in dir_flat:
                        continue

                    idx = dir_entry.table_index
                    file_header = file_headers[idx]

                    if file_headers[idx].file_type == c.FILE_BLOCK_TYPE_DIRECTORY:
                        dir_entry_block = {}  # regular dict to hold all files and dir dicts
                        next_dir_blocks[idx] = file_header
                    else:
                        dir_entry_block = file_header

                    dir_flat[idx] = dir_entry_block
                    parent_dir_dict[dir_entry.name] = dir_entry_block

            dir_blocks = next_dir_blocks

    return dir_tree


def _flatten_directory_tree(dir_tree, seen, root_dir):
    curr_dir_files = {}
    for name, block in dir_tree.items():
        curr_path = "%s/%s" % (root_dir, name)
        if id(block) in seen:
            continue

        seen.add(id(block))
        if isinstance(block, dict):
            # directory. append name to root_dir and call recursive
            curr_dir_files.update(_flatten_directory_tree(
                block, seen, curr_path
                ))
        else:
            curr_dir_files[curr_path] = block

    return curr_dir_files


def flatten_directory_tree(dir_tree):
    return _flatten_directory_tree(dir_tree, set(), "")


def _dump_hdd(dir_tree, output_path, rawdata, disc, skip_empty):
    for name, block in dir_tree.items():
        if isinstance(block, dict):
            # directory. append name to output path and call recursive
            _dump_hdd(block, f"{output_path}/{name}", rawdata, disc, skip_empty)
            continue

        file_data = read_file_fragments(
            block_header=block, rawdata=rawdata, disc=disc
            )
        if skip_empty and not file_data:
            continue

        os.makedirs(output_path, exist_ok=True)
        with open(f"{output_path}/{name}", "wb") as fout:
            fout.write(file_data)


def dump_hdd(*, output_dir, filepath=None, rawdata=None, disc=0, skip_empty=True):
    dir_tree = parse_directory_tree(
        filepath=filepath, rawdata=rawdata, disc=disc
        )
    with get_rawdata_context(filepath=filepath, rawdata=rawdata) as fin:
        _dump_hdd(dir_tree, output_dir, fin, disc, skip_empty)
