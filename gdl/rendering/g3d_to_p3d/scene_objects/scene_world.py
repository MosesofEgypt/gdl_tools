import traceback
import time

from panda3d.core import PandaNode, LVecBase3f, NodePath

from ...assets.scene_objects.scene_world import SceneWorld
from .scene_world_object import load_scene_world_object_from_tags
from ..collision import load_collision_from_worlds_tag
from .scene_item import load_scene_item_infos_from_worlds_tag,\
     load_scene_item_from_item_instance


def _load_nodes_from_worlds_tag(world_objects, parent_p3d_node, child_index, seen):
    if child_index in seen:
        return

    while child_index >= 0:
        seen.add(child_index)

        child_obj = world_objects[child_index]
        child_p3d_node = PandaNode(child_obj.name.upper().strip())

        x, y, z = child_obj.pos
        node_trans = child_p3d_node.get_transform().set_pos(
            LVecBase3f(x, z, y)
            )
        child_p3d_node.set_transform(node_trans)
        parent_p3d_node.addChild(child_p3d_node)

        if child_obj.child_index >= 0:
            _load_nodes_from_worlds_tag(
                world_objects, child_p3d_node, child_obj.child_index, seen
                )

        child_index = child_obj.next_index


def load_nodes_from_worlds_tag(worlds_tag, root_p3d_node):
    seen = set()
    for i in range(len(worlds_tag.data.world_objects)):
        _load_nodes_from_worlds_tag(
            worlds_tag.data.world_objects, root_p3d_node, i, seen
            )
    #for child in NodePath(root_p3d_node).findAllMatches('**'):
    #    print(child)


def load_scene_world_from_tags(
        *, worlds_tag, objects_tag, textures,
        anim_tag=None, world_item_actors=()
        ):
    if world_item_actors is None:
        world_item_actors = {}

    start = time.time()
    world_name = str(worlds_tag.filepath).upper().replace("\\", "/").\
                 split("LEVELS/")[-1].split("/")[0]
    scene_world = SceneWorld(name=world_name)
    load_nodes_from_worlds_tag(worlds_tag, scene_world.p3d_node)
    scene_world.cache_node_paths()

    scene_item_infos = load_scene_item_infos_from_worlds_tag(worlds_tag)

    # load and attach models and collision
    for world_object in worlds_tag.data.world_objects:
        scene_world_object = load_scene_world_object_from_tags(
            world_object, textures=textures,
            worlds_tag=worlds_tag, objects_tag=objects_tag
            )
        collision = load_collision_from_worlds_tag(
            worlds_tag, world_object.name,
            world_object.coll_tri_index,
            world_object.coll_tri_count,
            )

        coll_attach_node = scene_world_object.name if world_object.flags.animated_collision else world_name
        if collision:
            scene_world.attach_collision(collision, coll_attach_node)

        scene_world.attach_world_object(scene_world_object, world_object.name)

    for item_instance in worlds_tag.data.item_instances:
        try:
            scene_item = load_scene_item_from_item_instance(
                worlds_tag = worlds_tag,
                objects_tag = objects_tag, textures = textures,
                item_instance = item_instance,
                scene_item_infos = scene_item_infos,
                world_item_actors = world_item_actors
                )
            scene_world.attach_scene_item(scene_item)
        except Exception:
            print(traceback.format_exc())
            continue

    #print("Loading scene world '%s' took %s seconds" % (world_name, time.time() - start))
    return scene_world
