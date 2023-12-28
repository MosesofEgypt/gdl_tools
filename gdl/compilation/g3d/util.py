import string
from . import constants as c
from ..util import *


def locate_models(
        data_dir, cache_files=False, target_ps2=False,
        target_xbox=False, target_ngc=False,
        target_dreamcast=False, target_arcade=False,
        ):
    return locate_assets(data_dir,
        c.MODEL_ASSET_EXTENSIONS if not cache_files else
        (c.MODEL_CACHE_EXTENSION_XBOX, ) if target_xbox else
        (c.MODEL_CACHE_EXTENSION_NGC, )  if target_ngc else
        (c.MODEL_CACHE_EXTENSION_DC, )   if target_dreamcast else
        (c.MODEL_CACHE_EXTENSION_ARC, )  if target_arcade else
        (c.MODEL_CACHE_EXTENSION_PS2, )  if target_ps2 else
        ()
        )

def locate_textures(
        data_dir, cache_files=False, target_ps2=False,
        target_xbox=False, target_ngc=False,
        target_dreamcast=False, target_arcade=False
        ):
    return locate_assets(data_dir,
        c.TEXTURE_ASSET_EXTENSIONS if not cache_files else
        (c.TEXTURE_CACHE_EXTENSION_XBOX, ) if target_xbox else
        (c.TEXTURE_CACHE_EXTENSION_NGC, )  if target_ngc else
        (c.TEXTURE_CACHE_EXTENSION_DC, )   if target_dreamcast else
        (c.TEXTURE_CACHE_EXTENSION_ARC, )  if target_arcade else
        (c.TEXTURE_CACHE_EXTENSION_PS2, )  if target_ps2 else
        ()
        )

def locate_animations(data_dir, cache_files=False):
    return locate_assets(data_dir,
        c.ANIMATION_CACHE_EXTENSIONS if cache_files else
        c.ANIMATION_ASSET_EXTENSIONS
        )

def locate_metadata(data_dir, cache_files=False):
    return locate_assets(data_dir,
        c.METADATA_CACHE_EXTENSIONS if cache_files else
        c.METADATA_ASSET_EXTENSIONS
        )

def invert_map(mapping):
    if isinstance(mapping, dict):
        return {v: k for k, v in mapping.items()}
    elif isinstance(mapping, (list, tuple)):
        return {v: k for k, v in enumerate(mapping)}

    raise ValueError(f"Cannot invert mapping for type {type(mapping)}")

def dereference_indexed_values(indices, value_map):
    '''
    NOTE: This function returns a map iterator. To ensure
    the values it generates are concrete, you must pass it
    to a concrete iterable constructor(i.e. a list or tuple)
    '''
    return map(value_map.__getitem__, indices)


def _map_anim_nodes(src_nodes, dst_nodes, seen=()):
    if len(src_nodes) != len(dst_nodes):
        return None
    elif not src_nodes:
        return {}

    # make copies since we will be modifying them, and dont want our
    # modifications to travel up to the parent recursion calls
    seen = set(seen)
    node_map = {}
    dst_remaining = set(dst_nodes)
    for src_node_i in sorted(src_nodes):
        src_node     = src_nodes[src_node_i]
        src_children = src_node["children"]
        if src_node_i in seen:
            raise ValueError("Recursive hierarchy in nodes.")

        seen.add(src_node_i)
        for dst_node_i in sorted(dst_remaining):
            dst_node     = dst_nodes[dst_node_i]
            if src_node["name"] != dst_node["name"]:
                continue

            sub_node_map = _map_anim_nodes(src_children, dst_node["children"], seen)
            if sub_node_map is not None:
                node_map[src_node_i] = dst_node_i
                node_map.update(sub_node_map)
                dst_remaining.remove(dst_node_i)

    return None if dst_remaining else node_map


def map_src_anim_nodes_to_dst_anim_nodes(src_nodes, dst_nodes):
    if len(src_nodes) != len(dst_nodes):
        raise ValueError("Source and destination node array lengths do not"
                         f"match ({len(src_nodes)} vs {len(dst_nodes)})")

    src_nodes_list, dst_nodes_list = list(src_nodes), list(dst_nodes)
    for nodes_list in (src_nodes_list, dst_nodes_list):
        for i, node in enumerate(nodes_list):
            if hasattr(node, "name") and hasattr(node, "parent"): # AnimationCacheNode
                name    = node.name.upper().strip()
                parent  = node.parent
            elif hasattr(node, "name") and hasattr(node, "parent_index"): # JmsNode
                name    = node.name.upper().strip()
                parent  = node.parent_index
            elif isinstance(node, dict): # metadata dict
                name    = node.get("name", "").upper().strip()
                parent  = node.get("parent", -1)
            else:
                raise TypeError(f"Unknown anode type '{type(node)}'")

            nodes_list[i] = dict(name=name, parent=parent, children={})

    src_root_nodes, dst_root_nodes = {}, {}
    for nodes, roots in ([src_nodes_list, src_root_nodes],
                         [dst_nodes_list, dst_root_nodes]):
        for i, node in enumerate(nodes):
            (roots if node["parent"] < 0 else
             nodes[node["parent"]]["children"]
             )[i] = node

    index_map = _map_anim_nodes(src_root_nodes, dst_root_nodes)
    if index_map is None:
        raise ValueError("Unable to map source nodes to destination nodes.")

    return index_map
