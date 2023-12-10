import hashlib
import os

from .animation_cache import AnimationCache, AnimationCacheNode,\
     NODE_TYPES
from . import constants as c


class G3DAnimationNode(AnimationCacheNode):
    pass


class G3DAnimation():
    name        = ""
    nodes       = ()
    frame_count = 0

    def __init__(self):
        self.clear()

    def clear(self):
        self.name           = ""
        self.nodes          = {}
        self.frame_count    = 0

    def import_g3d(self, animation_cache):
        self.clear()
        #raise NotImplementedError()

    def compile_g3d(self, cache_type):
        animation_cache = AnimationCache()
        #raise NotImplementedError()

        return animation_cache

    def import_jmm(self, input_filepath):
        raise NotImplementedError()

    def export_jmm(self, output_filepath):
        raise NotImplementedError()
