import tkinter as tk
import tkinter.filedialog
import sys

from binilla.widgets.scroll_menu import ScrollMenu
from .hotkey_menu_binder import HotkeyMenuBinder

class SceneControlsWindow(tk.Toplevel, HotkeyMenuBinder):
    scene = None
    _hotkey_menu_binds = (
        dict(key="control-l",   name="Load world",   func="self.master.select_and_load_world"),
        dict(key="control-o",   name="Load objects", func="self.master.select_and_load_objects"),
        )

    def __init__(self, parent, *args, **kwargs):
        self.scene = kwargs.pop("scene")
        super().__init__(parent, *args, **kwargs)

        self.title("Scene controls")
        self.protocol("WM_DELETE_WINDOW", lambda: self.withdraw())
        self.bind_hotkeys(self.scene)
        self.generate_menu()
        self.transient(self.master)

        self.fov_var = tk.DoubleVar(self, self.scene.get_fov())
        self.player_count_var = tk.IntVar(self, self.scene.get_player_count())

        self.resource_frame = tk.LabelFrame(self, text="Resource selection")
        self.camera_frame   = tk.LabelFrame(self, text="Camera")
        self.world_frame    = tk.LabelFrame(self, text="World")
        self.scene_type_menu = ScrollMenu(
            self.resource_frame, menu_width=8, callback=self.select_scene_type,
            options=("World", "Actor", "Object"), sel_index=self.scene.scene_type
            )
        self.resource_set_menu = ScrollMenu(
            self.resource_frame, menu_width=16, callback=self.select_resource_set,
            option_getter=self.get_resource_sets, options_volatile=True
            )
        self.resource_name_menu = ScrollMenu(
            self.resource_frame, menu_width=16, callback=self.select_resource_name,
            option_getter=self.get_resource_names, options_volatile=True
            )
        self.scene_type_label = tk.Label(self.resource_frame, text="Type")
        self.scene_set_label  = tk.Label(self.resource_frame, text="Group")
        self.scene_name_label = tk.Label(self.resource_frame, text="Asset")

        self.fov_slider = tk.Scale(
            self.camera_frame, from_=0.1, to=180, orient=tk.HORIZONTAL,
            variable=self.fov_var, label="Field-of-view"
            )
        self.reset_camera_position_button = tk.Button(
            self.camera_frame, text="Reset position", width=15,
            command=self.reset_camera_position
            )
        self.reset_camera_rotation_button = tk.Button(
            self.camera_frame, text="Reset rotation", width=15,
            command=self.reset_camera_rotation
            )

        self.player_count_slider = tk.Scale(
            self.world_frame, from_=0, to=4, orient=tk.HORIZONTAL,
            variable=self.player_count_var, label="Player count"
            )

        for i in range(1,7):
            self.resource_frame.columnconfigure(i, weight=1)
        for i in range(2):
            self.resource_frame.rowconfigure(i, weight=1)

        self.camera_frame.columnconfigure(2, weight=1)
        for i in range(2):
            self.camera_frame.rowconfigure(i, weight=1)

        self.world_frame.columnconfigure(1, weight=1)

        self.resource_frame.grid(sticky='nwe',  column=0, row=0, padx=2, pady=2)
        self.camera_frame.grid(sticky='nwe',    column=0, row=1, padx=2, pady=2)
        self.world_frame.grid(sticky='nwe',     column=0, row=2, padx=2, pady=2)
        self.scene_type_label.grid(sticky='nw', column=0, row=0, columnspan=1, padx=5)
        self.scene_set_label.grid(sticky='nw',  column=1, row=0, columnspan=3, padx=5)
        self.scene_name_label.grid(sticky='nw', column=4, row=0, columnspan=3, padx=5)
        self.scene_type_menu.grid(sticky='nwe',    column=0, row=1, columnspan=1, padx=5, pady=5)
        self.resource_set_menu.grid(sticky='nwe',  column=1, row=1, columnspan=3, padx=5, pady=5)
        self.resource_name_menu.grid(sticky='nwe', column=4, row=1, columnspan=3, padx=5, pady=5)

        self.fov_slider.grid(sticky='nwe', column=0, row=0, columnspan=3, padx=5)
        self.reset_camera_position_button.grid(sticky='nw', column=0, columnspan=1, row=1, padx=5, pady=5)
        self.reset_camera_rotation_button.grid(sticky='nw', column=1, columnspan=1, row=1, padx=5, pady=5)

        self.player_count_slider.grid(sticky='nw', column=0, row=0, columnspan=3, padx=5)

        self.fov_var.trace("w", self.update_camera_fov)
        self.player_count_var.trace("w", self.update_player_count)

        self.update()
        width  = max((
            self.menus[""].winfo_reqwidth(),  # width of the root menu
            self.resource_frame.winfo_reqwidth(),
            self.camera_frame.winfo_reqwidth(),
            self.world_frame.winfo_reqwidth()
            )) + 4  # account for padding
        height = sum((
            self.resource_frame.winfo_reqheight(),
            self.camera_frame.winfo_reqheight(),
            self.world_frame.winfo_reqheight()
            )) + 4*3 # account for padding
        self.geometry("%dx%d" % (width, height))
        self.resizable(0, 0)

    def reset_camera_rotation(self):
        self.scene.camera.setH(0)
        self.scene.camera.setP(0)
        self.scene.camera.setR(0)

    def reset_camera_position(self):
        self.scene.camera.setX(0)
        self.scene.camera.setY(0)
        self.scene.camera.setZ(0)

    def update_player_count(self, *a):
        self.scene.set_player_count(self.player_count_var.get())

    def update_camera_fov(self, *a):
        self.scene.set_fov(self.fov_var.get())

    def scene_updated(self):
        '''
        Handles updating widgets when the scene has been
        updated outside the control of this window
        '''
        self.scene_type_menu.sel_index = self.scene.scene_type
        resource_sets  = self.get_resource_sets()
        resource_names = self.get_resource_names()

        self.resource_set_menu.set_options(resource_sets)
        self.resource_name_menu.set_options(resource_names)

        set_index = name_index = -1
        resource_sets_inv  = {v: k for k, v in resource_sets.items()}
        resource_names_inv = {v: k for k, v in resource_names.items()}
        if self.scene.scene_type == self.scene.SCENE_TYPE_WORLD:
            set_index = resource_sets_inv.get(self.scene.curr_world_name, set_index)
        elif self.scene.scene_type == self.scene.SCENE_TYPE_ACTOR:
            set_index = resource_sets_inv.get(self.scene.curr_actor_set_name, set_index)
        elif self.scene.scene_type == self.scene.SCENE_TYPE_OBJECT:
            set_index = resource_sets_inv.get(self.scene.curr_object_set_name, set_index)

        if self.scene.scene_type == self.scene.SCENE_TYPE_ACTOR:
            name_index = resource_names_inv.get(self.scene.curr_actor_name, name_index)
        elif self.scene.scene_type == self.scene.SCENE_TYPE_OBJECT:
            name_index = resource_names_inv.get(self.scene.curr_object_name, name_index)

        self.resource_set_menu.sel_index  = set_index
        self.resource_name_menu.sel_index = name_index

        self.player_count_var.set(self.scene.get_player_count())

    def get_resource_sets(self, opt_index=None):
        sets = tuple(sorted(
            self.scene.scene_worlds  if self.scene.scene_type == self.scene.SCENE_TYPE_WORLD else
            self.scene.scene_actors  if self.scene.scene_type == self.scene.SCENE_TYPE_ACTOR else 
            self.scene.scene_objects if self.scene.scene_type == self.scene.SCENE_TYPE_OBJECT else 
            ()
        ))
        return (
            {i: n for i, n in enumerate(sets)} if opt_index is None else
            sets[opt_index] if opt_index in range(len(sets)) else
            ""
            )

    def get_resource_names(self, opt_index=None):
        names = tuple(sorted(
            self.scene.scene_actors.get(self.scene.curr_actor_set_name, ())   if self.scene.scene_type == self.scene.SCENE_TYPE_ACTOR else 
            self.scene.scene_objects.get(self.scene.curr_object_set_name, ()) if self.scene.scene_type == self.scene.SCENE_TYPE_OBJECT else
            ()
        ))
        return (
            {i: n for i, n in enumerate(names)} if opt_index is None else
            names[opt_index] if opt_index in range(len(names)) else
            ""
            )

    def select_scene_type(self, scene_type):
        if scene_type not in range(3):
            return

        self.scene.switch_scene_type(scene_type)
        resource_sets = (
            self.scene.scene_worlds  if scene_type == self.scene.SCENE_TYPE_WORLD else
            self.scene.scene_actors  if scene_type == self.scene.SCENE_TYPE_ACTOR else
            self.scene.scene_objects if scene_type == self.scene.SCENE_TYPE_OBJECT else
            {}
            )

        self.resource_set_menu.set_options(tuple(sorted(resource_sets)))

    def select_resource_set(self, set_index):
        set_name = self.resource_set_menu.get_option(set_index)
        resources = {}
        if self.scene.scene_type == self.scene.SCENE_TYPE_WORLD:
            self.scene.switch_world(set_name)
        elif self.scene.scene_type == self.scene.SCENE_TYPE_ACTOR:
            self.scene.switch_actor(set_name, self.scene.curr_actor_name)
            resources = self.scene.scene_actors.get(self.scene.curr_actor_set_name, {})
        elif self.scene.scene_type == self.scene.SCENE_TYPE_OBJECT:
            self.scene.switch_object(set_name, self.scene.curr_object_name)
            resources = self.scene.scene_objects.get(self.scene.curr_object_set_name, {})

        self.resource_name_menu.set_options(tuple(sorted(resources)))

    def select_resource_name(self, set_index):
        name = self.resource_name_menu.get_option(set_index)
        if self.scene.scene_type == self.scene.SCENE_TYPE_ACTOR:
            self.scene.switch_actor(self.scene.curr_actor_set_name, name)
        elif self.scene.scene_type == self.scene.SCENE_TYPE_OBJECT:
            self.scene.switch_object(self.scene.curr_object_set_name, name)
        else:
            return

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
