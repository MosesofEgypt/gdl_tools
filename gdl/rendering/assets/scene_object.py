
class SceneNode:
    _name = ""

    _pos_xyz = (0, 0, 0)
    _rot_ypr = (0, 0, 0)
    _scale_xyz = (0, 0, 0)

    _parent = None
    _children = None

    def __init__(self, *args, **kwargs):
        pass

    @property
    def children(self): pass

    @property
    def parent(self):
        return self.parent

    @parent.setter
    def parent(self, parent):
        self.parent = parent

    def add_child(self, child):
        pass

    def get_child(self, child_name):
        pass

    def del_child(self, child_name):
        pass


class ParticleSystemNode(SceneNode):
    _texture = None
    # TODO: fill in all particle system parameters


class CollisionNode(SceneNode):
    _collision_model = None


class _AnimatedNode(SceneNode):
    _curr_frame = 0


class TextureNode(_AnimatedNode):
    _curr_texture = None


class SkeletonNode(_AnimatedNode):
    _render_model = None


class ShapeMorphNode(_AnimatedNode):
    _curr_render_model = None


class SceneObject(SceneNode):
    _animation_states = ()

    def __init__(self, *args, **kwargs):
        pass

    def start_animation(self, anim_name):
        pass

    def set_animation_state(self, anim_name, state_info):
        pass

    def stop_animation(self, anim_name):
        pass
