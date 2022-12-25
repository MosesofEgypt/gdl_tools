
class Geometry:
    _shader = None
    _panda3d_geometry = None

    def __init__(self, **kwargs):
        pass


class Model:
    '''
    This class represents a single non-skinned model consisting
    of one or more polygon-based geometry sets.
    '''
    _geometries = ()
    _bounding_radius = 0.0

    def __init__(self, **kwargs):
        pass
