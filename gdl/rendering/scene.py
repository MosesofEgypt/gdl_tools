import os
import sys
import panda3d.egg

from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, DirectionalLight, PointLight
from panda3d.core import NodePath

from .assets import scene_object
from .g3d_to_p3d.util import load_objects_dir_files
from .g3d_to_p3d.scene_actor import load_scene_actor_from_tags
from .g3d_to_p3d.scene_object import load_scene_object_from_tags
from .g3d_to_p3d.scene_world import load_scene_world_from_tags

class Scene(ShowBase):
    _scene_objects = ()

    def __init__(self, **kwargs):
        objects_dir  = kwargs.pop("objects_dir", None)
        object_name  = kwargs.pop("object_name", None)
        object_names = kwargs.pop("object_names", ())
        if object_name:
            object_names = tuple(object_names) + (object_name, )

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

        self._scene_objects = {}

        if objects_dir:
            self.load_scene(objects_dir, object_names=object_names)

    def load_scene(self, objects_dir, object_names=()):
        objects_data = load_objects_dir_files(objects_dir) if objects_dir else None

        anim_tag          = objects_data["anim_tag"]
        objects_tag       = objects_data["objects_tag"]
        worlds_tag        = objects_data["worlds_tag"]
        textures_filepath = objects_data["textures_filepath"]

        if worlds_tag is None and anim_tag and not object_names:
            object_names = tuple(atree.name for atree in anim_tag.data.atrees)

        for name in object_names:
            scene_object = load_scene_actor_from_tags(
                name,
                anim_tag=anim_tag,
                objects_tag=objects_tag,
                textures_filepath=textures_filepath
                )
            self.add_scene_object(scene_object)

        if worlds_tag:
            scene_world = load_scene_world_from_tags(
                worlds_tag=worlds_tag,
                objects_tag=objects_tag,
                anim_tag=anim_tag,
                textures_filepath=textures_filepath
                )
            self.add_scene_object(scene_world)
            

        #for scene_object in self.scene_objects.values():
        #    NodePath(scene_object.p3d_node).hprInterval(10, (360, 0, 0)).loop()

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
