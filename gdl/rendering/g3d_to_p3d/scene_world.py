import time

from panda3d.core import PandaNode, LVecBase3f, NodePath

from ..assets.scene_world import SceneWorld
from .model import load_model_from_objects_tag
from .texture import load_textures_from_objects_tag
from .collision import load_collision_from_worlds_tag


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
        *, worlds_tag, objects_tag, anim_tag=None,
        textures_filepath=None, is_ngc=False
        ):
    start = time.time()
    world_name = str(worlds_tag.filepath).upper().replace("\\", "/").\
                 split("LEVELS/")[-1].split("/")[0]
    scene_world = SceneWorld(name=world_name)
    load_nodes_from_worlds_tag(worlds_tag, scene_world.p3d_node)
    scene_world.cache_node_paths()

    textures = load_textures_from_objects_tag(
        objects_tag, textures_filepath, is_ngc
        )

    # load and attach models and collision
    for i, world_object in enumerate(worlds_tag.data.world_objects):
        model = load_model_from_objects_tag(objects_tag, world_object.name, textures)
        for geom in model.geometries:
            if not geom.shader.lm_texture:
                # non-lightmapped world objects are rendered with transparency
                # TODO: Doesn't work in all cases. Figure this out
                geom.shader.additive_diffuse = True
                geom.shader.apply_to_geometry(geom.p3d_geometry)

        scene_world.attach_model(model, world_object.name)

        if world_object.coll_tri_index >= 0 and world_object.coll_tri_count > 0:
            #if world_object.name == "E1BIGSLAB":
            #    print(i, world_object.name, world_object.coll_tri_index, world_object.coll_tri_count)
            collision = load_collision_from_worlds_tag(
                worlds_tag, world_object.name, world_object.coll_tri_index,
                world_object.coll_tri_count,
                )
            if world_object.flags.unknown12:  # flag 13 also seems always set?
                scene_world.attach_collision(collision, world_object.name)
            else:
                scene_world.attach_collision(collision, world_name)

    print("Loading scene world '%s' took %s seconds" % (world_name, time.time() - start))
    return scene_world
