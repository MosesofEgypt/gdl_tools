from . import scene_animation


class SceneObject:
    _actor_animations = ()
    _shape_morph_animations = ()
    _texture_swap_animations = ()
    
    def __init__(self, **kwargs):
        self._actor_animations = {}
        self._shape_morph_animations = {}
        self._texture_swap_animations = {}

    def create_instance(self):
        pass

    def add_animation(self, animation):
        animations = None
        if isinstance(animation, scene_animation.ActorAnimation):
            animations = self._actor_animations
        elif isinstance(animation, scene_animation.ShapeMorphAnimation):
            animations = self._shape_morph_animations
        elif isinstance(animation, scene_animation.TextureSwapAnimation):
            animations = self._texture_swap_animations
        else:
            raise TypeError(f"Unknown animation type {type(animation)}")

        if animation.name in animations:
            raise ValueError(f"Animation with name '{animation.name}' already exists")

        animations[animaton.name] = animation

    def play_animation(self, instance_id, anim_name):
        pass

    def stop_animation(self, instance_id, anim_name):
        pass

    def set_animation_time(self, instance_id, anim_name, frame_time):
        pass
