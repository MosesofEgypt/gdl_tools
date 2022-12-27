import panda3d

from . import shader


class Geometry:
    _shader = None
    _p3d_geometry = None

    def __init__(self, **kwargs):
        self._shader       = kwargs.pop("shader", self._shader)
        self._p3d_geometry = kwargs.pop("p3d_geometry", self._p3d_geometry)
        if self._shader is None:
            self._shader = shader.GeometryShader()

        if not isinstance(self._shader, shader.GeometryShader):
            raise TypeError(
                f"shader must be of type GeometryShader, not {type(self._shader)}"
                )
        elif not isinstance(self._p3d_geometry, panda3d.core.Geom):
            raise TypeError(
                f"shader must be of type panda3d.core.Geom, not {type(self._p3d_geometry)}"
                )

    @property
    def shader(self):
        return self._shader

    @property
    def p3d_geometry(self):
        return self._p3d_geometry


class Model:
    _name = ""
    _geometries = ()
    _bounding_radius = 0.0

    def __init__(self, **kwargs):
        self._name = kwargs.pop("name", self._name)
        self._bounding_radius = kwargs.pop("bounding_radius", self._bounding_radius)
        self._geometries = []

    def add_geometry(self, geometry):
        if not isinstance(geometry, Geometry):
            raise TypeError(f"geometry must be of type Geometry, not {type(geometry)}")

        self._geometries.append(geometry)

    @property
    def name(self): return self._name.upper()

    @property
    def geometries(self):
        return tuple(self._geometries)

    @property
    def bounding_radius(self):
        return self._bounding_radius
    @bounding_radius.setter
    def bounding_radius(self, val):
        self._bounding_radius = float(val)
