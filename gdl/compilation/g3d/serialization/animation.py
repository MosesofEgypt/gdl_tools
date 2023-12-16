import hashlib
import os

from .animation_cache import AnimationCache, AnimationCacheNode,\
     NODE_TYPES
from . import animation_jmm, animation_util, constants as c


class G3DAnimationNode(AnimationCacheNode):
    keyframe_indices = ()

    def generate_keyframe_indices(self, frame_count):
        keyframe_indices = [[0.0, 0.0, 0] for i in range(frame_count)]
        f_0 = kf_0 = 0
        f_1 = kf_1 = 0
        for i, flags in enumerate(self.frame_flags):
            for j in range(8):
                f_1 = i*8 + j
                if f_1 >= frame_count:
                    break
                elif flags&1:
                    scale = 1/(f_1 - f_0) if f_1 != f_0 else 1
                    for x, f_i in enumerate(range(f_0, f_1)):
                        keyframe_indices[f_i][2] = x*scale

                    f_0  = f_1
                    kf_0 = kf_1
                    kf_1 += 1

                keyframe_indices[f_1] = [kf_0, kf_1, 0]

                flags >>= 1

        for f_i in range(f_0, frame_count):
            keyframe_indices[f_i][:] = (kf_0, kf_0, 0)

        self.keyframe_indices = tuple(map(tuple, keyframe_indices))
        #print("Keyframes:", self.keyframe_indices)
        #print("Flags:", self.frame_flags)

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
                initial_val = self.initial_frame[off]
                frame_data[off::stride] = map(
                    initial_val.__add__,
                    animation_util.comp_frame_data_to_uncomp(
                        self.frame_data[off::stride], values
                        )
                    )
                #print("xyzhprXYZ"[i], initial_val, frame_data[off::stride])
            #i += 1
            off += flag

        self.compressed     = False
        self.frame_data     = self.initial_frame + tuple(self.frame_data)
        if self.initial_frame_only:
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

        px, py, pz = self._init_pos
        return (
            frame_data_pop(0) if self.pos_x else px,
            frame_data_pop(0) if self.pos_y else py,
            frame_data_pop(0) if self.pos_z else pz,
            frame_data_pop(0) if self.rot_x else 0.0,
            frame_data_pop(0) if self.rot_y else 0.0,
            frame_data_pop(0) if self.rot_z else 0.0,
            frame_data_pop(0) if self.scale_x else 1.0,
            frame_data_pop(0) if self.scale_y else 1.0,
            frame_data_pop(0) if self.scale_z else 1.0
            )

    def interpolate_keyframes(self, keyframe_0_index, keyframe_1_index, time):
        if self.initial_frame_only:
            keyframe_0_index = keyframe_1_index = 0

        kf0 = self.get_keyframe(keyframe_0_index)
        if keyframe_0_index == keyframe_1_index or time == 0.0:
            return kf0
    
        kf1 = self.get_keyframe(keyframe_1_index)
        t1  = 0 if time <= 0 else 1 if time >= 1 else time
        t0  = 1 - t1
        return (
            kf0[0]*t0 + kf1[0]*t1, kf0[1]*t0 + kf1[1]*t1, kf0[2]*t0 + kf1[2]*t1, # px, py, pz
            kf0[3]*t0 + kf1[3]*t1, kf0[4]*t0 + kf1[4]*t1, kf0[5]*t0 + kf1[5]*t1, # rx, ry, rz
            kf0[6]*t0 + kf1[6]*t1, kf0[7]*t0 + kf1[7]*t1, kf0[8]*t0 + kf1[8]*t1, # sx, sy, sz
            )

    def get_frame_data(self, frame):
        if self.compressed:
            raise ValueError("Must decompress animation before getting frame data.")

        kf_0, kf_1, t = self.keyframe_indices[frame]
        if self.initial_frame_only:
            return self.get_keyframe(0)

        return self.interpolate_keyframes(kf_0, kf_1, t)


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
        if animation_jmm.halo_anim is None:
            raise NotImplementedError(
                "Could not locate reclaimer animation module. Cannot export jmm."
                )

        with open(input_filepath, "r", newline="\n") as f:
            jma_anim = animation_jmm.halo_anim.read_jma(f.read())

        animation_jmm.import_jmm_to_g3d(jma_anim, self)

    def export_jmm(self, output_filepath):
        jma_anim = animation_jmm.export_g3d_to_jmm(self)

        animation_jmm.halo_anim.write_jma(output_filepath, jma_anim)
