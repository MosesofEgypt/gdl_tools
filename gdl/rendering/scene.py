import os
import sys
import time
import panda3d.egg
import traceback
import tkinter.filedialog

from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, DirectionalLight, PointLight,\
     NodePath, WindowProperties, CollisionVisualizer, PandaNode

from . import free_camera
from .assets.scene_objects import scene_actor, scene_object, scene_world
from .g3d_to_p3d.util import load_objects_dir_files
from .g3d_to_p3d.scene_objects.scene_actor import load_scene_actor_from_tags
from .g3d_to_p3d.scene_objects.scene_object import load_scene_object_from_tags
from .g3d_to_p3d.scene_objects.scene_world import load_scene_world_from_tags
from .g3d_to_p3d.texture import load_textures_from_objects_tag


class Scene(ShowBase):
    _game_root_dir = ""

    _scene_worlds  = ()
    _scene_objects = ()

    _world_root_node   = None
    _object_root_node = None

    _curr_scene_object_name = ""
    _curr_scene_world_name  = ""

    _camera_light_intensity  = 4
    _ambient_light_intensity = 1
    _camera_light_levels  = 5
    _ambient_light_levels = 5

    _world_camera_controller  = None
    _object_camera_controller = None

    _world_camera_transform  = None
    _object_camera_transform = None

    _viewing_world = True

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

        mat = self.camera.getTransform(render).getMat()
        self._world_camera_transform  = panda3d.core.LMatrix4f(mat)
        self._object_camera_transform = panda3d.core.LMatrix4f(mat)

        self._world_camera_controller  = free_camera.FreeCamera(self, self.camera)
        self._object_camera_controller = free_camera.FreeCamera(self, self.camera)

        self._scene_objects = {}
        self._scene_worlds  = {}

        self._world_root_node  = PandaNode("__world_root")
        self._object_root_node = PandaNode("__object_root")

        render.node().add_child(self._world_root_node)
        render.node().add_child(self._object_root_node)

        self._ambient_light_intensity = self._ambient_light_levels
        self.adjust_ambient_light(0)

    @property
    def active_world(self):
        return self._scene_worlds.get(self._curr_scene_world_name)

    @property
    def active_object(self):
        return self._scene_objects.get(self._curr_scene_object_name)

    @property
    def viewing_world(self):
        return self._viewing_world

    def adjust_fov(self, delta):
        lens = self.camNode.getLens(0)
        new_fov = min(180, max(5, lens.fov.getX() + delta))
        lens.fov = new_fov

    def set_collision_visible(self, visible=None):
        scene_world = self._scene_worlds.get(self._curr_scene_world_name)
        if not scene_world:
            return

        scene_collider_groups = tuple(scene_world.node_collision.values())
        for group in scene_collider_groups:
            for coll in group.values():
                node_path = NodePath(coll.p3d_collision)
                show = node_path.isHidden() if visible is None else visible

                if show:
                    node_path.show()
                else:
                    node_path.hide()

    def set_geometry_visible(self, visible=None):
        scene_world = self.active_world
        if not scene_world:
            return

        for world_scene_objects in scene_world.node_world_objects.values():
            for scene_object in world_scene_objects.values():
                for group in scene_object.node_models.values():
                    for model in group.values():
                        node_path = NodePath(model.p3d_model)
                        show = node_path.isHidden() if visible is None else visible

                        if show:
                            node_path.show()
                        else:
                            node_path.hide()

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

    def switch_scene_view(self, view_world=None):
        if view_world is None:
            view_world = not self.viewing_world

        mat = self.camera.getTransform(render).getMat()
        if view_world:
            self._object_camera_transform = mat
            mat = self._world_camera_transform
            self._object_camera_controller.stop()
            self._world_camera_controller.start()
            NodePath(self._world_root_node).show()
            NodePath(self._object_root_node).hide()
            self.setBackgroundColor(0,0,0)
        else:
            self._world_camera_transform = mat
            mat = self._object_camera_transform
            self._world_camera_controller.stop()
            self._object_camera_controller.start()
            NodePath(self._object_root_node).show()
            NodePath(self._world_root_node).hide()
            self.setBackgroundColor(0.5,0.5,0.5)

        self.camera.setMat(mat)
        self._viewing_world = view_world

    def clear_scene(self):
        for scene_world_name in tuple(self._scene_worlds.keys()):
            scene_world = self._scene_worlds[scene_world_name]
            NodePath(scene_world.p3d_node).removeNode()
            del self._scene_worlds[scene_world_name]

        for scene_object_name in tuple(self._scene_objects.keys()):
            scene_object = self._scene_objects[scene_object_name]
            NodePath(scene_object.p3d_node).removeNode()
            del self._scene_objects[scene_object_name]

    def load_objects(self, objects_path):
        try:
            self._load_objects(objects_path)
            self.switch_scene_view(view_world=False)
        except Exception:
            print(traceback.format_exc())

    def load_world(self, world_path):
        worlds_dir = os.path.join(self._game_root_dir, world_path)
        # TODO
        items_path = ""
        items_dirs = os.path.join(self._game_root_dir, items_path) if items_path else ""
        try:
            self._load_world(worlds_dir)
            for items_dir in items_dirs:
                self._load_items(self.active_world, items_dir)

            self.switch_scene_view(view_world=True)
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

        object_name_to_display = None
        for actor_name in sorted(anim_tag.actor_names):
            scene_actor = load_scene_actor_from_tags(
                actor_name, anim_tag=anim_tag,
                textures=textures, objects_tag=objects_tag,
                )
            self.add_scene_object(scene_actor)

            # remove all object names that will be rendered in an actor
            for model_name in anim_tag.get_model_node_name_map(actor_name)[0]:
                if model_name in object_names:
                    object_names.remove(model_name)

            if object_name_to_display is None:
                object_name_to_display = actor_name

        for object_name in sorted(object_names):
            # TODO: implement this when we can successfully load all object pieces
            break
            scene_object = load_scene_object_from_tags(
                object_name, textures=textures, objects_tag=objects_tag,
                )
            self.add_scene_object(scene_object)
            if object_name_to_display is None:
                object_name_to_display = object_name

        if object_name_to_display:
            self.switch_object(object_name_to_display)

    def _load_world(self, levels_dir):
        start = time.time()
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
            )
        self.add_scene_world(scene_world)
        self.switch_world(scene_world.name)

    def _load_items(self, scene_world, items_path):
        pass

    def add_scene_world(self, world):
        if not isinstance(world, scene_world.SceneWorld):
            raise TypeError(f"Scene world must be of type SceneWorld, not {type(world)}")
        elif world.name in self._scene_worlds:
            raise ValueError(f"SceneWorld with name '{world.name}' already exists")

        self._scene_worlds[world.name] = world

    def add_scene_object(self, object):
        if not isinstance(object, scene_object.SceneObject):
            raise TypeError(f"Scene object must be of type SceneObject, not {type(object)}")
        elif object.name in self._scene_objects:
            raise ValueError(f"SceneObject with name '{object.name}' already exists")

        self._scene_objects[object.name] = object

    @property
    def scene_objects(self):
        return dict(self._scene_objects)

    @property
    def scene_worlds(self):
        return dict(self._scene_worlds)
