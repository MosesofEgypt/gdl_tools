from .scene_object import SceneObject


class SceneActor(SceneObject):

    def add_actor_animation(self, animation):
        pass

    @property
    def name(self): return self._name.upper()

    @property
    def p3d_actor(self): return self._p3d_actor
