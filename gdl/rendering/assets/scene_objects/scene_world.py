import panda3d
from .. import constants
from .scene_world_object import SceneWorldObject
from .scene_object import SceneObject
from .scene_item import *
from ..model import Model, Geometry


class SceneWorld(SceneObject):
    _node_world_objects = ()
    _node_scene_items = ()

    _scene_item_infos = ()

    _coll_grid = None
    _static_collision_node = None
    _static_objects_node   = None
    _dynamic_objects_node  = None
    _coll_grid_model_node  = None
    _items_root_nodes   = ()
    _flattened_static_geometries = ()
    _flattened_texmod_models = ()

    _visible_states = ()

    _player_count = 4

    def __init__(self, **kwargs):
        self._node_world_objects = {}
        self._node_scene_items   = {}
        self._flattened_static_geometries = {}
        self._flattened_texmod_models = {}

        self._visible_states = dict(
            container_items     = True,
            item_geometry       = True,
            flattened_geometry  = True,
            world_geometry      = True,
            visible_items       = True,
            particle_systems    = True,
            hidden_items        = False,
            item_collision      = False,
            world_collision     = False,
            collision_grid      = False,
            )

        self._coll_grid = kwargs.pop("collision_grid")
        self._scene_item_infos = tuple(kwargs.pop("scene_item_infos", ()))

        for scene_item_info in self._scene_item_infos:
            if not isinstance(scene_item_info, SceneItemInfo):
                raise TypeError(f"Scene item info must be of type SceneItemInfo, not {type(scene_item_info)}")

        super().__init__(**kwargs)

        self._static_objects_node   = panda3d.core.PandaNode("__STATIC_OBJECTS_ROOT")
        self._dynamic_objects_node  = panda3d.core.PandaNode("__DYNAMIC_OBJECTS_ROOT")
        self._coll_grid_model_node  = panda3d.core.ModelNode("__COLL_GRID_MODEL")
        self._static_collision_node = panda3d.core.ModelNode("__STATIC_COLLISION_ROOT")
        self._items_root_nodes = {}
        for item_type in (
                "powerup", "container", "generator", "enemy", "trigger",
                "trap", "door", "damage_tile", "exit", "obstacle",
                "teleporter", "rotator", "sound", "random", "unknown",
                ):
            self._items_root_nodes[item_type] = panda3d.core.PandaNode(
                f"__{item_type}_ROOT".upper()
                )
            self._node_scene_items[item_type] = []

            self.p3d_node.add_child(self._items_root_nodes[item_type])

        self.p3d_node.add_child(self._static_collision_node)
        self.p3d_node.add_child(self._static_objects_node)
        self.p3d_node.add_child(self._dynamic_objects_node)
        self.p3d_node.add_child(self._coll_grid_model_node)

        self._static_collision_node.set_preserve_transform(
            panda3d.core.ModelNode.PT_no_touch
            )

    @property
    def node_world_objects(self): return dict(self._node_world_objects)
    @property
    def node_scene_items(self): return { k: tuple(v) for k, v in self._node_scene_items.items() }
    @property
    def static_objects_node(self): return self._static_objects_node
    @property
    def static_collision_node(self): return self._static_collision_node
    @property
    def dynamic_objects_node(self): return self._dynamic_objects_node
    @property
    def items_root_nodes(self): return { k: tuple(v) for k, v in self._items_root_nodes.items() }
    @property
    def coll_grid_model_node(self): return self._coll_grid_model_node
    @property
    def flattened_texmod_models(self): return dict(self._flattened_texmod_models)
    @property
    def flattened_static_geometries(self): return { k: tuple(v) for k, v in self._flattened_static_geometries.items()}
    @property
    def item_infos(self): return list(self._item_infos)

    @property
    def player_count(self): return self._player_count
    @player_count.setter
    def player_count(self, count):
        if not(isinstance(count, int) and count in range(5)):
            raise ValueError("Player count must be either 0, 1, 2, 3, or 4, not '%s'" % count)

        self._player_count = count
        for scene_items in self._node_scene_items.values():
            for scene_item in scene_items:
                self.set_item_visible(scene_item)

    def clean_orphaned_world_objects(self):
        for node_name, scene_object in self.node_world_objects.items():
            if not scene_object.p3d_node.children:
                self.remove_world_object(node_name)

    def flatten_static_geometries(self, global_tex_anims, flatten_tex_animated=True):
        # NOTE: this will need to be carefully controlled to prevent
        #       flattening too much and preventing world animations playing
        objects_nodepath = panda3d.core.NodePath(self.static_objects_node)

        if flatten_tex_animated:
            # if we are flattening static objects that use the same global
            # texture animations, we loop over all geometries bound to each
            # one, reparent them to a new node under a new node, and then
            # do a strong flatten on everything
            for tex_name, tex_anim in global_tex_anims.items():
                geometries = tex_anim.binds
                tex_anim.clear_binds()

                if not geometries:
                    continue

                lm_textures = {
                    id(g.shader.lm_texture): g.shader.lm_texture
                    for g in geometries
                    }

                for lm_texture in lm_textures.values():
                    lm_name = "" if lm_texture is None else lm_texture.name + "_"
                    # create a new model to hold the combination of these geoms
                    combined_model = Model(name=f"__texmod_{tex_name}_{lm_name}model")

                    self.static_objects_node.add_child(combined_model.p3d_model)
                    geometry_shader = None
                    for geometry in geometries:
                        if geometry.shader.lm_texture is not lm_texture:
                            continue

                        geometry.clear_shader()
                        if geometry_shader is None:
                            geometry_shader = geometry.shader

                        geometry_nodepath = geometry.p3d_nodepath
                        geom_world_pos = geometry_nodepath.get_pos(combined_model.p3d_nodepath)
                        geometry_nodepath.reparent_to(combined_model.p3d_nodepath)
                        geometry_nodepath.set_pos(combined_model.p3d_nodepath, geom_world_pos)

                    combined_model.p3d_nodepath.flatten_strong()
                    # right after flattening, update the preserve to not be touched
                    # by the flatten we're gonna run after. without this, something
                    # in the way animated textures work breaks, and they dont swap.
                    combined_model.p3d_model.set_preserve_transform(
                        panda3d.core.ModelNode.PT_no_touch
                        )

                    for geom_nodepath in combined_model.p3d_nodepath.children:
                        combined_geometry = Geometry(
                            shader=geometry_shader,
                            p3d_geometry=geom_nodepath.node()
                            )
                        combined_model.add_geometry(combined_geometry)

                    # bind the texanim to the new model and add the model to the tracking dict
                    #combined_geometry.apply_shader()
                    tex_anim.bind(combined_geometry)

                    self._flattened_texmod_models[combined_model.name] = combined_model
                    self._flattened_static_geometries.setdefault(combined_model.name, []).append(
                        combined_geometry.p3d_geometry
                        )

        objects_nodepath.flatten_strong()
        self.clean_orphaned_world_objects()

        # locate all flattened geometries(they'll have been autonamed
        # and have more than one geom) and add them to the tracking dict
        for child in self.p3d_nodepath.findAllMatches('**'):
            node = child.node()
            if isinstance(node, panda3d.core.GeomNode) and node.getNumGeoms() > 1:
                self._flattened_static_geometries.setdefault(child.name, []).append(node)

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
        self.set_item_visible(scene_item)

    def remove_world_object(self, object_name):
        object_name = object_name.upper().strip()
        self._node_world_objects.pop(object_name, None)

    def add_world_object(self, world_object):
        if not isinstance(world_object, SceneWorldObject):
            raise TypeError(f"World object must be of type SceneWorldObject, not {type(world_object)}")

        self._node_world_objects[world_object.name] = world_object

    def set_item_visible(self, scene_item):
        state_type = "hidden_items" if scene_item.hidden else "visible_items"
        visible = (self._visible_states[state_type] and
                   self.player_count >= scene_item.min_players)

        scene_item.set_visible(visible)

    def set_world_collision_visible(self, visible=None):
        if visible is None:
            visible = not self._visible_states["world_collision"]

        for scene_object in self.node_world_objects.values():
            scene_object.set_collision_visible(visible)

        self.set_collision_visible(visible)
        self._visible_states["world_collision"] = visible

    def set_world_geometry_visible(self, visible=None, include_flattened=True):
        if visible is None:
            visible = not self._visible_states["world_geometry"]

        self._visible_states["world_geometry"] = visible

        self.set_geometry_visible(visible)
        for scene_object in self.node_world_objects.values():
            scene_object.set_geometry_visible(visible)

        if include_flattened:
            self.set_flattened_geometry_visible(visible)

    def set_flattened_geometry_visible(self, visible=None):
        if visible is None:
            visible = not self._visible_states["flattened_geometry"]

        self._visible_states["flattened_geometry"] = visible

        for geometries in self._flattened_static_geometries.values():
            for p3d_geometry in geometries:
                node_path = panda3d.core.NodePath(p3d_geometry)

                if visible:
                    node_path.show()
                else:
                    node_path.hide()
        return visible

    def set_item_collision_visible(self, visible=None):
        if visible is None:
            visible = not self._visible_states["item_collision"]

        self._visible_states["item_collision"] = visible

        for scene_items in self.node_scene_items.values():
            for scene_item in scene_items:
                scene_item.set_collision_visible(visible)

    def set_item_geometry_visible(self, visible=None):
        if visible is None:
            visible = not self._visible_states["item_geometry"]

        self._visible_states["item_geometry"] = visible

        for scene_items in self.node_scene_items.values():
            for scene_item in scene_items:
                scene_item.set_geometry_visible(visible)

    def set_items_visible(self, visible=None, target_hidden=False):
        state_type = "hidden_items" if target_hidden else "visible_items"
        if visible is None:
            visible = not self._visible_states[state_type]

        self._visible_states[state_type] = visible

        for scene_items in self.node_scene_items.values():
            for scene_item in scene_items:
                self.set_item_visible(scene_item)

    def set_container_items_visible(self, visible=None):
        if visible is None:
            visible = not self._visible_states["container_items"]

        self._visible_states["container_items"] = visible

        for scene_items in self.node_scene_items.values():
            for scene_item in scene_items:
                if hasattr(scene_item, "set_conatiner_item_visible"):
                    scene_item.set_conatiner_item_visible(visible)

    def set_particles_visible(self, visible=None):
        if visible is None:
            visible = not self._visible_states["particle_systems"]

        self._visible_states["particle_systems"] = visible

        super().set_particles_visible(visible)

        for scene_items in self.node_scene_items.values():
            for scene_item in scene_items:
                scene_item.set_particles_visible(visible)

    def set_collision_grid_visible(self, visible=None):
        if visible is None:
            visible = not self._visible_states["collision_grid"]

        self._visible_states["collision_grid"] = visible

        if visible:
            panda3d.core.NodePath(self._coll_grid_model_node).show()
        else:
            panda3d.core.NodePath(self._coll_grid_model_node).hide()

    def snap_to_grid(self, nodepath, max_dist=float("inf"), debug=True):
        x, z, y = nodepath.getPos(self.p3d_nodepath)
        new_pos = self._coll_grid.snap_pos_to_grid(
            x, y, z, self.p3d_nodepath, max_dist
            )

        if new_pos:
            x, y, z = new_pos[0], new_pos[1] + constants.Z_FIGHT_OFFSET, new_pos[2]
            nodepath.setPos(self.p3d_nodepath, x, z, y)
        elif debug:
            print(f"Failed to snap object {nodepath} to collision grid at {(x, z, y)}")

        return bool(new_pos)
