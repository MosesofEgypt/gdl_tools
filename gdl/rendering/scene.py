import direct
import os
import time
import pathlib
import panda3d.egg
import traceback
import tkinter.filedialog

from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, DirectionalLight, PointLight,\
     NodePath, PandaNode, ConfigVariableBool

from . import free_camera
from .assets.scene_objects import scene_actor, scene_object, scene_world
from .g3d_to_p3d.util import load_objects_dir_files, load_realm_data, locate_dir
from .g3d_to_p3d.scene_objects.scene_actor import load_scene_actor_from_tags
from .g3d_to_p3d.scene_objects.scene_object import load_scene_object_from_tags
from .g3d_to_p3d.scene_objects.scene_world import load_scene_world_from_tags
from .g3d_to_p3d.animation import load_texmods_from_anim_tag
from .g3d_to_p3d.texture import load_textures_from_objects_tag


# not letting tkinter be in charge of the main loop gives a serious
# speed increase in windows because tkinter has to be emulated there.
# don't enable this in Mac because according to the docs it will
# lock up the GUI(no explanation as to why though)
TK_CONTROL_MAINLOOP = os.name != "nt"


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

    _curr_world_name      = ""
    _curr_actor_set_name  = ""
    _curr_object_set_name = ""

    _curr_actor_name   = ""
    _curr_object_name  = ""
    _realm_data = ()

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
        # do this before anything
        ConfigVariableBool("tk-main-loop").setValue(TK_CONTROL_MAINLOOP)

        super().__init__()

        # put lighting on the main scene
        self._ambient_light = AmbientLight('alight')
        self._ambient_light.setColor((1, 1, 1, 1))
        render.setLight(render.attachNewNode(self._ambient_light))

        object_camera_parent = NodePath(PandaNode("object_camera_node"))

        # world camera can start in world center
        self._world_camera_pos = self.camera.getPos()
        self._world_camera_rot = self.camera.getHpr()

        # put camera in a reasonable starting position and FOV
        self.camera.setX(5)
        self.camera.setY(-5)
        self.camera.setZ(5)
        self.camera.setH(45)
        self.camera.setP(-35)
        self.camera.setR(0)
        self.set_fov(90)

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
        self._realm_data = {}

        self._world_root_node  = PandaNode("__world_root")
        self._actor_root_node  = PandaNode("__actor_root")
        self._object_root_node = PandaNode("__object_root")

        render.node().add_child(self._world_root_node)
        render.node().add_child(self._actor_root_node)
        render.node().add_child(self._object_root_node)

    @property
    def scene_type(self): return self._scene_type
    @property
    def curr_world_name(self):return self._curr_world_name
    @property
    def curr_actor_name(self): return self._curr_actor_name
    @property
    def curr_actor_set_name(self): return self._curr_actor_set_name
    @property
    def curr_object_name(self): return self._curr_object_name
    @property
    def curr_object_set_name(self): return self._curr_object_set_name

    @property
    def active_world(self):
        return self._scene_worlds.get(self.curr_world_name)

    @property
    def active_actor(self):
        return self._scene_actors.get(self.curr_actor_set_name, {})\
               .get(self.curr_actor_name)

    @property
    def active_object(self):
        return self._scene_objects.get(self.curr_object_set_name, {})\
               .get(self.curr_object_name)

    def get_fov(self):
        return self.camNode.getLens(0).fov.getX()
    def set_fov(self, angle):
        self.camNode.getLens(0).fov = min(180, max(5, angle))

    def get_player_count(self):
        return self.active_world.player_count if self.active_world else 0
    def set_player_count(self, count):
        if self.active_world:
            self.active_world.player_count = count

    def set_world_geometry_visible(self, visible=None):
        scene_world = self.active_world
        if scene_world:
            scene_world.set_world_geometry_visible(visible)

    def set_world_collision_visible(self, visible=None):
        scene_world = self.active_world
        if scene_world:
            scene_world.set_world_collision_visible(visible)

    def set_collision_grid_visible(self, visible=None):
        scene_world = self.active_world
        if scene_world:
            scene_world.set_collision_grid_visible(visible)

    def set_item_geometry_visible(self, visible=None):
        scene_world = self.active_world
        if scene_world:
            scene_world.set_item_geometry_visible(visible)

    def set_container_items_visible(self, visible=None):
        scene_world = self.active_world
        if scene_world:
            scene_world.set_container_items_visible(visible)

    def set_item_collision_visible(self, visible=None):
        scene_world = self.active_world
        if scene_world:
            scene_world.set_item_collision_visible(visible)

    def set_items_visible(self, visible=None, target_hidden=False):
        scene_world = self.active_world
        if scene_world:
            scene_world.set_items_visible(visible, target_hidden)

    def switch_world(self, world_name):
        if not self._scene_worlds:
            return

        curr_world = self.active_world
        next_scene_world = self._scene_worlds.get(world_name)
        if curr_world:
            self._world_root_node.remove_child(curr_world.p3d_node)

        if next_scene_world:
            self._world_root_node.add_child(next_scene_world.p3d_node)
            next_scene_world.p3d_nodepath.show()

        self._curr_world_name = world_name

    def switch_actor(self, set_name, actor_name):
        if not self._scene_actors:
            return

        curr_actor = self.active_actor
        next_scene_actor = self._scene_actors.get(set_name, {}).get(actor_name)
        if curr_actor:
            self._actor_root_node.remove_child(curr_actor.p3d_node)

        if next_scene_actor:
            self._actor_root_node.add_child(next_scene_actor.p3d_node)
            next_scene_actor.p3d_nodepath.show()

        self._curr_actor_name = actor_name
        self._curr_actor_set_name = set_name

    def switch_object(self, set_name, object_name):
        if not self._scene_objects:
            return

        curr_object = self.active_object
        next_scene_object = self._scene_objects.get(set_name, {}).get(object_name)
        if curr_object:
            self._object_root_node.remove_child(curr_object.p3d_node)

        if next_scene_object:
            self._object_root_node.add_child(next_scene_object.p3d_node)
            next_scene_object.p3d_nodepath.show()

        self._curr_object_name = object_name
        self._curr_object_set_name = set_name

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
            scene_world.p3d_nodepath.removeNode()
            del self._scene_worlds[scene_world_name]

        for set_name in set(*self._scene_objects.keys(), *self._scene_actors.keys()):
            for scene_object_name in tuple(self._scene_objects.get(set_name, {}).keys()):
                scene_object = self._scene_objects[scene_object_name]
                scene_object.p3d_nodepath.removeNode()
                del self._scene_objects[set_name][scene_object_name]

            for scene_actor_name in tuple(self._scene_actors.get(set_name, {}).keys()):
                scene_actor = self._scene_actors[scene_actor_name]
                scene_actor.p3d_nodepath.removeNode()
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

    def get_realm_level(self, dirpath, level_name, recache=False):
        level_name = level_name.upper().strip()
        realm_name = level_name.rstrip("0123456789") # HAAAAAACK
        realm = self.get_realm(dirpath, realm_name, recache=recache)
        for level in realm.levels:
            if "LEVEL" + level.name == level_name:
                return level

    def get_realm(self, dirpath, realm_name, recache=False):
        realm_name = realm_name.upper().strip()
        if realm_name not in self._realm_data or recache:
            realm_datas = load_realm_data(dirpath, realm_name)
            self._realm_data[realm_name] = realm_datas.get(realm_name)

        return self._realm_data[realm_name]

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

        level_data = self.get_realm_level(
            locate_dir(game_root_dir, "WDATA"), level_name
            )

        # locate the folder all the level and shared item dirs are in
        items_dirs = set([
            locate_dir(game_root_dir, "ITEMS", level_name),
            locate_dir(game_root_dir, "ITEMS", realm_name),
            locate_dir(game_root_dir, "POWERUPS"),
            locate_dir(game_root_dir, "WEAPONS"),
            ])

        # locate the monsters
        monster_dirs = [
            ["DEATH"],  # always load this fuck
            ]
        if level_data is not None:
            if level_data.enemy_type_boss:      monster_dirs.append([level_data.enemy_type_boss])
            if level_data.enemy_type_aux:       monster_dirs.append([level_data.enemy_type_aux])
            if level_data.enemy_type_gen_small: monster_dirs.append([level_data.enemy_type_gen_small])
            if level_data.enemy_type_gen_large: monster_dirs.append([level_data.enemy_type_gen_large])
            if level_data.enemy_type_gargoyle:  monster_dirs.append([level_data.enemy_type_gargoyle])
            if level_data.enemy_type_golem:     monster_dirs.append(["GOLEM", level_data.enemy_type_golem])
            if level_data.enemy_type_general:   monster_dirs.append(["GENERAL", level_data.enemy_type_general])

            for enemy_type in level_data.enemy_types_special:
                monster_dirs.append([enemy_type])

        for dirs in monster_dirs:
            items_dirs.add(locate_dir(game_root_dir, "MONSTERS", *dirs))

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
            level_data=level_data, worlds_tag=worlds_tag,
            objects_tag=objects_tag, textures=textures, anim_tag=anim_tag,
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
