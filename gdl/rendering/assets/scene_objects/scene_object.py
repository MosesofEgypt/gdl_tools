import panda3d
from ..model import Model
from ..collision import Collision
from ..particle_system import ParticleSystemFactory


class SceneObject:
    _name = ""

    _p3d_nodepath = None

    _node_models = ()
    _node_collision = ()
    _node_particle_systems = ()
    
    def __init__(self, **kwargs):
        self._name = kwargs.pop("name", self._name)

        p3d_node = kwargs.pop("p3d_node", None)
        if p3d_node is None:
            p3d_node = panda3d.core.ModelNode(self.name)

        self._p3d_nodepath = panda3d.core.NodePath(p3d_node)
        self._node_models = {}
        self._node_collision = {}
        self._node_particle_systems = {}

    @property
    def name(self): return self._name.upper()
    @property
    def p3d_node(self): return self._p3d_nodepath.node()
    @property
    def p3d_nodepath(self): return self._p3d_nodepath
    @property
    def node_models(self): return dict(self._node_models)
    @property
    def node_collision(self): return dict(self._node_collision)
    @property
    def node_particle_systems(self): return dict(self._node_particle_systems)

    def get_bound_texmods(self, p3d_nodepath=None):
        if p3d_nodepath is None:
            p3d_nodepath = self.p3d_nodepath

        tex_anims_by_id = {}
        for child in p3d_nodepath.findAllMatches('**'):
            node = child.node()
            texmod = node.getPythonTag("tex_anim")
            if texmod:
                tex_anims_by_id[id(texmod)] = texmod
        
        return tuple(tex_anims_by_id.values())

    def add_model(self, model):
        if not isinstance(model, Model):
            raise TypeError(f"model must be of type Model, not {type(model)}")

        self._node_models[model.name] = model

    def add_collision(self, collision):
        if not isinstance(collision, Collision):
            raise TypeError(f"collision must be of type Collision, not {type(collision)}")

        self._node_collision[collision.name] = collision

    def add_particle_system(self, particle_system):
        if not isinstance(particle_system, ParticleSystemFactory):
            raise TypeError(f"particle_system must be of type ParticleSystemFactory, not {type(particle_system)}")

        self._node_particle_systems[particle_system.name] = particle_system

    def set_visible(self, visible=None):
        visible = self.p3d_nodepath.isHidden() if visible is None else visible
        if visible:
            self.p3d_nodepath.show()
        else:
            self.p3d_nodepath.hide()
        return visible

    def set_collision_visible(self, visible=None):
        for coll in self.node_collision.values():
            visible = coll.p3d_nodepath.isHidden() if visible is None else visible

            if visible:
                coll.p3d_nodepath.show()
            else:
                coll.p3d_nodepath.hide()
        return visible

    def set_geometry_visible(self, visible=None):
        for model in self.node_models.values():
            for geometry in model.geometries:
                visible = geometry.p3d_nodepath.isHidden() if visible is None else visible

                if visible:
                    geometry.p3d_nodepath.show()
                else:
                    geometry.p3d_nodepath.hide()
        return visible

    def set_particles_visible(self, visible=None):
        for psys in self.node_particle_systems.values():
            visible = psys.enabled() if visible is None else visible
            psys.set_enabled(visible)
        return visible

    def optimize_node_graph(self):
        self.p3d_nodepath.flatten_strong()

        for model in self.node_models.values():
            for geometry in model.geometries:
                geometry.apply_shader()
