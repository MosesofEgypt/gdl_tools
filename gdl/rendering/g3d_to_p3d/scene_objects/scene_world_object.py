from ...assets.scene_objects.scene_world_object import SceneWorldObject
from ..model import load_model_from_objects_tag


def load_scene_world_object_from_tags(
        world_object, *, textures, worlds_tag, objects_tag,
        global_tex_anims=(), allow_model_flatten=True, p3d_model=None
        ):
    model = None
    flags = world_object.mb_flags
    if not world_object.flags.particle_system:
        model = load_model_from_objects_tag(
            objects_tag, world_object.name, textures,
            global_tex_anims, is_static=allow_model_flatten,
            p3d_model=p3d_model,
            billboard_fixup=(flags.front_face or flags.camera_dir)
            )
        p3d_model = model.p3d_model
        
    scene_world_object = SceneWorldObject(
        name=world_object.name, p3d_node=p3d_model
        )

    if model:
        scene_world_object.add_model(model)

        flag_names = (
            'no_z_test', 'no_z_write', 'add_first', 'dist_alpha',
            'sort_alpha', 'alpha_last', 'alpha_last_2', 'no_shading',
            'chrome', 'fb_add', 'fb_mul'
            )
        set_flags = set(flag for flag in flag_names if flags[flag])

        if set_flags:
            for geom in model.geometries:
                for flag in set_flags:
                    setattr(geom.shader, flag, True)

                geom.apply_shader()

    return scene_world_object
