import panda3d

from .scene_object import SceneObject


class SceneActor(SceneObject):
    _p3d_actor = None
    _actor_animations = ()
    
    def __init__(self, **kwargs):
        self._p3d_actor = kwargs.pop("p3d_actor", self._p3d_actor)
        self._actor_animations = {}
        if self._p3d_actor is None:
            self._p3d_actor = panda3d.physics.ActorNode(self.name)

        super().__init__(**kwargs)

    def add_actor_animation(self, animation):
        pass

    @property
    def p3d_actor(self): return self._p3d_actor
