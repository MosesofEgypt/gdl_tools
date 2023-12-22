import hashlib
import os

from .animation_cache import AnimationCache, AnimationCacheNode,\
     NODE_TYPES
from . import halo_jm, animation_util, constants as c


class G3DAnimationNode(AnimationCacheNode):
    keyframe_spacing = ()

    def _get_keyframe(self, keyframe_slice):
        keyframe_data_pop = list(keyframe_slice).pop
        return (
             keyframe_data_pop(0) if self.rot_x   else 0.0,
             keyframe_data_pop(0) if self.rot_y   else 0.0,
             keyframe_data_pop(0) if self.rot_z   else 0.0,
            (keyframe_data_pop(0) if self.pos_x   else 0.0) + self.init_pos[0],
            (keyframe_data_pop(0) if self.pos_y   else 0.0) + self.init_pos[1],
            (keyframe_data_pop(0) if self.pos_z   else 0.0) + self.init_pos[2],
            (keyframe_data_pop(0) if self.scale_x else 0.0) + 1.0,
            (keyframe_data_pop(0) if self.scale_y else 0.0) + 1.0,
            (keyframe_data_pop(0) if self.scale_z else 0.0) + 1.0
            )

    def compress_keyframe_data(self):
        raise NotImplementedError()

    def decompress_keyframe_data(self, comp_angles, comp_positions, comp_scales):
        if not self.compressed:
            return

        i, stride     = 0, self.frame_size
        keyframe_data = list(self.keyframe_data)

        #axis_strs = list("hprxyzXYZ")
        #if self.flags & 2047: print(self.name)

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
            if flag and keyframe_data:
                # decompress the keyframe deltas
                keyframe_data[i::stride] = animation_util.comp_keyframe_data_to_uncomp(
                    self.keyframe_data[i::stride], values
                    )
                # transform deltas into absolute values by adding previous delta
                keyframe_data[i] += self.initial_keyframe[i]
                for j in range(i + stride, len(keyframe_data), stride):
                    keyframe_data[j] += keyframe_data[j-stride]

                i += 1

            #axis_str = axis_strs.pop(0)
            #if flag: print(f"   {axis_str}", [
            #    self.initial_keyframe[i-1], len(keyframe_data[i-1::stride])
            #    ])

        # NOTE: do not set keyframe data before changing compressed status.
        #       the function that converts keyframe_data values will try
        #       to convert them all to ints, which is completely wrong.
        self.compressed = False
        self.keyframe_data = keyframe_data

    def calculate_keyframe_spacing(self):
        kf_spacing  = []
        framecount  = 1
        for i, flags in enumerate(self.frame_flags):
            for j in range(8):
                if flags&1:
                    kf_spacing.append(framecount)
                    framecount = 0

                framecount += 1
                flags >>= 1

        if self.initial_keyframe:
            kf_spacing = kf_spacing[1:]

        self.keyframe_spacing = tuple(kf_spacing)

    def get_initial_keyframe(self):
        return (
            self._get_keyframe(self.initial_keyframe)
            if self.initial_keyframe else
            self._get_keyframe((0.0, )*9)
            )

    def get_keyframe(self, kfi):
        keyframe_slice = self.keyframe_data[
            self.frame_size*kfi:
            self.frame_size*(kfi+1)
            ]
        return self._get_keyframe(keyframe_slice)

    def get_frame(self, frame):
        if not self.frame_data:
            raise ValueError("Must generate all frames before getting frame data.")
        frame = max(0, min(frame, len(self.frame_data)-1))
        return self.frame_data[frame]

    def generate_frames(self, frame_count):
        if self.compressed:
            raise ValueError("Must decompress animation before getting frame data.")

        # fill in the initial frames to be overwritten as we parse the animation
        kf0 = self.get_initial_keyframe()

        if self.initial_keyframe_only:
            self.frame_data = [kf0] * max(1, frame_count)
            return

        frame_data, f = [kf0] * frame_count, 0
        for i, count in enumerate(self.keyframe_spacing):
            # NOTE: count is the number of frames from kf0 to kf1.
            #       this includes kf0, but excludes kf1
            kf1 = self.get_keyframe(i)
            if count > 1:
                rx0, ry0, rz0, px0, py0, pz0, sx0, sy0, sz0 = kf0
                rx1, ry1, rz1, px1, py1, pz1, sx1, sy1, sz1 = kf1

                frame_data[f: f+count] = [
                    (rx0*t0 + rx1*t1, ry0*t0 + ry1*t1, rz0*t0 + rz1*t1,
                     px0*t0 + px1*t1, py0*t0 + py1*t1, pz0*t0 + pz1*t1,
                     sx0*t0 + sx1*t1, sy0*t0 + sy1*t1, sz0*t0 + sz1*t1)
                    for t0, t1 in [(1.0 - i/count, i/count) for i in range(count)]
                    ]
            else:
                frame_data[f] = kf0

            f += count
            kf0 = kf1

        # pad with last frame
        remainder = frame_count - f
        frame_data[f: f+remainder] = (kf0, )*remainder

        self.frame_data = frame_data


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
            node.decompress_keyframe_data(
                self.comp_angles, self.comp_positions, self.comp_scales
                )

    def generate_frames(self):
        for node in self.nodes:
            node.generate_frames(self.frame_count)

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

            g3d_node.name       = cache_node.name
            g3d_node.parent     = cache_node.parent
            g3d_node.type_id    = cache_node.type_id
            g3d_node.flags      = cache_node.flags
            g3d_node.init_pos   = cache_node.init_pos
            g3d_node.frame_flags        = cache_node.frame_flags
            g3d_node.initial_keyframe   = cache_node.initial_keyframe
            g3d_node.keyframe_data      = cache_node.keyframe_data

            g3d_node.calculate_keyframe_spacing()

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
