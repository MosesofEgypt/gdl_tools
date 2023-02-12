import math
import panda3d

from ..collision import Collision
from .scene_object import SceneObject
from .. import constants as c
from . import util


class SceneItemInfo:
    _actor_name = ""

    _item_type    = c.ITEM_TYPE_NONE
    _item_subtype = c.ITEM_SUBTYPE_NONE
    _item_indices = ()

    _coll_type   = c.COLL_TYPE_NULL
    _coll_width  = 0.0
    _coll_length = 0.0
    _coll_offset = (0.0, 0.0, 0.0)

    _properties  = ()

    radius = 0.0
    height = 0.0
    snap_to_grid = True

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
        self._item_indices = tuple(kwargs.pop("item_indices", ()))

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

        self.snap_to_grid = bool(kwargs.pop("snap_to_grid", self.snap_to_grid))
        self.active_type  = kwargs.pop("active_type", self.active_type)
        self.active_off   = kwargs.pop("active_off",  self.active_off)
        self.active_on    = kwargs.pop("active_on",   self.active_on)

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
    def item_indices(self): return self._item_indices
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
        name           = kwargs.pop("name", "")
        flags          = kwargs.pop("flags", {})
        scene_objects  = kwargs.pop("scene_objects", {})
        min_players    = kwargs.pop("min_players", 0)
        params         = kwargs.pop("params", {})
        item_infos     = kwargs.pop("item_infos", [])
        value_override = kwargs.pop("value_override", None)

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
            name=name if name else self.actor_name, flags=flags,
            item_info=self, params=params, min_players=min_players,
            scene_objects=scene_objects, item_infos=item_infos,
            value_override=value_override
            )

        x, z, y = kwargs.pop("pos", (0, 0, 0))
        p, h, r = kwargs.pop("rot", (0, 0, 0))

        scene_item.p3d_nodepath.setPos(x, y, z)
        scene_item.p3d_nodepath.setQuat(panda3d.core.LQuaternionf(
            *util.gdl_euler_to_quaternion(r, h, p)
            ))

        return scene_item


class SceneItem(SceneObject):
    _item_info = None
    _copy_object  = True
    _scene_object = None
    _scene_objects = ()
    _min_players  = 0
    _item_infos   = ()

    def __init__(self, **kwargs):
        params  = kwargs.pop("params", {})
        flags   = dict(kwargs.pop("flags", {}))

        self._item_info = kwargs.pop("item_info", None)
        self._item_infos = tuple(kwargs.pop("item_infos",   ()))
        self._min_players = kwargs.pop("min_players", self._min_players)
        self._scene_objects = dict(kwargs.pop("scene_objects", {}))

        super().__init__(**kwargs)
        # TODO: initialize self using item_info and params

        self.scene_object = self._scene_objects.get(
            getattr(self._item_info, "actor_name", None)
            )
        coll_shape = None
        # TODO: copy self.scene_object if self._copy_object is True

        cx, cz, cy = self._item_info.coll_offset
        if self._item_info.coll_type == c.COLL_TYPE_CYLINDER:
            coll_shape = panda3d.core.CollisionCapsule(
                cx, cy, cz, cx, cy, cz + self._item_info.height, self._item_info.radius
                )
        elif self._item_info.coll_type == c.COLL_TYPE_SPHERE:
            coll_shape = panda3d.core.CollisionSphere(
                cx, cy, cz, self._item_info.radius
                )
        elif self._item_info.coll_type == c.COLL_TYPE_BOX:
            coll_shape = panda3d.core.CollisionBox(
                panda3d.core.Point3F(
                    cx - self._item_info.coll_width,
                    cy - self._item_info.coll_length,
                    cz
                    ),
                panda3d.core.Point3F(
                    cx + self._item_info.coll_width,
                    cy + self._item_info.coll_length,
                    cz + self._item_info.height
                    )
                )

        if coll_shape:
            collision = Collision(name=self.name)
            collision.p3d_collision.add_solid(coll_shape)
            self.p3d_node.add_child(collision.p3d_collision)
            self.add_collision(collision)

    @property
    def item_info(self):
        return self._item_info
    @property
    def item_infos(self):
        return self._item_infos
    @property
    def object_name(self):
        return self.scene_object.name if self.scene_object else ""
    @property
    def min_players(self):
        return self._min_players
    @property
    def copy_object(self):
        return self._copy_object

    @property
    def scene_object(self):
        return self._scene_object
    @scene_object.setter
    def scene_object(self, scene_object):
        if not isinstance(scene_object, (type(None), SceneObject)):
            raise TypeError(f"Scene object must be either None or of type SceneObject, not {type(scene_object)}")

        if self._scene_object:
            self.p3d_node.remove_child(self._scene_object.p3d_node)

        self._scene_object = scene_object
        if scene_object:
            self.p3d_node.add_child(scene_object.p3d_node)

    def set_collision_visible(self, visible=None):
        visible = super().set_collision_visible(visible)
        scene_object = self.scene_object
        if scene_object:
            visible = scene_object.set_collision_visible(visible)

        return visible

    def set_geometry_visible(self, visible=None):
        visible = super().set_geometry_visible(visible)
        scene_object = self.scene_object
        if scene_object:
            visible = scene_object.set_geometry_visible(visible)

        return visible


class SceneItemDoor(SceneItem):
    pass


class SceneItemDamageTile(SceneItem):
    pass


