import traceback
import direct
import os

import tkinter.filedialog

from .main_window import MainWindow
from ...rendering.scene import Scene
from ...rendering.assets.scene_objects.scene_item import SceneItemRandom
from .hotkey_menu_binder import HotkeyMenuBinder
from panda3d.core import WindowProperties


class LegendViewer(Scene, HotkeyMenuBinder):
    # cycle at the rate the game is hardcoded to animate at
    FRAME_RATE             = 1/30
    CYCLE_SUBVIEW_RATE     = FRAME_RATE
    CYCLE_SUBVIEW_MIN_TIME = 0.75

    _animation_timer_paused = False
    _animation_timer = 0
    _animation_step  = 1.0
    _prev_animation_timer = 0
    _update_task_timer = 0
    _cycle_subview_timer = 0
    _cycle_subview_left  = 0
    _cycle_subview_right = 0
    _frame_step_amount   = 0

    main_window = None

    _hotkey_menu_binds = (
        dict(key="tab",            func="self.cycle_scene_type", args=[1]),
        dict(key="arrow_up",       func="self.cycle_scene_view", args=[1]),
        dict(key="arrow_down",     func="self.cycle_scene_view", args=[-1]),
        dict(key="arrow_left",     func="lambda s=self: setattr(s, '_cycle_subview_left', -1)"),
        dict(key="arrow_left-up",  func="lambda s=self: setattr(s, '_cycle_subview_left',  0)"),
        dict(key="arrow_right",    func="lambda s=self: setattr(s, '_cycle_subview_right', 1)"),
        dict(key="arrow_right-up", func="lambda s=self: setattr(s, '_cycle_subview_right', 0)"),
        )

    def __init__(self):
        super().__init__(windowType='none')
        self.main_window = MainWindow(scene=self)
        self.startTk()

        props = WindowProperties()
        props.setParentWindow(self.main_window.winfo_id())
        props.setSize(1, 1)  # will be overridden by resize below
        self.openDefaultWindow(props=props)
        self.main_window.resize(None) # force screen refresh and size update

        self.bind_hotkeys(self)

        self.cycle_scene_type()
        self.taskMgr.add(self.update_task, 'LegendViewer::update_task')
        self.taskMgr.add(self.shader_main_loop, 'main_loop::shader_update')

    def shader_main_loop(self, task):
        # TODO: replace this with a proper animation handler
        delta = 0
        if not self._animation_timer_paused:
            delta = self._animation_step * (task.time - self._prev_animation_timer)
        elif self._frame_step_amount:
            delta = self._frame_step_amount
            self._frame_step_amount = 0

        if delta:
            self._animation_timer += delta
            for set_name, resource_set in self._cached_resource_texture_anims.items():
                for anim_name, global_anim in resource_set.get("global_anims", {}).items():
                    global_anim.update(self._animation_timer)

                for actor_name, anim_set in resource_set.get("actor_anims", {}).items():
                    for anim_name, actor_anim in anim_set.items():
                        actor_anim.update(self._animation_timer)

            for scene_item in getattr(self.active_world, "node_scene_items", {}).get("container", ()):
                contained_item = scene_item.contained_item
                if isinstance(contained_item, SceneItemRandom):
                    contained_item.update(self._animation_timer)

            psys_by_name = {}
            if self.active_world:
                psys_by_name.update(self.active_world.node_particle_systems)
                for scene_items in self.active_world.node_scene_items.values():
                    for scene_item in scene_items:
                        psys_by_name.update(scene_item.node_particle_systems)

            if self.active_actor:
                psys_by_name.update(self.active_actor.node_particle_systems)

            for psys in psys_by_name.values():
                psys.update(delta, self.cam)
                psys.render(render, self.cam)

        self._prev_animation_timer = task.time
        return direct.task.Task.cont

    def toggle_fps_counter(self):
        self.setFrameRateMeter(not self.frameRateMeter)

    def toggle_animations(self):
        self._animation_timer_paused = not self._animation_timer_paused

    def reset_animation_timer(self):
        self._animation_timer = 0.0

    def reverse_animation_timer(self):
        self._animation_step *= -1

    def decrement_animation_frame(self):
        self._frame_step_amount = -self.FRAME_RATE

    def increment_animation_frame(self):
        self._frame_step_amount = self.FRAME_RATE

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

        self._update_task_timer = task.time
        return direct.task.Task.cont

    def cycle_scene_type(self, increment=0):
        self.switch_scene_type((self.scene_type + increment) % 3)

    def switch_scene_type(self, scene_type):
        super().switch_scene_type(scene_type)
        self.main_window.scene_updated()

    def set_player_count(self, count):
        super().set_player_count(count)
        self.main_window.scene_updated()

    def cycle_scene_view(self, increment=0):
        if self.scene_type == self.SCENE_TYPE_WORLD:
            curr_set_name = self.curr_world_name
            set_names = tuple(sorted(self._scene_worlds))
        elif self.scene_type == self.SCENE_TYPE_ACTOR:
            curr_set_name = self.curr_actor_set_name
            set_names = tuple(sorted(self._scene_actors))
        elif self.scene_type == self.SCENE_TYPE_OBJECT:
            curr_set_name = self.curr_object_set_name
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

        if self.scene_type == self.SCENE_TYPE_WORLD:
            self.switch_world(set_name)
            self.switch_scene_subview()
        elif self.scene_type == self.SCENE_TYPE_ACTOR:
            self.switch_actor(set_name, self.curr_actor_name)
            self.switch_scene_subview()
        elif self.scene_type == self.SCENE_TYPE_OBJECT:
            self.switch_object(set_name, self.curr_object_name)
            self.switch_scene_subview()
        else:
            return

    def switch_scene_subview(self, increment=0):
        if self.scene_type == self.SCENE_TYPE_WORLD:
            # TODO: implement switching between camera points
            curr_name = self.curr_world_name
            names = tuple(sorted(self._scene_worlds))
        elif self.scene_type == self.SCENE_TYPE_ACTOR:
            curr_name = self.curr_actor_name
            names = tuple(sorted(self._scene_actors.get(
                self.curr_actor_set_name, {}
                )))
        elif self.scene_type == self.SCENE_TYPE_OBJECT:
            curr_name = self.curr_object_name
            names = tuple(sorted(self._scene_objects.get(
                self.curr_object_set_name, {}
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

        if self.scene_type == self.SCENE_TYPE_WORLD:
            self.switch_world(name)
        elif self.scene_type == self.SCENE_TYPE_ACTOR:
            self.switch_actor(self.curr_actor_set_name, name)
        elif self.scene_type == self.SCENE_TYPE_OBJECT:
            self.switch_object(self.curr_object_set_name, name)
        else:
            return

        self.main_window.scene_updated()
