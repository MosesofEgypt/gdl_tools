import panda3d

from . import shader


class CollisionMesh:
    _name = ""
    _p3d_collision = None

    def __init__(self, **kwargs):
        self._name          = kwargs.pop("name", self._name)
        self._p3d_collision = kwargs.pop("p3d_collision", self._p3d_collision)

        if self._p3d_collision is None:
            self._p3d_collision = panda3d.core.GeomNode()

        if not isinstance(self._p3d_collision, panda3d.core.CollisionNode):
            raise TypeError(
                f"p3d_collision must be of type panda3d.core.CollisionNode, not {type(self._p3d_collision)}"
                )

    @property
    def p3d_collision(self):
        return self._p3d_collision

    @property
    def name(self): return self._name.upper()
