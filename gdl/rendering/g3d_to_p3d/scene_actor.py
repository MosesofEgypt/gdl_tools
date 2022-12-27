from ..assets.scene_actor import SceneActor
from .model import load_model_from_objects_tag
from .scene_object import load_node_path_from_anim_tag
from . import util


def load_scene_actor_from_tags(
        actor_name, anim_tag, objects_tag=None, textures_filepath=None
        ):
    skeleton = load_node_path_from_anim_tag(anim_tag, actor_name)
    model_names = ()

    for model_name in model_names:
        model = load_model_from_objects_tag(objects_tag, model_name)    

    # TODO: write this
