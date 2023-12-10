import hashlib
import os

from .animation_cache import AnimationCache, AnimationCacheNode,\
     NODE_TYPES
from . import animation_jmm, constants as c


class G3DAnimationNode(AnimationCacheNode):
    pass


class G3DAnimation():
    name            = ""
    prefix          = ""
    frame_rate      = 30
    frame_count     = 0

    comp_angles     = ()
    comp_positions  = ()
    comp_scales     = ()
    nodes           = ()

    def __init__(self):
        self.clear()

    def clear(self):
        self.name           = ""
        self.prefix         = ""
        self.frame_rate     = 0
        self.frame_count    = 0
        self.nodes          = ()
        self.comp_angles    = ()
        self.comp_positions = ()
        self.comp_scales    = ()

    def import_g3d(self, animation_cache):
        self.clear()

        # NOTE: for now, the G3DAnimation and G3DAnimationNode are basically
        #       just copies of the AnimationCache and AnimationCacheNode.
        #       eventually this will change when compilation, exporting, and
        #       importing different formats is implemented. this works for now

        self.name           = animation_cache.name
        self.prefix         = animation_cache.prefix
        self.frame_rate     = animation_cache.frame_rate
        self.frame_count    = animation_cache.frame_count

        self.comp_angles    = tuple(animation_cache.comp_angles)
        self.comp_positions = tuple(animation_cache.comp_positions)
        self.comp_scales    = tuple(animation_cache.comp_scales)

        for cache_node in animation_cache.nodes:
            g3d_node = G3DAnimationNode()
            self.nodes += (g3d_node, )

            g3d_node.name           = cache_node.name
            g3d_node.parent         = cache_node.parent
            g3d_node.type_id        = cache_node.type_id
            g3d_node.flags          = cache_node.flags
            g3d_node.init_pos       = cache_node.init_pos
            g3d_node.frame_flags    = cache_node.frame_flags
            g3d_node.initial_frame  = cache_node.initial_frame
            g3d_node.frame_data     = cache_node.frame_data

    def compile_g3d(self, cache_type):
        animation_cache = AnimationCache()
        raise NotImplementedError()

        return animation_cache

    def import_jmm(self, input_filepath):
        with open(input_filepath, "r", newline="\n") as f:
            jma_anim = animation_jmm.halo_anim.read_jma(f.read())

        animation_jmm.import_jmm_to_g3d(jma_anim, self)

    def export_jmm(self, output_filepath):
        jma_anim = animation_jmm.export_g3d_to_jmm(self)

        animation_jmm.halo_anim.write_jma(output_filepath, jma_anim)
