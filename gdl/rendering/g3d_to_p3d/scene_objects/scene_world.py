import traceback

from panda3d.core import NodePath, ModelNode, GeomNode, Geom,\
     GeomTriangles, GeomVertexFormat, GeomVertexData, GeomVertexWriter

from ...assets.scene_objects.scene_world import SceneWorld
from .scene_world_object import load_scene_world_object_from_tags,\
     load_scene_world_psys_instance_from_tags
from ..collision import load_collision_grid_from_worlds_tag
from ..particle_system import load_particle_systems_from_worlds_tag
from .scene_item import load_scene_item_infos_from_worlds_tag,\
     load_scene_item_from_item_instance


def _load_nodes_from_worlds_tag(
        parent_p3d_node, world_objects, child_index, parent_index, nodes
        ):
    if child_index in nodes:
        return

    while child_index >= 0:
        child_obj = world_objects[child_index]

        mb_flags = child_obj.mb_flags
        x, y, z = child_obj.pos

        child_p3d_node = ModelNode(child_obj.name.upper().strip())
        child_p3d_nodepath = NodePath(child_p3d_node)

        child_p3d_nodepath.set_pos(x, z, y)
        parent_p3d_node.addChild(child_p3d_node)

        if mb_flags.front_face:
            child_p3d_nodepath.setBillboardAxis()
        elif mb_flags.camera_dir:
            child_p3d_nodepath.setBillboardPointWorld()

        nodes[child_index] = child_p3d_node

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
        *, worlds_tag, objects_tag, textures, anim_tag=None, level_data=None, 
        world_item_actors=(), world_item_objects=(), world_tex_anims=(), optimize=True,
        ):
    if world_item_actors is None:
        world_item_actors = {}

    world_name = getattr(level_data, "name",
                         str(worlds_tag.filepath).replace("\\", "/").
                         split('/')[-2]
                         )

    # get the world name from the prefix of the first world
    # object if it's blank for some reason in the level_data
    for world_obj in worlds_tag.data.world_objects:
        if world_name: break
        world_name = world_obj.name[:2]

    collision_grid = load_collision_grid_from_worlds_tag(worlds_tag)
    scene_world = SceneWorld(
        name=world_name, collision_grid=collision_grid,
        )
    world_nodes = load_nodes_from_worlds_tag(
        worlds_tag, scene_world.static_objects_node
        )
    particle_systems = load_particle_systems_from_worlds_tag(
        worlds_tag, world_name, textures, world_tex_anims,
        render_nodepath=scene_world.p3d_nodepath
        )
    scene_item_infos = load_scene_item_infos_from_worlds_tag(
        worlds_tag, level_data
        )
    dyn_obj_indices = set(
        worlds_tag.data.dynamic_grid_objects.world_object_indices
        )

    for texmod in world_tex_anims.values():
        scene_world.add_world_texmod(texmod)

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
        if world_object.flags.particle_system:
            load_scene_world_psys_instance_from_tags(
                world_object, scene_world=scene_world, worlds_tag=worlds_tag,
                particle_systems=particle_systems, p3d_node=world_nodes[i]
                )
        else:
            is_dynamic = i in dyn_obj_indices
            scene_world_object = load_scene_world_object_from_tags(
                world_object, scene_world=scene_world,
                textures=textures, worlds_tag=worlds_tag, objects_tag=objects_tag,
                world_tex_anims=world_tex_anims,
                is_dynamic=is_dynamic, p3d_model=world_nodes[i]
                )
            scene_world.add_world_object(scene_world_object)

            #if scene_world_object.p3d_node.get_preserve_transform() == ModelNode.PT_no_touch:
            #    print(scene_world_object.name)

    # optimize the world by flattening all statics
    if 0 and optimize:
        scene_world.optimize_node_graph()

    for psys in particle_systems.values():
        scene_world.add_particle_system(psys)
        psys.set_enabled(True)

    for item_instance in worlds_tag.data.item_instances:
        try:
            scene_item = load_scene_item_from_item_instance(
                worlds_tag = worlds_tag,
                level_data = level_data,
                objects_tag = objects_tag,
                textures = textures,
                world_tex_anims = world_tex_anims,
                item_instance = item_instance,
                scene_item_infos = scene_item_infos,
                world_item_actors = world_item_actors,
                world_item_objects = world_item_objects
                )
            scene_world.attach_scene_item(scene_item)
            if scene_item_infos[item_instance.item_index].snap_to_grid:
                scene_world.snap_to_grid(scene_item.p3d_nodepath)

        except Exception:
            print(traceback.format_exc())

    return scene_world
