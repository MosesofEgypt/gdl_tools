
from ..util import *


def comp_keyframe_data_to_uncomp(indices, values):
    return tuple(dereference_indexed_values(indices, values))


def combine_uncomp_values(*value_sets):
    all_values = set()
    [map(all_values.update, value_set) for value_set in value_sets]
    return tuple(sorted(all_values))


def rebase_comp_keyframe_data(indices, src_values, dst_values):
    return tuple(dereference_indexed_values(
        dereference_indexed_values(indices, src_values),
        invert_map(dst_values)
        ))


def combine_compressed_keyframe_data(*indices_and_values_pairs):
    for pair in indices_and_values_pairs:
        if not(isinstance(pair, tuple) and
               hasattr(pair[0], "__iter__") and
               hasattr(pair[1], "__iter__")):
            raise ValueError("Must pass in indices and values as tuple pairs.")

    combined_values = combine_uncomp_values(v for i, v in indices_and_values_pairs)
    return tuple(
        rebase_comp_keyframe_data(i, v, combined_values)
        for i, v in indices_and_values_pairs
        )


def reduce_compressed_keyframe_data(*indices_arrays, all_values):
    value_map   = invert_map(all_values)
    results     = [None] * len(indices_arrays)

    for i, indices in enumerate(indices_arrays):
        uncomp_data     = comp_keyframe_data_to_uncomp(indices, all_values)
        reduced_values  = tuple(sorted(set(uncomp_data)))
        reduced_indices = tuple(dereference_indexed_values(
            uncomp_data, invert_map(reduced_values)
            ))
        results[i]      = (reduced_indices, reduced_values)

    return results


def reduce_compressed_data(nodes, comp_angles, comp_positions, comp_scales):
    '''
    The goal of this function is to reduce the amount of angles,
    positions, and scales in the compressed data arrays. This is
    done by removing any values that arent referenced by the frame
    data indices, and rebasing indices to the reduced values set.
    '''
    all_angle_indices       = set()
    all_position_indices    = set()
    all_scale_indices       = set()
    for node in nodes:
        if not node.compressed: continue

        off     = 0
        stride  = node.frame_size
        for flag, indices in (
            (node.rot_x,    all_angle_indices),
            (node.rot_y,    all_angle_indices),
            (node.rot_z,    all_angle_indices),
            (node.pos_x,    all_position_indices),
            (node.pos_y,    all_position_indices),
            (node.pos_z,    all_position_indices),
            (node.scale_x,  all_scale_indices),
            (node.scale_y,  all_scale_indices),
            (node.scale_z,  all_scale_indices),
            ):
            if flag:
                indices.update(node.keyframe_data[off::stride])
                off += 1

    _, reduced_angles = reduce_compressed_keyframe_data(
        tuple(all_angle_indices), all_values=comp_angles
        )[0]
    _, reduced_positions = reduce_compressed_keyframe_data(
        tuple(all_position_indices), all_values=comp_positions
        )[0]
    _, reduced_scales = reduce_compressed_keyframe_data(
        tuple(all_scale_indices), all_values=comp_scales
        )[0]
    ang_reduced = len(reduced_angles)    != len(comp_angles)
    pos_reduced = len(reduced_positions) != len(comp_positions)
    sca_reduced = len(reduced_scales)    != len(comp_scales)

    new_keyframe_datas = {}

    # to save time, only iterate if something was reduced.
    if ang_reduced or pos_reduced or sca_reduced:
        for i, node in enumerate(nodes):
            if not node.compressed: continue

            off           = 0
            stride        = node.frame_size
            keyframe_data = new_keyframe_datas[i] = list(node.keyframe_data)

            for rebase, flag, full, reduced in (
                (ang_reduced, node.rot_x,   comp_angles,    reduced_angles),
                (ang_reduced, node.rot_y,   comp_angles,    reduced_angles),
                (ang_reduced, node.rot_z,   comp_angles,    reduced_angles),
                (pos_reduced, node.pos_x,   comp_positions, reduced_positions),
                (pos_reduced, node.pos_y,   comp_positions, reduced_positions),
                (pos_reduced, node.pos_z,   comp_positions, reduced_positions),
                (sca_reduced, node.scale_x, comp_scales,    reduced_scales),
                (sca_reduced, node.scale_y, comp_scales,    reduced_scales),
                (sca_reduced, node.scale_z, comp_scales,    reduced_scales),
                ):
                if rebase and flag:
                    keyframe_data[off::stride] = rebase_comp_keyframe_data(
                        node.keyframe_data[off::stride], full, reduced
                        )
                off += flag

    if ang_reduced: comp_angles    = reduced_angles
    if pos_reduced: comp_positions = reduced_positions
    if sca_reduced: comp_scales    = reduced_scales

    return new_keyframe_datas, comp_angles, comp_positions, comp_scales


def validate_hierarchy(nodes):
    root_node   = None
    node_map    = {}
    seen_nodes  = set()
    for i, node in enumerate(nodes):
        if node.type_name == "skeletal":
            pass
        elif node.flags:
            raise ValueError(
                f"Unsupported flags set in {node.type_name} "
                f"node '{node.name}' at index {i}.")
        elif node.frame_flags:
            raise ValueError(
                f"Unsupported frame_flags set in {node.type_name} "
                f"node '{node.name}' at index {i}.")
        elif node.initial_keyframe:
            raise ValueError(
                f"Unsupported initial_keyframe data in {node.type_name} "
                f"node '{node.name}' at index {i}.")
        elif node.keyframe_data:
            raise ValueError(
                f"Unsupported keyframe_data in {node.type_name} "
                f"node '{node.name}' at index {i}.")

        node_map.setdefault(node.parent, {})[i] = node_map.setdefault(i, {})
        if node.parent < 0:
            root_node = node_map[i]
            seen_nodes.add(i)

    if root_node is None:
        raise ValueError("Could not locate root node in atree.")

    curr_nodes = tuple(root_node.items())
    while curr_nodes:
        next_nodes = ()
        for i, node in curr_nodes:
            next_nodes += tuple(node.items())
            seen_nodes.add(i)

        curr_nodes = next_nodes

    if len(seen_nodes) != len(nodes):
        raise ValueError("Orphaned nodes detected in atree.")
