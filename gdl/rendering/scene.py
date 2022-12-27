import sys

from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, DirectionalLight, PointLight
from panda3d.core import NodePath

from .assets import scene_object
from .g3d_to_p3d.util import load_objects_dir_files
from .g3d_to_p3d.scene_actor import load_scene_actor_from_tags
from .g3d_to_p3d.scene_object import load_scene_object_from_tags

class Scene(ShowBase):
    _scene_objects = ()

    def __init__(self, **kwargs):
        objects_dir = kwargs.pop("objects_dir")
        object_name = kwargs.pop("object_name")

        super().__init__()

        # Put lighting on the main scene
        dlight = DirectionalLight('dlight')
        alight = AmbientLight('alight')
        dlight.setColor((0.75, 0.75, 0.75, 1))
        alight.setColor((0.25, 0.25, 0.25, 1))

        dlnp = render.attachNewNode(dlight)
        alnp = render.attachNewNode(alight)
        dlnp.setHpr(0, -60, 0)

        render.setLight(dlnp)
        render.setLight(alnp)

        self.accept("escape", sys.exit, [0])
        self.accept("w", self.zoomIn)
        self.accept("s", self.zoomOut)
        self.accept("a", self.moveLeft)
        self.accept("d", self.moveRight)

        self._scene_objects = {}

        objects_data = load_objects_dir_files(objects_dir) if objects_dir else None
        objects_data.pop("worlds_tag")

        #scene_object = load_scene_actor_from_tags(objects_dir, **objects_data)
        scene_object = load_scene_object_from_tags(objects_dir, **objects_data)
        self.add_scene_object(scene_object)

        for scene_object in self.scene_objects.values():
            scene_object.p3d_node.hprInterval(3, (360, 360, 360)).loop()

    def zoomIn(self):
        camera.setY(camera.getY() * 0.9)

    def zoomOut(self):
        camera.setY(camera.getY() * 1.2)

    def moveLeft(self):
        camera.setX(camera.getX() + 1)

    def moveRight(self):
        camera.setX(camera.getX() - 1)

    def add_scene_object(self, scene_obj):
        if not isinstance(scene_obj, scene_object.SceneObject):
            raise TypeError(f"scene object must be of type SceneObject, not {type(scene_obj)}")
        elif scene_obj.name in self._scene_objects:
            raise ValueError(f"SceneObject with name '{scene_obj.name}' already exists")

        self._scene_objects[scene_obj.name] = scene_obj

        scene_obj.p3d_node.reparentTo(self._scene_renderer)

    @property
    def scene_objects(self):
        return dict(self._scene_objects)
