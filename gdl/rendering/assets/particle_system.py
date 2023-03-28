import math
import random
import traceback
import types

from panda3d.core import NodePath, PandaNode, \
     LVector3, LVector4, Point2, Point3,\
     OmniBoundingVolume, MeshDrawer, ColorBlendAttrib
from direct.particles.ParticleEffect import ParticleEffect
from . import shader
from . import constants as c
from ...compilation.g3d.serialization import vector_util
from .scene_objects import util

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
        self.reset(invert_age=kwargs.get("invert_age"))

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
        if self.factory.gravity:
            k -= t*(c.PARTICLE_GRAVITY * self.factory.gravity_mod)

        return (
            x + t*i,
            y + t*j,
            z + t*k
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
    def geom_data(self):
        return (
            LVector3(*self.pos),
            LVector4(0.0, 0.0, 1.0, 1.0),
            self.width/2,
            LVector4(*self.color),
            )

    def is_visible(self, cam):
        # TODO: optimize to not consider particle
        #       visible if it's too far from camera
        p1 = cam.getRelativePoint(render, self.pos)
        return cam.node().getLens().project(p1, Point2())

    def reset(self, invert_age=False):
        self._age = self.factory.max_particle_age if invert_age else 0.0

    def update(self, age_delta):
        self._age += age_delta


class ParticleSystem:
    _age            = 0.0
    _emit_counter   = 0.0
    _paused         = False
    _factory        = None
    _particles      = ()

    _p3d_nodepath       = None
    _root_p3d_nodepath  = None

    def __init__(self, **kwargs):
        self._paused    = kwargs.pop("paused", False)
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
    def emit_counter(self): return self._emit_counter
    @property
    def paused(self): return self._paused
    @property
    def p3d_node(self): return self._p3d_nodepath.node()
    @property
    def p3d_nodepath(self): return self._p3d_nodepath
    @property
    def root_p3d_node(self): return self._root_p3d_nodepath.node()
    @property
    def root_p3d_nodepath(self): return self._root_p3d_nodepath
    @property
    def particles(self): return self._particles
    @property
    def emit_velocity(self):
        speed   = self.factory.speed
        i, j, k = self.factory.random_emit_vector
        return i*speed, j*speed, k*speed

    @property
    def emit_position(self):
        x, y, z = self.p3d_nodepath.get_pos(self.root_p3d_nodepath) # world-relative position
        w, h, l = self.factory.emit_vol
        if w or h or l:
            x += (random.random() * w*2 - w)/2
            y += (random.random() * h*2 - h)/2
            z += (random.random() * l*2 - l)/2

        return x, y, z

    @property
    def emit_rate(self):
        age = self.age
        if age < 0:
            # invert for negative age to keep our calculations
            # in the non-negative realm and make life easier.
            age = 1 - age

        phase, point = get_phase_and_point_from_age(
            age, self.factory.emit_life_a, self.factory.emit_life_b
            )
        r0, r1 = self.factory.emit_rates_b if phase == 1 else self.factory.emit_rates_a
        particles_per_sec = r0 + (r1 - r0)*point
        return particles_per_sec

    def is_visible(self, cam, lens_bounds):
        if self.p3d_nodepath.isHidden():
            return False

        p1 = cam.getRelativePoint(self.p3d_nodepath, Point3(0.0, 0.0, 0.0))
        return cam.node().getLens().project(p1, Point2())

    def emit(self, invert_age=False):
        particle = Particle(
            system=self,
            init_pos=self.emit_position,
            init_vel=self.emit_velocity,
            invert_age=invert_age
            )
        self._particles += (particle, )

    def reset(self):
        self._age           = 0.0
        self._emit_counter  = 0.0
        self._particles     = ()

    def update(self, age_delta):
        if self.paused:
            return

        self._age           += age_delta
        self._emit_counter  += abs(age_delta * self.emit_rate)

        # TODO: figure out what to do for emit_delay

        # update age of particles(clean up any that are too old)
        particles_to_delete = set()
        particles = self._particles
        for i, particle in enumerate(particles):
            # NOTE: checking for age < 0 to allow rewinding
            #       system to previous times(i.e. play in reverse)
            if (particle.age < 0 or
                particle.age > self.factory.max_particle_age):
                particles_to_delete.add(i)
            else:
                particle.update(age_delta)

                # TODO: record bounding radius of furthest away particle + its width to
                #       determine the bounding radius of this system. use that for quick
                #       determination of whether this system is visible or not.

        if particles_to_delete:
            self._particles = tuple(
                particle for i, particle in enumerate(particles)
                if i not in particles_to_delete
                )

        # emit new particles if it's time to
        for i in range(int(math.ceil(self.emit_counter))):
            self._emit_counter -= 1
            self.emit(age_delta < 0)


class ParticleSystemFactory:
    _name       = ""
    _instances  = ()
    _enabled    = False
    _shader     = None
    gravity     = False

    _mesh_drawer = None
    
    _max_particles  = MAX_PARTICLES
    gravity_mod     = 0.0
    speed           = 0.0
    emit_delay      = 0.0

    emit_life_a     = 1.0
    emit_life_b     = 1.0
    particle_life_a = 1.0
    particle_life_b = 1.0

    _emit_dir_quat     = (0.0, 0.0, 0.0, 1.0)
    _emit_dir          = (0.0, 0.0, 1.0)
    _emit_range        = 0.0
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

        # setup the particles mesh
        self._mesh_drawer = MeshDrawer()
        self.p3d_nodepath.reparentTo(render_nodepath)
        self.p3d_nodepath.node().setBounds(OmniBoundingVolume())
        self.p3d_nodepath.node().setFinal(True)

        self._instances = []

        self._name         = kwargs.pop("name", self._name).upper().strip()
        self.gravity       = bool(kwargs.get("gravity", self.gravity))
        self.gravity_mod   = kwargs.get("gravity_mod", self.gravity_mod)
        self.speed         = kwargs.get("speed", self.speed)
        self.max_particles = kwargs.get("max_particles", self.max_particles)
        self.emit_range    = kwargs.get("emit_range", self.emit_range)
        self.emit_delay    = kwargs.get("emit_delay", self.emit_delay)
        self.emit_vol      = kwargs.get("emit_vol", self.emit_vol)

        self.emit_life_a        = kwargs.get("emit_life_a", self.emit_life_a)
        self.emit_life_b        = kwargs.get("emit_life_b", self.emit_life_b)
        self.particle_life_a    = kwargs.get("particle_life_a", self.particle_life_a)
        self.particle_life_b    = kwargs.get("particle_life_b", self.particle_life_b)
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

        self.emit_dir = kwargs.get("emit_dir", self.emit_dir)

        self._shader = shader.GeometryShader(
            diff_texture=kwargs.get("texture"),
            )
        self.shader.alpha       = True
        self.shader.no_z_write  = True
        self.shader.no_shading  = True
        self.shader.sort        = kwargs.get("sort")
        self.shader.fb_mul      = kwargs.get("fb_mul")
        self.shader.fb_add      = kwargs.get("fb_add")
        self.shader.forced_sort = c.DRAW_SORT_PARTICLES
        self.apply_shader()

    @property
    def max_particle_age(self):
        return self.particle_life_a + self.particle_life_b
    @property
    def max_particles(self):
        return self._max_particles
    @max_particles.setter
    def max_particles(self, new_val):
        self._max_particles = int(new_val)
        self._mesh_drawer.setBudget(2*self.max_particles)
    @property
    def emit_range(self): return self._emit_range
    @emit_range.setter
    def emit_range(self, new_val):
        self._emit_range = max(0.0, min(180.0, abs(new_val)))
        emit_angle = self.emit_range*(math.pi/180)
        emit_angle /= 2   # divide by 2 since emit_range is provided as the
        #                   the angle of the entire inner cone, but for our
        #                   calculations we want the half-cone angle
        if emit_angle <= 90:
            self._top_cap_radius    = math.sin(emit_angle)
            self._bottom_cap_radius = 1.0
        else:
            self._top_cap_radius    = 1.0
            self._bottom_cap_radius = math.sin(emit_angle-math.pi/2)
    @property
    def shader(self): return self._shader
    @property
    def p3d_node(self): return self.p3d_nodepath.node()
    @property
    def p3d_nodepath(self): return self.mesh_drawer.getRoot()
    @property
    def instances(self): return tuple(self._instances)
    @property
    def mesh_drawer(self): return self._mesh_drawer
    @property
    def enabled(self): return self._enabled
    @property
    def name(self): return self._name
    @property
    def emit_dir_quat(self): return self._emit_dir_quat
    @property
    def emit_dir(self): return self._emit_dir
    @emit_dir.setter
    def emit_dir(self, emit_dir):
        # normalize the supplied vector and convert to a rotation quaternion
        i, j, k = emit_dir
        length = i**2 + j**2 + k**2
        if length:
            length = math.sqrt(length)
        else:
            i, j, k, length = 0.0, 0.0, 1.0, 1.0

        i, j, k = emit_dir = (i/length, j/length, k/length)
        r, y = math.acos(max(-1.0, min(1.0, k))), math.atan2(i, j)

        qw, qi, qj, qk = util.gdl_euler_to_quaternion(y, 0, r)
        self._emit_dir_quat = (qi, qj, qk, qw)
        self._emit_dir = emit_dir
    @property
    def random_emit_vector(self):
        i, j, k = 0.0, 0.0, 1.0
        if self._top_cap_radius:
            # NOTE: we're using the rejection method to select a random
            #       point within the spawn cone. We calculate the radius
            #       of the top cap of the cone(spawnable area), and the
            #       radius of the bottom cap of the cone(non-spawnable).
            #       the bottom radius is only not 1.0 when the cone is
            #       inverted, extending around to the bottom of the sphere.
            #       if the point we select is inside the top cap radius
            #       and outside the bottom cap radius, we can choose to
            #       spawn in either the top or bottom half. If the point
            #       is inside the top cap radius and inside the bottom
            #       cap radius, we can spawn in the top half. otherwise,
            #       we have to randomly select a different point to try.
            radius_scale = 2*self._top_cap_radius
            for _ in range(10):
                x = (random.random()-0.5)*radius_scale
                y = (random.random()-0.5)*radius_scale
                radius = math.sqrt(x**2 + y**2)
                if radius > self._top_cap_radius:
                    # not inside bounds. try again
                    continue

                i, j, k = x, y, math.sqrt(1.0 - radius**2)
                if radius >= self._bottom_cap_radius and random.random() >= 0.5:
                    k = -k
                break

        i, j, k = vector_util.rotate_vector_by_quaternion(
            (i, j, k), self.emit_dir_quat
            )
        return i, j, k

    def clear_shader(self):
        self.shader.clear(self.p3d_nodepath)

    def apply_shader(self):
        self.shader.apply(self.p3d_nodepath)

    def set_enabled(self, enabled=None):
        self._enabled = bool(not self.enabled if enabled is None else enabled)
        if self.enabled:
            self.p3d_nodepath.show()
        else:
            self.p3d_nodepath.hide()

    def update(self, age_delta, cam=None):
        if cam is None: cam = base.cam

        if not self.enabled:
            return

        lens_bounds = cam.node().getLens().makeBounds()
        for psys in self._instances:
            if not psys.is_visible(cam, lens_bounds):
                continue
            psys.update(age_delta)

    def render(self, root=None, cam=None):
        if root is None: root = render
        if cam is None:  cam  = base.cam

        self.mesh_drawer.begin(cam, root)
        budget = self.mesh_drawer.getBudget() // 2

        lens_bounds = cam.node().getLens().makeBounds()
        for psys in self.instances:
            if budget <= 0 or not self.enabled:
                break
            elif not psys.is_visible(cam, lens_bounds):
                continue

            for particle in psys.particles:
                if budget <= 0:
                    break
                elif particle.is_visible(cam):
                    self.mesh_drawer.billboard(*particle.geom_data)
                    budget -= 1

        self.mesh_drawer.end()

    def create_instance(self, nodepath):
        psys = ParticleSystem(factory=self, p3d_node=nodepath.node())
        self._instances.append(psys)
