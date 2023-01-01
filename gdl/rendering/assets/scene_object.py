import panda3d

from . import animation


class SceneObject:
    _name = ""

    _p3d_node = None
    _shape_morph_animations = ()
    _texture_swap_animations = ()

    _node_models = ()
    _node_paths = ()
    
    def __init__(self, **kwargs):
        self._name = kwargs.pop("name", self._name)
        self._p3d_node = kwargs.pop("p3d_node", self._p3d_node)
        if self._p3d_node is None:
            self._p3d_node = panda3d.core.PandaNode(self.name)

        self._shape_morph_animations = {}
        self._texture_swap_animations = {}
        self._node_models = {}
        self.cache_node_paths()

    def cache_node_paths(self):
        self._node_paths = {}
        # cache the nodepaths for quicker scene building
        self._cache_node_paths(self._p3d_node)

    def _cache_node_paths(self, p3d_node):
        node_path = panda3d.core.NodePath(p3d_node)
        self._node_paths[p3d_node.name] = node_path

        for child in node_path.getChildren():
            self._cache_node_paths(child)

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

    def attach_model(self, model, node_name=""):
        node_name = node_name.upper().strip()
        parent_node_path = self._node_paths.get(node_name)
        if parent_node_path is None:
            parent_node_path = panda3d.core.NodePath(self.p3d_node)
            if node_name and node_name != self.p3d_node.name.lower().strip():
                parent_node_path = parent_node_path.find("**/" + node_name)

            if parent_node_path is not None:
                self._cache_node_paths(parent_node_path)
            else:
                # TODO: raise error since node doesnt exist
                return

        node_model_collection = self._node_models.setdefault(node_name, dict())
        if model.name in node_model_collection:
            return

        node_model_collection[model.name] = model
        parent_node_path.node().add_child(model.p3d_model)

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
