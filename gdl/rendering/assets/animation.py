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

        self._frame_data = tuple(kwargs.pop("frame_data", ()))
        for frame in self._frame_data:
            if not isinstance(frame, self._frame_data_cls):
                raise TypeError(
                    "Invalid frame data type found. Expected "
                    f"{self._frame_data_cls}, but got {type(frame)}"
                    )

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
    def frame_data(self): return self._frame_data
    @property
    def frame_rate(self): return max(1, self._frame_rate)
    @property
    def length(self): return self.frame_count / self.frame_rate

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


class TextureSwapAnimation(Animation):
    _frame_data_cls = texture.Texture
