import panda3d

from .scene_object import SceneObject
from . import constants as c


class SceneItemInfo:
    _item_type    = c.ITEM_TYPE_NONE
    _item_subtype = c.ITEM_SUBTYPE_NONE

    _coll_type   = c.COLL_TYPE_NULL
    _coll_height = 0.0
    _coll_width  = 0.0
    _coll_offset = (0.0, 0.0, 0.0)

    radius = 0.0
    height = 0.0

    value  = 0
    armor  = 0
    health = 0
    active_type = 0
    active_off  = 0
    active_on   = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def create_instance(self, **kwargs):
        pass


class SceneItem(SceneObject):
    _scene_object  = None
    _instance_name = ""

    @property
    def scene_object(self):
        return self._scene_object

    @scene_object.setter
    def scene_object(self, object):
        if not isinstance(object, scene_object.SceneObject):
            raise TypeError(f"Scene object must be of type SceneObject, not {type(object)}")

        if self._scene_object:
            self.p3d_node.remove_child(self._scene_object.p3d_node)

        self._scene_object = object
        self.p3d_node.add_child(object.p3d_node)


class SceneContainer(SceneItem):
    item_info = None
    value     = 0


class SceneTrigger(SceneItem):
    target  = None
    flags   = 0
    radius  = 0.0
    sound   = None
    id      = -1
    next_id = -1
    start_y = 0
    end_y   = 0


class SceneEnemy(SceneItem):
    strength = 0.0
    ai_type  = -1
    radius   = 0.0
    interval = 0.0


class SceneGenerator(SceneItem):
    strength    = 0.0
    ai_type     = -1
    max_enemies = 0
    interval    = 0.0


class SceneExit(SceneItem):
    next_id = -1
    dest_id = ""


class SceneTeleporter(SceneItem):
    id      = -1
    dest_id = -1


class SceneRotator(SceneItem):
    target = None
    speed  = 0
    delta  = 0


class SceneSound(SceneItem):
    radius     = 0.0
    music_area = 0.0
    fade       = 0.0
    flags      = 0


class SceneObstacle(SceneItem):
    subtype  = c.OBSTACLE_TYPE_NONE
    strength = 0.0


class ScenePowerup(SceneItem):
    value    = 0.0


class SceneTrap(SceneItem):
    damage   = 0.0
    interval = 0.0
