
class Shader:
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

    _lm_tex   = None
    _diff_tex = None

    def __init__(self, *args, **kwargs):
        pass
