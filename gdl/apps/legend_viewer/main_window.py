import tkinter as tk
import tkinter.filedialog
import sys

from tkinter import TclError
from panda3d.core import WindowProperties
from .scene_controls import SceneControlsWindow
from .animation_controls import AnimationControlsWindow
from .hotkey_menu_binder import HotkeyMenuBinder

__version__ = (0, 1, 0)

class MainWindow(tk.Tk, HotkeyMenuBinder):
    scene = None
    _last_selected_dir = ""
    _title_prefix = "Legend Viewer v%s.%s.%s - Scene " % __version__

    scene_controls = None
    animation_controls = None

    _hotkey_menu_binds = [
        dict(key="l",   name="File|Load world",   func="self.select_and_load_world",   args=[]),
        dict(key="o",   name="File|Load objects", func="self.select_and_load_objects", args=[]),
        dict(name="File|"),
        dict(name="File|Quit", func="self.destroy", args=[]),
        dict(key="f1",  name="World|Toggle world geometry", func="self.scene.set_world_geometry_visible",  args=[]),
        dict(key="f2",  name="World|Toggle world collison", func="self.scene.set_world_collision_visible", args=[]),
        dict(key="f3",  name="World|Toggle item geometry",  func="self.scene.set_item_geometry_visible",   args=[]),
        dict(key="f4",  name="World|Toggle item collison",  func="self.scene.set_item_collision_visible",  args=[]),
        dict(key="f5",  name="World|Toggle collision grid", func="self.scene.set_collision_grid_visible",  args=[]),
        dict(name="World|"),
        dict(key="`",   name="World|Set 0-players", func="self.scene.set_player_count", args=[0]),
        dict(key="1",   name="World|Set 1-players", func="self.scene.set_player_count", args=[1]),
        dict(key="2",   name="World|Set 2-players", func="self.scene.set_player_count", args=[2]),
        dict(key="3",   name="World|Set 3-players", func="self.scene.set_player_count", args=[3]),
        dict(key="4",   name="World|Set 4-players", func="self.scene.set_player_count", args=[4]),
        dict(key="space",     name="Animation|Play/pause animations", func="self.scene.toggleAnimations", args=[]),
        dict(key="backspace", name="Animation|Reset animations",  func="self.scene.resetAnimationTimer",  args=[]),
        #dict(key="f9",  name="Window|Scene controls", func="self.scene_controls.toggle_visible", args=[]),
        #dict(key="f10", name="Window|Animation controls", func="self.animation_controls.toggle_visible", args=[]),
        #dict(key="",  name="Debug|Toggle vertices",    func="self.scene.toggleShowVertices", args=[]),
        dict(key="f6",  name="Debug|Toggle wireframe",   func="self.scene.toggleWireframe",    args=[]),
        dict(key="f7",  name="Debug|Toggle textures",    func="self.scene.toggleTexture",      args=[]),
        dict(key="f8",  name="Debug|Toggle FPS counter", func="self.scene.toggleFpsCounter",   args=[]),
        ]

    def __init__(self, *args, **kwargs):
        self.scene = kwargs.pop("scene")
        super().__init__(*args, **kwargs)

        self.geometry("640x480")
        self.update_title()
        self.update()  # necessary to allow focus to shift to window

        self.scene_controls     = SceneControlsWindow(self, scene=self.scene)
        self.animation_controls = AnimationControlsWindow(self, scene=self.scene)
        self.scene_controls.withdraw()
        self.animation_controls.withdraw()

        self.bind("<Configure>", self.resize)
        self.bind_hotkeys(self.scene)
        self.generate_menu()

    def update_title(self):
        self.title(self.get_title_text())

    def get_title_text(self):
        if self.scene.scene_type == self.scene.SCENE_TYPE_WORLD:
            name     = self.scene.curr_world_name
            suffix   = "World: %s"
        elif self.scene.scene_type == self.scene.SCENE_TYPE_ACTOR:
            name     = self.scene.curr_actor_name
            suffix   = f"Actor: {self.scene.curr_actor_set_name}: %s"
        elif self.scene.scene_type == self.scene.SCENE_TYPE_OBJECT:
            name     = self.scene.curr_object_name
            suffix   = f"Object: {self.scene.curr_object_set_name}: %s"
        else:
            return self._title_prefix

        return self._title_prefix + suffix % (name if name else "(none selected)")

    def resize(self, event):
        try:
            self.update()
            props = WindowProperties()
            props.setOrigin(0, 0)
            props.setSize(self.winfo_width(), self.winfo_height())
            self.scene.win.requestProperties(props)
        except TclError as e:
            pass

    def select_and_load_world(self):
        world_dir = tkinter.filedialog.askdirectory(
            initialdir=self._last_selected_dir,
            title="Select the folder containing the WORLDS.PS2/NGC to load"
            )
        if not world_dir:
            return

        self._last_selected_dir = world_dir
        self.scene.load_world(world_dir)
        self.scene.switch_scene_subview()

    def select_and_load_objects(self):
        objects_dir = tkinter.filedialog.askdirectory(
            initialdir=self._last_selected_dir,
            title="Select the folder containing the OBJECTS.PS2/NGC to load"
            )
        if not objects_dir:
            return

        self._last_selected_dir = objects_dir
        self.scene.load_objects(objects_dir)
        self.scene.switch_scene_subview()
