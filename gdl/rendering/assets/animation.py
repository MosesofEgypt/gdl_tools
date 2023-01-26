from . import model
from . import texture


class Animation:
    _name = "UNNAMED"

    loop = False
    reverse = False

    _frame_data = ()
    _frame_data_cls = type(None)
    _frame_rate  = 30
    _start_frame = 0

    def __init__(self, **kwargs):
        self._name       = kwargs.pop("name",      self._name)
        self.loop        = kwargs.pop("loop",      self.loop)
        self.reverse     = kwargs.pop("reverse",   self.reverse)
        self.frame_rate  = kwargs.pop("frame_rate",  self.frame_rate)
        self.start_frame = kwargs.pop("start_frame", self.start_frame)

        self.frame_data   = kwargs.pop("frame_data", ())

        if kwargs:
            raise ValueError("Unknown parameters detected: %s" % ', '.join(kwargs.keys()))

    @property
    def name(self): return self._name.upper()
    @property
    def frame_rate(self): return max(1, self._frame_rate)
    @frame_rate.setter
    def frame_rate(self, val): self._frame_rate = float(val)
    @property
    def start_frame(self): return max(0, self._start_frame)
    @start_frame.setter
    def start_frame(self, val): self._start_frame = max(0, int(val))
    @property
    def frame_count(self): return max(1, len(self.frame_data))
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

        if not self.loop:
            anim_frame = max(0, min(anim_frame, self.frame_count - 1))
        return (anim_frame + self.start_frame) % self.frame_count

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
    _fade_rate  = 0
    _fade_start = 0
    # TODO: figure out what mip_blend is

    def __init__(self, **kwargs):
        self.scroll_rate_u = kwargs.pop("scroll_rate_u", self.scroll_rate_u)
        self.scroll_rate_v = kwargs.pop("scroll_rate_v", self.scroll_rate_v)
        self.fade_rate     = kwargs.pop("fade_rate",     self.fade_rate)
        self.fade_start    = kwargs.pop("fade_start",    self.fade_start)
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
    def fade_start(self): return self._fade_start
    @fade_start.setter
    def fade_start(self, value): self._fade_start = float(value)

    @property
    def has_uv_animation(self):  return self.scroll_rate_u or self.scroll_rate_v
    @property
    def has_fade_animation(self): return bool(self.fade_rate)
    @property
    def has_swap_animation(self): return bool(self.frame_count)

    def get_uv(self, frame_time):
        rate_u = self.scroll_rate_u
        rate_v = self.scroll_rate_v
        if self.reverse:
            rate_u *= -1
            rate_v *= -1

        u, v = frame_time * rate_u, frame_time * rate_v
        return u - (int(u)), v - (int(v))

    def get_fade(self, frame_time):
        rate = self.fade_rate * (-1 if self.reverse else 1)
        return min(1.0, max(0.0, self.fade_start + frame_time * rate))
