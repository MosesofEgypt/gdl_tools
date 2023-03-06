import traceback
import types

from copy import deepcopy
from panda3d.core import NodePath, PandaNode

from direct.particles.ParticleEffect import ParticleEffect


class ParticleSystem:
    _name = ""
    _instances = ()
    _config_loader = None

    _enabled = False

    def __init__(self, **kwargs):
        self._name          = kwargs.pop("name", self._name).upper().strip()
        self._config_loader = kwargs.pop("config_loader", None)

        if not isinstance(self.config_loader, types.FunctionType):
            raise TypeError(
                f"config_loader must be of type {types.FunctionType}, not {type(self.config_loader)}"
                )

        self._instances = {}

    @property
    def enabled(self): return self._enabled
    @property
    def name(self): return self._name
    @property
    def config_loader(self): return self._config_loader

    def set_enabled(self, enabled=None):
        if enabled is None:
            self._enabled = not self.enabled
        else:
            self._enabled = bool(enabled)

        for effect_dict in self._instances.values():
            peffect = effect_dict["peffect"]
            parent  = effect_dict["parent"]
            if self.enabled and not peffect.isEnabled():
                peffect.reparentTo(parent)
                peffect.renderParent = parent
                peffect.enable()
            elif peffect.isEnabled():
                peffect.disable()

    def create_instance(self, parent):
        name = parent.name
        if name in self._instances:
            raise ValueError(f"Instance with name '{name}' already exists.")

        peffect = ParticleEffect(name)
        self._instances[name] = dict(
            peffect = peffect,
            parent  = parent,
            )
        try:
            self.config_loader(peffect)
        except Exception:
            print(traceback.format_exc())
            return

        peffect.reparentTo(parent)
        peffect.renderParent = parent

        if self.enabled:
            peffect.enable()
