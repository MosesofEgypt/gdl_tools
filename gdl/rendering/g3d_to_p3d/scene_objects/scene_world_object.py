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

    for geom in model.geometries:
        if False and not geom.shader.lm_texture:
            # non-lightmapped world objects are rendered with transparency
            # TODO: Doesn't work in all cases. Figure this out
            geom.shader.additive_diffuse = True
            geom.shader.apply_to_geometry(geom.p3d_geometry)

    scene_world_object.attach_model(model, scene_world_object.name)
    #print("Loading scene object '%s' took %s seconds" % (object_name, time.time() - start))
    return scene_world_object
