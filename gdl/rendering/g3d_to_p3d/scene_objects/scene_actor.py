from panda3d.core import NodePath, ModelNode, LVecBase3f
from panda3d.physics import ActorNode

from ...assets.scene_objects.scene_actor import SceneActor
from ..model import load_model_from_objects_tag
from .. import util


def load_nodes_from_anim_tag(actor_name, anim_tag):
    actor_name   = actor_name.upper().strip()
    actor_prefix = ""
    anodes = ()
    for atree in anim_tag.data.atrees:
        if atree.name.upper().strip() == actor_name:
            anodes       = atree.atree_header.atree_data.anode_infos
            actor_prefix = atree.atree_header.prefix.upper().strip()
            break

    root_node   = None
    p3d_nodes   = []
    node_map    = {}
    nodes_infos = []
    # build all the nodes in the atree
    for i, anode_info in enumerate(anodes):
        node_type = anode_info.anim_type.enum_name
        node_name = anode_info.mb_desc.upper().strip()
        parent    = anode_info.parent_index
        flags     = anode_info.mb_flags
        p3d_node  = ModelNode(node_name)
        x, y, z   = anode_info.init_pos

        node_trans = p3d_node.get_transform().set_pos(
            LVecBase3f(x, z, y)
            )
        p3d_node.set_transform(node_trans)

        # either find the root node, or setup info to link this node to its parent
        if parent in range(len(anodes)):
            node_map.setdefault(parent, []).append(p3d_node)
        elif parent < 0:
            root_node = p3d_node

        if node_type == "object":
            # TEMPORARY HACK
            # find a suitable "idle" frame to attach
            for obj_anim in atree.atree_header.atree_data.obj_anim_header.obj_anims:
                model_name = obj_anim.mb_desc
                break
        elif anode_info.flags.no_object_def:
            model_name = ""
        else:
            model_name = actor_prefix + node_name

        p3d_nodes.append(p3d_node)
        nodes_infos.append(dict(
            node_type=node_type,
            p3d_node=p3d_node,
            name=node_name,
            model_name=model_name,
            flags=dict(
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
            ))

    # link the nodes together
    for i in node_map:
        parent_node = p3d_nodes[i]
        for p3d_node in node_map[i]:
            parent_node.add_child(p3d_node)

    if root_node is None:
        raise ValueError(f"Could not locate root node for actor '{actor_name}'.")

    return root_node, nodes_infos


def load_scene_actor_from_tags(
        actor_name, *, anim_tag, textures, objects_tag=None,
        global_tex_anims=(), seq_tex_anims=(),
        ):
    actor_name = actor_name.upper().strip()
    actor_node = ActorNode(actor_name)

    root_node, nodes_infos = load_nodes_from_anim_tag(actor_name, anim_tag)
    actor_node.add_child(root_node)

    scene_actor = SceneActor(name=actor_name, p3d_node=actor_node)

    tex_anims_by_tex_name = {}
    # reorganize the texture animations
    for anims_by_tex_name in seq_tex_anims.values():
        for tex_name, anim in anims_by_tex_name.items():
            tex_anims_by_tex_name.setdefault(tex_name, []).append(anim)

    # load and attach models
    for node_info in nodes_infos:
        model_name = node_info["model_name"]
        p3d_node   = node_info["p3d_node"]
        flags      = node_info["flags"]
        if not model_name:
            continue

        model = load_model_from_objects_tag(
            objects_tag, model_name, textures,
            global_tex_anims, tex_anims_by_tex_name,
            is_static=False, p3d_model=p3d_node
            )
        scene_actor.add_model(model)

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
