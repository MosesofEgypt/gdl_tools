import math
import random
import traceback
import types

from panda3d.core import NodePath, PandaNode,\
     LVector3, LVector4, Point2, Point3, ColorBlendAttrib,\
     OmniBoundingVolume, BoundingSphere, MeshDrawer
from direct.particles.ParticleEffect import ParticleEffect
from . import shader
from . import constants as c
from ...compilation.g3d.serialization import vector_util
from .scene_objects import util

DEG_TO_RAD          = math.pi/180
SPAWN_PATCH_CUTOFF  = math.cos(30*DEG_TO_RAD) # patch will cover last 30 degrees
SPAWN_PATCH_MAGIC   = 0.367879442  # used to shift and scale range for logrithm input
SPAWN_REJECT_MAX    = 5 # max number of times to reject a particle before using default vector
WIDTH_TO_RADIUS     = math.sqrt(2)/2
MIN_PHASE_PERIOD    = 0.00001
MAX_PARTICLES       = 500

DEFAULT_SYSTEM_RADIUS   = 1.0
DEFAULT_EMITTER_LIFE    = 1.0
DEFAULT_PARTICLE_LIFE   = 1.0
DEFAULT_PARTICLE_WIDTH  = 1.0
DEFAULT_EMIT_RATE       = 30
DEFAULT_COLOR           = (1.0, 1.0, 1.0, 1.0)
MIN_PARTICLE_SIZE_SQ    = (1/128)**2


def get_phase_and_point_from_age_cycle(age, *periods):
    total_period = sum(periods)
    total_period = MIN_PHASE_PERIOD if total_period < MIN_PHASE_PERIOD else total_period
    point        = age - int(age / total_period) * total_period

    for i, period in enumerate(periods):
        period = MIN_PHASE_PERIOD if period < MIN_PHASE_PERIOD else period
        if point <= period and period:
            return i, point / period
        point -= period

    return 0, 0  # default case that should never be hit


def get_phase_and_point_from_age_clamp(age, *periods):
    total_period = sum(periods)
    total_period = MIN_PHASE_PERIOD if total_period < MIN_PHASE_PERIOD else total_period
    point        = 0 if age < 0 else (total_period if age > total_period else age)

    for i, period in enumerate(periods):
        period = MIN_PHASE_PERIOD if period < MIN_PHASE_PERIOD else period
        if point <= period and period:
            return i, point / period
        point -= period

    return 0, 0  # default case that should never be hit


class Particle:
    system = None

    age      = 0.0
    init_pos = (0.0, 0.0, 0.0)
    init_vel = (0.0, 0.0, 0.0)

    _cached_pos_age   = None
    _cached_color_age = None
    _cached_width_age = None
    _cached_pos   = (0.0, 0.0, 0.0)
    _cached_color = (1.0, 1.0, 1.0, 1.0)
    _cached_width = 0.0

    def __init__(self, **kwargs):
        self.system   = kwargs.pop("system", self.system)
        self.init_pos = kwargs.pop("init_pos", self.init_pos)
        self.init_vel = kwargs.pop("init_vel", self.init_vel)

        if not isinstance(self.system, ParticleSystem):
            raise TypeError(
                f"system must be of type ParticleSystem, not {type(self.system)}"
                )
        self.reset(invert_age=kwargs.get("invert_age"))

    @property
    def pos(self):
        if self._cached_pos_age != self.age:
            #pos = self.init_pos
            #vel = self.init_vel
            x, y, z = self.init_pos
            i, j, k = self.init_vel
            t = self.age
            factory = self.system.factory
            if factory.gravity:
                k -= t * c.PARTICLE_GRAVITY * factory.gravity_mod

            self._cached_pos = (
                x + t*i,
                y + t*j,
                z + t*k
                )
            self._cached_pos_age = self.age
        return self._cached_pos

    @property
    def color(self):
        if self._cached_color_age != self.age:
            factory = self.system.factory
            phase, point = get_phase_and_point_from_age_clamp(
                self.age, factory.particle_life_a, factory.particle_life_b
                )
            colors = (
                factory.particle_colors_b if phase == 1 else
                factory.particle_colors_a
                )
            r0, g0, b0, a0 = colors[0]
            r1, g1, b1, a1 = colors[1]

            self._cached_color = (
                r0 + (r1 - r0)*point,
                g0 + (g1 - g0)*point,
                b0 + (b1 - b0)*point,
                a0 + (a1 - a0)*point,
                )
            self._cached_color_age = self.age
        return self._cached_color

    @property
    def width(self):
        if self._cached_width_age != self.age:
            factory = self.system.factory
            phase, point = get_phase_and_point_from_age_clamp(
                self.age, factory.particle_life_a, factory.particle_life_b
                )
            w0, w1 = (
                factory.particle_widths_b if phase == 1 else
                factory.particle_widths_a
                )
            self._cached_width = w0 + (w1 - w0)*point
            self._cached_width_age = self.age
        return self._cached_width

    @property
    def geom_data(self):
        return (
            LVector3(*self.pos),
            LVector4(0.0, 0.0, 1.0, 1.0),
            self.width/2,
            LVector4(*self.color),
            )

    def is_visible(self, cam, lens_bounds, render_p3d_nodepath=None):
        if render_p3d_nodepath is None:
            render_p3d_nodepath = render

        pos = cam.getRelativePoint(render_p3d_nodepath, self.pos)
        # if the particle is too small from this distance, dont render it
        part_dist_sq = pos.x**2 + pos.y**2 + pos.z**2
        part_size_sq = (self.width**2) / part_dist_sq
        if part_size_sq < MIN_PARTICLE_SIZE_SQ:
            return False

        lens = cam.node().getLens()

        # if the center point is in the camera view, it's visible
        if lens.project(pos, Point2()):
            return True

        part_bounds = BoundingSphere(pos, self.width*WIDTH_TO_RADIUS)
        # return whether the particle bounds is inside the camera frustum
        return lens_bounds.contains(part_bounds)

    def reset(self, invert_age=False):
        self.age = self.system.factory.max_particle_age if invert_age else 0.0

    def update(self, age_delta):
        self.age += age_delta


