import panda3d

from . import shader
from . import animation


class Geometry:
    _shader = None
    _p3d_geometry = None
    _actor_tex_anim = None

    def __init__(self, **kwargs):
        self._shader       = kwargs.pop("shader", self._shader)
        self._p3d_geometry = kwargs.pop("p3d_geometry", self._p3d_geometry)

        if self._shader is None:
            self._shader = shader.GeometryShader()
        if self._p3d_geometry is None:
            self._p3d_geometry = panda3d.core.GeomNode()

        if not isinstance(self._shader, shader.GeometryShader):
            raise TypeError(
                f"shader must be of type GeometryShader, not {type(self._shader)}"
                )
        elif not isinstance(self._p3d_geometry, panda3d.core.GeomNode):
            raise TypeError(
                f"p3d_geometry must be of type panda3d.core.GeomNode, not {type(self._p3d_geometry)}"
                )

        self.apply_shader()

    @property
    def shader(self): return self._shader
    @property
    def p3d_geometry(self): return self._p3d_geometry
    @property
    def actor_tex_anim(self): return self._actor_tex_anim
    @actor_tex_anim.setter
    def actor_tex_anim(self, tex_anim):
        if not isinstance(tex_anim, (type(None), animation.TextureAnimation)):
            raise TypeError(
                f"tex_anim must be either None, or of type TextureAnimation, not {type(tex_anim)}"
                )
        self._actor_tex_anim = tex_anim

    def apply_shader(self):
        self.shader.apply(panda3d.core.NodePath(self.p3d_geometry))


class Model:
    _name = ""
    _geometries = ()
    _bound_rad = 0.0
    _p3d_model = None

    def __init__(self, **kwargs):
        self._name       = kwargs.pop("name", self._name)
        self._p3d_model  = kwargs.pop("p3d_model", self._p3d_model)
        self._bound_rad  = kwargs.pop("bounding_radius", self._bound_rad)
        self._geometries = {}
        if self._p3d_model is None:
            self._p3d_model = panda3d.core.ModelNode(self.name)

        if not isinstance(self._p3d_model, panda3d.core.ModelNode):
            raise TypeError(
                f"p3d_model must be of type panda3d.core.ModelNode, not {type(self._p3d_model)}"
                )

    def add_geometry(self, geometry):
        if not isinstance(geometry, Geometry):
            raise TypeError(f"geometry must be of type Geometry, not {type(geometry)}")
        elif id(geometry) in self._geometries:
            return

        self._geometries[id(geometry)] = geometry
        self.p3d_model.addChild(geometry.p3d_geometry)

    @property
    def name(self): return self._name.upper()

    @property
    def p3d_model(self):
        return self._p3d_model

    @property
    def geometries(self):
        return tuple(self._geometries.values())

    @property
    def bounding_radius(self):
        return self._bound_rad
    @bounding_radius.setter
    def bounding_radius(self, val):
        self._bound_rad = float(val)
