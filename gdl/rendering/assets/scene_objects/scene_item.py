import math
import panda3d

from ..collision import Collision
from .scene_actor import SceneActor
from .scene_object import SceneObject
from . import constants as c
from . import util


class SceneItemInfo:
    _actor_name = ""

    _item_type    = c.ITEM_TYPE_NONE
    _item_subtype = c.ITEM_SUBTYPE_NONE

    _coll_type   = c.COLL_TYPE_NULL
    _coll_width  = 0.0
    _coll_length = 0.0
    _coll_offset = (0.0, 0.0, 0.0)

    _properties  = ()

    radius = 0.0
    height = 0.0

    value  = 0
    armor  = 0
    health = 0
    active_type = 0
    active_off  = 0
    active_on   = 0

    def __init__(self, **kwargs):
        self._actor_name   = kwargs.pop("actor_name",   self._actor_name)
        self._item_type    = kwargs.pop("item_type",    self._item_type)
        self._item_subtype = kwargs.pop("item_subtype", self._item_subtype)

        self._coll_type   = kwargs.pop("coll_type",   self._coll_type)
        self._coll_width  = kwargs.pop("coll_width",  self._coll_width)
        self._coll_length = kwargs.pop("coll_length", self._coll_length)
        self._coll_offset = tuple(kwargs.pop("coll_offset", self._coll_offset))

        self._properties  = dict(kwargs.pop("properties", self._properties))

        self.radius = kwargs.pop("radius", self.radius)
        self.height = kwargs.pop("height", self.height)
        self.value  = kwargs.pop("value",  self.value)
        self.armor  = kwargs.pop("armor",  self.armor)
        self.health = kwargs.pop("health", self.health)

        self.active_type = kwargs.pop("active_type", self.active_type)
        self.active_off  = kwargs.pop("active_off",  self.active_off)
        self.active_on   = kwargs.pop("active_on",   self.active_on)

        if self._item_type not in c.ITEM_TYPES:
            raise ValueError("Unknown item type '%s'" % self._item_type)
        elif self._item_subtype not in c.ITEM_SUBTYPES:
            raise ValueError("Unknown item subtype type '%s'" % self._item_subtype)
        elif self._coll_type not in c.COLL_TYPES:
            raise ValueError("Unknown collision type '%s'" % self._coll_type)

    @property
    def actor_name(self): return self._actor_name
    @property
    def item_type(self): return self._item_type
    @property
    def item_subtype(self): return self._item_subtype
    @property
    def coll_type(self): return self._coll_type
    @property
    def coll_width(self): return self._coll_width
    @property
    def coll_length(self): return self._coll_length
    @property
    def coll_offset(self): return self._coll_offset
    @property
    def properties(self): return dict(self._properties)

    def create_instance(self, **kwargs):
        name        = kwargs.pop("name", "")
        flags       = kwargs.pop("flags", {})
        scene_actor = kwargs.pop("scene_actor", None)
        min_players = kwargs.pop("min_players", 0)
        params      = kwargs.pop("params", {})

        scene_item_class = (
            SceneItemPowerup    if self.item_type == c.ITEM_TYPE_POWERUP else
            SceneItemContainer  if self.item_type == c.ITEM_TYPE_CONTAINER else
            SceneItemGenerator  if self.item_type == c.ITEM_TYPE_GENERATOR else
            SceneItemEnemy      if self.item_type == c.ITEM_TYPE_ENEMY else
            SceneItemTrigger    if self.item_type == c.ITEM_TYPE_TRIGGER else
            SceneItemTrap       if self.item_type == c.ITEM_TYPE_TRAP else
            SceneItemDoor       if self.item_type == c.ITEM_TYPE_DOOR else
            SceneItemDamageTile if self.item_type == c.ITEM_TYPE_DAMAGE_TILE else
            SceneItemExit       if self.item_type == c.ITEM_TYPE_EXIT else
            SceneItemObstacle   if self.item_type == c.ITEM_TYPE_OBSTACLE else
            SceneItemTeleporter if self.item_type == c.ITEM_TYPE_TRANSPORTER else
            SceneItemRotator    if self.item_type == c.ITEM_TYPE_ROTATOR else
            SceneItemSound      if self.item_type == c.ITEM_TYPE_SOUND else
            SceneItemRandom     if self.item_type == c.ITEM_TYPE_RANDOM else
            SceneItem
            )

        scene_item = scene_item_class(
            name=name, scene_actor=scene_actor, flags=flags,
            item_info=self, params=params, min_players=min_players,
            )

        x, z, y = kwargs.pop("pos", (0, 0, 0))
        p, h, r = kwargs.pop("rot", (0, 0, 0))
        # offset z by a certain amount to fix z-fighting
        z += 0.001

        nodepath = panda3d.core.NodePath(scene_item.p3d_node)
        nodepath.setPos(panda3d.core.LVecBase3f(x, y, z))
        nodepath.setQuat(panda3d.core.LQuaternionf(
            *util.gdl_euler_to_quaternion(r, h, p)
            ))
        return scene_item