class ParticleSystem:
    _age             = 0.0
    _emit_counter    = 0.0
    _bounding_radius = 1.0
    _paused          = False
    _particles       = ()

    factory          = None

    _p3d_nodepath           = None
    _root_p3d_nodepath      = None

    def __init__(self, **kwargs):
        self._paused    = kwargs.pop("paused", False)
        self.factory    = kwargs.pop("factory", self.factory)
        p3d_node        = kwargs.pop("p3d_node", None)
        root_p3d_node   = kwargs.pop("root_p3d_node", render.node())

        if not isinstance(root_p3d_node, PandaNode):
            raise TypeError(
                f"root_p3d_node must be of type panda3d.core.PandaNode, not {type(root_p3d_node)}"
                )
        elif not isinstance(p3d_node, PandaNode):
            raise TypeError(
                f"p3d_node must be of type panda3d.core.PandaNode, not {type(p3d_node)}"
                )
        elif not isinstance(self.factory, ParticleSystemFactory):
            raise TypeError(
                f"factory must be of type ParticleSystemFactory, not {type(self.factory)}"
                )

        self._p3d_nodepath = NodePath(p3d_node)
        self._root_p3d_nodepath = NodePath(root_p3d_node)
        self._bounding_radius = DEFAULT_SYSTEM_RADIUS
        self.reset()

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
        vector  = self.factory.random_emit_vector
        return vector[0]*speed, vector[1]*speed, vector[2]*speed
    @property
    def pos(self):
        # world-relative position
        return tuple(self.p3d_nodepath.get_pos(self.root_p3d_nodepath))

    @property
    def emit_position(self):
        x, y, z = self.pos
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
            # negate for negative age to keep our calculations
            # in the non-negative realm and make life easier.
            age = -age

        phase, point = get_phase_and_point_from_age_cycle(
            age, self.factory.emit_delay, self.factory.emit_life_a, self.factory.emit_life_b
            )
        if phase == 0:
            # dont emit anything during delay period
            return 0

        r0, r1 = self.factory.emit_rates_b if phase == 2 else self.factory.emit_rates_a
        particles_per_sec = r0 + (r1 - r0)*point
        return particles_per_sec

    def is_visible(self, cam, lens_bounds):
        if (self.p3d_nodepath.isHidden() or not
            self.root_p3d_nodepath.isAncestorOf(self.p3d_nodepath)):
            return False

        bounding_volume = BoundingSphere()
        bounding_volume.setRadius(self._bounding_radius)
        bounding_volume.xform(self.p3d_nodepath.getMat(cam))

        return lens_bounds.contains(bounding_volume)

    def emit(self, count=1, invert_age=False):
        self._particles += tuple(
            Particle(
                system=self,
                init_pos=self.emit_position,
                init_vel=self.emit_velocity,
                invert_age=invert_age
                )
            for i in range(count)
            )

    def reset(self):
        self._age           = 0.0
        self._emit_counter  = 0.0
        self._particles     = ()

    def update(self, age_delta):
        if self.paused:
            return

        self._age           += age_delta
        self._emit_counter  += abs(age_delta * self.emit_rate)

        # update age of particles(clean up any that are too old)
        retained_particles = ()
        radius_sq = DEFAULT_SYSTEM_RADIUS**2
        x0, y0, z0 = self.pos
        for particle in self.particles:
            # NOTE: checking for age < 0 to allow rewinding
            #       system to previous times(i.e. play in reverse)
            if (particle.age >= 0 and
                particle.age <= self.factory.max_particle_age
                ):
                particle.update(age_delta)
                retained_particles += (particle, )

                x1, y1, z1 = particle.pos
                new_radius_sq = (
                    (x1-x0)**2 + (y1-y0)**2 + (z1-z0)**2 +
                    (particle.width/2)**2
                    )

                # record bounding radius of furthest away particle + its
                # width to determine the bounding radius of this system.
                # NOTE: adding width this way will produce a larger bounding
                #       radius, than actual, but it's close enough to be fine.
                radius_sq = radius_sq if new_radius_sq <= radius_sq else new_radius_sq

        self._particles = retained_particles
        self._bounding_radius = math.sqrt(radius_sq)

        # emit new particles if it's time to
        if self._emit_counter > 0:
            emit_count = int(math.ceil(self.emit_counter))
            self.emit(emit_count, age_delta < 0)
            self._emit_counter -= emit_count


