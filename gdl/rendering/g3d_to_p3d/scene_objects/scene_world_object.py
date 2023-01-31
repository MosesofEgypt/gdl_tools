from ...assets.scene_objects.scene_world_object import SceneWorldObject
from ..model import load_model_from_objects_tag


def load_scene_world_object_from_tags(
        world_object, *, textures, worlds_tag, objects_tag,
        global_tex_anims=(), allow_model_flatten=True, p3d_model=None
        ):
    model = load_model_from_objects_tag(
        objects_tag, world_object.name, textures,
        global_tex_anims, is_static=allow_model_flatten,
        p3d_model=p3d_model
        )
    scene_world_object = SceneWorldObject(
        name=world_object.name, p3d_node=model.p3d_model
        )
    scene_world_object.add_model(model)

    fb_add = False #world_object.flags.unknown
    chrome = False
    for geom in model.geometries:
        shader_updated = False
        # TODO: fix this to be more accurate. This is only correct
        #       in some circumstances, but is wrong in others.
        #fb_add = not geom.shader.lm_texture

        if chrome: geom.shader.chrome = shader_updated = True
        if fb_add: geom.shader.fb_add = shader_updated = True

        if shader_updated:
            geom.apply_shader()

    return scene_world_object
