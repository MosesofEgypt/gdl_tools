import traceback
import direct
import os

import tkinter.filedialog

from tkinter import TclError
from ..rendering.scene import Scene
from panda3d.core import WindowProperties

__version__ = (0, 1, 0)

class LegendViewer(Scene):
    # cycle at the rate the game is hardcoded to animate at
    CYCLE_SUBVIEW_RATE     = 1/30
    CYCLE_SUBVIEW_MIN_TIME = 0.75

    _last_selected_dir = ""

    _fps_counter_toggle = False
    _animation_timer_toggle = False
    _animation_timer_paused = False
    _animation_timer = 0
    _prev_animation_timer = 0
    _update_task_timer = 0
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

        self.accept("f9",  setattr, [self, "_fps_counter_toggle", True])
        self.accept("f11", self.set_collision_grid_visible, [])
        self.accept("f12", self.adjust_ambient_light, [1])

        for i in range(5):
            self.accept(str(i), self.set_player_count, [i])

        self.accept("arrow_up",   self.cycle_scene_view, [1])
        self.accept("arrow_down", self.cycle_scene_view, [-1])
        self.accept("arrow_left",     setattr, [self, "_cycle_subview_left", -1])
        self.accept("arrow_left-up",  setattr, [self, "_cycle_subview_left",  0])
        self.accept("arrow_right",    setattr, [self, "_cycle_subview_right", 1])
        self.accept("arrow_right-up", setattr, [self, "_cycle_subview_right", 0])
        self.accept("space",          setattr, [self, "_animation_timer_toggle", True])

        self.accept("tab", self.cycle_scene_type, [1])

        self.accept("l", self.select_and_load_world, [])
        self.accept("o", self.select_and_load_objects, [])
        self.accept("-", self.adjust_fov, [-5])
        self.accept("=", self.adjust_fov, [5])

        self.cycle_scene_type()
        self.taskMgr.add(self.update_task, 'LegendViewer::update_task')
        self.taskMgr.add(self.shader_main_loop, 'main_loop::shader_update')

    def shader_main_loop(self, task):
        if self._animation_timer_toggle:
            self._animation_timer_paused = not self._animation_timer_paused
            self._animation_timer_toggle = False

        if not self._animation_timer_paused:
            self._animation_timer += task.time - self._prev_animation_timer

        # TODO: replace this with a proper animation handler
        if not self._animation_timer_paused:
            for set_name, resource_set in self._cached_resource_texture_anims.items():
                for anim_name, global_anim in resource_set.get("global_anims", {}).items():
                    global_anim.update(self._animation_timer)

                for actor_name, anim_set in resource_set.get("actor_anims", {}).items():
                    for anim_name, actor_anim in anim_set.items():
                        actor_anim.update(self._animation_timer)

        self._prev_animation_timer = task.time
        return direct.task.Task.cont

    def update_task(self, task):
        delta_t = task.time - self._update_task_timer

        if self._cycle_subview_left or self._cycle_subview_right:
            cycle_time = self._cycle_subview_timer - self.CYCLE_SUBVIEW_MIN_TIME

            if self._cycle_subview_timer == 0 or cycle_time >= self.CYCLE_SUBVIEW_RATE:
                self.switch_scene_subview(self._cycle_subview_left + self._cycle_subview_right)
                self._cycle_subview_timer -= self.CYCLE_SUBVIEW_RATE

            self._cycle_subview_timer += delta_t
        else:
            self._cycle_subview_timer = 0

        if self._fps_counter_toggle:
            self._fps_counter_toggle = False
            self.setFrameRateMeter(not self.frameRateMeter)

        self._update_task_timer = task.time
        return direct.task.Task.cont

    @property
    def title_text(self):
        if self._scene_type == self.SCENE_TYPE_WORLD:
            name     = self._curr_scene_world_name
            suffix   = "World: %s"
        elif self._scene_type == self.SCENE_TYPE_ACTOR:
            name     = self._curr_scene_actor_name
            suffix   = f"Actor: {self._curr_scene_actor_set_name}: %s"
        elif self._scene_type == self.SCENE_TYPE_OBJECT:
            name     = self._curr_scene_object_name
            suffix   = f"Object: {self._curr_scene_object_set_name}: %s"
        else:
            return self._title_prefix

        return self._title_prefix + suffix % (name if name else "(none selected)")

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
        if self._scene_type == self.SCENE_TYPE_WORLD:
            curr_set_name = self._curr_scene_world_name
            set_names = tuple(sorted(self._scene_worlds))
        elif self._scene_type == self.SCENE_TYPE_ACTOR:
            curr_set_name = self._curr_scene_actor_set_name
            set_names = tuple(sorted(self._scene_actors))
        elif self._scene_type == self.SCENE_TYPE_OBJECT:
            curr_set_name = self._curr_scene_object_set_name
            set_names = tuple(sorted(self._scene_objects))
        else:
            return

        set_name = ""
        if set_names:
            try:
                name_index = increment + set_names.index(curr_set_name)
            except ValueError:
                name_index = increment
            set_name = set_names[name_index % len(set_names)]

        if self._scene_type == self.SCENE_TYPE_WORLD:
            self.switch_world(set_name)
        elif self._scene_type == self.SCENE_TYPE_ACTOR:
            self.switch_actor(set_name, self._curr_scene_actor_name)
            self.switch_scene_subview()
        elif self._scene_type == self.SCENE_TYPE_OBJECT:
            self.switch_object(set_name, self._curr_scene_object_name)
            self.switch_scene_subview()
        else:
            return

    def switch_scene_subview(self, increment=0):
        if self._scene_type == self.SCENE_TYPE_WORLD:
            # TODO: implement switching between camera points
            return
        elif self._scene_type == self.SCENE_TYPE_ACTOR:
            curr_name = self._curr_scene_actor_name
            names = tuple(sorted(self._scene_actors.get(
                self._curr_scene_actor_set_name, {}
                )))
        elif self._scene_type == self.SCENE_TYPE_OBJECT:
            curr_name = self._curr_scene_object_name
            names = tuple(sorted(self._scene_objects.get(
                self._curr_scene_object_set_name, {}
                )))
        else:
            return

        name = ""
        if names:
            name_index = increment
            try:
                name_index = increment + names.index(curr_name)
            except ValueError:
                name_index = increment
            name = names[name_index % len(names)]

        if self._scene_type == self.SCENE_TYPE_WORLD:
            self.switch_world(name)
        elif self._scene_type == self.SCENE_TYPE_ACTOR:
            self.switch_actor(self._curr_scene_actor_set_name, name)
        elif self._scene_type == self.SCENE_TYPE_OBJECT:
            self.switch_object(self._curr_scene_object_set_name, name)
        else:
            return

    def switch_world(self, world_name):
        super().switch_world(world_name)
        self.tk_root.title(self.title_text)

    def switch_actor(self, set_name, actor_name):
        super().switch_actor(set_name, actor_name)
        self.tk_root.title(self.title_text)

    def switch_object(self, set_name, object_name):
        super().switch_object(set_name, object_name)
        self.tk_root.title(self.title_text)

    def switch_scene_type(self, scene_type):
        super().switch_scene_type(scene_type)
        self.tk_root.title(self.title_text)
