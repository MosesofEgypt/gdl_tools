import panda3d
from .scene_world_object import SceneWorldObject
from .scene_object import SceneObject
from .scene_item import *


class SceneWorld(SceneObject):
    _node_world_objects = ()
    _node_scene_items = ()

    _scene_item_infos = ()

    _objects_root_node = None
    _items_root_nodes  = ()

    _player_count = 4

    def __init__(self, **kwargs):
        self._node_world_objects = {}
        self._node_scene_items   = {}

        self._scene_item_infos = tuple(kwargs.pop("scene_item_infos", ()))

        for scene_item_info in self._scene_item_infos:
            if not isinstance(scene_item_info, SceneItemInfo):
                raise TypeError(f"Scene item info must be of type SceneItemInfo, not {type(scene_item_info)}")

        super().__init__(**kwargs)

        self._objects_root_node = panda3d.core.PandaNode("__objects_root")
        self._items_root_nodes = {}
        for item_type in (
                "powerup", "container", "generator", "enemy", "trigger",
                "trap", "door", "damage_tile", "exit", "obstacle",
                "teleporter", "rotator", "sound", "random", "unknown",
                ):
            self._items_root_nodes[item_type] = panda3d.core.PandaNode("__%s_root" % item_type)
            self._node_scene_items[item_type] = []

            self.p3d_node.add_child(self._items_root_nodes[item_type])

        self.p3d_node.add_child(self._objects_root_node)

    @property
    def player_count(self): return self._player_count
    @player_count.setter
    def player_count(self, count):
        if not(isinstance(count, int) and count in range(5)):
            raise ValueError("Player count must be either 0, 1, 2, 3, or 4, not '%s'" % count)

        self._player_count = count
        for scene_items in self._node_scene_items.values():
            for scene_item in scene_items:
                node_path = panda3d.core.NodePath(scene_item.p3d_node)
                if scene_item.min_players > self.player_count:
                    node_path.hide()
                else:
                    node_path.show()

    def attach_scene_item(self, scene_item):
        item_type = ""
        if   isinstance(scene_item, SceneItemPowerup):      item_type = "powerup"
        elif isinstance(scene_item, SceneItemContainer):    item_type = "container"
        elif isinstance(scene_item, SceneItemGenerator):    item_type = "generator"
        elif isinstance(scene_item, SceneItemEnemy):        item_type = "enemy"
        elif isinstance(scene_item, SceneItemTrigger):      item_type = "trigger"
        elif isinstance(scene_item, SceneItemTrap):         item_type = "trap"
        elif isinstance(scene_item, SceneItemDoor):         item_type = "door"
        elif isinstance(scene_item, SceneItemDamageTile):   item_type = "damage_tile"
        elif isinstance(scene_item, SceneItemExit):         item_type = "exit"
        elif isinstance(scene_item, SceneItemObstacle):     item_type = "obstacle"
        elif isinstance(scene_item, SceneItemTeleporter):   item_type = "teleporter"
        elif isinstance(scene_item, SceneItemRotator):      item_type = "rotator"
        elif isinstance(scene_item, SceneItemSound):        item_type = "sound"
        elif isinstance(scene_item, SceneItemRandom):       item_type = "random"
        elif isinstance(scene_item, SceneItem):             item_type = "unknown"

        if not item_type:
            raise TypeError(f"Scene item must be of type SceneItem, not {type(scene_item)}")

        self._items_root_nodes[item_type].add_child(scene_item.p3d_node)
        self._node_scene_items[item_type].append(scene_item)

        node_path = panda3d.core.NodePath(scene_item.p3d_node)
        if scene_item.min_players > self.player_count:
            node_path.hide()
        else:
            node_path.show()

    def attach_world_object(self, world_object, node_name=""):
        if not isinstance(world_object, SceneWorldObject):
            raise TypeError(f"World object must be of type SceneWorldObject, not {type(world_object)}")

        node_name = node_name.upper().strip()
        node_collection = self._node_world_objects.setdefault(node_name, dict())
        parent_node_path = self._get_node_path(node_name)

        if world_object.name in node_collection or parent_node_path is None:
            return

        node_collection[world_object.name] = world_object
        parent_node_path.node().add_child(world_object.p3d_node)

    @property
    def node_world_objects(self): return { k: dict(v) for k, v in self._node_world_objects.items() }
    @property
    def node_scene_items(self): return { k: tuple(v) for k, v in self._node_scene_items.items() }
    @property
    def item_infos(self): return list(self._item_infos)
