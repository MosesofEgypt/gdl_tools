import tkinter as tk
import tkinter.filedialog
import sys

from tkinter import TclError
from panda3d.core import WindowProperties
from .scene_controls import SceneControlsWindow
from .animation_controls import AnimationControlsWindow
from .hotkey_menu_binder import HotkeyMenuBinder

__version__ = (0, 3, 0)

class MainWindow(tk.Tk, HotkeyMenuBinder):
    scene = None
    _last_selected_dir = ""
    _title_prefix = "Legend Viewer v%s.%s.%s - Scene " % __version__

    scene_controls = None
    animation_controls = None

    _hotkey_menu_binds = (
        dict(key="control-l",   name="File|Load world",   func="self.select_and_load_world"),
        dict(key="control-o",   name="File|Load objects", func="self.select_and_load_objects"),
        dict(           name="File|"),
        dict(           name="File|Quit", func="self.destroy"),
        dict(key="`",   name="Edit|Players|0-players", func="self.scene.set_player_count", args=[0]),
        dict(key="1",   name="Edit|Players|1-players", func="self.scene.set_player_count", args=[1]),
        dict(key="2",   name="Edit|Players|2-players", func="self.scene.set_player_count", args=[2]),
        dict(key="3",   name="Edit|Players|3-players", func="self.scene.set_player_count", args=[3]),
        dict(key="4",   name="Edit|Players|4-players", func="self.scene.set_player_count", args=[4]),
        dict(name="Window|Scene controls", func="self.scene_controls.toggle_visible"),
        dict(name="Window|Animation controls", func="self.animation_controls.toggle_visible"),
        dict(key="f1",  name="Debug|Toggle world geometry", func="self.scene.set_world_geometry_visible"),
        dict(key="f2",  name="Debug|Toggle world collison", func="self.scene.set_world_collision_visible"),
        dict(key="f3",  name="Debug|Toggle item geometry",  func="self.scene.set_item_geometry_visible"),
        dict(key="f4",  name="Debug|Toggle item collison",  func="self.scene.set_item_collision_visible"),
        #dict(key="f4",  name="Debug|", func=""),
        dict(name="Debug|"),
        dict(key="f5",  name="Debug|Toggle items visible",  func="self.scene.set_items_visible",  args=[None, False]),
        dict(key="f6",  name="Debug|Toggle hidden items visible",  func="self.scene.set_items_visible",  args=[None, True]),
        dict(key="f7",  name="Debug|Toggle container items", func="self.scene.set_container_items_visible"),
        dict(key="f8",  name="Debug|Toggle collision grid", func="self.scene.set_collision_grid_visible"),
        dict(name="Debug|"),
        dict(key="f9",  name="Debug|Toggle framerate",  func="self.scene.toggle_fps_counter"),
        dict(key="f10", name="Debug|Toggle particles",  func="self.scene.set_particles_visible"),
        dict(key="f11", name="Debug|Toggle textures",   func="self.scene.toggleTexture"),
        dict(key="f12", name="Debug|Toggle wireframe",  func="self.scene.toggleWireframe"),
        dict(           name="Debug|Toggle vertices",   func="self.scene.toggleShowVertices"),
        )

    def __init__(self, *args, **kwargs):
        self.scene = kwargs.pop("scene")
        super().__init__(*args, **kwargs)

        self.geometry("640x480")
        self.title(self.get_title_text())
        self.update()  # necessary to allow focus to shift to window

        self.scene_controls     = SceneControlsWindow(self, scene=self.scene)
        self.animation_controls = AnimationControlsWindow(self, scene=self.scene)
        self.scene_controls.withdraw()
        self.animation_controls.withdraw()

        self.bind("<Configure>", self.resize)
        self.bind_hotkeys(self.scene)
        self.generate_menu()

    def scene_updated(self):
        self.title(self.get_title_text())
        self.scene_controls.scene_updated()

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
