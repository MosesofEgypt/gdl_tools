import array
import struct

from sys import byteorder

from . import constants
from .asset_cache import AssetCache
from .. import util

# ensure they're all no more than 4 characters since we use them as the cache_type
for ext in (constants.ANIMATION_CACHE_EXTENSION_NGC, constants.ANIMATION_CACHE_EXTENSION_PS2,
            constants.ANIMATION_CACHE_EXTENSION_XBOX, constants.ANIMATION_CACHE_EXTENSION_DC,
            constants.ANIMATION_CACHE_EXTENSION_ARC):
    assert len(ext) <= 4

ANIM_CACHE_VER  = 0x0001


ANIM_CACHE_HEADER_STRUCT = struct.Struct('<hh BB HHH')
#   frame_rate
#   frame_count
#   prefix_length
#   sequence_name_length
#   comp_angles_count
#   comp_positions_count
#   comp_scales_count


NODES_ARRAY_HEADER_STRUCT = struct.Struct('<Hxx')
#   node_count

NODE_HEADER_STRUCT = struct.Struct('<3f Hh HBB')
#   init_pos
#   flags
#   parent_index
#   frame_flag_count
#   node_type_id
#   node_name_length

# node flags
ANIM_CACHE_NODE_FLAG_ROT_X          = 1 << 0
ANIM_CACHE_NODE_FLAG_ROT_Y          = 1 << 1
ANIM_CACHE_NODE_FLAG_ROT_Z          = 1 << 2
ANIM_CACHE_NODE_FLAG_POS_X          = 1 << 3
ANIM_CACHE_NODE_FLAG_POS_Y          = 1 << 4
ANIM_CACHE_NODE_FLAG_POS_Z          = 1 << 5
ANIM_CACHE_NODE_FLAG_SCALE_X        = 1 << 6
ANIM_CACHE_NODE_FLAG_SCALE_Y        = 1 << 7
ANIM_CACHE_NODE_FLAG_SCALE_Z        = 1 << 8
ANIM_CACHE_NODE_FLAG_COMPRESSED     = 1 << 9
ANIM_CACHE_NODE_FLAG_INITIAL_ONLY   = 1 << 10
ANIM_CACHE_NODE_FLAG_HAS_ANIM_DATA  = 1 << 15


NODE_TYPES  = (
    "null",
    "skeletal",
    "object",
    "texture",
    "particle_system"
    )


def comp_frame_data_to_uncomp(indices, values):
    return tuple(util.dereference_indexed_values(indices, values))

def combine_uncomp_values(*values):
    all_values = set()
    [map(all_values.update, value_set) for value_set in value_sets]
    return tuple(sorted(all_values))

def rebase_comp_frame_data(indices, src_values, dst_values):
    return tuple(util.dereference_indexed_values(
        util.dereference_indexed_values(indices, src_values),
        util.invert_map(dst_values)
        ))

def combine_compressed_frame_data(*indices_and_values_pairs):
    for pair in indices_and_values_pairs:
        if not(isinstance(pair, tuple) and
               hasattr(pair[0], "__iter__") and
               hasattr(pair[1], "__iter__")):
            raise ValueError("Must pass in indices and values as tuple pairs.")

    combined_values = combine_uncomp_values(v for i, v in indices_and_values_pairs)
    return tuple(
        rebase_comp_frame_data(i, v, combined_values)
        for i, v in indices_and_values_pairs
        )

def reduce_compressed_frame_data(*indices_arrays, all_values):
    value_map   = util.invert_map(all_values)
    results     = [None] * len(indices_arrays)

    for i, indices in enumerate(indices_arrays):
        uncomp_data     = comp_frame_data_to_uncomp(indices, all_values)
        reduced_values  = tuple(sorted(set(uncomp_data)))
        reduced_indices = tuple(util.dereference_indexed_values(
            uncomp_data, util.invert_map(reduced_values)
            ))
        results[i]      = (reduced_indices, reduced_values)

    return results


