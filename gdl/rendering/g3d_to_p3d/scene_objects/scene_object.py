from ...assets.scene_objects.scene_object import SceneObject
from ..model import load_model_from_objects_tag


def load_scene_object_from_tags(
        object_name, *, textures, objects_tag,
        global_tex_anims=(), is_static=False, p3d_model=None
        ):
    model = load_model_from_objects_tag(
        objects_tag, object_name, textures,
        global_tex_anims, is_static=is_static,
        p3d_model=p3d_model
        )
    scene_object = SceneObject(
        name=model.name, p3d_node=model.p3d_model
        )
    scene_object.add_model(model)

    return scene_object
