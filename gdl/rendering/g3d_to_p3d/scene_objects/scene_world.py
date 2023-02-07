import traceback

from panda3d.core import NodePath, ModelNode, LVecBase3f, GeomNode, Geom,\
     GeomTriangles, GeomVertexFormat, GeomVertexData, GeomVertexWriter

from ...assets.scene_objects.scene_world import SceneWorld
from .scene_world_object import load_scene_world_object_from_tags
from ..collision import load_collision_from_worlds_tag,\
     load_collision_grid_from_worlds_tag
from .scene_item import load_scene_item_infos_from_worlds_tag,\
     load_scene_item_from_item_instance


def _load_nodes_from_worlds_tag(
        parent_p3d_node, world_objects, child_index, parent_index, nodes
        ):
    if child_index in nodes:
        return

    while child_index >= 0:
        child_obj = world_objects[child_index]
        child_p3d_node = ModelNode(child_obj.name.upper().strip())
        nodes[child_index] = child_p3d_node

        x, y, z = child_obj.pos
        node_trans = child_p3d_node.get_transform().set_pos(
            LVecBase3f(x, z, y)
            )
        child_p3d_node.set_transform(node_trans)
        parent_p3d_node.addChild(child_p3d_node)

        if child_obj.child_index >= 0:
            _load_nodes_from_worlds_tag(
                child_p3d_node, world_objects,
                child_obj.child_index, child_index, nodes
                )

        child_index = child_obj.next_index


def load_nodes_from_worlds_tag(worlds_tag, root_p3d_node):
    nodes = {}
    world_objects = worlds_tag.data.world_objects
    for i in range(len(world_objects)):
        _load_nodes_from_worlds_tag(
            root_p3d_node, world_objects, i, -1, nodes
            )

    return nodes


def generate_collision_grid_model(coll_grid):
    tris  = GeomTriangles(Geom.UHDynamic)
    vdata = GeomVertexData('', GeomVertexFormat.getV3c4(), Geom.UHDynamic)
    vert_count = 0
    for z in range(coll_grid.height):
        for x in range(coll_grid.width):
            if coll_grid.get_collision_cell_at_grid_pos(x, z):
                vert_count += 4

    vdata.setNumRows(vert_count)

    addPosData   = GeomVertexWriter(vdata, 'vertex').addData3f
    addColorData = GeomVertexWriter(vdata, 'color').addData4f
    # add 4 verts for each
    v_i = 0
    for z in range(coll_grid.height):
        for x in range(coll_grid.width):
            grid_coll = coll_grid.get_collision_cell_at_grid_pos(x, z)
            if not grid_coll:
                # no collision here, so empty grid spot. skip
                continue

            # rotate coordinates
            addPosData(*coll_grid.grid_pos_to_world_pos(x,   z  ), 0)
            addPosData(*coll_grid.grid_pos_to_world_pos(x+1, z  ), 0)
            addPosData(*coll_grid.grid_pos_to_world_pos(x,   z+1), 0)
            addPosData(*coll_grid.grid_pos_to_world_pos(x+1, z+1), 0)
            # add color to help visualize
            color_val = min(1.0, sum(
                len(coll_object.tris)
                for coll_object in grid_coll.values()
                ) / 32)
            color = (color_val, 0, 1.0 - color_val, 0.8)
            addColorData(*color)
            addColorData(*color)
            addColorData(*color)
            addColorData(*color)

            tris.addVertices(v_i,   v_i+1, v_i+2)
            tris.addVertices(v_i+1, v_i+3, v_i+2)
            tris.addVertices(v_i+1,   v_i, v_i+2)
            tris.addVertices(v_i+3, v_i+1, v_i+2)
            v_i += 4

    p3d_geometry = GeomNode("")
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    p3d_geometry.addGeom(geom)

    return p3d_geometry


def load_scene_world_from_tags(
        *, level_data, worlds_tag, objects_tag, textures, anim_tag=None,
        world_item_actors=(), world_item_objects=(), global_tex_anims=(),
        flatten_static=True, flatten_static_tex_anims=True
        ):
    if world_item_actors is None:
        world_item_actors = {}

    world_name = str(worlds_tag.filepath).upper().replace("\\", "/").\
                 split("LEVELS/")[-1].split("/")[0]
    collision_grid   = load_collision_grid_from_worlds_tag(worlds_tag)
    scene_world = SceneWorld(
        name=world_name, collision_grid=collision_grid,
        )
    world_nodes = load_nodes_from_worlds_tag(
        worlds_tag, scene_world.static_objects_node
        )

    dyn_p3d_nodepath = NodePath(scene_world.dynamic_objects_node)
    dyn_coll_objects = collision_grid.dyn_collision_objects
    dyn_obj_indices = set(
        worlds_tag.data.dynamic_grid_objects.world_object_indices
        )

    scene_item_infos = load_scene_item_infos_from_worlds_tag(
        worlds_tag, level_data
        )

    # load the grid for use in debugging
    scene_world.coll_grid_model_node.addChild(
        generate_collision_grid_model(collision_grid)
        )
    scene_world.set_collision_grid_visible(False)

    # load and attach models and collision
    for i, world_object in enumerate(worlds_tag.data.world_objects):
        # TODO: pass animations list to have them bound to the object and
        #       allow determining if the node hierarchy can be flattened.
        # TODO: figure out how collision transforms will need to be handled.
        #       maybe look at world_object.flags.animated???
        object_name = world_object.name.upper().strip()
        p3d_node = world_nodes[i]
        scene_world_object = load_scene_world_object_from_tags(
            world_object, textures=textures,
            worlds_tag=worlds_tag, objects_tag=objects_tag,
            global_tex_anims=global_tex_anims,
            allow_model_flatten=flatten_static,
            p3d_model=p3d_node
            )
        collision = load_collision_from_worlds_tag(
            worlds_tag, object_name,
            world_object.coll_tri_index,
            world_object.coll_tri_count,
            )

        if collision:
            parent_node = (p3d_node if world_object.flags.animated
                           else scene_world.static_collision_node)

            parent_node.add_child(collision.p3d_collision)
            scene_world.add_collision(collision)
            if object_name in dyn_coll_objects:
                dyn_coll_objects[object_name].scene_object = scene_world_object

        scene_world.add_world_object(scene_world_object)

        # reparent the dynamic object to the dynamic root if it's not already under it
        if i in dyn_obj_indices and dyn_p3d_nodepath.find_path_to(p3d_node).is_empty():
            child_p3d_nodepath = NodePath(p3d_node)
            world_pos = child_p3d_nodepath.get_pos(dyn_p3d_nodepath)
            child_p3d_nodepath.reparent_to(dyn_p3d_nodepath)
            child_p3d_nodepath.set_pos(dyn_p3d_nodepath, world_pos)

    # optimize the world by flattening all statics
    if flatten_static:
        scene_world.flatten_static_geometries(
            global_tex_anims, flatten_static_tex_anims
            )

    for item_instance in worlds_tag.data.item_instances:
        try:
            scene_item = load_scene_item_from_item_instance(
                worlds_tag = worlds_tag,
                objects_tag = objects_tag,
                textures = textures,
                item_instance = item_instance,
                scene_item_infos = scene_item_infos,
                world_item_actors = world_item_actors,
                world_item_objects = world_item_objects
                )
            scene_world.attach_scene_item(scene_item)
            if scene_item_infos[item_instance.item_index].snap_to_grid:
                scene_world.snap_to_grid(NodePath(scene_item.p3d_node))

        except Exception:
            print(traceback.format_exc())

    return scene_world
