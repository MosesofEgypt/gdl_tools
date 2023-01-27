import panda3d

from .scene_object import SceneObject
from .. import animation


class SceneActor(SceneObject):
    _p3d_actor = None
    _actor_animations = ()
    _texture_animations = ()
    _shape_morph_animations = ()
    
    def __init__(self, **kwargs):
        self._p3d_actor = kwargs.pop("p3d_actor", self._p3d_actor)
        self._actor_animations = {}
        self._texture_animations = {}
        self._shape_morph_animations = {}
        if self._p3d_actor is None:
            self._p3d_actor = panda3d.physics.ActorNode(self.name)

        super().__init__(**kwargs)

    @property
    def p3d_actor(self): return self._p3d_actor
    @property
    def actor_animations(self): return dict(self._actor_animations)
    @property
    def texture_animations(self): return dict(self._texture_animations)
    @property
    def shape_morph_animations(self): return dict(self._shape_morph_animations)

    def add_actor_animation(self, animation):
        pass

    def add_texture_animation(self, animation):
        if not isinstance(animation, scene_animation.TextureAnimation):
            raise TypeError(f"animation must be of type TextureAnimation, {type(animation)}")
        elif animation.name in self._texture_animations:
            raise ValueError(f"animation with name '{animation.name}' already exists")

        self._texture_animations[animaton.name] = animation

    def add_shape_morph_animation(self, animation):
        if not isinstance(animation, scene_animation.ShapeMorphAnimation):
            raise TypeError(f"animation must be of type ShapeMorphAnimation, not {type(animation)}")
        elif animation.name in self._shape_morph_animations:
            raise ValueError(f"animation with name '{animation.name}' already exists")

        self._shape_morph_animations[animaton.name] = animation
