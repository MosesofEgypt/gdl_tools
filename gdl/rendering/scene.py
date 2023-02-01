import direct
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
from .g3d_to_p3d.animation import load_texmods_from_anim_tag
from .g3d_to_p3d.texture import load_textures_from_objects_tag


class Scene(ShowBase):
    SCENE_TYPE_WORLD  = 0
    SCENE_TYPE_ACTOR  = 1
    SCENE_TYPE_OBJECT = 2

    _scene_worlds  = ()
    _scene_actors  = ()
    _scene_objects = ()
    _cached_resource_tags = ()
    _cached_resource_textures = ()
    _cached_resource_texture_anims = ()

    _world_root_node  = None
    _actor_root_node  = None
    _object_root_node = None

    _scene_type = SCENE_TYPE_WORLD

    _curr_scene_world_name      = ""
    _curr_scene_actor_set_name  = ""
    _curr_scene_object_set_name = ""

    _curr_scene_actor_name   = ""
    _curr_scene_object_name  = ""

    _ambient_light_intensity = 1
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

    def __init__(self, **kwargs):
        super().__init__()

        # put lighting on the main scene
        self._ambient_light = AmbientLight('alight')
        self.adjust_ambient_light(0)
        self.adjust_ambient_light(0)

        alnp = render.attachNewNode(self._ambient_light)

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
        self._cached_resource_tags = {}
        self._cached_resource_textures = {}
        self._cached_resource_texture_anims = {}

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
        return self._scene_actors.get(self._curr_scene_actor_set_name, {})\
               .get(self._curr_scene_actor_name)

    @property
    def active_object(self):
        return self._scene_objects.get(self._curr_scene_object_set_name, {})\
               .get(self._curr_scene_object_name)

    def adjust_fov(self, angle, delta=True):
        lens = self.camNode.getLens(0)
        new_fov = min(180, max(5, (lens.fov.getX() if delta else 0) + angle))
        lens.fov = new_fov

    def set_world_collision_visible(self, visible=None):
        scene_world = self.active_world
        if scene_world:
            scene_world.set_world_collision_visible(visible)

    def set_item_collision_visible(self, visible=None):
        scene_world = self.active_world
        if scene_world:
            scene_world.set_item_collision_visible(visible)

    def set_world_geometry_visible(self, visible=None):
        scene_world = self.active_world
        if scene_world:
            scene_world.set_world_geometry_visible(visible)

    def set_item_geometry_visible(self, visible=None):
        scene_world = self.active_world
        if scene_world:
            scene_world.set_item_geometry_visible(visible)

    def set_collision_grid_visible(self, visible=None):
        scene_world = self.active_world
        if scene_world:
            scene_world.set_collision_grid_visible(visible)

    def set_player_count(self, count):
        if self.active_world:
            self.active_world.player_count = count

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

    def switch_actor(self, set_name, actor_name):
        if not self._scene_actors:
            return

        curr_scene_actor = self.active_actor
        next_scene_actor = self._scene_actors.get(set_name, {}).get(actor_name)
        if curr_scene_actor:
            self._actor_root_node.remove_child(curr_scene_actor.p3d_node)

        if next_scene_actor:
            self._actor_root_node.add_child(next_scene_actor.p3d_node)
            NodePath(next_scene_actor.p3d_node).show()

        self._curr_scene_actor_name = actor_name
        self._curr_scene_actor_set_name = set_name

    def switch_object(self, set_name, object_name):
        if not self._scene_objects:
            return

        curr_scene_object = self.active_object
        next_scene_object = self._scene_objects.get(set_name, {}).get(object_name)
        if curr_scene_object:
            self._object_root_node.remove_child(curr_scene_object.p3d_node)

        if next_scene_object:
            self._object_root_node.add_child(next_scene_object.p3d_node)
            NodePath(next_scene_object.p3d_node).show()

        self._curr_scene_object_name = object_name
        self._curr_scene_object_set_name = set_name

    def switch_scene_type(self, scene_type):
        if scene_type not in (
                self.SCENE_TYPE_WORLD, self.SCENE_TYPE_ACTOR, self.SCENE_TYPE_OBJECT,
                ):
            return

        try:
            pos = self.camera.getPos()
            rot = self.camera.getHpr()
        except Exception:
            print(traceback.format_exc())
            return

        if self._scene_type == self.SCENE_TYPE_WORLD:
            self._world_camera_pos = pos
            self._world_camera_rot = rot
            self._world_camera_controller.stop()
        elif self._scene_type == self.SCENE_TYPE_ACTOR:
            self._actor_camera_pos = pos
            self._actor_camera_rot = rot
            self._actor_camera_controller.stop()
        elif self._scene_type == self.SCENE_TYPE_OBJECT:
            self._object_camera_pos = pos
            self._object_camera_rot = rot
            self._object_camera_controller.stop()

        NodePath(self._world_root_node).hide()
        NodePath(self._actor_root_node).hide()
        NodePath(self._object_root_node).hide()

        if scene_type == self.SCENE_TYPE_WORLD:
            pos = self._world_camera_pos
            rot = self._world_camera_rot
            self._world_camera_controller.start()
            NodePath(self._world_root_node).show()
            self.setBackgroundColor(0,0,0)
        elif scene_type == self.SCENE_TYPE_ACTOR:
            pos = self._actor_camera_pos
            rot = self._actor_camera_rot
            self._actor_camera_controller.start()
            NodePath(self._actor_root_node).show()
            self.setBackgroundColor(0.5,0.5,0.5)
        elif scene_type == self.SCENE_TYPE_OBJECT:
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

        self._scene_type = scene_type

    def clear_scene(self):
        for scene_world_name in tuple(self._scene_worlds.keys()):
            scene_world = self._scene_worlds[scene_world_name]
            NodePath(scene_world.p3d_node).removeNode()
            del self._scene_worlds[scene_world_name]

        for set_name in set(*self._scene_objects.keys(), *self._scene_actors.keys()):
            for scene_object_name in tuple(self._scene_objects.get(set_name, {}).keys()):
                scene_object = self._scene_objects[scene_object_name]
                NodePath(scene_object.p3d_node).removeNode()
                del self._scene_objects[set_name][scene_object_name]

            for scene_actor_name in tuple(self._scene_actors.get(set_name, {}).keys()):
                scene_actor = self._scene_actors[scene_actor_name]
                NodePath(scene_actor.p3d_node).removeNode()
                del self._scene_actors[set_name][scene_actor_name]

            del self._scene_actors[set_name]

    def build_external_tex_anim_cache(self):
        # loop through all texture animations and link external
        # textures to the global texture they reference.
        anims_by_name = {}
        for set_name, anim_set in self._cached_resource_texture_anims.items():
            for anim_name, global_anim in anim_set.get("global_anims", {}).items():
                if global_anim.external:
                    anims_by_name.setdefault(global_anim.name, []).append(global_anim)

        for set_name, anim_set in self._cached_resource_texture_anims.items():
            for anim_name, global_anim in anim_set.get("global_anims", {}).items():
                external_anims = anims_by_name.get(global_anim.name, ())
                if global_anim.external or not external_anims:
                    continue

                for external_anim in external_anims:
                    external_anim.external_anim = global_anim

    def get_resource_set_textures(self, filepath, is_ngc=False, recache=False):
        resource_dir = os.path.dirname(filepath)
        set_name = self.get_resource_set_name(resource_dir)
        objects_data = self.get_resource_set_tags(resource_dir)
        objects_tag  = objects_data.get("objects_tag")

        if set_name not in self._cached_resource_textures or recache:
            self._cached_resource_textures[set_name] = load_textures_from_objects_tag(
                objects_tag, filepath, is_ngc
                ) if objects_tag else {}

        return dict(self._cached_resource_textures[set_name])

    def get_resource_set_texture_anims(self, dirpath, recache=False):
        set_name = self.get_resource_set_name(dirpath)
        objects_data = self.get_resource_set_tags(dirpath)
        anim_tag = objects_data.get("anim_tag")

        if set_name not in self._cached_resource_texture_anims or recache:
            textures = self.get_resource_set_textures(
                objects_data["textures_filepath"],
                objects_data["is_ngc"],
                recache
                )
            self._cached_resource_texture_anims[set_name] = load_texmods_from_anim_tag(
                anim_tag, textures
                ) if anim_tag else {}

        return dict(self._cached_resource_texture_anims[set_name])

    def get_resource_set_tags(self, dirpath, recache=False):
        set_name = self.get_resource_set_name(dirpath)
        if not self._cached_resource_tags.get(set_name) or recache:
            self._cached_resource_tags[set_name] = dict(
                **(load_objects_dir_files(dirpath) if dirpath else {})
                )

        return dict(self._cached_resource_tags[set_name])

    def get_resource_set_name(self, dirpath):
        set_name = ""
        for part in pathlib.Path(dirpath).parts[::-1]:
            part = part.upper()
            set_name = part.upper() + "/" + set_name
            if part in (
                    "GEN", "ITEMS", "LEVELS", "MAPS",
                    "MONSTERS", "PLAYERS", "POWERUPS", "WEAPONS",
                    "CREDITS", "GROUP1", "GROUP2", "SONY",
                    "INVENTORY", "SELECT", "STATIC", "TITLE",
                    "RETIRE", "LVLADV", "WORLDSEL", "HISCORE", "SHOP", "TEST",
                ):
                break

        return set_name.strip("/")

    def load_objects(self, objects_path, switch_display=True):
        try:
            start = time.time()
            result = self._load_objects(objects_path, switch_display)
            self.build_external_tex_anim_cache()
            if switch_display:
                self.switch_scene_type(
                    self.SCENE_TYPE_ACTOR if self._scene_actors else
                    self.SCENE_TYPE_OBJECT
                    )

            print("Loading '%s' took %s seconds" % (objects_path, time.time() - start))
        except Exception:
            print(traceback.format_exc())
            result = None

        return result

    def load_world(self, worlds_dir, switch_display=True):
        try:
            start = time.time()
            print("Loading '%s'..." % worlds_dir)
            result = self._load_world(worlds_dir, switch_display)
            self.build_external_tex_anim_cache()
            if switch_display:
                self.switch_scene_type(self.SCENE_TYPE_WORLD)

            print("Loading world took %s seconds" % (time.time() - start))
        except Exception:
            print(traceback.format_exc())
            result = None

        return result

    def _load_objects(self, objects_dir, switch_display):
        objects_data = self.get_resource_set_tags(objects_dir)
        set_name = self.get_resource_set_name(objects_dir)
        texture_anims = self.get_resource_set_texture_anims(objects_dir)

        is_ngc            = objects_data.get("is_ngc")
        anim_tag          = objects_data.get("anim_tag")
        objects_tag       = objects_data.get("objects_tag")
        textures_filepath = objects_data.get("textures_filepath")
        actor_tex_anims   = texture_anims.get("actor_anims", {})
        seq_tex_anims     = texture_anims.get("seq_anims", {})
        global_tex_anims  = texture_anims.get("global_anims", {})
        if not objects_tag:
            return {}, {}

        textures = self.get_resource_set_textures(textures_filepath, is_ngc)

        actor_names  = anim_tag.actor_names if anim_tag else ()
        object_names = set()
        if objects_tag:
            object_names = set(objects_tag.get_cache_names(by_name=True)[0])

        scene_actors  = []
        scene_objects = []
        for actor_name in sorted(actor_names):
            scene_actor = self.get_scene_actor(set_name, actor_name)
            if not scene_actor:
                scene_actor = load_scene_actor_from_tags(
                    actor_name, anim_tag=anim_tag,
                    textures=textures, objects_tag=objects_tag,
                    global_tex_anims={
                        **global_tex_anims,
                        **actor_tex_anims.get(actor_name, {})
                        },
                    seq_tex_anims=seq_tex_anims.get(actor_name, {}),
                    )
                self.add_scene_actor(set_name, scene_actor)

            scene_actors.append(scene_actor)
            # remove all object names that will be rendered in an actor
            # TODO: implement removing all objets included in animations
            for model_name in scene_actor.node_models:
                if model_name in object_names:
                    object_names.remove(model_name)

            if switch_display:
                self.switch_actor(set_name, actor_name)
                switch_display = False

        for object_name in sorted(object_names):
            scene_object = self.get_scene_object(set_name, object_name)
            if not scene_object:
                scene_object = load_scene_object_from_tags(
                    object_name, textures=textures, objects_tag=objects_tag,
                    global_tex_anims=global_tex_anims,
                    )
                self.add_scene_object(set_name, scene_object)

            scene_objects.append(scene_object)
            if switch_display:
                self.switch_object(set_name, object_name)
                switch_display = False

        return (
            {a.name: a for a in scene_actors},
            {o.name: o for o in scene_objects}
            )

    def _load_world(self, levels_dir, switch_display):
        objects_data = self.get_resource_set_tags(levels_dir)
        set_name = self.get_resource_set_name(levels_dir)
        texture_anims = self.get_resource_set_texture_anims(levels_dir)

        is_ngc            = objects_data.get("is_ngc")
        anim_tag          = objects_data.get("anim_tag")
        objects_tag       = objects_data.get("objects_tag")
        worlds_tag        = objects_data.get("worlds_tag")
        textures_filepath = objects_data.get("textures_filepath")
        global_tex_anims  = texture_anims.get("global_anims", {})
        if not worlds_tag:
            return None

        game_root_dir = pathlib.Path(levels_dir).parent.parent
        level_name = os.path.basename(levels_dir).lower()
        realm_name = level_name.rstrip("0123456789")

        # locate the folder all the level and shared item dirs are in
        items_dirs = set([
            locate_objects_dir(game_root_dir, "ITEMS", level_name),
            locate_objects_dir(game_root_dir, "ITEMS", realm_name),
            locate_objects_dir(game_root_dir, "POWERUPS"),
            locate_objects_dir(game_root_dir, "WEAPONS"),
            ])

        # loacate the monsters
        enemy_dirs = set()
        for item_instance in worlds_tag.data.item_instances:
            item_info = worlds_tag.data.item_infos[item_instance.item_index]
            if item_info.item_type.enum_name not in ("enemy", "generator"):
                continue

            enemy_name = item_info.data.name.upper().strip()
            enemy_dirnames = ("MONSTERS", enemy_name)
            if enemy_name in ("GENERAL", "GOLEM"):
                enemy_dirnames += (realm_name, )

            items_dirs.add(locate_objects_dir(game_root_dir, *enemy_dirnames))

        # load all necessary items
        world_item_actors = {}
        world_item_objects = {}
        for items_dir in sorted(items_dirs):
            results = self.load_objects(
                items_dir, switch_display=False
                ) if items_dir else None

            if results:
                scene_actors, scene_objects = results
                world_item_actors.update(scene_actors)
                world_item_objects.update(scene_objects)

        # TODO: clean this up to treat different item classes differently
        #       instead of lumping all scene objects and actors into one dict

        textures = self.get_resource_set_textures(textures_filepath, is_ngc)
        scene_world = load_scene_world_from_tags(
            worlds_tag=worlds_tag, objects_tag=objects_tag,
            textures=textures, anim_tag=anim_tag,
            world_item_actors=world_item_actors,
            world_item_objects=world_item_objects,
            global_tex_anims=global_tex_anims,
            )
        self.add_scene_world(scene_world)
        if switch_display:
            self.switch_world(scene_world.name)

        return scene_world

    def add_scene_world(self, world):
        if not isinstance(world, scene_world.SceneWorld):
            raise TypeError(f"Scene world must be of type SceneWorld, not {type(world)}")
        elif world.name in self._scene_worlds:
            # TODO: replace existing world
            return

        self._scene_worlds[world.name] = world

    def add_scene_actor(self, set_name, actor):
        if not isinstance(actor, scene_actor.SceneActor):
            raise TypeError(f"Scene actor must be of type SceneActor, not {type(actor)}")

        self._scene_actors.setdefault(set_name, {})
        if actor.name in self._scene_actors[set_name]:
            # TODO: replace existing object
            return

        self._scene_actors[set_name][actor.name] = actor

    def add_scene_object(self, set_name, object):
        if not isinstance(object, scene_object.SceneObject):
            raise TypeError(f"Scene object must be of type SceneObject, not {type(object)}")

        self._scene_objects.setdefault(set_name, {})
        if object.name in self._scene_objects[set_name]:
            # TODO: replace existing object
            return

        self._scene_objects[set_name][object.name] = object

    @property
    def scene_worlds(self):
        return dict(self._scene_worlds)

    @property
    def scene_actors(self):
        return { k: dict(v) for k, v in self._scene_actors.items() }

    @property
    def scene_objects(self):
        return { k: dict(v) for k, v in self._scene_objects.items() }

    def get_scene_actor(self, set_name, actor_name):
        return self._scene_actors.get(set_name, {}).get(actor_name, None)

    def get_scene_object(self, set_name, object_name):
        return self._scene_objects.get(set_name, {}).get(object_name, None)
