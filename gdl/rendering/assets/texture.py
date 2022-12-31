import panda3d

class Texture:
    _name = ""
    _p3d_texture = None

    def __init__(self, **kwargs):
        self._name        = kwargs.pop("name", self._name)
        self._p3d_texture = kwargs.pop("p3d_texture", self._p3d_texture)

        if not isinstance(self.p3d_texture, panda3d.core.Texture):
            raise TypeError(
                f"p3d_texture must be of type panda3d.core.Texture, not {type(self.p3d_texture)}"
                )

    @property
    def p3d_texture(self):
        return self._p3d_texture

    @property
    def name(self): return self._name.upper()


class AnimatedTexture(Texture):
    _p3d_texture_frames = ()
    _frame = 0

    def __init__(self, **kwargs):
        p3d_texture  = kwargs.pop("p3d_texture", self._p3d_texture)
        p3d_texture_frames = tuple(kwargs.pop("p3d_texture_frames", ()))

        if p3d_texture and not p3d_texture_frames:
            p3d_texture_frames = (p3d_texture, )

        self.p3d_texture_frames = p3d_texture_frames

        super().__init__(**kwargs)

    @property
    def p3d_texture_frames(self):
        return self._p3d_texture_frames
    @p3d_texture_frames.setter
    def p3d_texture_frames(self, p3d_texture_frames):
        if not p3d_texture_frames:
            raise ValueError("p3d_texture_frames cannot be empty")

        for frame in p3d_texture_frames:
            if not isinstance(frame, panda3d.core.Texture):
                raise TypeError(
                    f"p3d_texture_frame must be of type panda3d.core.Texture, not {type(frame)}"
                    )
        self._p3d_texture_frames = tuple(p3d_texture_frames)

    @property
    def p3d_texture(self):
        return self._p3d_texture_frames[self.frame]

    @property
    def frame(self):
        return self._frame
    @frame.setter
    def frame(self, frame):
        self._frame = int(frame) % len(self._p3d_texture_frames)
