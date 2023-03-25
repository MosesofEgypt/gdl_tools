import math
import random
import traceback
import types

from copy import deepcopy
from panda3d.core import NodePath, PandaNode

from direct.particles.ParticleEffect import ParticleEffect

DEFAULT_TEXTURE_NAME = "000GRID"
MIN_PHASE_PERIOD = 0.00001
MAX_PARTICLES    = 1000

DEFAULT_EMITTER_LIFE    = 1.0
DEFAULT_PARTICLE_LIFE   = 1.0
DEFAULT_PARTICLE_WIDTH  = 1.0
DEFAULT_EMIT_RATE       = 30
DEFAULT_COLOR           = (1.0, 1.0, 1.0, 1.0)


def get_phase_and_point_from_age(age, period_a, period_b, clamp=False):
    total_period = max(MIN_PHASE_PERIOD, period_a + period_b)
    if clamp:
        point = max(0, min(age, total_period))
    else:
        cycles  = int(age / total_period)
        point = age - cycles * total_period

    if point >= period_a and period_b:
        return "b", (point - period_a) / period_b
    return "a", point / max(MIN_PHASE_PERIOD, period_a)


class Particle:
    age = 0.0
    _system = None

    init_pos = (0.0, 0.0, 0.0)
    init_vel = (0.0, 0.0, 0.0)

    def __init__(self, **kwargs):
        self._system  = kwargs.pop("system", self._system)
        self.init_pos = kwargs.pop("init_pos", self.init_pos)
        self.init_vel = kwargs.pop("init_vel", self.init_vel)

        if not isinstance(self._system, ParticleSystem):
            raise TypeError(
                f"system must be of type ParticleSystem, not {type(self._system)}"
                )

    @property
    def pos(self):
        x, y, z = self.init_pos
        i, j, k = self.init_vel
        t = self.age
        return (
            x + t*i,
            y + t*j,
            z + t*(k - t*self.factory.gravity)
            )

    @property
    def system(self): return self._system
    @property
    def factory(self): return self.system.factory

    @property
    def color(self):
        phase, point = get_phase_and_point_from_age(
            self.age, self.factory.particle_life_a, self.factory.particle_life_b, clamp=True
            )
        colors = (
            self.factory.particle_colors_b if phase == "b" else
            self.factory.particle_colors_a
            )
        r0, g0, b0, a0 = colors[0]
        r1, g1, b1, a1 = colors[1]

        return (
            r0 + (r1 - r0)*point,
            g0 + (g1 - g0)*point,
            b0 + (b1 - b0)*point,
            a0 + (a1 - a0)*point,
            )

    @property
    def width(self):
        phase, point = get_phase_and_point_from_age(
            self.age, self.factory.particle_life_a, self.factory.particle_life_b, clamp=True
            )
        w0, w1 = (
            self.factory.particle_widths_b if phase == "b" else
            self.factory.particle_widths_a
            )
        return w0 + (w1 - w0)*point


class ParticleSystem:
    age = 0
    paused = False

    _factory        = None
    _particles      = []
    _p3d_nodepath   = None

    # NOTE: use visiblity of p3d_node to determine if system should render
    #       attach model from objects as invisible tri and use for determining visiblity
    # NOTE: only increase system age if it's visible
    # NOTE: particles need to be spawned relative to p3d_nodepath, but need to
    #       be attached to the world(check smoke vents on plague ship in K2)

    def __init__(self, **kwargs):
        self._factory = kwargs.pop("factory", None)

        if not isinstance(self._factory, ParticleSystemFactory):
            raise TypeError(
                f"factory must be of type ParticleSystemFactory, not {type(self._factory)}"
                )

    @property
    def factory(self): return self._factory
    @property
    def p3d_node(self): return self._p3d_nodepath.node()
    @property
    def p3d_nodepath(self): return self._p3d_nodepath

    @property
    def emit_velocity(self):
        y, p    = self.factory.emit_dir_yp
        speed   = self.factory.speed
        angle   = self.factory.emit_range

        i, j, k = 0.0, 0.0, 1.0
        if angle:
            # TODO: correct this to make it uniform and constrain to max angle
            dy = random.random() * angle*2 - angle
            dp = random.random() * angle*2 - angle
            y += dy
            p += dp

        # TODO: convert i/j/k from a local vector to world

        return i*speed, j*speed, k*speed

    @property
    def emit_position(self):
        # TODO: clean this up to no use global "render" variable
        x, y, z = self.p3d_node.get_pos(render) # world-relative position
        w, h, l = self.factory.emit_vol
        if w or h or l:
            x += random.random() * w*2 - w
            y += random.random() * h*2 - h
            z += random.random() * l*2 - l

        return x, y, z

    @property
    def emit_rate(self):
        phase, point = self.get_phase_and_point_from_age(
            self.age, self.factory.emit_life_a, self.factory.emit_life_b
            )
        r0, r1 = self.factory.emit_rates_b if phase == "b" else self.factory.emit_rates_a
        return r0 + (r1 - r0)*point

    def update(self, age_delta):
        if self.paused:
            return

        self.age += age_delta
        # TODO