class ParticleSystemFactory:
    _name       = ""
    _instances  = ()
    _enabled    = False
    _shader     = None
    gravity     = False

    _mesh_drawer = None
    
    _max_particles  = MAX_PARTICLES
    _spawn_patch_cutoff = SPAWN_PATCH_CUTOFF
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
        self.shader.color_scale = 2
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
        self._emit_range = max(0.0, min(360.0, abs(new_val)))
        emit_angle = self.emit_range / 2
        # NOTE: we divide by 2 since emit_range is provided as the angle of
        #       the entire inner cone, but our calculations want half-angles
        if emit_angle <= 90:
            self._top_cap_radius    = math.sin(emit_angle*DEG_TO_RAD)
            self._bottom_cap_radius = 1.0
        else:
            self._top_cap_radius    = 1.0
            self._bottom_cap_radius = math.sin((180-emit_angle)*DEG_TO_RAD)
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
            # NOTE: to fix a weakness of the rejection method and cover
            #       bald spots it generates on the outside ring of the
            #       sphere, we take the rejections as a chance to generate
            #       a coordinate a certain minimum distance from the edge.
            #       we use a logrithmic scale to weight the positions
            #       towards the edge and away from the center. we do this
            #       to try to smooth the transition from bald to patched.
            radius_scale = 2*self._top_cap_radius
            convert_period = self._top_cap_radius - self._spawn_patch_cutoff
            spawn_tries = SPAWN_REJECT_MAX
            while spawn_tries > 0:
                spawn_tries -= 1

                x = (random.random()-0.5)*radius_scale
                y = (random.random()-0.5)*radius_scale
                radius_sq = x**2 + y**2

                if (radius_sq > self._top_cap_radius**2 and
                    self._spawn_patch_cutoff <= self._top_cap_radius):
                    # not inside bounds. generate coordinates from edge and try those
                    angle = math.pi*random.random()*2
                    radius_scale = 1 - math.log(
                        1/(random.random()*(1 - SPAWN_PATCH_MAGIC)+SPAWN_PATCH_MAGIC)
                        )**3

                    radius = self._spawn_patch_cutoff + convert_period*radius_scale
                    x = math.sin(angle) * radius
                    y = math.cos(angle) * radius
                    radius_sq = radius**2

                if radius_sq > self._top_cap_radius**2:
                    # not inside bounds. try again
                    continue

                i, j, k = x, y, math.sqrt(1.0 - radius_sq)
                if radius_sq >= self._bottom_cap_radius**2 and random.random() >= 0.5:
                    k = -k
                break

        emit_dir_quat = self.emit_dir_quat
        if emit_dir_quat != (0.0, 0.0, 0.0, 1.0):
            i, j, k = vector_util.rotate_vector_by_quaternion(
                (i, j, k), emit_dir_quat
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
                elif particle.is_visible(cam, lens_bounds, psys.root_p3d_nodepath):
                    self.mesh_drawer.billboard(*particle.geom_data)
                    budget -= 1

        self.mesh_drawer.end()

    def create_instance(self, nodepath):
        psys = ParticleSystem(factory=self, p3d_node=nodepath.node())
        self._instances.append(psys)
