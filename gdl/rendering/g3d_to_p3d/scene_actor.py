import time

from panda3d.core import NodePath
from panda3d.physics import ActorNode

from ..assets.scene_actor import SceneActor
from .model import load_model_from_objects_tag
from .texture import load_textures_from_objects_tag
from .scene_object import get_model_node_name_map, load_nodes_from_anim_tag
from . import util


def load_scene_actor_from_tags(
        actor_name, *, anim_tag, objects_tag=None,
        textures_filepath=None, is_ngc=False
        ):
    actor_name = actor_name.upper().strip()
    actor_node = ActorNode(actor_name)
    actor_node.add_child(load_nodes_from_anim_tag(actor_name, anim_tag))

    scene_actor = SceneActor(name=actor_name, p3d_node=actor_node)

    print("Loading textures")
    start = time.time()
    textures = load_textures_from_objects_tag(
        objects_tag, textures_filepath, is_ngc
        )
    print("Finished. Took %s seconds" % (time.time() - start))

    # load and attach models
    print("Loading world objects")
    start = time.time()
    _, bitmap_names = objects_tag.get_cache_names()
    for model_name, node_name in zip(*get_model_node_name_map(actor_name, anim_tag)):
        model = load_model_from_objects_tag(
            objects_tag, model_name, textures, bitmap_names
            )
        scene_actor.attach_model(model, node_name)

    print("Finished. Took %s seconds" % (time.time() - start))
    return scene_actor
