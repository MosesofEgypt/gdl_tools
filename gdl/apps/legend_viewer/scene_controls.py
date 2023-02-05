import tkinter as tk
import tkinter.filedialog
import sys

from .hotkey_menu_binder import HotkeyMenuBinder

class SceneControlsWindow(tk.Toplevel, HotkeyMenuBinder):
    scene = None
    _hotkey_menu_binds = [
        ]

    def __init__(self, parent, *args, **kwargs):
        self.scene = kwargs.pop("scene")
        super().__init__(parent, *args, **kwargs)

        self.title("Scene controls")
        self.protocol("WM_DELETE_WINDOW", lambda: self.withdraw())
        self.bind_hotkeys(self.scene)
        self.generate_menu()
        self.transient(self.master)

    def toggle_visible(self):
        self.geometry('350x200+%d+%d' % (self.master.winfo_x(),
                                         self.master.winfo_y()))
        if self.winfo_viewable():
            self.withdraw()
        else:
            self.deiconify()

    def switch_world(self, world_name):
        self.scene.switch_world(world_name)
        self.master.update_title()

    def switch_actor(self, set_name, actor_name):
        self.scene.switch_actor(set_name, actor_name)
        self.master.update_title()

    def switch_object(self, set_name, object_name):
        self.scene.switch_object(set_name, object_name)
        self.master.update_title()

    def switch_scene_type(self, scene_type):
        self.scene.switch_scene_type(scene_type)
        self.master.update_title()
