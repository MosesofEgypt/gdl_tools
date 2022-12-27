from .model import load_model_from_objects_tag


def load_node_path_from_anim_tag(anim_tag, object_name):
    pass
    # TODO: write this


def load_scene_object_from_tags(
        object_name, anim_tag, objects_tag=None, textures_filepath=None
        ):
    skeleton = load_node_path_from_anim_tag(anim_tag, object_name)
    model_names = ()

    for model_name in model_names:
        model = load_model_from_objects_tag(objects_tag, model_name)

    # TODO: write this
