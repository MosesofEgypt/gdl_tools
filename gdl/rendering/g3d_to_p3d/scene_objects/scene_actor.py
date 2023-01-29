from panda3d.core import NodePath, PandaNode, LVecBase3f
from panda3d.physics import ActorNode

from ...assets.scene_objects.scene_actor import SceneActor
from ..model import load_model_from_objects_tag
from .. import util


def load_nodes_from_anim_tag(object_name, anim_tag):
    anodes = ()
    for atree in anim_tag.data.atrees:
        if atree.name.upper().strip() == object_name.upper().strip():
            anodes = atree.atree_header.atree_data.anode_infos
            break

    root_node = None
    p3d_nodes = {}
    node_map = {}
    for anode_info in anodes:
        node_name = anode_info.mb_desc.upper().strip()
        p3d_node = PandaNode(node_name)
        x, y, z = anode_info.init_pos

        node_trans = p3d_node.get_transform().set_pos(
            LVecBase3f(x, z, y)
            )

        p3d_node.set_transform(node_trans)

        p3d_nodes[len(p3d_nodes)] = p3d_node
        node_map.setdefault(anode_info.parent_index, []).append(dict(
            node_type=anode_info.anim_type.enum_name,
            flags=anode_info.mb_flags,
            p3d_node=p3d_node,
            name=node_name
            ))

    root_node  = None
    node_flags = {}
    for parent_index in sorted(node_map):
        # TODO: add checks to ensure parent exists
        parent_node = p3d_nodes.get(parent_index)

        for node_info in node_map[parent_index]:
            if parent_node is None:
                root_node = node_info["p3d_node"]
                break

            parent_node.addChild(node_info["p3d_node"])
            flags = node_info["flags"]
            node_flags[node_info["name"]] = dict(
                no_z_test   = bool(flags.no_z_test),
                no_z_write  = bool(flags.no_z_write),

                add_first   = bool(flags.add_first),
                sort_alpha  = bool(flags.sort_alpha),
                alpha_last  = bool(flags.alpha_last or flags.alpha_last_2), # ???
                no_shading  = bool(flags.no_shading),

                chrome      = bool(flags.chrome),
                fb_add      = bool(flags.fb_add),
                fb_mul      = bool(flags.fb_mul),

                front_face  = bool(flags.front_face), 
                camera_dir  = bool(flags.camera_dir), 
                )

    if root_node is None:
        root_node = PandaNode("")
        node_flags = {}

    return root_node, node_flags


def load_scene_actor_from_tags(
        actor_name, *, anim_tag, textures, objects_tag=None,
        global_tex_anims=(), seq_tex_anims=(),
        ):
    actor_name = actor_name.upper().strip()
    actor_node = ActorNode(actor_name)

    nodes, node_flags = load_nodes_from_anim_tag(actor_name, anim_tag)
    actor_node.add_child(nodes)

    scene_actor = SceneActor(name=actor_name, p3d_node=actor_node)

    tex_anims_by_tex_name = {}
    for anims_by_tex_name in seq_tex_anims.values():
        for tex_name, anim in anims_by_tex_name.items():
            tex_anims_by_tex_name.setdefault(tex_name, []).append(anim)

    # load and attach models
    for model_name, node_name in zip(*anim_tag.get_model_node_name_map(actor_name)):
        model = load_model_from_objects_tag(
            objects_tag, model_name, textures,
            global_tex_anims, tex_anims_by_tex_name,
            is_static=False
            )
        scene_actor.attach_model(model, node_name)
        flags = node_flags.get(node_name, {})

        for geometry in model.geometries:
            shader_updated = False
            for flag_name in (
                    "no_z_test", "no_z_write", "chrome", "fb_add", "fb_mul",
                    "add_first", "sort_alpha", "alpha_last", "no_shading",
                    ):
                if flags.get(flag_name):
                    setattr(geometry.shader, flag_name, True)
                    shader_updated = True

            if shader_updated:
                geometry.apply_shader()

    for anims in tex_anims_by_tex_name.values():
        for anim in anims:
            scene_actor.add_texture_animation(anim)

    return scene_actor
