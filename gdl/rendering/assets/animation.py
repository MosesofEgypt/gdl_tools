import panda3d
import weakref

from . import model
from . import texture


class Animation:
    _name = "UNNAMED"
    # these are the animations bound to each item type:
    #       generator enemies:
    #           ACTIVE ATTACK1 ATTACK1R ATTACK2 ATTACK2R ATTACK3 ATTACK3R
    #           ATTTOREADY EXPLODE GETUP HIT1 HIT2
    #           READY READYTOWALK RUN RUNATTACK1 RUNATTACK2 START
    #           THROW1 THROW2 THROWF WALK WALKTOREADY
    #       gargoyles:
    #           ACTIVE BITE CLAW DEATH FIRE
    #           FLY HIT1 HOVER IDLE INIT JUMP2FLY LAND
    #           LEFT READY RIGHT ROAR START WALK
    #       generals:
    #           ATTACK1 ATTACK2 ATTACK3 BLOCK CHARGE CHARGEATK
    #           DEATH GETUP HIT1 HIT2 HIT3 INIT READY START WALK
    #       gates found in level items:
    #           ACTIV CLOSE OPEN
    #       chests found in level items(including explosion):
    #           ACTIVE CLOSED OPEN
    #       all barrel animations:
    #           ACTIVE DONE IDLE
    #       exit portal's animations:
    #           ACTIVE1 ACTIVE2 ACTIVE3 IDLE READY
    #       pojo's animations:
    #           ATTACK ATTPWR DEATH HIT READY RUN
    #       phoenix familiar's animations:
    #           ATTACK READY
    #       wizard ghost's animations:
    #           READY
    #       triggers:
    #           OFF OFFA ON ONA
    #       traps:
    #           OFF OFFA ON ONA ONB
    #       sawblade in LEVELD items:
    #           OFF OFFA ON ONA ONB OBC ON2
    #       sumner in LEVELL items:
    #           GESTLEFT GESTRIGHT GOAWAY
    #           READING READY THINKING WELCOME
    #       most items just have the following animation(including destroyed traps):
    #           ACTIVE
    #       TODO: list player and boss animations
    loop    = False
    reverse = False

    _frame_data = ()
    _frame_data_cls = type(None)
    _frame_rate  = 30
    _start_frame = 0

    def __init__(self, **kwargs):
        self._name       = kwargs.pop("name",      self._name).upper().strip()
        self.loop        = kwargs.pop("loop",      self.loop)
        self.reverse     = kwargs.pop("reverse",   self.reverse)
        self.frame_rate  = kwargs.pop("frame_rate",  self.frame_rate)
        self.start_frame = kwargs.pop("start_frame", self.start_frame)
        self.frame_data  = kwargs.pop("frame_data",  self.frame_data)

        if kwargs:
            raise ValueError("Unknown parameters detected: %s" % ', '.join(kwargs.keys()))

    @property
    def name(self): return self._name
    @property
    def frame_rate(self): return max(1, self._frame_rate)
    @frame_rate.setter
    def frame_rate(self, val): self._frame_rate = float(val)
    @property
    def start_frame(self): return max(0, self._start_frame)
    @start_frame.setter
    def start_frame(self, val): self._start_frame = max(0, int(val))
    @property
    def frame_count(self): return max(0, len(self.frame_data))
    @property
    def length(self): return self.frame_count / self.frame_rate
    @property
    def frame_data(self): return self._frame_data
    @frame_data.setter
    def frame_data(self, frame_data):
        self._set_frame_data(frame_data)

    def _set_frame_data(self, frame_data):
        # setter properties are broken on subclasses
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
        return self.frame_data[self.get_anim_frame(frame_time)]


class SkeletalAnimation(Animation):
    pass


