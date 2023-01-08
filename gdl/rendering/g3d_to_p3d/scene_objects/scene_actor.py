import time

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


def load_scene_actor_from_tags(
        actor_name, *, anim_tag, textures, objects_tag=None
        ):
    start = time.time()
    actor_name = actor_name.upper().strip()
    actor_node = ActorNode(actor_name)
    actor_node.add_child(load_nodes_from_anim_tag(actor_name, anim_tag))

    scene_actor = SceneActor(name=actor_name, p3d_node=actor_node)

    # load and attach models
    for model_name, node_name in zip(*anim_tag.get_model_node_name_map(actor_name)):
        model = load_model_from_objects_tag(objects_tag, model_name, textures)
        scene_actor.attach_model(model, node_name)

    #print("Loading scene actor '%s' took %s seconds" % (actor_name, time.time() - start))
    return scene_actor