class AnimationCacheNode():
    name            = ""
    parent          = -1
    _type_id        = 0
    _flags          = 0
    _frame_flags    = ()
    _frame_data     = ()
    _initial_frame  = ()
    _init_pos       = ()

    def _get_flag(self, mask):
        return bool(self._flags, mask)

    @property
    def rot_x(self): return self._get_flag(ANIM_CACHE_NODE_FLAG_ROT_X)
    @property
    def rot_y(self): return self._get_flag(ANIM_CACHE_NODE_FLAG_ROT_Y)
    @property
    def rot_z(self): return self._get_flag(ANIM_CACHE_NODE_FLAG_ROT_Z)
    @property
    def pos_x(self): return self._get_flag(ANIM_CACHE_NODE_FLAG_POS_X)
    @property
    def pos_y(self): return self._get_flag(ANIM_CACHE_NODE_FLAG_POS_Y)
    @property
    def pos_z(self): return self._get_flag(ANIM_CACHE_NODE_FLAG_POS_Z)
    @property
    def scale_x(self): return self._get_flag(ANIM_CACHE_NODE_FLAG_SCALE_X)
    @property
    def scale_y(self): return self._get_flag(ANIM_CACHE_NODE_FLAG_SCALE_Y)
    @property
    def scale_z(self): return self._get_flag(ANIM_CACHE_NODE_FLAG_SCALE_Z)
    @property
    def compressed(self): return self._get_flag(ANIM_CACHE_NODE_FLAG_COMPRESSED)
    @property
    def initial_frame_only(self): return self._get_flag(ANIM_CACHE_NODE_FLAG_INITIAL_ONLY)

    def _set_flag(self, val, mask):
        if val: self._flags |=  mask
        else:   self._flags &= (mask ^ 0xFFFF)

    @rot_x.setter
    def rot_x(self, val): self._set_flag(val, ANIM_CACHE_NODE_FLAG_ROT_X)
    @rot_y.setter
    def rot_y(self, val): self._set_flag(val, ANIM_CACHE_NODE_FLAG_ROT_Y)
    @rot_z.setter
    def rot_z(self, val): self._set_flag(val, ANIM_CACHE_NODE_FLAG_ROT_Z)
    @pos_x.setter
    def pos_x(self, val): self._set_flag(val, ANIM_CACHE_NODE_FLAG_POS_X)
    @pos_y.setter
    def pos_y(self, val): self._set_flag(val, ANIM_CACHE_NODE_FLAG_POS_Y)
    @pos_z.setter
    def pos_z(self, val): self._set_flag(val, ANIM_CACHE_NODE_FLAG_POS_Z)
    @scale_x.setter
    def scale_x(self, val): self._set_flag(val, ANIM_CACHE_NODE_FLAG_SCALE_X)
    @scale_y.setter
    def scale_y(self, val): self._set_flag(val, ANIM_CACHE_NODE_FLAG_SCALE_Y)
    @scale_z.setter
    def scale_z(self, val): self._set_flag(val, ANIM_CACHE_NODE_FLAG_SCALE_Z)
    @compressed.setter
    def compressed(self, val): self._set_flag(val, ANIM_CACHE_NODE_FLAG_COMPRESSED)
    @initial_frame_only.setter
    def initial_frame_only(self, val): self._set_flag(val, ANIM_CACHE_NODE_FLAG_INITIAL_ONLY)

    @property
    def frame_size(self):
        return sum((
            self.rot_x,   self.rot_y,   self.rot_z,
            self.pos_x,   self.pos_y,   self.pos_z,
            self.scale_x, self.scale_y, self.scale_z
            ))

    @property
    def initial_frame_size(self):
        return self.frame_size if self.compressed or self.initial_frame_only else 0

    @property
    def frame_flags(self): return self._frame_flags
    @property
    def frame_flags(self, val):
        if not hasattr(val, "__iter__"):
            raise TypeError(f"frame_flags must be an iterable, not {type(val)}")
        self._frame_flags = tuple(map(int, val))

    @property
    def frame_data(self): return self._frame_data
    @frame_data.setter
    def frame_data(self, val):
        if not hasattr(val, "__iter__"):
            raise TypeError(f"frame_data must be an iterable, not {type(val)}")
        elif len(val) % self.frame_size:
            raise ValueError(f"frame_data must contain a multiple of {self.frame_size} values")

        self._frame_data = tuple(map(int if self.compressed else float, val))

    @property
    def flags(self): return self._flags
    @flags.setter
    def flags(self, val):
        if not isinstance(val, int):
            raise ValueError("flags must be an int")
        self._flags = int(val)

    @property
    def initial_frame(self): return tuple(self._initial_frame)
    @initial_frame.setter
    def initial_frame(self, val):
        if not hasattr(val, "__iter__"):
            raise TypeError(f"initial_frame must be an iterable, not {type(val)}")
        elif len(val) != self.initial_frame_size:
            raise ValueError(f"initial_frame must contain {self.initial_frame_size} values")

        self._initial_frame = tuple(map(float, val))

    @property
    def init_pos(self): return tuple(self._init_pos)
    @init_pos.setter
    def init_pos(self, val):
        if not hasattr(val, "__iter__"):
            raise TypeError(f"init_pos must be an iterable, not {type(val)}")
        elif len(val) != 3:
            raise ValueError("init_pos must contain 3 numbers")

        self._init_pos = tuple(map(float, val))

    @property
    def type_id(self): return self._type_id
    @type_id.setter
    def type_id(self, val):
        if val not in range(len(NODE_TYPES)):
            raise ValueError(f"Invalid type_id '{val}'")
        self._type_id = val

    @property
    def type_name(self): return NODE_TYPES[self._type_id]
    @type_name.setter
    def type_name(self, val):
        if val not in NODE_TYPES:
            raise ValueError(f"Invalid type_name '{val}'")
        self._type_id = NODE_TYPES.index(val)


