import tkinter as tk
import tkinter.filedialog
import sys

from .hotkey_menu_binder import HotkeyMenuBinder

class AnimationControlsWindow(tk.Toplevel, HotkeyMenuBinder):
    scene = None
    _hotkey_menu_binds = [
        ]

    def __init__(self, parent, *args, **kwargs):
        self.scene = kwargs.pop("scene")
        super().__init__(parent, *args, **kwargs)

        self.title("Animation controls")
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
