import os

from supyr_struct.buffer import get_rawdata_context
from ..defs.arcade_hdd import arcade_hdd_def, dir_entry_list_def,\
     file_table_def, block_header_def, SECTOR_SIZE,\
     FILE_BLOCK_TYPE_DIRECTORY


# root of tree is file header 2(0 is the file table, and 1 is unknown)
FILE_TABLE_INDEX   = 0
UNKNOWN_FILE_INDEX = 1
ROOT_DIR_INDEX     = 2


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
        read_size = min(data_remaining, fragments[i+1]*SECTOR_SIZE)
        if read_size <= 0:
            break

        rawdata.seek(fragments[i]*SECTOR_SIZE)
        ft_data += rawdata.read(read_size)
        data_remaining = max(0, data_remaining - read_size)

    return ft_data


def read_file_table(*, filepath=None, rawdata=None, disc=0):
    assert disc in (0, 1, 2)
    with get_rawdata_context(filepath=filepath, rawdata=rawdata) as fin:
        hdd_block = arcade_hdd_def.build(rawdata=fin)
        ft_header = (
            hdd_block.file_table_header_ter if disc == 2 else
            hdd_block.file_table_header_sec if disc == 1 else
            hdd_block.file_table_header_pri
            )
        ft_data = read_file_fragments(
            block_header=ft_header, rawdata=fin, disc=disc
            )

    file_table = file_table_def.build(rawdata=ft_data)
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
            header = block_header_def.build(
                rawdata=fin, offset=record[disc] * SECTOR_SIZE
                )
            headers.append(header.block_header)

    return headers


def parse_directory_tree(*, file_headers=None, filepath=None, rawdata=None, disc=0):
    if file_headers is None:
        file_headers = read_file_headers(
            filepath=filepath, rawdata=rawdata, disc=disc
            )

    dir_tree = {
        'unknown': file_headers[UNKNOWN_FILE_INDEX]
        }
    dir_flat = {
        ROOT_DIR_INDEX: dir_tree,
        UNKNOWN_FILE_INDEX: file_headers[UNKNOWN_FILE_INDEX]
        }

    dir_blocks  = {ROOT_DIR_INDEX: file_headers[ROOT_DIR_INDEX]}
    with get_rawdata_context(filepath=filepath, rawdata=rawdata) as fin:
        while dir_blocks:
            next_dir_blocks = {}
            for dir_idx, dir_block in dir_blocks.items():
                if dir_block.file_type.data != FILE_BLOCK_TYPE_DIRECTORY:
                    continue

                dir_data = read_file_fragments(
                    block_header=dir_block, rawdata=fin, disc=disc
                    )
                dir_list = dir_entry_list_def.build(rawdata=dir_data).dir_entry_list

                parent_dir_dict = dir_flat[dir_idx]
                for dir_entry in dir_list:
                    if dir_entry.table_index in dir_flat:
                        continue

                    idx = dir_entry.table_index
                    file_header = file_headers[idx]

                    if file_headers[idx].file_type.data == FILE_BLOCK_TYPE_DIRECTORY:
                        dir_entry_block = {}  # regular dict to hold all files and dir dicts
                        next_dir_blocks[idx] = file_header
                    else:
                        dir_entry_block = file_header

                    dir_flat[idx] = dir_entry_block
                    parent_dir_dict[dir_entry.name] = dir_entry_block

            dir_blocks = next_dir_blocks

    return dir_tree


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
