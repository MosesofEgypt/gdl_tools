
class Triangle:
    _pos_indices   = ()
    _tex_indices   = ()
    _norm_indices  = ()
    _color_indices = ()

    def __init__(self, *args, **kwargs):
        pass

    @property
    def pos_indices(self): return self._pos_indices
    @property
    def tex_indices(self): return self._tex_indices
    @property
    def norm_indices(self): return self._norm_indices
    @property
    def color_indices(self): return self._color_indices


class Geometry:
    _tris = ()

    _shader = None

    _vert_norm_coords = ()
    _vert_pos_coords  = ()
    _vert_tex_coords  = ()
    _vert_colors      = ()

    def __init__(self, *args, **kwargs):
        pass


class RenderModel:
    '''
    This class represents a single non-skinned model consisting of one
    or more triangle-based geometry sets. Each geometry may contain uv
    coordinates, vertex normals, vertex colors, and textures.
    '''
    _geometries = ()
    _bounding_radius = 0.0

    def __init__(self, *args, **kwargs):
        pass
