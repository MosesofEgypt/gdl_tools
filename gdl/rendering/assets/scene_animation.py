
class SceneAnimation:
    _loop = False
    _start_frame = 0
    _frame_rate = 1.0
    _frames = 1


class SceneSkeletalAnimation(SceneAnimation):
    _pos_xyz_frame_data = ()
    _rot_ypr_frame_data = ()
    _scale_xyz_frame_data = ()


class SceneShapeMorphAnimation(SceneAnimation):
    _render_models = ()


class SceneTextureAnimation(SceneAnimation):
    _textures = ()
