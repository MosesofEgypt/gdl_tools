from ...assets.scene_objects.scene_object import SceneObject
from ..model import load_model_from_objects_tag


def load_scene_object_from_tags(
        object_name, *, textures, objects_tag, global_tex_anims=(),
        ):
    object_name = object_name.upper().strip()
    scene_object = SceneObject(name=object_name)

    # load and attach model
    model = load_model_from_objects_tag(
        objects_tag, object_name, textures, global_tex_anims
        )
    scene_object.attach_model(model, object_name)

    return scene_object