class SceneItemContainer(SceneItem):
    _contained_item_info = None
    _contained_item_p3d_node = None
    _cached_contained_items = ()
    value      = 0

    def __init__(self, **kwargs):
        self._cached_contained_items = {}
        params = kwargs.pop("params", {})

        self._contained_item_p3d_nodepath = panda3d.core.NodePath(
            panda3d.core.PandaNode("__CONT_ITEM")
            )

        super().__init__(**kwargs)
        self.p3d_node.add_child(self.contained_item_p3d_node)

        if params:
            params = params.container_info
            item_index = params["item_index"]
            self.value = params["value"]
            if item_index in range(len(self.item_infos)):
                self.contained_item_info = self.item_infos[item_index]

    @property
    def contained_item(self):
        return self._cached_contained_items.get(id(self._contained_item_info))
    @property
    def contained_item_info(self):
        return self._contained_item_info
    @contained_item_info.setter
    def contained_item_info(self, item_info):
        if not isinstance(item_info, (type(None), SceneItemInfo)):
            raise TypeError(f"item_info must be either None or of type SceneItemInfo, not {type(item_info)}")

        self.contained_item_p3d_node.remove_all_children()

        if id(item_info) not in self._cached_contained_items:
            self._cached_contained_items[id(item_info)] = item_info.create_instance(
                scene_objects=self._scene_objects,
                item_info=item_info, item_infos=self.item_infos,
                value_override=self.value if item_info.item_subtype == c.ITEM_SUBTYPE_KEY else None
                )

        self.contained_item_p3d_node.add_child(
            self._cached_contained_items[id(item_info)].p3d_node
            )
        self._contained_item_info = item_info

    @property
    def contained_item_p3d_node(self): return self._contained_item_p3d_nodepath.node()
    @property
    def contained_item_p3d_nodepath(self): return self._contained_item_p3d_nodepath

    def set_conatiner_item_visible(self, visible=None):
        visible = self.contained_item_p3d_nodepath.isHidden() if visible is None else visible
        if visible:
            self.contained_item_p3d_nodepath.show()
        else:
            self.contained_item_p3d_nodepath.hide()
        return visible


class SceneItemRandom(SceneItemContainer):
    _copy_object  = False
    _item_indices = ()
    _swap_rate    = 1.0/1.5

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        item_indices = []
        item_indices_to_check = self.item_info.item_indices
        next_item_indices_to_check = []
        seen = set()
        while item_indices_to_check:
            for i in item_indices_to_check:
                if i in seen:
                    continue

                seen.add(i)
                item_info = self.item_infos[i]
                if item_info.item_indices:
                    next_item_indices_to_check.extend(item_info.item_indices)
                else:
                    item_indices.append(i)

            item_indices_to_check = next_item_indices_to_check
            next_item_indices_to_check = []

        self._item_indices = tuple(item_indices)

    @property
    def item_indices(self): return self._item_indices
    @property
    def item_infos(self): return self._item_infos
    @property
    def swap_rate(self): return self._swap_rate

    def update(self, frame_time):
        if not self.item_indices or not self.item_infos:
            return

        item_index_index = int(frame_time * self.swap_rate) % len(self.item_indices)
        item_index = self.item_indices[item_index_index]
        if item_index in range(len(self.item_infos)):
            item_info = self.item_infos[item_index]
        else:
            item_info = None

        if self.contained_item_info is not item_info:
            self.contained_item_info = item_info


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
    _copy_object = False
    _strength    = 0
    ai_type      = 0
    max_enemies  = 0
    interval     = 0.0

    _generator_objects = ()

    def __init__(self, **kwargs):
        self.generator_objects = kwargs.pop("generator_objects", ())

        params = kwargs.pop("params", {})
        if params:
            params = params.generator_info
            self.strength    = params["strength"]
            self.ai_type     = params["ai"]
            self.max_enemies = params["max_enemies"]
            self.interval    = params["interval"]

        super().__init__(**kwargs)

    @property
    def generator_objects(self):
        return self._generator_objects
    @generator_objects.setter
    def generator_objects(self, generator_objects):
        generator_objects = tuple(generator_objects)
        for scene_object in generator_objects:
            if not isinstance(scene_object, (type(None), SceneObject)):
                raise TypeError(f"Generator scene objects must be either None or of type SceneObject, not {type(scene_object)}")

        self._generator_objects = generator_objects
        self.strength = self.strength  # force refreshing generator model

    @property
    def strength(self): return self._strength
    @strength.setter
    def strength(self, strength):
        if isinstance(strength, int) and strength in range(len(self._generator_objects)):
            self.scene_object = self._generator_objects[strength]
        else:
            self.scene_object = None

        self._strength = strength


class SceneItemExit(SceneItem):
    next_id = -1
    dest_id = ""


class SceneItemTeleporter(SceneItem):
    _copy_object  = False
    id      = -1
    dest_id = -1


class SceneItemRotator(SceneItem):
    target = None
    speed  = 0
    delta  = 0


class SceneItemSound(SceneItem):
    _copy_object = False
    radius     = 0.0
    music_area = 0.0
    fade       = 0.0
    flags      = 0


class SceneItemObstacle(SceneItem):
    _copy_object = False
    subtype  = c.OBSTACLE_TYPE_NONE
    strength = 0.0


class SceneItemPowerup(SceneItem):
    _copy_object = False
    value = 0
    
    def __init__(self, **kwargs):
        params = kwargs.get("params", {})
        value_override = kwargs.pop("value_override", None)

        super().__init__(**kwargs)
        if params:
            params = params.powerup_info
            self.value = params["value"]

        if value_override is not None:
            self.value = value_override

        if self.item_info.item_subtype == c.ITEM_SUBTYPE_KEY:
            # MIDWAY HACKS
            actor_name = "KEYRING" if self.value > 1 else "KEY"
            self.scene_object = self._scene_objects.get(actor_name)


class SceneItemTrap(SceneItem):
    damage   = 0.0
    interval = 0.0
