import array
import struct

from sys import byteorder

from . import animation_util, constants
from .asset_cache import AssetCache

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
#   node_name_length
#   node_type_id

# node flags
ANIM_CACHE_NODE_FLAG_ROT_X          = 1 << 0
ANIM_CACHE_NODE_FLAG_ROT_Y          = 1 << 1
ANIM_CACHE_NODE_FLAG_ROT_Z          = 1 << 2

ANIM_CACHE_NODE_FLAG_POS_X          = 1 << 4
ANIM_CACHE_NODE_FLAG_POS_Y          = 1 << 5
ANIM_CACHE_NODE_FLAG_POS_Z          = 1 << 6

ANIM_CACHE_NODE_FLAG_SCALE_X        = 1 << 8
ANIM_CACHE_NODE_FLAG_SCALE_Y        = 1 << 9
ANIM_CACHE_NODE_FLAG_SCALE_Z        = 1 << 10

ANIM_CACHE_NODE_FLAG_COMPRESSED     = 1 << 13
ANIM_CACHE_NODE_FLAG_INITIAL_ONLY   = 1 << 14


NODE_TYPES  = (
    "null",
    "skeletal",
    "object",
    "texture",
    "particle_system"
    )


class AnimationCacheNode():
    name                = ""
    parent              = -1
    _type_id            = 0
    _flags              = 0
    _init_pos           = ()
    _frame_flags        = ()
    _keyframe_data      = ()
    _initial_keyframe   = ()

    @property
    def rot_x(self): return bool(self._flags & ANIM_CACHE_NODE_FLAG_ROT_X)
    @property
    def rot_y(self): return bool(self._flags & ANIM_CACHE_NODE_FLAG_ROT_Y)
    @property
    def rot_z(self): return bool(self._flags & ANIM_CACHE_NODE_FLAG_ROT_Z)
    @property
    def pos_x(self): return bool(self._flags & ANIM_CACHE_NODE_FLAG_POS_X)
    @property
    def pos_y(self): return bool(self._flags & ANIM_CACHE_NODE_FLAG_POS_Y)
    @property
    def pos_z(self): return bool(self._flags & ANIM_CACHE_NODE_FLAG_POS_Z)
    @property
    def scale_x(self): return bool(self._flags & ANIM_CACHE_NODE_FLAG_SCALE_X)
    @property
    def scale_y(self): return bool(self._flags & ANIM_CACHE_NODE_FLAG_SCALE_Y)
    @property
    def scale_z(self): return bool(self._flags & ANIM_CACHE_NODE_FLAG_SCALE_Z)
    @property
    def compressed(self): return bool(self._flags & ANIM_CACHE_NODE_FLAG_COMPRESSED)
    @property
    def initial_keyframe_only(self): return bool(self._flags & ANIM_CACHE_NODE_FLAG_INITIAL_ONLY)

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
    @initial_keyframe_only.setter
    def initial_keyframe_only(self, val): self._set_flag(val, ANIM_CACHE_NODE_FLAG_INITIAL_ONLY)

    @property
    def frame_size(self):
        return sum((
            self.rot_x,   self.rot_y,   self.rot_z,
            self.pos_x,   self.pos_y,   self.pos_z,
            self.scale_x, self.scale_y, self.scale_z
            ))
    @property
    def initial_keyframe_size(self):
        return self.frame_size if self.compressed or self.initial_keyframe_only else 0
    @property
    def framedata_typecode(self):
        return "B" if self.compressed else "f"

    @property
    def keyframe_count(self):
        keyframe_count = animation_util.count_set_bits(self._frame_flags) - self.compressed
        return 0 if keyframe_count <= 0 else keyframe_count

    @property
    def frame_flags(self): return self._frame_flags
    @frame_flags.setter
    def frame_flags(self, val):
        if not hasattr(val, "__iter__"):
            raise TypeError(f"frame_flags must be an iterable, not {type(val)}")
        self._frame_flags = tuple(map(int, val))

    @property
    def keyframe_data(self): return self._keyframe_data
    @keyframe_data.setter
    def keyframe_data(self, val):
        if not hasattr(val, "__iter__"):
            raise TypeError(f"keyframe_data must be an iterable, not {type(val)}")
        elif self.frame_size and len(val) % self.frame_size:
            raise ValueError(f"keyframe_data must contain a multiple of {self.frame_size} values")

        self._keyframe_data = tuple(map(int if self.compressed else float, val))

    @property
    def flags(self): return self._flags
    @flags.setter
    def flags(self, val):
        if not isinstance(val, int):
            raise ValueError("flags must be an int")
        self._flags = int(val)

    @property
    def initial_keyframe(self): return tuple(self._initial_keyframe)
    @initial_keyframe.setter
    def initial_keyframe(self, val):
        if not hasattr(val, "__iter__"):
            raise TypeError(f"initial_keyframe must be an iterable, not {type(val)}")
        elif len(val) != self.initial_keyframe_size:
            raise ValueError(
                f"initial_keyframe must contain {self.initial_keyframe_size} values, not {len(val)}"
                )

        self._initial_keyframe = tuple(map(float, val))

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

    name                = ""
    prefix              = ""
    frame_rate          = 30
    frame_count         = 0

    comp_angles         = ()
    comp_positions      = ()
    comp_scales         = ()
    nodes               = ()

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

    def serialize(self):
        self.cache_type_version = ANIM_CACHE_VER

        cache_header_rawdata    = super().serialize()
        anim_header_rawdata     = ANIM_CACHE_HEADER_STRUCT.pack(
            self.frame_rate, self.frame_count, len(self.prefix), len(self.name),
            len(self.comp_angles), len(self.comp_positions), len(self.comp_scales)
            )
        ang_array   = array.array("f", self.comp_angles)
        pos_array   = array.array("f", self.comp_positions)
        sca_array   = array.array("f", self.comp_scales)

        if byteorder == ">": # expected to be in little-endian
            ang_array.byteswap()
            pos_array.byteswap()
            sca_array.byteswap()

        prefix_rawdata  = self.prefix.upper().encode('latin-1')
        name_rawdata    = self.name.upper().encode('latin-1')
        ang_rawdata     = ang_array.tobytes()
        pos_rawdata     = pos_array.tobytes()
        sca_rawdata     = sca_array.tobytes()
        nodes_rawdata   = self.serialize_nodes()

        return b''.join((
            cache_header_rawdata, anim_header_rawdata, prefix_rawdata,
            name_rawdata, ang_rawdata, pos_rawdata, sca_rawdata, nodes_rawdata
            ))

    def parse_nodes(self, rawdata):
        (node_count, ) = NODES_ARRAY_HEADER_STRUCT.unpack(
           rawdata.read(NODES_ARRAY_HEADER_STRUCT.size)
           )
        nodes   = [None] * node_count
        for i in range(node_count):
            node = nodes[i] = AnimationCacheNode()
            ix, iy, iz, flags, parent, frame_flag_ct, name_len, type_id = \
                NODE_HEADER_STRUCT.unpack(
                    rawdata.read(NODE_HEADER_STRUCT.size)
                    )
            name = rawdata.read(name_len).decode('latin-1').upper()

            if parent >= 0 and parent not in range(node_count):
                raise ValueError(f"Node '{name}' at index {i} specifies "
                                 f"non-existent parent index {parent}.")

            node.flags          = flags
            node.name           = name
            node.parent         = parent
            node.type_id        = type_id
            node.init_pos       = (ix, iy, iz)
            node.frame_flags    = rawdata.read(frame_flag_ct)

            initial_data_size   = 4*node.initial_keyframe_size
            keyframe_data_size  = node.keyframe_count * node.frame_size * (
                1 if node.compressed else 4
                )

            initial_keyframe = array.array("f", rawdata.read(initial_data_size))
            keyframe_data    = array.array(node.framedata_typecode, rawdata.read(keyframe_data_size))
            if byteorder == ">":
                initial_keyframe.byteswap()
                keyframe_data.byteswap()

            if node.type_name != "skeletal":
                node.flags, node.frame_flags    = 0, ()
                initial_keyframe, keyframe_data    = (), ()

            node.initial_keyframe = initial_keyframe
            node.keyframe_data    = keyframe_data

        self.nodes = nodes
        self.validate_hierarchy()

    def serialize_nodes(self):
        self.validate_hierarchy()

        nodes_rawdata = NODES_ARRAY_HEADER_STRUCT.pack(len(self.nodes))

        for node in self.nodes:
            if node.type_name == "skeletal":
                flags, frame_flags              = node.flags, node.frame_flags
                initial_keyframe, keyframe_data = node.initial_keyframe, node.keyframe_data
            else:
                flags, frame_flags              = 0, ()
                initial_keyframe, keyframe_data = (), ()

            nodes_rawdata += NODE_HEADER_STRUCT.pack(
                *node.init_pos, flags, node.parent,
                len(frame_flags), len(node.name), node.type_id
                )
            initial_keyframe = array.array("f", initial_keyframe)
            keyframe_data    = array.array(node.framedata_typecode, keyframe_data)
            if byteorder == ">":
                initial_keyframe.byteswap()
                keyframe_data.byteswap()

            nodes_rawdata += b''.join((
                node.name.upper().encode('latin-1'),
                bytes(frame_flags),
                initial_keyframe.tobytes(),
                keyframe_data.tobytes()
                ))

        return nodes_rawdata

    def reduce_compressed_data(self):
        keyframe_datas, angles, positions, scales = animation_util.reduce_compressed_data(
            self.nodes, self.comp_angles, self.comp_positions, self.comp_scales
            )

        for i, keyframe_data in keyframe_datas.items():
            self.nodes[i].keyframe_data = keyframe_data

        self.comp_angles    = angles 
        self.comp_positions = positions
        self.comp_scales    = scales

    def validate_hierarchy(self):
        animation_util.validate_hierarchy(self.nodes)


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
