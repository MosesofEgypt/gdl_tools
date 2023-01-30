import panda3d


class SceneObject:
    _name = ""

    _dont_cache_root = False
    _p3d_node = None

    _node_models = ()
    _node_collision = ()
    _node_paths = ()
    
    def __init__(self, **kwargs):
        self._name = kwargs.pop("name", self._name)
        self._p3d_node = kwargs.pop("p3d_node", self._p3d_node)
        if self._p3d_node is None:
            self._p3d_node = panda3d.core.PandaNode(self.name)

        self._node_models = {}
        self._node_collision = {}
        self.cache_node_paths()

    def cache_node_paths(self):
        # cache the nodepaths for quicker scene building
        self._node_paths = self.get_node_paths()

    def _get_node_paths(self, node_path, collection, types):
        for child in node_path.getChildren():
            if isinstance(child.node(), types):
                collection.setdefault(child.name, child)

            self._get_node_paths(child, collection, types)

    def get_node_paths(self, types=None):
        collection = {}
        if types is None:
            types = panda3d.core.PandaNode
        if isinstance(types, type):
            types = (types, )

        # NOTE: this is a bit of a hack. we don't want to cache the
        #       root node on actors, as it may be the same name as
        #       one of the nodes within it. Since we're doing a bit
        #       of a weird thing with caching each node by its name
        #       instead of its full path. This can lead to instances
        #       where models become attached to the root node instead
        #       of a child node inside it. To prevent this, we only
        #       cache the root node if this is a simple object, such
        #       as SceneObject or SceneWorldObject. We can also skip
        #       caching it on SceneWorld since nothing gets attached
        #       to the root anyway.
        root_nodepath = panda3d.core.NodePath(self._p3d_node)
        if not self._dont_cache_root and isinstance(self._p3d_node, types):
            collection.setdefault(root_nodepath.name, root_nodepath)

        self._get_node_paths(root_nodepath, collection, types)
        return collection

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

    def get_node_path(self, node_name):
        parent_node_path = self._node_paths.get(node_name)
        if parent_node_path is None:
            parent_node_path = panda3d.core.NodePath(self.p3d_node)
            if node_name and node_name != self.p3d_node.name.lower().strip():
                parent_node_path = parent_node_path.find("**/" + node_name)

            if not parent_node_path.is_empty():
                self._get_node_paths(
                    parent_node_path, self._node_paths,
                    (panda3d.core.PandaNode, )
                    )
            else:
                raise KeyError(f"Cannot locate node '{node_name}'")

        return parent_node_path

    def attach_model(self, model, node_name=""):
        node_name = node_name.upper().strip()
        node_collection = self._node_models.setdefault(node_name, dict())
        parent_node_path = self.get_node_path(node_name)

        if model.name in node_collection or parent_node_path is None:
            # TODO: raise error
            return

        node_collection[model.name] = model
        parent_node_path.node().add_child(model.p3d_model)

    def attach_collision(self, collision, node_name=""):
        node_name = node_name.upper().strip()
        node_collection = self._node_collision.setdefault(node_name, dict())
        parent_node_path = self.get_node_path(node_name)

        if collision.name in node_collection or parent_node_path is None:
            # TODO: raise error
            return

        node_collection[collision.name] = collision
        parent_node_path.node().add_child(collision.p3d_collision)

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
