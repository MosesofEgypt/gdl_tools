import time

from ...assets.scene_objects.scene_world_object import SceneWorldObject
from ..model import load_model_from_objects_tag


def load_scene_world_object_from_tags(
        world_object, *, textures, worlds_tag, objects_tag
        ):
    scene_world_object = SceneWorldObject(name=world_object.name)

    model = load_model_from_objects_tag(
        objects_tag, world_object.name, textures
        )

    additive_diffuse = False #world_object.flags.unknown
    chrome = False
    for geom in model.geometries:
        shader_updated = False
        if chrome:
            geom.shader.chrome = shader_updated = True

        if additive_diffuse:
            geom.shader.additive_diffuse = shader_updated = True

        if shader_updated:
            geom.apply_shader()

    scene_world_object.attach_model(model, scene_world_object.name)
    #print("Loading scene object '%s' took %s seconds" % (object_name, time.time() - start))
    return scene_world_object
