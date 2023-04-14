import panda3d

from .scene_object import SceneObject
from ..animation import TextureAnimation, ShapeMorphAnimation, SkeletalAnimation


class SceneActor(SceneObject):
    _actor_animations = ()
    _texture_animations = ()
    _shape_morph_animations = ()

    # TODO: create method to take all attached models and
    #       make skin-rigged singular mesh out of them.
    
    def __init__(self, **kwargs):
        self._actor_animations = {}
        self._texture_animations = {}
        self._shape_morph_animations = {}

        self._name = kwargs.pop("name", self._name)
        p3d_node   = kwargs.pop("p3d_node")
        if p3d_node is None:
            p3d_node = panda3d.physics.ActorNode(self.name)

        if not isinstance(p3d_node, panda3d.physics.ActorNode):
            raise TypeError(f"p3d_node must be of type panda3d.physics.ActorNode, {type(p3d_node)}")

        kwargs["p3d_node"] = p3d_node

        super().__init__(**kwargs)

    @property
    def actor_animations(self): return dict(self._actor_animations)
    @property
    def texture_animations(self): return dict(self._texture_animations)
    @property
    def shape_morph_animations(self): return dict(self._shape_morph_animations)

    def add_actor_animation(self, anim):
        pass

    def add_texture_animation(self, anim):
        if not isinstance(anim, TextureAnimation):
            raise TypeError(f"animation must be of type TextureAnimation, {type(anim)}")

        seq_tex_anims = self._texture_animations.setdefault(anim.name, {})
        if anim.tex_name in seq_tex_anims:
            raise ValueError(f"animation with name '{anim.name}' already exists for texture {anim.tex_name}")

        seq_tex_anims[anim.tex_name] = anim

    def add_shape_morph_animation(self, anim):
        if not isinstance(anim, ShapeMorphAnimation):
            raise TypeError(f"animation must be of type ShapeMorphAnimation, not {type(anim)}")
        elif anim.name in self._shape_morph_animations:
            raise ValueError(f"animation with name '{anim.name}' already exists")

        self._shape_morph_animations[anim.name] = anim
