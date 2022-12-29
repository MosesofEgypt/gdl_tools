from panda3d.core import PandaNode, LVecBase3f, NodePath

from ..assets.scene_world import SceneWorld
from .model import load_model_from_objects_tag
from .texture import load_textures_from_objects_tag


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
    scene_world = SceneWorld(name="")
    load_nodes_from_worlds_tag(worlds_tag, scene_world.p3d_node)

    textures = load_textures_from_objects_tag(
        objects_tag, textures_filepath, is_ngc
        )

    # load and attach models
    for world_object in worlds_tag.data.world_objects:
        model = load_model_from_objects_tag(objects_tag, world_object.name, textures)
        scene_world.attach_model(model, world_object.name)

    return scene_world
