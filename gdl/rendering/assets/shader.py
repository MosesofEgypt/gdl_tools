from . import texture

class GeometryShader:
    alpha = False
    sort  = False
    sort_alpha = False

    sharp  = False
    blur   = False
    chrome = False

    _diff_textures = ()
    _lm_texture = None

    _diff_texture_name = None

    def __init__(self, *args, **kwargs):
        self._lm_texture        = kwargs.pop("lm_texture", self._lm_texture)
        self._diff_texture_name = kwargs.pop("diff_texture_name", self._diff_texture_name)
        diff_texture  = kwargs.pop("diff_texture", None)
        diff_textures = kwargs.pop("diff_textures", ())

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
        # TODO: implement texture switching through changing shader
        # input value that controls what texture to display
