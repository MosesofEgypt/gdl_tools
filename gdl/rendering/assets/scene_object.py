import panda3d

from . import animation


class SceneObject:
    _name = ""

    _p3d_node = None
    _shape_morph_animations = ()
    _texture_swap_animations = ()

    _node_models = ()
    
    def __init__(self, **kwargs):
        self._name = kwargs.pop("name", self._name)
        self._p3d_node = kwargs.pop("p3d_node", self._p3d_node)

        self._shape_morph_animations = {}
        self._texture_swap_animations = {}
        self._node_models = {}

    @property
    def name(self): return self._name.upper()
    @property
    def p3d_node(self): return self._p3d_node
    @property
    def node_models(self): return {k: dict(v) for k, v in self._node_models.items()}
    @property
    def shape_morph_animations(self): return dict(self._shape_morph_animations)
    @property
    def texture_swap_animations(self): return dict(self._texture_swap_animations)

    def attach_model(self, model, node_name):
        node_name = node_name.upper().strip()
        parent_node_path = panda3d.core.NodePath(self.p3d_node).find("**/" + node_name)

        if parent_node_path.isEmpty() and parent_node_path.parent.isEmpty():
            # TODO: raise error since node doesnt exist
            return

        node_model_collection = self._node_models.setdefault(node_name, dict())
        if model.name in node_model_collection:
            return

        node_model_collection[model.name] = model
        parent_node_path.node().add_child(model.p3d_model)

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
