import traceback

from panda3d.core import NodePath, PandaNode, LVecBase3f, GeomNode, Geom,\
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
        child_p3d_node = PandaNode(child_obj.name.upper().strip())
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
    # create enough rows to hold every vert we COULD create.
    # its possible to optimize this, but it's not really necessary
    vdata.setNumRows((coll_grid.height * 4) * coll_grid.width)

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
        *, worlds_tag, objects_tag, textures, anim_tag=None,
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
    child_nodes = load_nodes_from_worlds_tag(
        worlds_tag, scene_world.static_objects_node
        )

    dyn_p3d_nodepath = NodePath(scene_world.dynamic_objects_node)
    dyn_coll_objects = collision_grid.dyn_collision_objects
    dyn_root_indices = set(
        anim.world_object_index
        for anim in worlds_tag.data.world_anims.animations
        )

    scene_world.cache_node_paths()
    scene_item_infos = load_scene_item_infos_from_worlds_tag(worlds_tag)

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
        scene_world_object = load_scene_world_object_from_tags(
            world_object, textures=textures,
            worlds_tag=worlds_tag, objects_tag=objects_tag,
            global_tex_anims=global_tex_anims,
            allow_model_flatten=flatten_static
            )
        collision = load_collision_from_worlds_tag(
            worlds_tag, world_object.name,
            world_object.coll_tri_index,
            world_object.coll_tri_count,
            )

        if collision:
            if world_object.flags.animated:
                node_name = scene_world_object.name
            else:
                node_name = scene_world.static_objects_node.name

            if node_name in dyn_coll_objects:
                dyn_coll_objects[node_name].scene_object = scene_world_object

            scene_world.attach_collision(collision, node_name)

        scene_world.attach_world_object(scene_world_object, scene_world_object.name)

        if i in dyn_root_indices:
            # reparent the animation root node to the dynamic root
            child_p3d_nodepath = scene_world.get_node_path(scene_world_object.name)
            world_pos = child_p3d_nodepath.get_pos(dyn_p3d_nodepath)
            child_p3d_nodepath.reparent_to(dyn_p3d_nodepath)
            child_p3d_nodepath.set_pos(dyn_p3d_nodepath, world_pos)

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