class AnimationCache(AssetCache):
    cache_type_version  = ANIM_CACHE_VER
    prefix              = ""
    name                = ""
    comp_angles         = ()
    comp_positions      = ()
    comp_scales         = ()
    nodes               = ()
    frame_rate          = 30
    frame_count         = 0

    def parse(self, rawdata):
        super().parse(rawdata)

        f_rate, f_ct, prefix_len, name_len, ang_ct, pos_ct, scale_ct = \
           ANIM_CACHE_HEADER_STRUCT.unpack(
               rawdata.read(ANIM_CACHE_HEADER_STRUCT.size)
               )

        # read names and compressed vector values
        prefix          = rawdata.read(prefix_len).decode('latin-1').upper()
        name            = rawdata.read(name_len).decode('latin-1').upper()
        comp_angles     = array.array("f", rawdata.read(ang_ct*4))
        comp_positions  = array.array("f", rawdata.read(pos_ct*4))
        comp_scales     = array.array("f", rawdata.read(scale_ct*4))

        if byteorder == ">": # expected to be in little-endian
            comp_angles.byteswap()
            comp_positions.byteswap()
            comp_scales.byteswap()

        self.prefix,        self.name           = prefix, name
        self.frame_rate,    self.frame_count    = f_rate, f_ct
        self.comp_angles    = tuple(comp_angles)
        self.comp_positions = tuple(comp_positions)
        self.comp_scales    = tuple(comp_scales)

        self.parse_nodes(rawdata)

    def parse_nodes(self, rawdata):
        node_count = NODES_ARRAY_HEADER_STRUCT.unpack(
           rawdata.read(NODES_ARRAY_HEADER_STRUCT.size)
           )
        nodes           = [None] * node_count
        node_map        = {}
        node_map_root   = None
        seen_nodes      = set()
        for i in range(node_count):
            node = nodes[i] = AnimationCacheNode()
            ix, iy, iz, flags, parent, frame_flag_ct, type_id, name_len = \
                NODE_HEADER_STRUCT.unpack(
                    rawdata.read(NODE_HEADER_STRUCT.size)
                    )
            name    = rawdata.read(name_len).decode('latin-1').upper()

            if parent >= 0 and parent not in range(node_count):
                raise ValueError(f"Node '{name}' at index {i} specifies "
                                 f"non-existent parent index {parent}.")

            node.flags      = flags
            node.name       = name
            node.parent     = parent
            node.type_id    = type_id
            node.init_pos   = (ix, iy, iz)

            frame_flags = rawdata.read(frame_flag_ct)
            frame_size  = node.frame_size*(1 if node.is_compressed else 4)
            frame_count = max(
                0, util.count_set_bits(frame_flags) - (1 if node.is_compressed else 0)
                )
            initial_frame   = array.array(
                "f", rawdata.read(4*node.initial_frame_size)
                )
            frame_data      = array.array(
                "B" if node.is_compressed else "f",
                rawdata.read(frame_count*frame_size)
                )

            if byteorder == ">":
                initial_frame.byteswap()
                frame_data.byteswap()

            node.initial_frame  = initial_frame
            node.frame_data     = frame_data

            node_map.setdefault(parent, {})[i] = node_map.setdefault(i, {})
            if parent < 0:
                node_map_root = node_map[i]
                seen_nodes.add(i)

        if node_map_root is None:
            raise ValueError("Could not locate root node in atree.")

        curr_nodes = tuple(node_map_root.items())
        while curr_nodes:
            next_nodes = ()
            for i, node in curr_nodes.items():
                next_nodes += tuple(node.items())
                if i in seen_nodes:
                    raise ValueError("Cyclical hierarchy detected in atree.")
                seen_nodes.add(i)

            curr_nodes = next_nodes

        if len(seen_nodes) != node_count:
            raise ValueError("Orphaned nodes detected in atree.")

        self.nodes = nodes

    def serialize(self):
        self.cache_type_version = ANIM_CACHE_VER

        cache_header_rawdata = super().serialize()
        return cache_header_rawdata


class Ps2AnimationCache(AnimationCache):
    cache_type  = constants.ANIMATION_CACHE_EXTENSION_PS2

class XboxAnimationCache(Ps2AnimationCache):
    cache_type  = constants.ANIMATION_CACHE_EXTENSION_XBOX

class GamecubeAnimationCache(Ps2AnimationCache):
    cache_type  = constants.ANIMATION_CACHE_EXTENSION_NGC

class DreamcastAnimationCache(AnimationCache):
    cache_type  = constants.ANIMATION_CACHE_EXTENSION_DC

class ArcadeAnimationCache(AnimationCache):
    cache_type  = constants.ANIMATION_CACHE_EXTENSION_ARC


AnimationCache._sub_classes = {
    cls.cache_type: cls for cls in (
        Ps2AnimationCache, XboxAnimationCache, GamecubeAnimationCache,
        DreamcastAnimationCache, ArcadeAnimationCache
        )
    }
