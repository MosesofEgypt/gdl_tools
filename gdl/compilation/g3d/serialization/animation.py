import hashlib
import os

from .animation_cache import AnimationCache, AnimationCacheNode,\
     NODE_TYPES
from . import halo_jm, animation_util, constants as c


class G3DAnimationNode(AnimationCacheNode):
    keyframe_indices = ()

    def generate_keyframe_indices(self, frame_count):
        keyframe_indices = [[0, 0] for i in range(frame_count)]
        f_0  = f  = 0
        kf_0 = kf = 0
        for i, flags in enumerate(self.frame_flags):
            for j in range(8):
                f = i*8 + j
                if f >= frame_count:
                    break
                elif flags&1:
                    keyframe_indices[f] = [kf, 1.0]

                    f_0, kf_0 = f, kf
                    kf += 1

                flags >>= 1

        #print("Keyframes:", self.keyframe_indices)
        #print("Flags:", self.frame_flags)
        self.keyframe_indices = tuple(map(tuple, keyframe_indices))

    def decompress_frame_data(self, comp_angles, comp_positions, comp_scales):
        off         = 0
        stride      = self.frame_size
        frame_data  = list(self.frame_data)
        #i = 0
        for flag, values in (
            (self.rot_x,   comp_angles),
            (self.rot_y,   comp_angles),
            (self.rot_z,   comp_angles),
            (self.pos_x,   comp_positions),
            (self.pos_y,   comp_positions),
            (self.pos_z,   comp_positions),
            (self.scale_x, comp_scales),
            (self.scale_y, comp_scales),
            (self.scale_z, comp_scales),
            ):
            if flag:
                frame_data[off::stride] = animation_util.comp_frame_data_to_uncomp(
                    self.frame_data[off::stride], values
                    )
                off += 1
                #print("xyzhprXYZ"[i], initial_val, frame_data[off::stride])
            #i += 1

        self.compressed     = False
        self.frame_data     = self.initial_frame + tuple(frame_data)
        if self.initial_frame_only:
            # TODO: figure out wtf is going on here
            self.frame_flags = (
                [self.frame_flags[0] | 1, *self.frame_flags[1:]]
                if self.frame_flags else
                [1]
                )
            self.initial_frame_only = False

        self.initial_frame  = ()

    def compress_frame_data(self):
        raise NotImplementedError()

    def get_keyframe(self, kf_i):
        frame_data = list(self.frame_data[
            self.frame_size*kf_i:
            self.frame_size*(kf_i+1)
            ])
        frame_data_pop = frame_data.pop
        return (
            frame_data_pop(0) if self.pos_x else 0.0,
            frame_data_pop(0) if self.pos_y else 0.0,
            frame_data_pop(0) if self.pos_z else 0.0,
            frame_data_pop(0) if self.rot_x else 0.0,
            frame_data_pop(0) if self.rot_y else 0.0,
            frame_data_pop(0) if self.rot_z else 0.0,
            frame_data_pop(0) if self.scale_x else 0.0,
            frame_data_pop(0) if self.scale_y else 0.0,
            frame_data_pop(0) if self.scale_z else 0.0
            )

    def get_frame_data(self, frame):
        if self.compressed:
            raise ValueError("Must decompress animation before getting frame data.")
        elif self.initial_frame_only:
            return self.get_keyframe(0)

        kf_i, t = self.keyframe_indices[frame]
        kf      = self.get_keyframe(kf_i)
        return (
            kf[0]*t, kf[1]*t, kf[2]*t, # px, py, pz
            kf[3]*t, kf[4]*t, kf[5]*t, # rx, ry, rz
            kf[6]*t, kf[7]*t, kf[8]*t, # sx, sy, sz
            )


class G3DAnimation():
    name            = ""
    prefix          = ""
    frame_rate      = 30
    frame_count     = 0

    comp_angles     = ()
    comp_positions  = ()
    comp_scales     = ()
    nodes           = ()

    @property
    def compressed(self):
        compressed = sum(n.compressed for n in self.nodes)
        return (
            #  0 == none compressed
            #  1 == all compressed
            # -1 == some compressed
            0 if not compressed else
            1 if compressed == len(self.nodes) else
            -1
            )

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

    def decompress(self):
        for node in self.nodes:
            if node.compressed:
                node.decompress_frame_data(
                    self.comp_angles, self.comp_positions, self.comp_scales
                    )
                node.generate_keyframe_indices(self.frame_count)

    def compress(self):
        raise NotImplementedError()

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
            g3d_node.generate_keyframe_indices(self.frame_count)

    def compile_g3d(self, cache_type):
        animation_cache = AnimationCache()
        raise NotImplementedError()

        return animation_cache

    def import_jmm(self, input_filepath):
        if halo_jm.halo_anim is None:
            raise NotImplementedError(
                "Could not locate reclaimer animation module. Cannot export jmm."
                )

        with open(input_filepath, "r", newline="\n") as f:
            jma_anim = halo_jm.halo_anim.read_jma(f.read())

        halo_jm.import_jmm_to_g3d(jma_anim, self)

    def export_jmm(self, output_filepath):
        jma_anim = halo_jm.export_g3d_to_jmm(self)

        halo_jm.halo_anim.write_jma(output_filepath, jma_anim)
