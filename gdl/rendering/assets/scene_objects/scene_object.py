import panda3d

from .. import animation


class SceneObject:
    _name = ""

    _p3d_node = None
    _texture_animations = ()

    _node_models = ()
    _node_collision = ()
    _node_paths = ()
    
    def __init__(self, **kwargs):
        self._name = kwargs.pop("name", self._name)
        self._p3d_node = kwargs.pop("p3d_node", self._p3d_node)
        if self._p3d_node is None:
            self._p3d_node = panda3d.core.PandaNode(self.name)

        self._texture_animations = {}
        self._node_models = {}
        self._node_collision = {}
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
    def has_animation(self):
        return bool(self._texture_animations)

    @property
    def name(self): return self._name.upper()
    @property
    def p3d_node(self): return self._p3d_node
    @property
    def node_paths(self): return dict(self._node_paths)
    @property
    def node_models(self): return {k: dict(v) for k, v in self._node_models.items()}
    @property
    def node_collision(self): return {k: dict(v) for k, v in self._node_collision.items()}
    @property
    def texture_animations(self): return dict(self._texture_animations)

    def _get_node_path(self, node_name):
        parent_node_path = self._node_paths.get(node_name)
        if parent_node_path is None:
            parent_node_path = panda3d.core.NodePath(self.p3d_node)
            if node_name and node_name != self.p3d_node.name.lower().strip():
                parent_node_path = parent_node_path.find("**/" + node_name)

            if parent_node_path is not None:
                self._cache_node_paths(parent_node_path)
            else:
                # TODO: raise error since node doesnt exist
                pass

        return parent_node_path

    def attach_model(self, model, node_name=""):
        node_name = node_name.upper().strip()
        node_collection = self._node_models.setdefault(node_name, dict())
        parent_node_path = self._get_node_path(node_name)

        if model.name in node_collection or parent_node_path is None:
            # TODO: raise error
            return

        node_collection[model.name] = model
        parent_node_path.node().add_child(model.p3d_model)

    def attach_collision(self, collision, node_name=""):
        node_name = node_name.upper().strip()
        node_collection = self._node_collision.setdefault(node_name, dict())
        parent_node_path = self._get_node_path(node_name)

        if collision.name in node_collection or parent_node_path is None:
            # TODO: raise error
            return

        node_collection[collision.name] = collision
        parent_node_path.node().add_child(collision.p3d_collision)

    def add_texture_animation(self, animation):
        if not isinstance(animation, scene_animation.TextureAnimation):
            raise TypeError(f"animation must be of type TextureAnimation, {type(animation)}")
        elif animation.name in self._texture_animations:
            raise ValueError(f"animation with name '{animation.name}' already exists")

        self._texture_animations[animaton.name] = animation

    def set_collision_visible(self, visible=None):
        for group in self.node_collision.values():
            for coll in group.values():
                node_path = panda3d.core.NodePath(coll.p3d_collision)
                visible = node_path.isHidden() if visible is None else visible

                if visible:
                    node_path.show()
                else:
                    node_path.hide()
        return visible

    def set_geometry_visible(self, visible=None):
        for group in self.node_models.values():
            for model in group.values():
                node_path = panda3d.core.NodePath(model.p3d_model)
                visible = node_path.isHidden() if visible is None else visible

                if visible:
                    node_path.show()
                else:
                    node_path.hide()
        return visible
