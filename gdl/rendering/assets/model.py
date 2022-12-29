import panda3d

from . import shader


class Geometry:
    _shader = None
    _p3d_geometry = None
        
    _diff_texture_stage = None
    _lm_texture_stage   = None

    def __init__(self, **kwargs):
        self._shader       = kwargs.pop("shader", self._shader)
        self._p3d_geometry = kwargs.pop("p3d_geometry", self._p3d_geometry)
        
        self._diff_texture_stage = panda3d.core.TextureStage('diffuse')
        self._lm_texture_stage   = panda3d.core.TextureStage('lightmap')
        self._lm_texture_stage.setTexcoordName("lm")

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
    def shader(self):
        return self._shader
    @property
    def p3d_geometry(self):
        return self._p3d_geometry

    def apply_shader(self):
        # TODO: move most of this into GeometryShader
        nodepath = panda3d.core.NodePath(self.p3d_geometry)
        if self.shader.diff_texture:
            nodepath.setTexture(
                self._diff_texture_stage,
                self.shader.diff_texture.p3d_texture
                )

        if self.shader.lm_texture:
            nodepath.setTexture(
                self._lm_texture_stage,
                self.shader.lm_texture.p3d_texture
                )

        nodepath.setTransparency(
            panda3d.core.TransparencyAttrib.MAlpha if self.shader.alpha else
            panda3d.core.TransparencyAttrib.MNone
            )
        if self.shader.chrome:
            nodepath.setTexGen(
                self._diff_texture_stage,
                panda3d.core.TexGenAttrib.MEyeSphereMap
                )
        else:
            nodepath.clearTexGen()
            

        # ps2 textures use signed alpha channels, so double
        # the value to achieve the transparency level we want
        if self.shader.signed_alpha:
            self._diff_texture_stage.setCombineAlpha(
                panda3d.core.TextureStage.CMAdd,
                panda3d.core.TextureStage.CSTexture,
                panda3d.core.TextureStage.COSrcAlpha,
                panda3d.core.TextureStage.CSTexture,
                panda3d.core.TextureStage.COSrcAlpha,
                )
        else:
            self._diff_texture_stage.setCombineAlpha(
                panda3d.core.TextureStage.CMReplace,
                panda3d.core.TextureStage.CSTexture,
                panda3d.core.TextureStage.COSrcAlpha,
                )


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
