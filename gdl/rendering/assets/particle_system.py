import panda3d

class ParticleSystem:
    _name = ""
    _p3d_psys = None

    def __init__(self, **kwargs):
        self._name     = kwargs.pop("name", self._name).upper().strip()
        self._p3d_psys = kwargs.pop("p3d_psys", self._p3d_psys)

        if not isinstance(self._p3d_psys, panda3d.physics.ParticleSystem):
            raise TypeError(
                f"p3d_psys must be of type panda3d.physics.ParticleSystem, not {type(self.p3d_psys)}"
                )

    @property
    def p3d_psys(self):
        return self._p3d_psys

    @property
    def name(self): return self._name
