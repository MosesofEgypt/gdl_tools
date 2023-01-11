import direct
import os

import tkinter.filedialog

from tkinter import TclError
from ..rendering.scene import Scene
from panda3d.core import WindowProperties

__version__ = (0, 0, 2)

class LegendViewer(Scene):
    # cycle at the rate the game is hardcoded to animate at
    CYCLE_SUBVIEW_RATE     = 1/30
    CYCLE_SUBVIEW_MIN_TIME = 0.75

    _last_selected_dir = ""

    _time = 0
    _cycle_subview_timer = 0
    _cycle_subview_left  = 0
    _cycle_subview_right = 0

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

        self.accept("f1", self.set_world_geometry_visible, [])
        self.accept("f2", self.set_item_geometry_visible, [])
        self.accept("f3", self.set_world_collision_visible, [])
        self.accept("f4", self.set_item_collision_visible, [])

        self.accept("f5", self.toggleWireframe, [])
        self.accept("f6", self.toggleShowVertices, [])
        self.accept("f7", self.toggleTexture, [])
        self.accept("f8", self.toggleParticles, [])

        self.accept("f11", self.adjust_ambient_light, [1])
        self.accept("f12", self.adjust_camera_light,  [1])

        for i in range(5):
            self.accept(str(i), self.set_player_count, [i])

        self.accept("arrow_up",   self.cycle_scene_view, [1])
        self.accept("arrow_down", self.cycle_scene_view, [1])
        self.accept("arrow_left",     setattr, [self, "_cycle_subview_left", -1])
        self.accept("arrow_left-up",  setattr, [self, "_cycle_subview_left",  0])
        self.accept("arrow_right",    setattr, [self, "_cycle_subview_right", 1])
        self.accept("arrow_right-up", setattr, [self, "_cycle_subview_right", 0])

        self.accept("tab", self.cycle_scene_type, [1])

        self.accept("l", self.select_and_load_world, [])
        self.accept("o", self.select_and_load_objects, [])
        self.accept("-", self.adjust_fov, [-5])
        self.accept("=", self.adjust_fov, [5])

        self.cycle_scene_type()
        self.taskMgr.add(self.update_task, 'LegendViewer::update_task')

    def update_task(self, task):
        delta_t = task.time - self._time

        if self._cycle_subview_left or self._cycle_subview_right:
            cycle_time = self._cycle_subview_timer - self.CYCLE_SUBVIEW_MIN_TIME

            if self._cycle_subview_timer == 0 or cycle_time >= self.CYCLE_SUBVIEW_RATE:
                self.switch_scene_subview(self._cycle_subview_left + self._cycle_subview_right)
                self._cycle_subview_timer -= self.CYCLE_SUBVIEW_RATE

            self._cycle_subview_timer += delta_t
        else:
            self._cycle_subview_timer = 0

        self._time = task.time
        return direct.task.Task.cont

    @property
    def title_prefix(self):
        return self._title_prefix + (
            "World: "  if self._scene_type == self.SCENE_TYPE_WORLD  else
            "Actor: "  if self._scene_type == self.SCENE_TYPE_ACTOR  else
            "Object: " if self._scene_type == self.SCENE_TYPE_OBJECT else
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

    def select_and_load_world(self):
        world_dir = tkinter.filedialog.askdirectory(
            initialdir=self._last_selected_dir,
            title="Select the folder containing the WORLDS.PS2/NGC to load"
            )
        if not world_dir:
            return

        self._last_selected_dir = world_dir
        self.load_world(world_dir)

    def select_and_load_objects(self):
        objects_dir = tkinter.filedialog.askdirectory(
            initialdir=self._last_selected_dir,
            title="Select the folder containing the OBJECTS.PS2/NGC to load"
            )
        if not objects_dir:
            return

        self._last_selected_dir = objects_dir
        self.load_objects(objects_dir)

    def cycle_scene_type(self, increment=0):
        self.switch_scene_type((self._scene_type + increment) % 3)

    def cycle_scene_view(self, increment=0):
        pass

    def switch_scene_subview(self, increment=0):
        if self._scene_type == self.SCENE_TYPE_WORLD:
            curr_name = self._curr_scene_world_name
            curr_object = self.active_world
            names = tuple(sorted(self._scene_worlds))
        elif self._scene_type == self.SCENE_TYPE_ACTOR:
            curr_name = self._curr_scene_actor_name
            curr_object = self.active_actor
            names = tuple(sorted(self._scene_actors))
        elif self._scene_type == self.SCENE_TYPE_OBJECT:
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

        if self._scene_type == self.SCENE_TYPE_WORLD:
            self.switch_world(name)
        elif self._scene_type == self.SCENE_TYPE_ACTOR:
            self.switch_actor(name)
        elif self._scene_type == self.SCENE_TYPE_OBJECT:
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

    def switch_scene_type(self, scene_type):
        super().switch_scene_type(scene_type)
        scene_object = (
            self.active_world  if self._scene_type == self.SCENE_TYPE_WORLD else
            self.active_actor  if self._scene_type == self.SCENE_TYPE_ACTOR else
            self.active_object
            )
        name = scene_object.name if scene_object else "(none selected)"
        self.tk_root.title(self.title_prefix + name)
