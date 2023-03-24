import traceback
import types

from copy import deepcopy
from panda3d.core import NodePath, PandaNode

from direct.particles.ParticleEffect import ParticleEffect


MASTER_PEFFECT_NAME = "__MASTER_PEFFECT_NAME"


class ParticleSystem:
    _name = ""
    _instances = ()
    _config_loader = None

    _enabled = False
    _unique_instances = False

    def __init__(self, **kwargs):
        self._name              = kwargs.pop("name", self._name).upper().strip()
        self._config_loader     = kwargs.pop("config_loader", None)
        self._unique_instances  = bool(kwargs.pop("unique_instances", False))

        if not isinstance(self.config_loader, types.FunctionType):
            raise TypeError(
                f"config_loader must be of type {types.FunctionType}, not {type(self.config_loader)}"
                )

        self._instances = {}

    @property
    def enabled(self): return self._enabled
    @property
    def unique_instances(self): return self._unique_instances
    @property
    def name(self): return self._name
    @property
    def config_loader(self): return self._config_loader

    def update(self, frame_time):
        pass

    def set_enabled(self, enabled=None):
        if enabled is None:
            self._enabled = not self.enabled
        else:
            self._enabled = bool(enabled)

        for name, effect_dict in self._instances.items():
            peffect = effect_dict["peffect"]
            parent  = effect_dict["parent"]
            if self.enabled and not peffect.isEnabled():
                peffect.reparentTo(parent)
                peffect.renderParent = parent
                peffect.enable()
            elif peffect.isEnabled():
                peffect.disable()

    def _create_instance(self, parent_nodepath, unique=True):
        if unique:
            name = parent_nodepath.name
            if name in self._instances:
                raise ValueError(f"Instance with name '{name}' already exists.")

            peffect = ParticleEffect(name)
            self._instances[name] = dict(
                peffect = peffect,
                parent  = parent_nodepath,
                )

            peffect.reparentTo(parent_nodepath)
            peffect.renderParent = parent_nodepath
            try:
                self.config_loader(peffect)
            except Exception:
                print(traceback.format_exc())
                return

            if self.enabled:
                peffect.enable()
        else:
            self._instances[MASTER_PEFFECT_NAME]["parent"].instanceTo(parent_nodepath)

    def create_instance(self, parent_nodepath):
        if not self.unique_instances and MASTER_PEFFECT_NAME not in self._instances:
            master_nodepath = NodePath(PandaNode(MASTER_PEFFECT_NAME))
            self._create_instance(master_nodepath, unique=True)

        self._create_instance(parent_nodepath, unique=self.unique_instances)
