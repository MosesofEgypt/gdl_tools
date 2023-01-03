import os
import sys
import time
import panda3d.egg
import traceback
import tkinter.filedialog

from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, DirectionalLight, PointLight,\
     NodePath, WindowProperties, CollisionVisualizer

from . import free_camera
from .assets import scene_object
from .g3d_to_p3d.util import load_objects_dir_files
from .g3d_to_p3d.scene_actor import load_scene_actor_from_tags
from .g3d_to_p3d.scene_object import load_scene_object_from_tags
from .g3d_to_p3d.scene_world import load_scene_world_from_tags


# TODO: restructure this class to be a container for loading all
# objects/actors/particle systems/collision/animations/textures/etc
# in a scene and making them available for consumption by root scene
class Scene(ShowBase):
    _scene_objects = ()
    _curr_scene_object_name = ""
    _objects_dir = ""

    _camera_light_intensity = 4
    _ambient_light_intensity = 1
    _light_levels = 5

    _camera_controller = None
    _collision_visualizer = None
    _collision_visible = False
    _geometry_visible = True

    def __init__(self, **kwargs):
        self.objects_dir  = kwargs.pop("objects_dir", None)

        object_name  = kwargs.pop("object_name", None)
        object_names = kwargs.pop("object_names", ())
        if object_name:
            object_names = tuple(object_names) + (object_name, )

        super().__init__()

        # Put lighting on the main scene
        self._camera_light = DirectionalLight('dlight')
        self._ambient_light = AmbientLight('alight')
        self.adjust_ambient_light(0)
        self.adjust_ambient_light(0)

        dlnp = self.camera.attachNewNode(self._camera_light)
        alnp = render.attachNewNode(self._ambient_light)

        render.setLight(dlnp)
        render.setLight(alnp)

        self.accept("escape", sys.exit, [0])
        self.accept("arrow_left", self.switch_model, [False])
        self.accept("arrow_right", self.switch_model, [True])
        self.accept("1", self.toggle_geometry_view, [])
        self.accept("2", self.toggle_collision_view, [])
        self.accept("o", self.load_objects, [])
        self.accept("i", self.import_objects, [])
        self.accept("k", self.adjust_ambient_light, [1])
        self.accept("l", self.adjust_camera_light, [1])
        self.accept("-", self.adjust_fov, [False])
        self.accept("=", self.adjust_fov, [True])

        self._camera_controller = free_camera.FreeCamera(self, self.camera)
        self._camera_controller.start()

        #self._collision_visualizer = CollisionVisualizer("collision_debug")

        self._scene_objects = {}

        self.clear_scene()
        if self.objects_dir:
            self.load_scene(self.objects_dir, object_names=object_names)

    def adjust_fov(self, increase):
        lens = self.camNode.getLens(0)
        new_fov = min(180, max(5, lens.fov.getX() + (5 if increase else -5)))
        lens.fov = new_fov

    def toggle_collision_view(self):
        curr_scene_object = self._scene_objects.get(self._curr_scene_object_name)
        if not curr_scene_object:
            return

        for coll_group in curr_scene_object.node_collision.values():
            for coll in coll_group.values():
                coll_node_path = NodePath(coll.p3d_collision)
                if self._collision_visible:
                    coll_node_path.hide()
                else:
                    coll_node_path.show()

        self._collision_visible = not self._collision_visible

    def toggle_geometry_view(self):
        curr_scene_object = self._scene_objects.get(self._curr_scene_object_name)
        if not curr_scene_object:
            return

        for model_group in curr_scene_object.node_models.values():
            for model in model_group.values():
                model_node_path = NodePath(model.p3d_model)
                if self._geometry_visible:
                    model_node_path.hide()
                else:
                    model_node_path.show()

        self._geometry_visible = not self._geometry_visible

    def adjust_camera_light(self, amount):
        self._camera_light_intensity += amount
        self._camera_light_intensity %= self._light_levels + 1
        self._camera_light.setColor((
            self._camera_light_intensity / self._light_levels,
            self._camera_light_intensity / self._light_levels,
            self._camera_light_intensity / self._light_levels,
            1
            ))

    def adjust_ambient_light(self, amount):
        self._ambient_light_intensity += amount
        self._ambient_light_intensity %= self._light_levels + 1
        self._ambient_light.setColor((
            self._ambient_light_intensity / self._light_levels,
            self._ambient_light_intensity / self._light_levels,
            self._ambient_light_intensity / self._light_levels,
            1
            ))

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
        if not self._scene_objects:
            return

        model_names = tuple(sorted(self._scene_objects))
        curr_scene_object = self._scene_objects.get(self._curr_scene_object_name)

        if curr_scene_object:
            NodePath(curr_scene_object.p3d_node).hide()
            name_index = model_names.index(self._curr_scene_object_name)
            name_index += 1 if next_model else -1
        else:
            name_index = 0

        self._curr_scene_object_name = model_names[name_index % len(model_names)]
        NodePath(self._scene_objects[self._curr_scene_object_name].p3d_node).show()

        props = WindowProperties()
        props.setTitle("Preview: %s" % self._curr_scene_object_name)
        base.win.requestProperties(props)

    def clear_scene(self):
        for scene_object_name in tuple(self._scene_objects.keys()):
            scene_object = self._scene_objects[scene_object_name]
            NodePath(scene_object.p3d_node).removeNode()
            del self._scene_objects[scene_object_name]

        props = WindowProperties()
        props.setTitle("Preview: ")
        base.win.requestProperties(props)

    def load_scene(self, objects_dir, object_names=()):
        try:
            self._load_scene(objects_dir, object_names)
        except Exception:
            print(traceback.format_exc())

    def _load_scene(self, objects_dir, object_names=()):
        start = time.time()
        objects_data = load_objects_dir_files(objects_dir) if objects_dir else None
        print("Loading objects dir files took %s seconds" % (time.time() - start))

        is_ngc            = objects_data["is_ngc"]
        anim_tag          = objects_data["anim_tag"]
        objects_tag       = objects_data["objects_tag"]
        worlds_tag        = objects_data["worlds_tag"]
        textures_filepath = objects_data["textures_filepath"]

        if worlds_tag is None and anim_tag and not object_names:
            object_names = tuple(atree.name for atree in anim_tag.data.atrees)

        for name in object_names:
            old_scene_object = self._scene_objects.pop(name, None)
            if old_scene_object:
                render.node().removeChild(old_scene_object.p3d_node)

            scene_object = load_scene_actor_from_tags(
                name,
                anim_tag=anim_tag,
                objects_tag=objects_tag,
                textures_filepath=textures_filepath,
                is_ngc=is_ngc
                )
            self.add_scene_object(scene_object)
            NodePath(scene_object.p3d_node).hide()

        if worlds_tag:
            scene_world = load_scene_world_from_tags(
                worlds_tag=worlds_tag,
                objects_tag=objects_tag,
                anim_tag=anim_tag,
                textures_filepath=textures_filepath,
                is_ngc=is_ngc
                )
            self.add_scene_object(scene_world)
            self._ambient_light_intensity = self._light_levels
            self.adjust_ambient_light(0)
            self.setBackgroundColor(0,0,0)
        else:
            self.setBackgroundColor(0.5,0.5,0.5)

        self.switch_model()

    def add_scene_object(self, scene_obj):
        if not isinstance(scene_obj, scene_object.SceneObject):
            raise TypeError(f"scene object must be of type SceneObject, not {type(scene_obj)}")
        elif scene_obj.name in self._scene_objects:
            raise ValueError(f"SceneObject with name '{scene_obj.name}' already exists")

        self._scene_objects[scene_obj.name] = scene_obj

        render.node().addChild(scene_obj.p3d_node)

    @property
    def scene_objects(self):
        return dict(self._scene_objects)
