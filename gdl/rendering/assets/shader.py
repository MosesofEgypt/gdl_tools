import panda3d

from . import texture

class GeometryShader:
    alpha       = False
    sort        = False
    sort_alpha  = False

    no_z_test   = False
    no_z_write  = False

    add_first   = False
    sort_alpha  = False
    alpha_last  = False
    no_shading  = False

    fb_add      = False
    fb_mul      = False

    chrome      = False
    sharp       = False
    blur        = False

    signed_alpha    = True

    _diff_texture   = None
    _lm_texture     = None

    _diff_texture_stage = None
    _lm_texture_stage   = None

    _color_blend_attrib = None
    _shade_model_attrib = None

    _alpha_level = 1.0
    _u_offset    = 0.0
    _v_offset    = 0.0

    DRAW_SORT_LMAP   = 0
    DRAW_SORT_OPAQUE = 10
    DRAW_SORT_ALPHA  = 20
    DRAW_SORT_SFX    = 1000

    ALPHA_SCALE_PRIORITY = 10000

    def __init__(self, *args, **kwargs):
        self.lm_texture    = kwargs.pop("lm_texture",   self.lm_texture)
        self.diff_texture  = kwargs.pop("diff_texture", self.diff_texture)
        
        self._diff_texture_stage = panda3d.core.TextureStage('diffuse')
        self._lm_texture_stage   = panda3d.core.TextureStage('lightmap')

        self._lm_texture_stage.setTexcoordName("lm")
        self._lm_texture_stage.setSort(GeometryShader.DRAW_SORT_LMAP)
        self._diff_texture_stage.setSort(GeometryShader.DRAW_SORT_OPAQUE)

    @property
    def lm_texture(self):
        return self._lm_texture
    @lm_texture.setter
    def lm_texture(self, tex):
        if not isinstance(tex, (type(None), texture.Texture)):
            raise TypeError(
                f"textures must be either None, or of type Texture, not {type(tex)}"
                )
        self._lm_texture = tex
    @property
    def diff_texture(self):
        return self._diff_texture
    @diff_texture.setter
    def diff_texture(self, tex):
        if not isinstance(tex, (type(None), texture.Texture)):
            raise TypeError(
                f"textures must be either None, or of type Texture, not {type(tex)}"
                )
        self._diff_texture = tex

    def set_diffuse_offset(self, nodepath, u=None, v=None):
        self._u_offset = float(self._u_offset if u is None else u)
        self._v_offset = float(self._v_offset if v is None else v)
        nodepath.setTexPos(
            self._diff_texture_stage,
            self._u_offset, self._v_offset, 0.0
            )

    def set_diffuse_alpha_level(self, nodepath, alpha_level=None):
        self._alpha_level = min(1.0, max(0.0, float(
            self._alpha_level if alpha_level is None else alpha_level
            )))
        nodepath.setAlphaScale(self._alpha_level, self.ALPHA_SCALE_PRIORITY)
        # ps2 textures use signed alpha channels, so double
        # the value to achieve the transparency level we want
        self._diff_texture_stage.setAlphaScale(
            2 if self.signed_alpha else 1
            )

    def apply_diffuse(self, nodepath):
        if self.diff_texture:
            nodepath.setTexture(
                self._diff_texture_stage,
                self.diff_texture.p3d_texture
                )

    def apply(self, nodepath):
        self.apply_diffuse(nodepath)
        if self.lm_texture:
            nodepath.setTexture(
                self._lm_texture_stage,
                self.lm_texture.p3d_texture
                )

        if self.chrome:
            nodepath.setTexGen(
                self._diff_texture_stage,
                panda3d.core.TexGenAttrib.MEyeSphereMap
                )
        else:
            nodepath.clearTexGen()

        self._diff_texture_stage.setCombineRgb(
            panda3d.core.TextureStage.CMModulate,
            panda3d.core.TextureStage.CSPrevious,
            panda3d.core.TextureStage.COSrcColor,
            panda3d.core.TextureStage.CSTexture,
            panda3d.core.TextureStage.COSrcColor,
            )
        self._diff_texture_stage.setCombineAlpha(
            panda3d.core.TextureStage.CMModulate,
            panda3d.core.TextureStage.CSPrevious,
            panda3d.core.TextureStage.COSrcAlpha,
            panda3d.core.TextureStage.CSTexture,
            panda3d.core.TextureStage.COSrcAlpha,
            )
        
        nodepath.clearDepthTest()
        nodepath.clearDepthWrite()

        nodepath.setDepthTest(not self.no_z_test)
        nodepath.setDepthWrite(not self.no_z_write)

        if self._color_blend_attrib:
            nodepath.clearAttrib(panda3d.core.ColorBlendAttrib)
            self._color_blend_attrib = None

        if self._shade_model_attrib:
            nodepath.clearAttrib(panda3d.core.ShadeModelAttrib)
            self._shade_model_attrib = None

        if self.no_shading:
            self._shade_model_attrib = panda3d.core.ShadeModelAttrib.make(
                panda3d.core.ShadeModelAttrib.M_flat 
                )
            nodepath.setAttrib(self._shade_model_attrib)

        if self.alpha:
            nodepath.setTransparency(panda3d.core.TransparencyAttrib.MAlpha)
            self._diff_texture_stage.setSort(GeometryShader.DRAW_SORT_OPAQUE)
        elif self.fb_add:
            self._color_blend_attrib = panda3d.core.ColorBlendAttrib.make(
                panda3d.core.ColorBlendAttrib.MAdd
                )
            nodepath.setAttrib(self._color_blend_attrib)
            self._diff_texture_stage.setSort(GeometryShader.DRAW_SORT_SFX)
        else:
            nodepath.setTransparency(panda3d.core.TransparencyAttrib.MNone)
            self._diff_texture_stage.setSort(GeometryShader.DRAW_SORT_OPAQUE)

        self.set_diffuse_offset(nodepath)
        self.set_diffuse_alpha_level(nodepath)
