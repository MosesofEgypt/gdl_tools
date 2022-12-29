from panda3d.core import PandaNode, LVecBase3f

from ..assets.scene_object import SceneObject
from .model import load_model_from_objects_tag
from .texture import load_textures_from_objects_tag


def load_nodes_from_anim_tag(object_name, anim_tag):
    anodes = ()
    for atree in anim_tag.data.atrees:
        if atree.name.upper().strip() == object_name.upper().strip():
            anodes = atree.atree_header.atree_data.anode_infos
            break

    root_node = None
    p3d_nodes = {}
    node_map = {}
    for anode_info in anodes:
        p3d_node = PandaNode(anode_info.mb_desc.upper().strip())
        x, y, z = anode_info.init_pos

        node_trans = p3d_node.get_transform().set_pos(
            LVecBase3f(x, z, y)
            )

        p3d_node.set_transform(node_trans)

        p3d_nodes[len(p3d_nodes)] = p3d_node
        node_map.setdefault(anode_info.parent_index, []).append(dict(
            node_type=anode_info.anim_type.enum_name,
            flags=anode_info.mb_flags,
            p3d_node=p3d_node,
            ))

    root_node = None
    for parent_index in sorted(node_map):
        # TODO: add checks to ensure parent exists
        parent_node = p3d_nodes.get(parent_index)

        for node_info in node_map[parent_index]:
            if parent_node is None:
                root_node = node_info["p3d_node"]
                break

            parent_node.addChild(node_info["p3d_node"])

    return root_node if root_node is not None else PandaNode("")


def get_model_node_name_map(object_name, anim_tag):
    model_names = []
    node_names = []
    atree_header = None
    for atree in anim_tag.data.atrees:
        if atree.name.upper().strip() == object_name.upper().strip():
            atree_header = atree.atree_header
            break

    if atree_header:
        for anode in atree_header.atree_data.anode_infos:
            if anode.flags.no_object_def:
                continue

            model_names.append(atree_header.prefix + anode.mb_desc)
            node_names.append(anode.mb_desc)

    return model_names, node_names


def load_scene_object_from_tags(
        object_name, *, anim_tag, objects_tag=None,
        textures_filepath=None, is_ngc=False
        ):
    object_name = object_name.upper().strip()
    skeleton = load_nodes_from_anim_tag(object_name, anim_tag)
    scene_object = SceneObject(name=object_name, p3d_node=skeleton)

    textures = load_textures_from_objects_tag(
        objects_tag, textures_filepath, is_ngc
        )
    for model_name, node_name in zip(*get_model_node_name_map(object_name, anim_tag)):
        model = load_model_from_objects_tag(objects_tag, model_name, textures)
        scene_object.attach_model(model, node_name)

    return scene_object
