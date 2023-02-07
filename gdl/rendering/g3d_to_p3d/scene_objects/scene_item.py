import traceback

from ...assets.scene_objects.scene_item import SceneItemInfo,\
     SceneItemGenerator
from ...assets import constants as c
from ..model import load_model_from_objects_tag
from ..collision import load_collision_from_worlds_tag
from .scene_object import load_scene_object_from_tags


def load_scene_item_infos_from_worlds_tag(worlds_tag, level_data=None):
    scene_item_infos = []
    for item_info in worlds_tag.data.item_infos:
        try:
            item_data = item_info.data
            if hasattr(item_data, "item_subtype"):
                actor_name = item_data.name.upper().strip()
                # TEMPORARY HACK(blame midway)
                if item_info.item_type.enum_name == "enemy":
                    if actor_name == "DEATH":
                        actor_name = c.STATUE_NAME_DEATH1
                    elif actor_name == "GENERAL":
                        actor_name = c.ACTOR_NAME_GENERAL
                    elif actor_name == "GAR":
                        actor_name = c.STATUE_NAME_GAR
                    elif actor_name == "GOLEM":
                        actor_name = c.STATUE_NAME_GOL
                elif item_info.item_type.enum_name == "generator":
                    if actor_name == c.DEFAULT_ENEMY_TYPE_TINY:
                        actor_name = level_data.enemy_type_gen_small
                    elif actor_name in (
                            c.DEFAULT_ENEMY_TYPE_PRI, c.DEFAULT_ENEMY_TYPE_SEC
                            ):
                        actor_name = level_data.enemy_type_gen_large

                scene_item_info = SceneItemInfo(
                    actor_name   = actor_name,
                    item_type    = item_info.item_type.data,
                    item_subtype = item_data.item_subtype.data,
                    radius       = item_data.radius,
                    height       = item_data.height,

                    coll_type   = item_data.coll_type.data,
                    coll_offset = item_data.coll_offset,
                    coll_width  = item_data.x_dim,
                    coll_length = item_data.z_dim,

                    properties   = {},

                    value        = item_data.value,
                    armor        = item_data.armor,
                    health       = item_data.hit_points,
                    active_type  = item_data.active_type,
                    active_off   = item_data.active_off,
                    active_on    = item_data.active_on,
                    snap_to_grid = not item_data.coll_flags.no_gravity
                    )
            else:
                scene_item_info = SceneItemInfo(
                    item_type    = item_info.item_type.data,
                    item_indices = item_data.indices[: item_data.item_count]
                    )

        except ValueError:
            print(traceback.format_exc())
            scene_item_info = SceneItemInfo()

        scene_item_infos.append(scene_item_info)

    return scene_item_infos


def load_scene_item_from_item_instance(
        *, worlds_tag, objects_tag, textures,
        item_instance, scene_item_infos,
        world_item_actors, world_item_objects
        ):
    instance_name = item_instance.name.upper().strip()

    flags = item_instance.flags
    scene_item_info = scene_item_infos[item_instance.item_index]

    scene_item = scene_item_info.create_instance(
        name = instance_name,
        min_players = item_instance.min_players,
        params = item_instance.params,
        pos = item_instance.pos,
        rot = item_instance.rot,
        scene_object = world_item_actors.get(scene_item_info.actor_name),
        flags = { n: bool(flags[n]) for n in flags.NAME_MAP }
        )

    # NOTE: temporary hack
    if isinstance(scene_item, SceneItemGenerator):
        # locate and attach generator objects
        model = None
        generator_objects = []
        for i in range(4):
            for object_set in (world_item_actors, world_item_objects):
                name = c.OBJECT_NAME_GEN % (scene_item_info.actor_name, i)
                if name in object_set:
                    generator_objects.append(object_set[name])
                elif name + "L1" in object_set:
                    generator_objects.append(object_set[name + "L1"])

        scene_item.generator_objects = generator_objects
    elif instance_name:
        model = load_model_from_objects_tag(
            objects_tag, instance_name, textures, is_static=False
            )
        if model:
            scene_item.add_model(model)
            scene_item.p3d_node.add_child(model.p3d_model)

    # NOTE: might be worth keeping scene items root node
    #       separate to allow moving them in world?
    collision = load_collision_from_worlds_tag(
        worlds_tag, scene_item.name,
        item_instance.coll_tri_index,
        item_instance.coll_tri_count,
        ) if scene_item_info.coll_type == c.COLL_TYPE_OBJECT else None

    if collision:
        scene_item.add_collision(collision)
        scene_item.p3d_node.add_child(collision.p3d_collision)

    return scene_item
