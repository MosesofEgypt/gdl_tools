import os

import tkinter.filedialog

from tkinter import TclError
from ..rendering.scene import Scene
from panda3d.core import WindowProperties

__version__ = (0, 0, 1)

class LegendViewer(Scene):

    _title_prefix = "Legend Viewer v%s.%s.%s - " % __version__

    def __init__(self):
        super().__init__(windowType='none')
        self.startTk()
        
        self.tk_root = self.tkRoot
        self.tk_root.geometry("640x480")
        self.tk_root.update()
        
        props = WindowProperties()
        props.setParentWindow(self.tk_root.winfo_id())
        props.setOrigin(0, 0)
        props.setSize(
            self.tk_root.winfo_width(),
            self.tk_root.winfo_height()
            )

        base.openDefaultWindow(props=props)
        self.tk_root.bind("<Configure>", self.resize)

        self.accept("arrow_left", self.cycle_viewed, [-1])
        self.accept("arrow_right", self.cycle_viewed, [1])

        self.accept("f1", self.set_geometry_visible, [])
        self.accept("f2", self.set_collision_visible, [])
        self.accept("f3", self.toggleWireframe, [])
        self.accept("f4", self.toggleShowVertices, [])

        self.accept("f5", self.toggleTexture, [])
        self.accept("f6", self.toggleParticles, [])

        self.accept("tab", self.cycle_scene_view, [])

        self.accept("k", self.select_game_root_dir, [])
        self.accept("l", self.select_and_load_world, [])
        self.accept("o", self.select_and_load_objects, [])
        #self.accept("k", self.adjust_ambient_light, [1])
        #self.accept("l", self.adjust_camera_light, [1])
        self.accept("-", self.adjust_fov, [-5])
        self.accept("=", self.adjust_fov, [5])
        self.cycle_viewed()

    @property
    def title_prefix(self):
        return self._title_prefix + (
            "World: "  if self._scene_view == self.SCENE_VIEW_WORLD  else
            "Actor: "  if self._scene_view == self.SCENE_VIEW_ACTOR  else
            "Object: " if self._scene_view == self.SCENE_VIEW_OBJECT else
            ""
            )

    def resize(self, event):
        self.tk_root.update()
        
        props = WindowProperties()
        props.setOrigin(0, 0)
        try:
            props.setSize(self.tk_root.winfo_width(), self.tk_root.winfo_height())
        except TclError as e:
            return

        self.win.requestProperties(props)

    def select_game_root_dir(self):
        root_dir = tkinter.filedialog.askdirectory(
            initialdir=self._game_root_dir,
            title="Select the folder containing the LEVELS and ITEMS folders"
            )
        if root_dir:
            self._game_root_dir = root_dir

    def select_and_load_world(self):
        if not self._game_root_dir:
            self.select_game_root_dir()
            if not self._game_root_dir:
                return

        world_dir = tkinter.filedialog.askdirectory(
            initialdir=self._game_root_dir,
            title="Select the folder containing the WORLDS.PS2/NGC to load"
            )
        if not world_dir:
            return

        world_path = os.path.relpath(world_dir, self._game_root_dir)
        if world_path.startswith("."):
            print("That folder does not exist inside the game directory root '%s'" %
                  self._game_root_dir)
            return

        self.load_world(world_path)

    def select_and_load_objects(self):
        objects_dir = tkinter.filedialog.askdirectory(
            initialdir=self._game_root_dir,
            title="Select the folder containing the OBJECTS.PS2/NGC to load"
            )
        if not objects_dir:
            return

        self.load_objects(objects_dir)

    def cycle_viewed(self, increment=0):
        if self._scene_view == self.SCENE_VIEW_WORLD:
            curr_name = self._curr_scene_world_name
            curr_object = self.active_world
            names = tuple(sorted(self._scene_worlds))
        elif self._scene_view == self.SCENE_VIEW_ACTOR:
            curr_name = self._curr_scene_actor_name
            curr_object = self.active_actor
            names = tuple(sorted(self._scene_actors))
        elif self._scene_view == self.SCENE_VIEW_OBJECT:
            curr_name = self._curr_scene_object_name
            curr_object = self.active_object
            names = tuple(sorted(self._scene_objects))
        else:
            return
        
        name = ""
        if names:
            name_index = increment
            if curr_object:
                name_index += names.index(curr_name)
            name = names[name_index % len(names)]

        if self._scene_view == self.SCENE_VIEW_WORLD:
            self.switch_world(name)
        elif self._scene_view == self.SCENE_VIEW_ACTOR:
            self.switch_actor(name)
        elif self._scene_view == self.SCENE_VIEW_OBJECT:
            self.switch_object(name)
        else:
            return

    def switch_world(self, world_name):
        super().switch_world(world_name)
        name = self.active_world.name if self.active_world else "(none selected)"
        self.tk_root.title(self.title_prefix + name)

    def switch_actor(self, actor_name):
        super().switch_actor(actor_name)
        name = self.active_actor.name if self.active_actor else "(none selected)"
        self.tk_root.title(self.title_prefix + name)

    def switch_object(self, object_name):
        super().switch_object(object_name)
        name = self.active_object.name if self.active_object else "(none selected)"
        self.tk_root.title(self.title_prefix + name)

    def cycle_scene_view(self):
        self.switch_scene_view((self._scene_view + 1) % 3)

    def switch_scene_view(self, scene_view):
        super().switch_scene_view(scene_view)
        scene_object = (
            self.active_world  if self._scene_view == self.SCENE_VIEW_WORLD else
            self.active_actor  if self._scene_view == self.SCENE_VIEW_ACTOR else
            self.active_object
            )
        name = scene_object.name if scene_object else "(none selected)"
        self.tk_root.title(self.title_prefix + name)
