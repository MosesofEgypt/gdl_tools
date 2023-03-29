import panda3d
from panda3d.core import TextureStage, ColorBlendAttrib,\
     ShadeModelAttrib, TransparencyAttrib

from . import texture
from . import constants as c

class GeometryShader:
    dist_alpha   = False
    alpha        = False
    sort         = False
    forced_sort  = None

    no_z_test    = False
    no_z_write   = False

    add_first    = False
    sort_alpha   = False
    alpha_last   = False
    alpha_last_2 = False
    no_shading   = False
    color_scale  = 1

    fb_add      = False
    fb_mul      = False

    chrome       = False
    sharp        = False
    blur         = False

    _diff_texture   = None
    _lm_texture     = None

    _diff_texture_stage = None
    _lm_texture_stage   = None

    _color_blend_attrib = None
    _shade_model_attrib = None

    _alpha_level = 1.0
    _u_offset    = 0.0
    _v_offset    = 0.0

    ALPHA_SCALE_PRIORITY = 10000

    def __init__(self, *args, **kwargs):
        self.lm_texture    = kwargs.pop("lm_texture",   self.lm_texture)
        self.diff_texture  = kwargs.pop("diff_texture", self.diff_texture)
        
        self._diff_texture_stage = TextureStage('diffuse')
        self._lm_texture_stage   = TextureStage('lightmap')

        self._lm_texture_stage.setTexcoordName("lm")
        self._lm_texture_stage.setSort(c.DRAW_SORT_LMAP)
        self._diff_texture_stage.setSort(c.DRAW_SORT_OPAQUE)

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

        # some textures use signed alpha channels(ps2/xbox), so double
        # the value to achieve the transparency level we want
        signed = not self.dist_alpha and getattr(self.diff_texture, "signed_alpha", True)
        self._diff_texture_stage.setAlphaScale(2 if signed else 1)

    def apply_diffuse(self, nodepath):
        if self.diff_texture:
            nodepath.setTexture(
                self._diff_texture_stage,
                self.diff_texture.p3d_texture
                )

    def clear(self, nodepath):
        nodepath.clearTexture()
        nodepath.clearTexGen()
        nodepath.clearTexTransform()
        nodepath.clearAttrib(ColorBlendAttrib)
        nodepath.clearTransparency()

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

        if self.color_scale != 1:
            self._diff_texture_stage.setRgbScale(self.color_scale)
            self._diff_texture_stage.setMode(TextureStage.MCombine)

        self._diff_texture_stage.setCombineRgb(
            TextureStage.CMModulate,
            TextureStage.CSPrevious,
            TextureStage.COSrcColor,
            TextureStage.CSTexture,
            TextureStage.COSrcColor,
            )
        self._diff_texture_stage.setCombineAlpha(
            TextureStage.CMModulate,
            TextureStage.CSPrevious,
            TextureStage.COSrcAlpha,
            TextureStage.CSTexture,
            TextureStage.COSrcAlpha,
            )

        nodepath.clearDepthTest()
        nodepath.clearDepthWrite()

        nodepath.setDepthTest(not self.no_z_test)
        nodepath.setDepthWrite(not self.no_z_write)

        if self._color_blend_attrib:
            nodepath.clearAttrib(ColorBlendAttrib)
            self._color_blend_attrib = None

        if self._shade_model_attrib:
            nodepath.clearAttrib(ShadeModelAttrib)
            self._shade_model_attrib = None

        if self.no_shading:
            self._shade_model_attrib = ShadeModelAttrib.make(
                ShadeModelAttrib.M_flat 
                )
            nodepath.setAttrib(self._shade_model_attrib)

        if self.forced_sort is not None:
            self._diff_texture_stage.setSort(self.forced_sort)
        elif self.fb_add or self.fb_mul or self.add_first:
            self._diff_texture_stage.setSort(c.DRAW_SORT_SFX)
        elif self.alpha_last_2:
            self._diff_texture_stage.setSort(c.DRAW_SORT_ALPHA_LAST2)
        elif self.alpha_last:
            self._diff_texture_stage.setSort(c.DRAW_SORT_ALPHA_LAST)
        elif self.alpha or self.sort:
            self._diff_texture_stage.setSort(c.DRAW_SORT_ALPHA)
        else:
            self._diff_texture_stage.setSort(c.DRAW_SORT_OPAQUE)

        if (self.fb_mul or self.fb_add or self.alpha or self.sort_alpha or
            self.alpha_last or self.alpha_last_2 or self.dist_alpha):
            if self.fb_mul:
                self._color_blend_attrib = ColorBlendAttrib.make(
                    ColorBlendAttrib.MAdd,
                    ColorBlendAttrib.OFbufferColor,
                    ColorBlendAttrib.OZero,
                    )
            elif self.fb_add:
                self._color_blend_attrib = ColorBlendAttrib.make(
                    ColorBlendAttrib.MAdd,
                    ColorBlendAttrib.OIncomingAlpha,
                    ColorBlendAttrib.OOne,
                    )

            if self.sort_alpha and not (self.fb_mul or self.fb_add):
                nodepath.setTransparency(TransparencyAttrib.MDual)
            else:
                nodepath.setTransparency(TransparencyAttrib.MAlpha)
        else:
            nodepath.setTransparency(TransparencyAttrib.MNone)

        if self._color_blend_attrib:
            nodepath.setAttrib(self._color_blend_attrib)

        self.set_diffuse_offset(nodepath)
        self.set_diffuse_alpha_level(nodepath)
