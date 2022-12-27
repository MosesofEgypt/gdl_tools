
class GeometryShader:
    alpha = False
    sort  = False
    sort_alpha = False

    use_v_normals = True
    use_v_colors  = True

    sharp  = False
    blur   = False
    chrome = False

    pre_lit  = False
    lmap_lit = False
    dyn_lit  = False

    _lm_textures = ()
    _diff_texture = None

    _diff_texture_name = None

    def __init__(self, *args, **kwargs):
        self._lm_textures = {}

    def set_diffuse_texture(self, texture_name):
        # TODO: implement texture switching through changing shader
        # input value that controls what texture to display
        pass
