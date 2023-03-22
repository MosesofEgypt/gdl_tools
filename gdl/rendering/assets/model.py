import panda3d

from . import shader


class Geometry:
    _shader = None
    _p3d_nodepath = None
    _actor_tex_anim = None
    billboard = False

    def __init__(self, **kwargs):
        self._shader  = kwargs.pop("shader", self._shader)
        self.billboard = bool(kwargs.pop("billboard", self.billboard))
        if self._shader is None:
            self._shader = shader.GeometryShader()

        p3d_geometry = kwargs.pop("p3d_geometry", None)
        if p3d_geometry is None:
            p3d_geometry = panda3d.core.GeomNode("")

        if not isinstance(self._shader, shader.GeometryShader):
            raise TypeError(
                f"shader must be of type GeometryShader, not {type(self._shader)}"
                )
        elif not isinstance(p3d_geometry, panda3d.core.GeomNode):
            raise TypeError(
                f"p3d_geometry must be of type panda3d.core.GeomNode, not {type(p3d_geometry)}"
                )

        self._p3d_nodepath = panda3d.core.NodePath(p3d_geometry)
        self.apply_shader()

    @property
    def shader(self): return self._shader
    @property
    def p3d_geometry(self): return self._p3d_nodepath.node()
    @property
    def p3d_nodepath(self): return self._p3d_nodepath
    @property
    def actor_tex_anim(self): return self._actor_tex_anim
    @actor_tex_anim.setter
    def actor_tex_anim(self, tex_anim):
        self._actor_tex_anim = tex_anim

    def clear_shader(self):
        self.p3d_nodepath.clearTexture()
        self.p3d_nodepath.clearTexGen()
        self.p3d_nodepath.clearTexTransform()
        self.p3d_nodepath.clearAttrib(panda3d.core.ColorBlendAttrib)
        self.p3d_nodepath.clearTransparency()

    def apply_shader(self):
        self.shader.apply(self.p3d_nodepath)


class Model:
    _name = ""
    _geometries = ()
    _bound_rad = 0.0
    _p3d_nodepath = None

    def __init__(self, **kwargs):
        self._name       = kwargs.pop("name", self._name).upper().strip()
        self._bound_rad  = kwargs.pop("bounding_radius", self._bound_rad)
        self._geometries = {}

        p3d_model = kwargs.pop("p3d_model", None)
        if p3d_model is None:
            p3d_model = panda3d.core.ModelNode(self.name)

        if not isinstance(p3d_model, panda3d.core.ModelNode):
            raise TypeError(
                f"p3d_model must be of type panda3d.core.ModelNode, not {type(p3d_model)}"
                )

        self._p3d_nodepath = panda3d.core.NodePath(p3d_model)

    def add_geometry(self, geometry):
        if not isinstance(geometry, Geometry):
            raise TypeError(f"geometry must be of type Geometry, not {type(geometry)}")
        elif id(geometry) in self._geometries:
            return

        self._geometries[id(geometry)] = geometry
        self.p3d_model.add_child(geometry.p3d_geometry)

    @property
    def name(self): return self._name

    @property
    def p3d_model(self): return self._p3d_nodepath.node()
    @property
    def p3d_nodepath(self): return self._p3d_nodepath

    @property
    def geometries(self):
        return tuple(self._geometries.values())

    @property
    def bounding_radius(self):
        return self._bound_rad
    @bounding_radius.setter
    def bounding_radius(self, val):
        self._bound_rad = float(val)


class ObjectAnimModel(Model):
    _obj_anim_model = None

    def __init__(self, **kwargs):
        obj_anim_model = kwargs.pop("obj_anim_model", self._obj_anim_model)
        super().__init__(**kwargs)
        # do this after initializing self so self.p3d_model exists
        self.obj_anim_model = obj_anim_model

    @property
    def obj_anim_model(self):
        return self._obj_anim_model
    @obj_anim_model.setter
    def obj_anim_model(self, obj_anim_model):
        if not isinstance(obj_anim_model, (type(None), Model)):
            raise TypeError(
                f"obj_anim_model must be either None, or of type Model, not {type(obj_anim_model)}"
                )
        if self.obj_anim_model:
            self.p3d_model.remove_child(self.obj_anim_model.p3d_model)

        if obj_anim_model:
            self.p3d_model.add_child(obj_anim_model.p3d_model)

        self._obj_anim_model = obj_anim_model
