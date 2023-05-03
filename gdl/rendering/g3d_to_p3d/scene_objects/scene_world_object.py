from panda3d.core import NodePath, ModelNode, LQuaternionf
from ....compilation.g3d.serialization import vector_util
from ...assets.scene_objects.scene_world_object import SceneWorldObject
from ..model import load_model_from_objects_tag
from ..collision import load_collision_from_worlds_tag


def load_scene_world_object_from_tags(
        world_object, *, scene_world, textures, worlds_tag, objects_tag,
        world_tex_anims=(), is_dynamic=False, p3d_model=None
        ):
    dyn_p3d_nodepath = NodePath(scene_world.dynamic_objects_node)
    dyn_coll_objects = scene_world.collision_grid.dyn_collision_objects

    scene_world_object = model = collision = None
    flags     = world_object.flags
    mb_flags  = world_object.mb_flags

    billboard = (mb_flags.front_face or mb_flags.camera_dir)
    model = load_model_from_objects_tag(
        objects_tag, world_object.name, textures,
        world_tex_anims, p3d_model=p3d_model,
        is_static=not(is_dynamic or billboard),
        billboard=billboard
        )
    scene_world_object = SceneWorldObject(
        name=world_object.name,
        p3d_node=getattr(model, "p3d_model", None)
        )
    p3d_nodepath = scene_world_object.p3d_nodepath

    p3d_node = p3d_nodepath.node()
    collision = load_collision_from_worlds_tag(
        worlds_tag, p3d_node.name,
        world_object.coll_tri_index,
        world_object.coll_tri_count,
        )

    if is_dynamic and dyn_p3d_nodepath.find_path_to(p3d_node).is_empty():
        # reparent the dynamic object to the dynamic root if it's not already under it
        p3d_nodepath.wrtReparentTo(dyn_p3d_nodepath)
        p3d_nodepath.setScale(1,1,1)
        p3d_nodepath.setShear(0,0,0)

    if scene_world_object and model:
        scene_world_object.add_model(model)

        flag_names = (
            'no_z_test', 'no_z_write', 'add_first', 'dist_alpha',
            'sort_alpha', 'alpha_last', 'alpha_last_2', 'no_shading',
            'chrome', 'fb_add', 'fb_mul'
            )
        set_flags = set(flag for flag in flag_names if mb_flags[flag])

        if set_flags:
            for geom in model.geometries:
                for flag in set_flags:
                    setattr(geom.shader, flag, True)

                geom.apply_shader()

    if scene_world_object and collision:
        if flags.animated:
            scene_world_object.p3d_node.add_child(collision.p3d_collision)
            scene_world_object.add_collision(collision)
        else:
            scene_world.static_collision_node.add_child(collision.p3d_collision)
            scene_world.add_collision(collision)

        if p3d_node.name in dyn_coll_objects:
            dyn_coll_objects[p3d_node.name].scene_object = scene_world_object

    return scene_world_object


def load_scene_world_psys_instance_from_tags(
        world_object, *, scene_world, worlds_tag, particle_systems=(), p3d_node=None
        ):
    dyn_p3d_nodepath = NodePath(scene_world.dynamic_objects_node)
    static_psys_p3d_nodepath = NodePath(scene_world.static_psys_node)

    flags = world_object.flags

    p3d_nodepath = NodePath(p3d_node)

    psys_prefix_len = max(len(n) for n in particle_systems) if particle_systems else 0
    psys_name = world_object.name[:psys_prefix_len].upper()
    psys = particle_systems.get(psys_name)
    p3d_node.set_preserve_transform(
        ModelNode.PT_local if flags.animated else
        ModelNode.PT_net
        )

    try:
        coll_tri    = worlds_tag.data.coll_tris[world_object.coll_tri_index]
        scale       = coll_tri.scale
        ni, nj, nk  = coll_tri.norm
    except IndexError:
        ni, nj, nk, scale = 0.0, -1.0, 0.0, 1.0

    qi, qj, qk, qw = vector_util.gdl_normal_to_quaternion(
        # HACK: we're negating nj because it seems to correct the
        #       facing direction of several particle systems.
        -ni * scale, -nj, -nk * scale
        )

    if not flags.animated:
        p3d_nodepath.wrtReparentTo(static_psys_p3d_nodepath)
        p3d_nodepath.setScale(1,1,1)
        p3d_nodepath.setShear(0,0,0)

    if psys:
        psys.create_instance(p3d_nodepath)
        p3d_nodepath.setQuat(LQuaternionf(qw, qi, qj, qk))
    else:
        print("Warning: Referenced particle system {eff_index} does not exist")
