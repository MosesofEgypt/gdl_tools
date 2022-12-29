import panda3d

from . import texture

class GeometryShader:
    alpha = False
    sort  = False
    sort_alpha = False

    signed_alpha = True

    sharp  = False
    blur   = False
    chrome = False

    _diff_textures = ()
    _lm_texture = None

    _diff_texture_name = None

    _diff_texture_stage = None
    _lm_texture_stage   = None

    _color_blend_attrib = None

    DRAW_SORT_LMAP   = 0
    DRAW_SORT_OPAQUE = 1
    DRAW_SORT_ALPHA  = 2
    DRAW_SORT_SFX    = 1000

    def __init__(self, *args, **kwargs):
        self._lm_texture        = kwargs.pop("lm_texture", self._lm_texture)
        self._diff_texture_name = kwargs.pop("diff_texture_name", self._diff_texture_name)
        diff_texture  = kwargs.pop("diff_texture", None)
        diff_textures = kwargs.pop("diff_textures", ())
        
        self._diff_texture_stage    = panda3d.core.TextureStage('diffuse')
        self._lm_texture_stage      = panda3d.core.TextureStage('lightmap')

        self._lm_texture_stage.setTexcoordName("lm")
        self._lm_texture_stage.setSort(GeometryShader.DRAW_SORT_LMAP)
        self._diff_texture_stage.setSort(GeometryShader.DRAW_SORT_OPAQUE)

        if diff_texture:
            diff_textures = tuple(diff_textures) + (diff_texture, )

        for tex in diff_textures + (self._lm_texture, ):
            if not isinstance(tex, (type(None), texture.Texture)):
                raise TypeError(
                    f"textures must be either None, or of type Texture, not {type(tex)}"
                    )

        self._diff_textures = {
            tex.name: tex for tex in diff_textures
            }
        if self._diff_textures and not self._diff_texture_name:
            self.set_diffuse_texture(tuple(self._diff_textures.keys())[0])

    @property
    def lm_texture(self):
        return self._lm_texture
    @property
    def diff_texture(self):
        return self._diff_textures.get(self._diff_texture_name)
    @property
    def diff_textures(self):
        return dict(self._diff_textures)
    @property
    def diff_texture_name(self):
        return self._diff_texture_name

    def set_diffuse_texture(self, texture_name):
        if texture_name not in self._diff_textures:
            raise ValueError(f"No texture found with name '{texture_name}'")

        self._diff_texture_name = texture_name
        # TODO: implement texture switching through keeping a record of every
        #       geometry using this shader, and update them in a loop here

    def apply_to_geometry(self, p3d_geometry):
        nodepath = panda3d.core.NodePath(p3d_geometry)
        if self.diff_texture:
            nodepath.setTexture(
                self._diff_texture_stage,
                self.diff_texture.p3d_texture
                )

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

        if self._color_blend_attrib:
            nodepath.clearAttrib(self._color_blend_attrib)
            self._color_blend_attrib = None

        if self.alpha:
            nodepath.setTransparency(panda3d.core.TransparencyAttrib.MAlpha)
            self._diff_texture_stage.setSort(GeometryShader.DRAW_SORT_OPAQUE)
        else:
            nodepath.setTransparency(panda3d.core.TransparencyAttrib.MNone)
            if self.sort_alpha:
                # Doesn't work in all cases.
                # TODO: figure out what controls transparenc for these objects
                #self._color_blend_attrib = panda3d.core.ColorBlendAttrib.make(
                #    panda3d.core.ColorBlendAttrib.MAdd,
                #    panda3d.core.ColorBlendAttrib.OOne,
                #    panda3d.core.ColorBlendAttrib.OOne,
                #    )
                #nodepath.setAttrib(self._color_blend_attrib)
                self._diff_texture_stage.setSort(GeometryShader.DRAW_SORT_SFX)
            else:
                self._diff_texture_stage.setSort(GeometryShader.DRAW_SORT_OPAQUE)

        # ps2 textures use signed alpha channels, so double
        # the value to achieve the transparency level we want
        self._diff_texture_stage.setAlphaScale(2 if self.signed_alpha else 1)
