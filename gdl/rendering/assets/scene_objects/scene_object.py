import panda3d
from ..model import Model
from ..collision import Collision
from ..particle_system import ParticleSystem


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
    def node_models(self): return {k: dict(v) for k, v in self._node_models.items()}
    @property
    def node_collision(self): return {k: dict(v) for k, v in self._node_collision.items()}
    @property
    def node_particle_systems(self): return {k: dict(v) for k, v in self._node_particle_systems.items()}

    def add_model(self, model):
        if not isinstance(model, Model):
            raise TypeError(f"model must be of type Model, not {type(model)}")

        # TODO: simplify this(multiple models per name not possible?)
        node_collection = self._node_models.setdefault(model.name, dict())
        node_collection[model.name] = model

    def add_collision(self, collision):
        if not isinstance(collision, Collision):
            raise TypeError(f"collision must be of type Collision, not {type(collision)}")

        # TODO: simplify this(multiple collision per name not possible?)
        node_collection = self._node_collision.setdefault(collision.name, dict())
        node_collection[collision.name] = collision

    def add_particle_system(self, particle_system):
        if not isinstance(particle_system, ParticleSystem):
            raise TypeError(f"particle_system must be of type ParticleSystem, not {type(particle_system)}")

        # TODO: simplify this(multiple collision per name not possible?)
        node_collection = self._node_particle_systems.setdefault(particle_system.name, dict())
        node_collection[particle_system.name] = particle_system

    def set_collision_visible(self, visible=None):
        for group in self.node_collision.values():
            for coll in group.values():
                visible = coll.p3d_nodepath.isHidden() if visible is None else visible

                if visible:
                    coll.p3d_nodepath.show()
                else:
                    coll.p3d_nodepath.hide()
        return visible

    def set_geometry_visible(self, visible=None):
        for group in self.node_models.values():
            for model in group.values():
                for geometry in model.geometries:
                    visible = geometry.p3d_nodepath.isHidden() if visible is None else visible

                    if visible:
                        geometry.p3d_nodepath.show()
                    else:
                        geometry.p3d_nodepath.hide()
        return visible
