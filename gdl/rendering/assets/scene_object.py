from . import animation


class SceneObject:
    _name = ""

    _p3d_node = None
    _shape_morph_animations = ()
    _texture_swap_animations = ()
    
    def __init__(self, **kwargs):
        self._name = kwargs.pop("name", self._name)
        self._p3d_node = kwargs.pop("p3d_node", self._p3d_node)

        self._shape_morph_animations = {}
        self._texture_swap_animations = {}

    @property
    def name(self): return self._name.upper()
    @property
    def p3d_node(self): return self._p3d_node
    @property
    def shape_morph_animations(self): return dict(self._shape_morph_animations)
    @property
    def texture_swap_animations(self): return dict(self._texture_swap_animations)

    def create_instance(self):
        pass

    def add_shape_morph_animation(self, animation):
        if not isinstance(animation, scene_animation.ShapeMorphAnimation):
            raise TypeError(f"animation must be of type ShapeMorphAnimation, not {type(animation)}")
        elif animation.name in self._shape_morph_animations:
            raise ValueError(f"animation with name '{animation.name}' already exists")

        self._shape_morph_animations[animaton.name] = animation

    def add_texture_swap_animation(self, animation):
        if not isinstance(animation, scene_animation.TextureSwapAnimation):
            raise TypeError(f"animation must be of type TextureSwapAnimation, {type(animation)}")
        elif animation.name in self._texture_swap_animations:
            raise ValueError(f"animation with name '{animation.name}' already exists")

        self._texture_swap_animations[animaton.name] = animation

    def play_animation(self, instance_id, anim_name):
        pass

    def stop_animation(self, instance_id, anim_name):
        pass

    def set_animation_time(self, instance_id, anim_name, frame_time):
        pass
