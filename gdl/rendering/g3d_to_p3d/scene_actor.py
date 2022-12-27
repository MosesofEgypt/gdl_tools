from panda3d.core import NodePath
from panda3d.physics import ActorNode

from ..assets.scene_actor import SceneActor
from .model import load_model_from_objects_tag
from .scene_object import get_model_node_name_map, load_nodes_from_anim_tag
from . import util


def load_scene_actor_from_tags(
        actor_name, anim_tag, objects_tag=None, textures_filepath=None
        ):
    actor_node = ActorNode(actor_name)
    actor_node.add_child(load_nodes_from_anim_tag(anim_tag, actor_name))

    scene_actor = SceneActor(name=actor_name, p3d_node=actor_node)

    for model_name, node_name in zip(*get_model_node_name_map(actor_name, anim_tag)):
        model = load_model_from_objects_tag(objects_tag, model_name)
        scene_actor.attach_model(model, node_name)

    return scene_actor
