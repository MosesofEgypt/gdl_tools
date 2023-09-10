from panda3d.core import ModelNode, NodePath, LQuaternionf
from panda3d.physics import ActorNode

from ....compilation.g3d.serialization import vector_util
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
    anim_model_prefix = ""  # HACK
    seen_anim_models = set() # HACK
    # build all the nodes in the atree
    for i, anode_info in enumerate(anodes):
        node_type = anode_info.anim_type.enum_name
        node_name = anode_info.mb_desc.upper().strip()
        parent    = anode_info.parent_index
        flags     = anode_info.mb_flags
        x, y, z   = anode_info.init_pos

        p3d_node = ModelNode(
            f"{actor_name}PSYS{i}"
            if node_type == "particle_system" else
            node_name
            )

        p3d_nodepath = NodePath(p3d_node)
        p3d_nodepath.set_pos(x, z, y)

        can_drop_node = node_type in ("null", "skeletal")
        if flags.front_face:
            p3d_nodepath.setBillboardAxis()
            can_drop_node = False
        elif flags.camera_dir:
            p3d_nodepath.setBillboardPointWorld()
            can_drop_node = False

        if node_type == "skeletal" and can_drop_node:
            for seq_info in anode_info.anim_seq_infos:
                if seq_info.size:
                    can_drop_node = False
                    break

        # either find the root node, or setup info to link this node to its parent
        if parent in range(len(anodes)):
            node_map.setdefault(parent, []).append(p3d_node)
        elif parent < 0:
            root_node = p3d_node

        # TODO: consider changing this to not load models if node_type != "skeletal"
        if anode_info.flags.no_object_def:
            model_name = ""

            if node_type == "object":
                # TEMPORARY HACK
                # find a suitable "idle" frame to attach
                for obj_anim in atree.atree_header.atree_data.obj_anim_header.obj_anims:
                    if node_type != "object":
                        break

                    model_prefix = obj_anim.mb_desc[:-4]
                    if not anim_model_prefix:
                        anim_model_prefix = model_prefix

                    if model_prefix == anim_model_prefix and obj_anim.mb_desc not in seen_anim_models:
                        model_name = obj_anim.mb_desc
                        seen_anim_models.add(model_name)
                        node_type = "skeletal"
                        break
        else:
            model_name = actor_prefix + node_name

        if can_drop_node:
            p3d_node.set_preserve_transform(ModelNode.PT_drop_node)

        p3d_nodes.append(p3d_node)
        nodes_infos.append(dict(
            node_type=node_type,
            p3d_node=p3d_node,
            name=node_name,
            model_name=model_name,
            flags=dict(
                no_z_test    = bool(flags.no_z_test),
                no_z_write   = bool(flags.no_z_write),

                add_first    = bool(flags.add_first),
                sort_alpha   = bool(flags.sort_alpha),
                alpha_last   = bool(flags.alpha_last),
                alpha_last_2 = bool(flags.alpha_last_2),
                no_shading   = bool(flags.no_shading),

                chrome       = bool(flags.chrome),
                fb_add       = bool(flags.fb_add),
                fb_mul       = bool(flags.fb_mul),
                ),
            can_drop_node = can_drop_node,
            billboard     = (flags.front_face or flags.camera_dir),
            effect_index  = anode_info.anim_seq_info_index,
            ))

    # link the nodes together
    for i in sorted(node_map):
        parent_node = p3d_nodes[i]
        for p3d_node in node_map[i]:
            parent_node.add_child(p3d_node)

    if root_node is None:
        raise ValueError(f"Could not locate root node for actor '{actor_name}'.")

    return root_node, nodes_infos


def load_scene_actor_from_tags(
        actor_name, *, anim_tag, textures, objects_tag=None,
        global_tex_anims=(), seq_tex_anims=(), shape_morph_anims=(), psys_by_index=(),
        optimize=True
        ):
    actor_name = actor_name.upper().strip()
    actor_node = ActorNode(actor_name)

    root_node, nodes_infos = load_nodes_from_anim_tag(
        actor_name, anim_tag
        )
    actor_node.add_child(root_node)

    scene_actor = SceneActor(name=actor_name, p3d_node=actor_node)

    tex_anims_by_tex_name = {}
    # reorganize the texture animations
    for anims_by_tex_name in seq_tex_anims.values():
        for tex_name, anim in anims_by_tex_name.items():
            tex_anims_by_tex_name.setdefault(tex_name, []).append(anim)

    # load and attach models
    psys_to_add = {}
    for node_info in nodes_infos:
        can_drop_node = node_info["can_drop_node"]
        model_name    = node_info["model_name"]
        node_type     = node_info["node_type"]
        p3d_node      = node_info["p3d_node"]
        flags         = node_info["flags"]
        eff_index     = node_info["effect_index"]

        if node_type == "particle_system":
            # NOTE: for some reason, actor particle systems default to
            #       facing along the x-axis if emit_dir is not set.
            qi, qj, qk, qw = vector_util.gdl_normal_to_quaternion(1, 0, 0)
            p3d_nodepath = NodePath(p3d_node)
            p3d_nodepath.setQuat(LQuaternionf(qw, qi, qj, qk))

            if eff_index in range(len(psys_by_index)):
                psys = psys_by_index[eff_index]
                psys.create_instance(p3d_nodepath)
                psys_to_add[psys.name] = psys
            else:
                print("Warning: Referenced particle system {eff_index} does not exist")

        elif node_type in ("null", "skeletal") and model_name:
            # NOTE: the null type is used on ALL the nodes found in the skeleton of players
            model = load_model_from_objects_tag(
                objects_tag, model_name, textures,
                global_tex_anims, tex_anims_by_tex_name,
                shape_morph_anims=shape_morph_anims, p3d_model=p3d_node,
                is_static=can_drop_node, is_obj_anim=(node_type == "object"),
                billboard=node_info["billboard"]
                )

            scene_actor.add_model(model)
            for geometry in model.geometries:
                shader_updated = False
                for flag_name in (
                        "no_z_test", "no_z_write", "chrome",
                        "fb_add", "fb_mul", "add_first", "no_shading",
                        "sort_alpha", "alpha_last", "alpha_last2",
                        ):
                    if flags.get(flag_name):
                        setattr(geometry.shader, flag_name, True)
                        shader_updated = True

                if shader_updated:
                    geometry.apply_shader()
        elif node_type == "texture":
            # TODO: bind texmod to node with higher priority than default
            pass
        elif can_drop_node:
            # node isn't animated. prepare to drop
            p3d_node.set_preserve_transform(ModelNode.PT_drop_node)

    for psys in psys_to_add.values():
        scene_actor.add_particle_system(psys)
        psys.set_enabled(True)

    for anims in tex_anims_by_tex_name.values():
        for anim in anims:
            scene_actor.add_texture_animation(anim)

    if optimize:
        scene_actor.optimize_node_graph()

    return scene_actor
