import tkinter as tk
import tkinter.filedialog
import sys

from .hotkey_menu_binder import HotkeyMenuBinder

class AnimationControlsWindow(tk.Toplevel, HotkeyMenuBinder):
    scene = None
    _hotkey_menu_binds = (
        dict(key="space",     name="Play/pause animations", func="self.scene.toggle_animations"),
        dict(key="0",         name="Reset animations",      func="self.scene.reset_animation_timer"),
        dict(key="backspace", name="Reverse animations",    func="self.scene.reverse_animation_timer"),
        dict(key="-",         name="Previous frame",        func="self.scene.decrement_animation_frame"),
        dict(key="=",         name="Next frame",            func="self.scene.increment_animation_frame"),
        )

    def __init__(self, parent, *args, **kwargs):
        self.scene = kwargs.pop("scene")
        super().__init__(parent, *args, **kwargs)

        self.title("Animation controls")
        self.protocol("WM_DELETE_WINDOW", lambda: self.withdraw())
        self.bind_hotkeys(self.scene)
        self.generate_menu()
        self.transient(self.master)

        # things to implement:
        #   segmentation by animation location:
        #       separate section for world animations
        #       separate section for actor animations
        #       separate section for item animations
        #   ability to play default animations everywhere applicable
        #   ability to clear animations being played
        #   ability to queue animation to play
        #   ability to specify loop/reverse/framerate override while queueing
        #   ability to specify end state(loop/rewind to start/stop on last frame)
        #   button to process queue
        #   animation handler object for each resource set
        #   main loop that will start animation playing in handlers, and
        #       will remove them when user selects a different animation
        self.update()
        width  = max((
            self.menus[""].winfo_reqwidth(),  # width of the root menu
            300
            )) + 4  # account for padding
        height = sum((
            0,
            )) + 4*0 # account for padding
        self.geometry("%dx%d" % (width, height))
        self.resizable(0, 0)

    def toggle_visible(self):
        self.geometry('%s+%d+%d' % (
            self.geometry().split("+")[0],
            self.master.winfo_x(),
            self.master.winfo_y()
            ))
        if self.winfo_viewable():
            self.withdraw()
        else:
            self.deiconify()