class SceneItem(SceneObject):
    _scene_actor  = None
    _min_players  = 0
    _flags = ()

    def __init__(self, **kwargs):
        item_info = kwargs.pop("item_info", None)
        params    = kwargs.pop("params", {})

        self._min_players = kwargs.pop("min_players", self._min_players)
        self._flags        = dict(kwargs.pop("flags", self._flags))

        super().__init__(**kwargs)
        # TODO: initialize self using item_info and params

        self.scene_actor  = kwargs.pop("scene_actor", self.scene_actor)
        coll_shape = None

        cx, cz, cy = item_info.coll_offset
        if item_info.coll_type == c.COLL_TYPE_CYLINDER:
            coll_shape = panda3d.core.CollisionCapsule(
                cx, cy, cz, cx, cy, cz + item_info.height, item_info.radius
                )
        elif item_info.coll_type == c.COLL_TYPE_SPHERE:
            coll_shape = panda3d.core.CollisionSphere(
                cx, cy, cz, item_info.radius
                )
        elif item_info.coll_type == c.COLL_TYPE_BOX:
            coll_shape = panda3d.core.CollisionBox(
                panda3d.core.Point3F(
                    cx - item_info.coll_width,
                    cy - item_info.coll_length,
                    cz
                    ),
                panda3d.core.Point3F(
                    cx + item_info.coll_width,
                    cy + item_info.coll_length,
                    cz + item_info.height
                    )
                )

        if coll_shape:
            collision = Collision(name=self.name)
            collision.p3d_collision.add_solid(coll_shape)
            self.attach_collision(collision, self.name)

    @property
    def actor_name(self):
        return self.scene_actor.name if self.scene_actor else ""
    @property
    def min_players(self):
        return self._min_players
    @property
    def flags(self): return dict(self._flags)

    @property
    def scene_actor(self):
        return self._scene_actor
    @scene_actor.setter
    def scene_actor(self, scene_actor):
        if not isinstance(scene_actor, (type(None), SceneActor)):
            raise TypeError(f"Scene actor must be either None or of type SceneActor, not {type(scene_actor)}")

        if self._scene_actor:
            self.p3d_node.remove_child(self._scene_actor.p3d_node)

        self._scene_actor = scene_actor
        if scene_actor:
            self.p3d_node.add_child(scene_actor.p3d_node)


class SceneItemRandom(SceneItem):
    _item_indices = ()

    def __init__(self, **kwargs):
        self._item_indices = tuple(kwargs.pop("item_indices", ()))
        super().__init__(**kwargs)

    @property
    def item_indices(self): return self._item_indices


class SceneItemDoor(SceneItem):
    pass


class SceneItemDamageTile(SceneItem):
    pass


class SceneItemContainer(SceneItem):
    item_info = None
    value     = 0


class SceneItemTrigger(SceneItem):
    target  = None
    flags   = 0
    radius  = 0.0
    sound   = None
    id      = -1
    next_id = -1
    start_y = 0
    end_y   = 0


class SceneItemEnemy(SceneItem):
    strength = 0
    ai_type  = 0
    radius   = 0.0
    interval = 0.0


class SceneItemGenerator(SceneItem):
    strength    = 0
    ai_type     = 0
    max_enemies = 0
    interval    = 0.0

    _generator_scene_actors = ()

    def __init__(self, **kwargs):
        self._generator_scene_actors = tuple(kwargs.pop("generator_scene_actors", ()))
        for scene_actor in self._generator_scene_actors:
            if not isinstance(scene_actor, (type(None), SceneActor)):
                raise TypeError(f"Generator scene actors must be either None or of type SceneActor, not {type(scene_actor)}")

        super().__init__(**kwargs)

    @property
    def generator_scene_actors(self): return self._generator_scene_actors

    def set_strength(self, strength):
        if not(isinstance(strength, int) and strength in range(len(self._generator_scene_actors))):
            raise ValueError("No enemy varient for strength of '%s'" % strength)
            
        self.scene_actor = self._generator_scene_actors[strength]
        self.strength = strength


class SceneItemExit(SceneItem):
    next_id = -1
    dest_id = ""


class SceneItemTeleporter(SceneItem):
    id      = -1
    dest_id = -1


class SceneItemRotator(SceneItem):
    target = None
    speed  = 0
    delta  = 0


class SceneItemSound(SceneItem):
    radius     = 0.0
    music_area = 0.0
    fade       = 0.0
    flags      = 0


class SceneItemObstacle(SceneItem):
    subtype  = c.OBSTACLE_TYPE_NONE
    strength = 0.0


class SceneItemPowerup(SceneItem):
    value = 0.0


class SceneItemTrap(SceneItem):
    damage   = 0.0
    interval = 0.0