class ShapeMorphAnimation(Animation):
    _frame_data_cls = model.Model

    @property
    def binds(self):
        return tuple(ref() for ref in self._binds.values() if ref())
    def bind(self, model):
        self._binds[id(model)] = weakref.ref(model)
    def unbind(self, model):
        try:
            del self._binds[id(model)]
        except KeyError:
            try:
                del self._binds[model]
            except TypeError:
                pass

    def clear_binds(self):
        self._binds = {}

    def update(self, frame_time):
        frame_model = self.get_frame_data(frame_time)

        # iterate as tuple in case we unbind it in the loop
        for ref_id, model_ref in tuple(self._binds.items()):
            parent_model = model_ref()
            if parent_model is None:
                self.unbind(ref_id)
                continue
            elif parent_model.obj_anim_model is frame_model:
                continue

            parent_model.obj_anim_model = frame_model


class TextureAnimation(Animation):
    _frame_data_cls = texture.Texture
    _scroll_rate_u = 0
    _scroll_rate_v = 0
    _fade_rate  = 0
    _fade_start = 0
    _binds = ()
    _external_anim = None
    _tex_name = ""
    external = False

    def __init__(self, **kwargs):
        self._tex_name     = kwargs.pop("tex_name",      self._tex_name).upper()
        self.scroll_rate_u = kwargs.pop("scroll_rate_u", self.scroll_rate_u)
        self.scroll_rate_v = kwargs.pop("scroll_rate_v", self.scroll_rate_v)
        self.fade_rate     = kwargs.pop("fade_rate",     self.fade_rate)
        self.fade_start    = kwargs.pop("fade_start",    self.fade_start)
        self.external_anim = kwargs.pop("external_anim", self.external_anim)
        self.external      = kwargs.pop("external",      self.external) or self.external_anim
        self.clear_binds()
        super().__init__(**kwargs)

    @property
    def tex_name(self): return self._tex_name.upper().strip()
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
    def external_anim(self): return self._external_anim
    @external_anim.setter
    def external_anim(self, external_anim):
        if not isinstance(external_anim, (type(None), TextureAnimation)):
            raise TypeError(
                "Invalid frame data type found. Expected "
                f"TextureAnimation, but got {type(external_anim)}"
                )
        self._external_anim = external_anim

    @property
    def has_uv_animation(self):  return self.scroll_rate_u or self.scroll_rate_v
    @property
    def has_fade_animation(self): return bool(self.fade_rate)
    @property
    def has_swap_animation(self): return bool(self.frame_count)
    @property
    def frame_data(self):
        return getattr(self.external_anim, "frame_data", (None,)) if self.external else self._frame_data
    @frame_data.setter
    def frame_data(self, frame_data):
        self._set_frame_data(frame_data)

    @property
    def binds(self):
        return tuple(ref() for ref in self._binds.values() if ref())
    def bind(self, geometry):
        self._binds[id(geometry)] = weakref.ref(geometry)
    def unbind(self, geometry):
        try:
            del self._binds[id(geometry)]
        except KeyError:
            try:
                del self._binds[geometry]
            except TypeError:
                pass

    def clear_binds(self):
        self._binds = {}

    def __eq__(self, other):
        if self is other:
            return True
        elif not isinstance(other, TextureAnimation):
            return False

        return not sum(
            getattr(self, name) != getattr(other, name)
            for name in (
                "_scroll_rate_u", "_scroll_rate_v",
                "_fade_rate", "_fade_start",
                "external", "loop", "reverse", "_tex_name", "_name",
                "_start_frame", "_frame_rate", "_frame_data"
                )
            )

    def update(self, frame_time):
        u, v    = self.get_uv(frame_time)
        alpha   = self.get_fade(frame_time)
        texture = self.get_frame_data(frame_time) if self.has_swap_animation else None

        # iterate as tuple in case we unbind it in the loop
        for ref_id, geometry_ref in tuple(self._binds.items()):
            geometry = geometry_ref()
            if geometry is None:
                self.unbind(ref_id)
                continue
            elif geometry.actor_tex_anim not in (self, None):
                continue

            nodepath = geometry.p3d_nodepath
            shader   = geometry.shader
            if self.has_uv_animation:
                shader.set_diffuse_offset(nodepath, u, v)

            if self.has_fade_animation:
                shader.set_diffuse_alpha_level(nodepath, alpha)

            if shader.diff_texture is not texture and texture:
                shader.diff_texture = texture
                shader.apply_diffuse(nodepath)

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
