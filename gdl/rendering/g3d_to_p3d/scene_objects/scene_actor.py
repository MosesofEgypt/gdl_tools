from panda3d.core import NodePath, PandaNode, LVecBase3f
from panda3d.physics import ActorNode

from ...assets.scene_objects.scene_actor import SceneActor
from ..model import load_model_from_objects_tag
from .. import util


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
        node_name = anode_info.mb_desc.upper().strip()
        p3d_node = PandaNode(node_name)
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
            name=node_name
            ))

    root_node  = None
    node_flags = {}
    for parent_index in sorted(node_map):
        # TODO: add checks to ensure parent exists
        parent_node = p3d_nodes.get(parent_index)

        for node_info in node_map[parent_index]:
            if parent_node is None:
                root_node = node_info["p3d_node"]
                break

            parent_node.addChild(node_info["p3d_node"])
            flags = node_info["flags"]
            node_flags[node_info["name"]] = dict(
                chrome          = bool(flags.chrome),
                framebuffer_add = bool(flags.fb_add),
                )

    if root_node is None:
        root_node = PandaNode("")
        node_flags = {}

    return root_node, node_flags


def load_scene_actor_from_tags(
        actor_name, *, anim_tag, textures, objects_tag=None
        ):
    actor_name = actor_name.upper().strip()
    actor_node = ActorNode(actor_name)

    nodes, node_flags = load_nodes_from_anim_tag(actor_name, anim_tag)
    actor_node.add_child(nodes)

    scene_actor = SceneActor(name=actor_name, p3d_node=actor_node)

    # load and attach models
    for model_name, node_name in zip(*anim_tag.get_model_node_name_map(actor_name)):
        model = load_model_from_objects_tag(objects_tag, model_name, textures)
        scene_actor.attach_model(model, node_name)
        flags = node_flags.get(node_name, {})

        for geometry in model.geometries:
            shader_updated = False
            if flags.get("chrome"):
                geometry.shader.chrome = shader_updated = True

            if flags.get("fb_add"):
                geometry.shader.framebuffer_add = shader_updated = True

            if shader_updated:
                geometry.apply_shader()

    return scene_actor
