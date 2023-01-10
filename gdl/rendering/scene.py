import os
import time
import pathlib
import panda3d.egg
import traceback
import tkinter.filedialog

from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, DirectionalLight, PointLight,\
     NodePath, WindowProperties, CollisionVisualizer, PandaNode

from . import free_camera
from .assets.scene_objects import scene_actor, scene_object, scene_world
from .g3d_to_p3d.util import load_objects_dir_files, locate_objects_dir
from .g3d_to_p3d.scene_objects.scene_actor import load_scene_actor_from_tags
from .g3d_to_p3d.scene_objects.scene_object import load_scene_object_from_tags
from .g3d_to_p3d.scene_objects.scene_world import load_scene_world_from_tags
from .g3d_to_p3d.texture import load_textures_from_objects_tag


class Scene(ShowBase):
    SCENE_VIEW_WORLD  = 0
    SCENE_VIEW_ACTOR  = 1
    SCENE_VIEW_OBJECT = 2

    _scene_worlds  = ()
    _scene_actors  = ()
    _scene_objects = ()

    _world_root_node  = None
    _actor_root_node  = None
    _object_root_node = None

    _curr_scene_world_name  = ""
    _curr_scene_actor_name  = ""
    _curr_scene_object_name = ""

    _camera_light_intensity  = 4
    _ambient_light_intensity = 1
    _camera_light_levels  = 5
    _ambient_light_levels = 5

    _world_camera_controller  = None
    _actor_camera_controller  = None
    _object_camera_controller = None

    _world_camera_pos  = None
    _actor_camera_pos  = None
    _object_camera_pos = None
    _world_camera_rot  = None
    _actor_camera_rot  = None
    _object_camera_rot = None

    _scene_view = SCENE_VIEW_WORLD

    def __init__(self, **kwargs):
        super().__init__()

        # put lighting on the main scene
        self._camera_light  = DirectionalLight('dlight')
        self._ambient_light = AmbientLight('alight')
        self.adjust_ambient_light(0)
        self.adjust_ambient_light(0)

        dlnp = self.camera.attachNewNode(self._camera_light)
        alnp = render.attachNewNode(self._ambient_light)

        render.setLight(dlnp)
        render.setLight(alnp)

        object_camera_parent = NodePath(PandaNode("object_camera_node"))

        # world camera can start in world center
        self._world_camera_pos = self.camera.getPos()
        self._world_camera_rot = self.camera.getHpr()

        # put camera in a reasonable starting position
        self.camera.setX(5)
        self.camera.setY(-5)
        self.camera.setZ(5)
        self.camera.setH(45)
        self.camera.setP(-35)
        self.adjust_fov(90, delta=False)

        self._actor_camera_pos = self._object_camera_pos = self.camera.getPos()
        self._actor_camera_rot = self._object_camera_rot = self.camera.getHpr()

        self._world_camera_controller  = free_camera.FreeCamera(self, self.camera, self.camera.parent)
        self._actor_camera_controller  = free_camera.FreeCamera(self, self.camera, self.camera.parent)
        self._object_camera_controller = free_camera.FreeCamera(self, self.camera, self.camera.parent)
        self._world_camera_controller.start()

        self._scene_worlds  = {}
        self._scene_actors  = {}
        self._scene_objects = {}

        self._world_root_node  = PandaNode("__world_root")
        self._actor_root_node  = PandaNode("__actor_root")
        self._object_root_node = PandaNode("__object_root")

        render.node().add_child(self._world_root_node)
        render.node().add_child(self._actor_root_node)
        render.node().add_child(self._object_root_node)

        self._ambient_light_intensity = self._ambient_light_levels
        self.adjust_ambient_light(0)

    @property
    def active_world(self):
        return self._scene_worlds.get(self._curr_scene_world_name)

    @property
    def active_actor(self):
        return self._scene_actors.get(self._curr_scene_actor_name)

    @property
    def active_object(self):
        return self._scene_objects.get(self._curr_scene_object_name)

    def adjust_fov(self, angle, delta=True):
        lens = self.camNode.getLens(0)
        new_fov = min(180, max(5, (lens.fov.getX() if delta else 0) + angle))
        lens.fov = new_fov

    def set_world_collision_visible(self, visible=None):
        scene_world = self._scene_worlds.get(self._curr_scene_world_name)
        if not scene_world:
            return

        for group in scene_world.node_collision.values():
            for coll in group.values():
                node_path = NodePath(coll.p3d_collision)
                visible = node_path.isHidden() if visible is None else visible

                if visible:
                    node_path.show()
                else:
                    node_path.hide()

    def set_item_collision_visible(self, visible=None):
        scene_world = self._scene_worlds.get(self._curr_scene_world_name)
        if not scene_world:
            return

        # TODO: write this

    def set_world_geometry_visible(self, visible=None):
        scene_world = self.active_world
        if not scene_world:
            return

        # TODO: move this logic into SceneObject and SceneWorld and SceneWorldObject
        for world_scene_objects in scene_world.node_world_objects.values():
            for scene_object in world_scene_objects.values():
                for group in scene_object.node_models.values():
                    for model in group.values():
                        node_path = NodePath(model.p3d_model)
                        visible = node_path.isHidden() if visible is None else visible

                        if visible:
                            node_path.show()
                        else:
                            node_path.hide()

    def set_item_geometry_visible(self, visible=None):
        scene_world = self.active_world
        if not scene_world:
            return

        # TODO: write this

    def set_player_count(self, count):
        if self.active_world:
            self.active_world.player_count = count

    def adjust_camera_light(self, amount):
        self._camera_light_intensity += amount
        self._camera_light_intensity %= self._camera_light_levels + 1
        self._camera_light.setColor((
            self._camera_light_intensity / self._camera_light_levels,
            self._camera_light_intensity / self._camera_light_levels,
            self._camera_light_intensity / self._camera_light_levels,
            1
            ))

    def adjust_ambient_light(self, amount):
        self._ambient_light_intensity += amount
        self._ambient_light_intensity %= self._ambient_light_levels + 1
        self._ambient_light.setColor((
            self._ambient_light_intensity / self._ambient_light_levels,
            self._ambient_light_intensity / self._ambient_light_levels,
            self._ambient_light_intensity / self._ambient_light_levels,
            1
            ))

    def switch_world(self, world_name):
        if not self._scene_worlds:
            return

        curr_scene_world = self.active_world
        next_scene_world = self._scene_worlds.get(world_name)
        if curr_scene_world:
            self._world_root_node.remove_child(curr_scene_world.p3d_node)

        if next_scene_world:
            self._world_root_node.add_child(next_scene_world.p3d_node)
            NodePath(next_scene_world.p3d_node).show()

        self._curr_scene_world_name = world_name

    def switch_actor(self, actor_name):
        if not self._scene_actors:
            return

        curr_scene_actor = self.active_actor
        next_scene_actor = self._scene_actors.get(actor_name)
        if curr_scene_actor:
            self._actor_root_node.remove_child(curr_scene_actor.p3d_node)

        if next_scene_actor:
            self._actor_root_node.add_child(next_scene_actor.p3d_node)
            NodePath(next_scene_actor.p3d_node).show()

        self._curr_scene_actor_name = actor_name

    def switch_object(self, object_name):
        if not self._scene_objects:
            return

        curr_scene_object = self.active_object
        next_scene_object = self._scene_objects.get(object_name)
        if curr_scene_object:
            self._object_root_node.remove_child(curr_scene_object.p3d_node)

        if next_scene_object:
            self._object_root_node.add_child(next_scene_object.p3d_node)
            NodePath(next_scene_object.p3d_node).show()

        self._curr_scene_object_name = object_name

    def switch_scene_view(self, scene_view):
        if scene_view not in (
                self.SCENE_VIEW_WORLD, self.SCENE_VIEW_ACTOR, self.SCENE_VIEW_OBJECT,
                ):
            return

        try:
            pos = self.camera.getPos()
            rot = self.camera.getHpr()
        except Exception:
            print(traceback.format_exc())
            return

        if self._scene_view == self.SCENE_VIEW_WORLD:
            self._world_camera_pos = pos
            self._world_camera_rot = rot
            self._world_camera_controller.stop()
            NodePath(self._world_root_node).hide()
        elif self._scene_view == self.SCENE_VIEW_ACTOR:
            self._actor_camera_pos = pos
            self._actor_camera_rot = rot
            self._actor_camera_controller.stop()
            NodePath(self._actor_root_node).hide()
        elif self._scene_view == self.SCENE_VIEW_OBJECT:
            self._object_camera_pos = pos
            self._object_camera_rot = rot
            self._object_camera_controller.stop()
            NodePath(self._object_root_node).hide()

        if scene_view == self.SCENE_VIEW_WORLD:
            pos = self._world_camera_pos
            rot = self._world_camera_rot
            self._world_camera_controller.start()
            NodePath(self._world_root_node).show()
            self.setBackgroundColor(0,0,0)
        elif scene_view == self.SCENE_VIEW_ACTOR:
            pos = self._actor_camera_pos
            rot = self._actor_camera_rot
            self._actor_camera_controller.start()
            NodePath(self._actor_root_node).show()
            self.setBackgroundColor(0.5,0.5,0.5)
        elif scene_view == self.SCENE_VIEW_OBJECT:
            pos = self._object_camera_pos
            rot = self._object_camera_rot
            self._object_camera_controller.start()
            NodePath(self._object_root_node).show()
            self.setBackgroundColor(0.5,0.5,0.5)

        try:
            self.camera.setPos(pos)
            self.camera.setHpr(rot)
        except Exception:
            print(traceback.format_exc())

        self._scene_view = scene_view

    def clear_scene(self):
        for scene_world_name in tuple(self._scene_worlds.keys()):
            scene_world = self._scene_worlds[scene_world_name]
            NodePath(scene_world.p3d_node).removeNode()
            del self._scene_worlds[scene_world_name]

        for scene_object_name in tuple(self._scene_objects.keys()):
            scene_object = self._scene_objects[scene_object_name]
            NodePath(scene_object.p3d_node).removeNode()
            del self._scene_objects[scene_object_name]

        for scene_actor_name in tuple(self._scene_actors.keys()):
            scene_actor = self._scene_actors[scene_actor_name]
            NodePath(scene_actor.p3d_node).removeNode()
            del self._scene_actors[scene_actor_name]

    def load_objects(self, objects_path):
        try:
            self._load_objects(objects_path)
            self.switch_scene_view(
                self.SCENE_VIEW_ACTOR if self._scene_actors else
                self.SCENE_VIEW_OBJECT
                )
        except Exception:
            print(traceback.format_exc())

    def load_world(self, worlds_dir):
        game_root_dir = pathlib.Path(worlds_dir).parent.parent

        world_name = os.path.basename(worlds_dir).lower()
        realm_name = world_name.rstrip("0123456789")

        # locate the folder all the level items dirs are in
        items_dirs = [
            locate_objects_dir(game_root_dir, "items", world_name),
            locate_objects_dir(game_root_dir, "items", realm_name),
            locate_objects_dir(game_root_dir, "powerups"),
            locate_objects_dir(game_root_dir, "weapons"),
            ]

        try:
            world_item_actors = {}
            for items_dir in items_dirs:
                world_item_actors.update(self._load_world_item_actors(items_dir))

            self._load_world(worlds_dir, world_item_actors)

            self.switch_scene_view(self.SCENE_VIEW_WORLD)
        except Exception:
            print(traceback.format_exc())

    def _load_objects(self, objects_dir):
        start = time.time()
        objects_data = load_objects_dir_files(objects_dir) if objects_dir else None
        if not objects_data:
            return

        print("Loading files took %s seconds" % (time.time() - start))
        is_ngc            = objects_data["is_ngc"]
        anim_tag          = objects_data["anim_tag"]
        objects_tag       = objects_data["objects_tag"]
        textures_filepath = objects_data["textures_filepath"]
        if not objects_tag:
            return

        textures = load_textures_from_objects_tag(
            objects_tag, textures_filepath, is_ngc
            )

        actor_names  = anim_tag.actor_names if anim_tag else ()
        object_names = set()
        if objects_tag:
            object_names = set(objects_tag.get_cache_names(by_name=True)[0])

        display_actor = display_object = True
        for actor_name in sorted(anim_tag.actor_names):
            scene_actor = load_scene_actor_from_tags(
                actor_name, anim_tag=anim_tag,
                textures=textures, objects_tag=objects_tag,
                )
            self.add_scene_actor(scene_actor)

            # remove all object names that will be rendered in an actor
            # TODO: implement removing all objets included in animations
            for model_name in anim_tag.get_model_node_name_map(actor_name)[0]:
                if model_name in object_names:
                    object_names.remove(model_name)

            if display_actor:
                self.switch_actor(actor_name)
                display_actor = False

        for object_name in sorted(object_names):
            scene_object = load_scene_object_from_tags(
                object_name, textures=textures, objects_tag=objects_tag,
                )
            self.add_scene_object(scene_object)
            if display_object:
                self.switch_object(object_name)
                display_object = False

    def _load_world(self, levels_dir, world_item_actors=()):
        start = time.time()
        if world_item_actors is None:
            world_item_actors = {}

        objects_data = load_objects_dir_files(levels_dir) if levels_dir else None
        if not objects_data:
            return

        print("Loading files took %s seconds" % (time.time() - start))
        is_ngc            = objects_data["is_ngc"]
        anim_tag          = objects_data["anim_tag"]
        objects_tag       = objects_data["objects_tag"]
        worlds_tag        = objects_data["worlds_tag"]
        textures_filepath = objects_data["textures_filepath"]
        if not worlds_tag:
            return

        textures = load_textures_from_objects_tag(
            objects_tag, textures_filepath, is_ngc
            )
        scene_world = load_scene_world_from_tags(
            worlds_tag=worlds_tag, objects_tag=objects_tag,
            textures=textures, anim_tag=anim_tag,
            world_item_actors=world_item_actors,
            )
        self.add_scene_world(scene_world)
        self.switch_world(scene_world.name)

    def _load_world_item_actors(self, items_dir):
        start = time.time()
        objects_data = load_objects_dir_files(items_dir) if items_dir else None
        world_item_actors = {}
        if objects_data:
            print("Loading files took %s seconds" % (time.time() - start))
            is_ngc            = objects_data["is_ngc"]
            anim_tag          = objects_data["anim_tag"]
            objects_tag       = objects_data["objects_tag"]
            textures_filepath = objects_data["textures_filepath"]

            textures = load_textures_from_objects_tag(
                objects_tag, textures_filepath, is_ngc
                )

            # load the actors so they're ready to map to items
            for actor_name in (anim_tag.actor_names if anim_tag else ()):
                world_item_actors[actor_name] = load_scene_actor_from_tags(
                    actor_name, anim_tag=anim_tag,
                    textures=textures, objects_tag=objects_tag,
                    )

        return world_item_actors

    def add_scene_world(self, world):
        if not isinstance(world, scene_world.SceneWorld):
            raise TypeError(f"Scene world must be of type SceneWorld, not {type(world)}")
        elif world.name in self._scene_worlds:
            # TODO: replace existing world
            return

        self._scene_worlds[world.name] = world

    def add_scene_actor(self, actor):
        if not isinstance(actor, scene_actor.SceneActor):
            raise TypeError(f"Scene actor must be of type SceneActor, not {type(actor)}")
        elif actor.name in self._scene_actors:
            # TODO: replace existing actor
            return

        self._scene_actors[actor.name] = actor

    def add_scene_object(self, object):
        if not isinstance(object, scene_object.SceneObject):
            raise TypeError(f"Scene object must be of type SceneObject, not {type(object)}")
        elif object.name in self._scene_objects:
            # TODO: replace existing object
            return

        self._scene_objects[object.name] = object

    @property
    def scene_worlds(self):
        return dict(self._scene_worlds)

    @property
    def scene_actors(self):
        return dict(self._scene_actors)

    @property
    def scene_objects(self):
        return dict(self._scene_objects)
