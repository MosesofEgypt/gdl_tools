

class ActorSkeletonNode:
    _name = "UNNAMED"

    _pos_xyz   = (0, 0, 0)
    _rot_ypr   = (0, 0, 0)
    _scale_xyz = (1.0, 1.0, 1.0)

    _parent = None
    _children = None

    def __init__(self, **kwargs):
        self._pos_xyz   = tuple(kwargs.pop("pos",   self._pos_xyz))
        self._rot_ypr   = tuple(kwargs.pop("rot",   self._rot_ypr))
        self._scale_xyz = tuple(kwargs.pop("scale", self._scale_xyz))
        self._name      = kwargs.pop("name", self._name)
        self._children = {}

        self.parent = kwargs.pop("parent", self._parent)

        assert len(self.pos) == 3
        assert len(self.rot) == 3
        assert len(self.scale) == 3
        if kwargs:
            raise ValueError("Unknown parameters detected: %s" % ', '.join(kwargs.keys()))

    @property
    def pos(self): return self._pos_xyz
    @property
    def rot(self): return self._rot_ypr
    @property
    def scale(self): return self._scale_xyz

    @property
    def name(self): return self._name.upper()
    @property
    def children(self): return dict(self._children)
    @property
    def parent(self): return self._parent
    @parent.setter
    def parent(self, parent):
        if parent is None:
            pass
        elif not isinstance(parent, ActorSkeletonNode):
            raise TypeError(f"Parent must either be None or an instance of ActorSkeletonNode, not {type(parent)}")
        elif self.name in parent.children:
            raise ValueError(f"Child already exists in this ActorSkeletonNode with the name '{child.name}'")

        root = parent
        while root is not None:
            if root is self:
                raise ValueError(
                    f"Recursive hierarchy detected. Cannot set {parent.name} as parent of {self.name}"
                    )
            root = parent.parent

        if parent is not None:
            parent._children[self.name] = self

        if self.parent:
            self.parent._children.pop(self.name, None)

        self._parent = parent


class ActorSkeleton(ActorSkeletonNode):
    pass
