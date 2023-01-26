from . import model
from . import texture


class Animation:
    _name = "UNNAMED"

    loop = False
    reverse = False

    _frame_data = ()
    _frame_data_cls = type(None)
    _frame_rate = 30

    def __init__(self, **kwargs):
        self.loop         = kwargs.pop("loop", self.loop)
        self.reverse      = kwargs.pop("reverse", self.reverse)
        self._name        = kwargs.pop("name", self._name)
        self._frame_rate  = kwargs.pop("frame_rate",  self._frame_rate)

        self.frame_data   = kwargs.pop("frame_data", ())

        frame0 = kwargs.pop("initial_frame", 0) % self.frame_count
        if frame0:
            # shift frames if the initial frame is non-zero
            self._frame_data = self.frame_data[frame0: ] + self.frame_data[: frame0]

        if kwargs:
            raise ValueError("Unknown parameters detected: %s" % ', '.join(kwargs.keys()))

    @property
    def name(self): return self._name.upper()
    @property
    def frame_count(self): return max(1, len(self.frame_data))
    @property
    def frame_rate(self): return max(1, self._frame_rate)
    @property
    def length(self): return self.frame_count / self.frame_rate
    @property
    def frame_data(self): return self._frame_data
    @frame_data.setter
    def frame_data(self, frame_data):
        frame_data = tuple(frame_data)
        for frame in frame_data:
            if not isinstance(frame, self._frame_data_cls):
                raise TypeError(
                    "Invalid frame data type found. Expected "
                    f"{self._frame_data_cls}, but got {type(frame)}"
                    )
        self._frame_data = frame_data

    def get_anim_frame(self, frame_time):
        '''
        frame_time is the moment in time in seconds we want the frame data for.
        '''
        anim_frame = int(frame_time * self._frame_rate)
        if self.reverse:
            anim_frame = (self.frame_count - 1) - anim_frame
            
        if self.loop:
            return anim_frame % self.frame_count
        return min(anim_frame, self.frame_count - 1)

    def get_frame_data(self, frame_time):
        return self._frame_data[self.get_anim_frame(frame_time)]


class ActorAnimation(Animation):
    pass


class ShapeMorphAnimation(Animation):
    _frame_data_cls = model.Model


class TextureAnimation(Animation):
    _frame_data_cls = texture.Texture
    _scroll_rate_u = 0
    _scroll_rate_v = 0
    _fade_rate = 0
    # TODO: figure out what mip_blend is

    def __init__(self, **kwargs):
        self.scroll_rate_u = kwargs.pop("scroll_rate_u", self.scroll_rate_u)
        self.scroll_rate_v = kwargs.pop("scroll_rate_v", self.scroll_rate_v)
        self.fade_rate     = kwargs.pop("fade_rate",     self.fade_rate)
        super().__init__(**kwargs)

    @property
    def scroll_rate_u(self): return self._scroll_rate_u
    @scroll_rate_u.setter
    def scroll_rate_u(self, value): self._scroll_rate_u = float(value)
    @property
    def scroll_rate_v(self): return self._scroll_rate_v
    @scroll_rate_v.setter
    def scroll_rate_v(self, value): self._scroll_rate_v = float(value)
    @property
    def fade_rate(self): return self._fade_rate
    @fade_rate.setter
    def fade_rate(self, value): self._fade_rate = float(value)

    @property
    def has_uv_animation(self):  return self.scroll_rate_u or self.scroll_rate_v
    @property
    def has_fade_animation(self): return bool(self.fade_rate)
    @property
    def has_swap_animation(self): return bool(self.frame_count)

    def get_uv(self, frame_time):
        rate_u = self._scroll_rate_u
        rate_v = self._scroll_rate_v
        if self.reverse:
            rate_u *= -1
            rate_v *= -1

        u, v = frame_time * rate_u, frame_time * rate_v
        return u - (int(u)), v - (int(v))

    def get_fade(self, frame_time):
        rate = self._fade_rate * (-1 if self.reverse else 1)
        start = 1.0 if rate < 0 else 0.0
        return min(1.0, max(0.0, start + frame_time * rate))
