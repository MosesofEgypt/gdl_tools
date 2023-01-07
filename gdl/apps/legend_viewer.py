import tkinter.filedialog

from tkinter import TclError
from ..rendering.scene import Scene
from panda3d.core import WindowProperties

__version__ = (0, 0, 1)

class LegendViewer(Scene):

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

        self.accept("arrow_left", self.switch_model, [False])
        self.accept("arrow_right", self.switch_model, [True])

        self.accept("f1", self.toggle_geometry_view, [])
        self.accept("f2", self.toggle_collision_view, [])
        self.accept("f3", self.toggleWireframe, [])
        self.accept("f4", self.toggleShowVertices, [])

        self.accept("f5", self.toggleTexture, [])
        self.accept("f6", self.toggleParticles, [])

        self.accept("o", self.load_objects, [])
        self.accept("k", self.adjust_ambient_light, [1])
        self.accept("l", self.adjust_camera_light, [1])
        self.accept("-", self.adjust_fov, [-5])
        self.accept("=", self.adjust_fov, [5])
        self.switch_model()

    def resize(self, event):
        self.tk_root.update()
        
        props = WindowProperties()
        props.setOrigin(0, 0)
        try:
            props.setSize(self.tk_root.winfo_width(), self.tk_root.winfo_height())
        except TclError as e:
            return
        
        self.win.requestProperties(props)

    def import_objects(self):
        objects_dir = tkinter.filedialog.askdirectory(
            initialdir=self.objects_dir,
            title="Select the folder containing OBJECTS.PS2/NGC to import"
            )
        if objects_dir:
            self.objects_dir = objects_dir
            self.load_scene(self.objects_dir)

    def load_objects(self):
        objects_dir = tkinter.filedialog.askdirectory(
            initialdir=self.objects_dir,
            title="Select the folder containing OBJECTS.PS2/NGC to load"
            )
        if objects_dir:
            self.clear_scene()
            self.objects_dir = objects_dir
            self.load_scene(self.objects_dir)

    def switch_model(self, next_model=True):
        super().switch_model(next_model)
        self.tk_root.title("Legend Viewer v%s.%s.%s: %s" % (*__version__, self._curr_scene_object_name))
