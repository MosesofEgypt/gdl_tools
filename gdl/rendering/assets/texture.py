import panda3d

class Texture:
    _name = ""
    _p3d_texture = None

    def __init__(self, **kwargs):
        self._name        = kwargs.pop("name", self._name).upper().strip()
        self._p3d_texture = kwargs.pop("p3d_texture", self._p3d_texture)

        if not isinstance(self.p3d_texture, panda3d.core.Texture):
            raise TypeError(
                f"p3d_texture must be of type panda3d.core.Texture, not {type(self.p3d_texture)}"
                )

    @property
    def p3d_texture(self):
        return self._p3d_texture

    @property
    def name(self): return self._name
