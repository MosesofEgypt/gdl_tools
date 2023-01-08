import time

from panda3d.core import PandaNode, LVecBase3f

from ...assets.scene_objects.scene_object import SceneObject
from ..model import load_model_from_objects_tag


def load_scene_object_from_tags(
        object_name, *, textures, objects_tag
        ):
    start = time.time()
    object_name = object_name.upper().strip()
    scene_object = SceneObject(name=object_name)

    # load and attach model
    model = load_model_from_objects_tag(objects_tag, object_name, textures)
    scene_object.attach_model(model, object_name)

    print("Loading scene object '%s' took %s seconds" % (object_name, time.time() - start))
    return scene_object
