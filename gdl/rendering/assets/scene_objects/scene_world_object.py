from .scene_object import SceneObject


class SceneWorldObject(SceneObject):
    _trigger_type    = -1
    _trigger_state   = -1
    _p_trigger_state = -1

    _flags = 0

    @property
    def trigger_type(self): return self._trigger_state
    @property
    def trigger_state(self): return self._trigger_state
    @property
    def p_trigger_state(self): return self._p_trigger_state
