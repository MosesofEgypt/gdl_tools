import panda3d
from .scene_object import SceneObject


class SceneWorld(SceneObject):
    _node_world_objects = ()

    _scene_items     = ()
    _scene_item_inst = ()

    _objects_root_node = None
    _items_root_node   = None

    def __init__(self, **kwargs):
        self._node_world_objects = {}

        self._scene_items        = []
        self._scene_item_inst    = {}

        super().__init__(**kwargs)

        self._objects_root_node = panda3d.core.PandaNode("__objects_root")
        self._items_root_node   = panda3d.core.PandaNode("__items_root")

        self.p3d_node.add_child(self._objects_root_node)
        self.p3d_node.add_child(self._items_root_node)

    def attach_world_object(self, world_object, node_name=""):
        node_name = node_name.upper().strip()
        node_collection = self._node_world_objects.setdefault(node_name, dict())
        parent_node_path = self._get_node_path(node_name)

        if world_object.name in node_collection or parent_node_path is None:
            return

        node_collection[world_object.name] = world_object
        parent_node_path.node().add_child(world_object.p3d_node)

    @property
    def node_world_objects(self): return {k: dict(v) for k, v in self._node_world_objects.items()}
