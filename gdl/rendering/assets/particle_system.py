import math
import random
import traceback
import types

from panda3d.core import NodePath, PandaNode, LVector3, LVector4,\
     BoundingSphere, MeshDrawer
from direct.particles.ParticleEffect import ParticleEffect
from .texture import Texture

MIN_PHASE_PERIOD    = 0.00001
MAX_PARTICLES       = 1000
FLOAT_INFINITY      = float("inf") 

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
        return 1, (point - period_a) / period_b
    return 0, point / max(MIN_PHASE_PERIOD, period_a)


class Particle:
    _age = 0.0
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
        self.reset()

    @property
    def age(self): return self._age
    @property
    def system(self): return self._system
    @property
    def factory(self): return self.system.factory

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
    def color(self):
        phase, point = get_phase_and_point_from_age(
            self.age, self.factory.particle_life_a, self.factory.particle_life_b, clamp=True
            )
        colors = (
            self.factory.particle_colors_b if phase == 1 else
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
            self.factory.particle_widths_b if phase == 1 else
            self.factory.particle_widths_a
            )
        return w0 + (w1 - w0)*point

    @property
    def tex_coords(self):
        # TODO: look into whether or not particle textures can uv animate as well
        return 0.0, 0.0, 1.0, 1.0

    @property
    def geom_data(self):
        return (
            LVector3(*self.pos),
            LVector4(*self.tex_coords),
            self.width,
            LVector4(*self.color),
            )

    def reset(self):
        self._age = 0.0

    def update(self, age_delta):
        self._age += age_delta


class ParticleSystem:
    _age        = 0
    _emit_timer = 0
    _paused     = False

    _factory        = None
    _particles      = ()
    _p3d_nodepath   = None
    _root_nodepath  = None

    def __init__(self, **kwargs):
        self._paused    = kwargs.pop("paused", True)
        self._factory   = kwargs.pop("factory", None)
        p3d_node        = kwargs.pop("p3d_node", None)
        root_p3d_node   = kwargs.pop("root_p3d_node", render.node())

        if not isinstance(root_p3d_node, PandaNode):
            raise TypeError(
                f"root_p3d_node must be of type panda3d.core.PandaNode, not {type(root_p3d_node)}"
                )
        if not isinstance(p3d_node, PandaNode):
            raise TypeError(
                f"p3d_node must be of type panda3d.core.PandaNode, not {type(p3d_node)}"
                )
        elif not isinstance(self._factory, ParticleSystemFactory):
            raise TypeError(
                f"factory must be of type ParticleSystemFactory, not {type(self._factory)}"
                )

        self._p3d_nodepath = NodePath(p3d_node)
        self._root_p3d_nodepath = NodePath(root_p3d_node)
        self.reset()

    @property
    def factory(self): return self._factory
    @property
    def age(self): return self._age
    @property
    def emit_timer(self): return self._emit_timer
    @property
    def paused(self): return self._paused
    @property
    def p3d_node(self): return self._p3d_nodepath.node()
    @property
    def p3d_nodepath(self): return self._p3d_nodepath
    @property
    def particles(self): return tuple(self._particles.values())

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
        x, y, z = self.p3d_node.get_pos(self._root_p3d_nodepath) # world-relative position
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
        particles_per_sec = max(r0 + (r1 - r0)*point)
        return 1/particles_per_sec if particles_per_sec else FLOAT_INFINITY

    def is_visible(self, cam=None):
        if cam is None:
            cam = camera

        if self.p3d_nodepath.isHidden():
            return False

        # TODO: figure out how to determine if particle system
        #       is visible to camera(need to do it quickly too)

        return True

    def emit(self):
        particle = Particle(
            system=self,
            init_pos=self.emit_position,
            init_vel=self.emit_velocity,
            )
        self._particles[id(particle)] = particle

    def reset(self):
        self._age       = 0.0
        self._particles = {}

    def update(self, age_delta):
        if self.paused:
            return

        # NOTE: only update system if it's visible(not sure how this is determined exactly)

        # update age of particles(clean up any that are too old)
        for pid in tuple(self._particles):
            particle = self._particles[pid]
            if particle.age >= self.system.max_particle_age:
                del self._particles[pid]
            else:
                particle.update(age_delta)

        self._age        += age_delta
        self._emit_timer += age_delta

        # emit new particles if it's time to
        emit_rate = self.emit_rate
        for i in range(int(self.emit_timer / emit_rate)):
            self._emit_timer -= emit_rate
            self.emit()


class ParticleSystemFactory:
    _name       = ""
    _instances  = ()
    _flags      = ()
    _enabled    = False

    _mesh_drawer = None
    
    _max_particles  = MAX_PARTICLES
    _texture        = None
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
        render_nodepath  = kwargs.pop("render_nodepath", render)

        self._mesh_drawer = MeshDrawer()
        mesh_nodepath = self._mesh_drawer.getRoot()
        mesh_nodepath.reparentTo(render_nodepath)

        self._instances = []

        self._name         = kwargs.pop("name", self._name).upper().strip()
        self._texture      = kwargs.get("texture", self.texture)
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

        mesh_nodepath.setDepthWrite(False)
        mesh_nodepath.setTransparency(True)
        #mesh_nodepath.setTwoSided(True)

        # setup bounding sphere for particles mesh
        mesh_nodepath.node().setBounds(BoundingSphere((0, 0, 0), 1000000))
        mesh_nodepath.node().setFinal(True)

    @property
    def enabled(self): return self._enabled
    @property
    def instances(self): return tuple(self._instances)
    @property
    def max_particle_age(self): return self.particle_life_a + self.particle_life_b
    @property
    def max_particles(self): return self._max_particles
    @max_particles.setter
    def max_particles(self, new_val):
        self._max_particles = int(new_val)
        self._mesh_drawer.setBudget(2*self.max_particles)
    @property
    def mesh_drawer(self): return self._mesh_drawer
    @property
    def name(self): return self._name
    @property
    def texture(self): return self._texture
    @texture.setter
    def texture(self, texture):
        if not isinstance(texture, (Texture, type(None))):
            raise TypeError(
                f"texture must be of type texture.Texture, not {type(texture)}"
                )
        self._texture = texture
        if getattr(self.texture, "p3d_texture", None):
            self._mesh_drawer.getRoot().setTexture(self.texture.p3d_texture)

    def _set_emit_dir(self, i, j, k):
        # TODO: calculate self.emit_dir_yp from i, j, k dir(look at collision code for example)
        pass

    def update(self, age_delta, cam=None):
        if cam is None: cam = base.cam

        if not self.enabled:
            return

        for psys in self._instances:
            if psys.is_visible(cam):
                psys.update(age_delta)

    def render(self, root=None, cam=None):
        if root is None: root = render
        if cam is None:  cam  = base.cam

        self.mesh_drawer.begin(cam, root)

        for psys in self.instances:
            if psys.is_visible(cam):
                for particle in psys.particles:
                    self.mesh_drawer.billboard(*particle.geom_data)

        self.mesh_drawer.end()

    def set_enabled(self, enabled=None):
        self._enabled = bool(not self.enabled if enabled is None else enabled)

    def create_instance(self, nodepath):
        psys = ParticleSystem(factory=self, p3d_node=nodepath.node())
        self._instances.append(psys)
