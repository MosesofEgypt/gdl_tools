import hashlib
import os

from math import sqrt

from .animation_cache import AnimationCache
from . import constants as c


class G3DAnimation():

    def __init__(self):
        self.clear()

    def clear(self):
        pass

    def import_g3d(self, animation_cache):
        self.clear()
        raise NotImplementedError()

    def compile_g3d(self):
        animation_cache = AnimationCache()
        raise NotImplementedError()

        return animation_cache