class ParticleSystemFactory:
    _name       = ""
    _instances  = ()
    _flags      = ()
    _enabled    = False
    
    texture         = None
    max_particles   = MAX_PARTICLES
    emit_range      = 0
    emit_delay      = 0
    gravity         = 0
    speed           = 0

    emit_life_a     = 1.0
    emit_life_b     = 1.0
    particle_life_a = 1.0
    particle_life_b = 1.0

    emit_dir_yp        = (0.0, 0.0)
    emit_vol           = (0.0, 0.0, 0.0)
    emit_rates_a       = (1, 1)
    emit_rates_b       = (1, 1)
    particle_widths_a  = (1, 1)
    particle_widths_b  = (1, 1)
    particle_colors_a  = [(1.0, 1.0, 1.0, 1.0),
                          (1.0, 1.0, 1.0, 1.0)]
    particle_colors_b  = [(1.0, 1.0, 1.0, 1.0),
                          (1.0, 1.0, 1.0, 1.0)]

    def __init__(self, **kwargs):
        self._name         = kwargs.pop("name", self._name).upper().strip()
        self.texture       = kwargs.get("texture", self.texture)
        self.max_particles = kwargs.get("max_particles", self.max_particles)
        self.emit_range    = kwargs.get("emit_range", self.emit_range)
        self.emit_delay    = kwargs.get("emit_delay", self.emit_delay)
        self.gravity       = kwargs.get("gravity", self.gravity)
        self.speed         = kwargs.get("speed", self.speed)

        self.emit_life_a        = kwargs.get("emit_life_a", self.emit_life_a)
        self.emit_life_b        = kwargs.get("emit_life_a", self.emit_life_b)
        self.particle_life_a    = kwargs.get("particle_life_a", self.particle_life_a)
        self.particle_life_b    = kwargs.get("particle_life_a", self.particle_life_b)
        self.emit_rates_a = (
            kwargs.get("a_in_rate",  DEFAULT_EMIT_RATE),
            kwargs.get("a_out_rate", DEFAULT_EMIT_RATE),
            )
        self.emit_rates_b = (
            kwargs.get("b_in_rate",  DEFAULT_EMIT_RATE),
            kwargs.get("b_out_rate", DEFAULT_EMIT_RATE),
            )
        self.particle_widths_a = (
            kwargs.get("a_in_width",  DEFAULT_PARTICLE_WIDTH),
            kwargs.get("a_out_width", DEFAULT_PARTICLE_WIDTH),
            )
        self.particle_widths_b = (
            kwargs.get("b_in_width",  DEFAULT_PARTICLE_WIDTH),
            kwargs.get("b_out_width", DEFAULT_PARTICLE_WIDTH),
            )
        self.particle_colors_a = (
            kwargs.get("a_in_color",  DEFAULT_COLOR),
            kwargs.get("a_out_color", DEFAULT_COLOR),
            )
        self.particle_colors_b = (
            kwargs.get("b_in_color",  DEFAULT_COLOR),
            kwargs.get("b_out_color", DEFAULT_COLOR),
            )

        self._flags = {
            bool(kwargs.get("flags", {}).get(n))
            for n in (
                "gravity", "sort", "no_tex_rgb", "no_tex_a",
                "fb_add", "fb_mul", "no_z_test", "no_z_write"
                )
            }
        if "emit_dir" in kwargs:
            self._set_emit_dir(*kwargs["emit_dir"])

        self._instances = {}

    @property
    def enabled(self): return self._enabled
    @property
    def name(self): return self._name

    def _set_emit_dir(self, i, j, k):
        # TODO: calculate self.emit_dir_yp from i, j, k dir(look at collision code for example)
        pass

    def set_enabled(self, enabled=None):
        self._enabled = bool(not self.enabled if enabled is None else enabled)

    def create_instance(self, parent_nodepath):
        pass

if __name__ == "__main__":
    test_sys  = ParticleSystemFactory(
        a_in_color  = (0.0, 1.0, 1.0, 1.0),
        a_out_color = (1.0, 0.0, 1.0, 1.0),
        b_in_color  = (1.0, 1.0, 0.0, 1.0),
        b_out_color = (1.0, 1.0, 1.0, 0.0),
        a_in_width  = 2.0,
        a_out_width = 3.0,
        b_in_width  = 5.0,
        b_out_width = 1.0,
        )
    test_part = Particle()

    test_part._factory = test_sys
