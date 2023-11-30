import hashlib
import os

from .animation_cache import AnimationCache,\
    SEQ_DATA_TYPE_ROT_X, SEQ_DATA_TYPE_ROT_Y, SEQ_DATA_TYPE_ROT_Z,\
    SEQ_DATA_TYPE_POS_X, SEQ_DATA_TYPE_POS_Y, SEQ_DATA_TYPE_POS_Z,\
    SEQ_DATA_TYPE_SCALE_X , SEQ_DATA_TYPE_SCALE_Y, SEQ_DATA_TYPE_SCALE_Z,\
    SEQ_DATA_TYPE_COMPRESSED, SEQ_DATA_TYPE_INITIAL_ONLY
from . import constants as c


class G3DNodeAnimation():
    name                = ""
    _node_type          = ""
    _init_pos           = ()
    comp_frame_data     = ()
    uncomp_frame_data   = ()

    rot_x = pos_x = scale_x = False
    rot_y = pos_y = scale_y = False
    rot_z = pos_z = scale_z = False
    compressed_data         = False
    initial_frame_only      = False

    NODE_TYPE_NULL      = "null"
    NODE_TYPE_SKELETAL  = "skeletal"
    NODE_TYPE_OBJECT    = "object"
    NODE_TYPE_TEXTURE   = "texture"
    NODE_TYPE_PSYS      = "particle_system"
    NODE_TYPES          = frozenset((
        NODE_TYPE_NULL,
        NODE_TYPE_SKELETAL,
        NODE_TYPE_OBJECT,
        NODE_TYPE_TEXTURE,
        NODE_TYPE_PSYS
        ))

    @property
    def flags(self):
        return (
            (SEQ_DATA_TYPE_ROT_X        if self.rot_x               else 0) |
            (SEQ_DATA_TYPE_ROT_Y        if self.rot_y               else 0) |
            (SEQ_DATA_TYPE_ROT_Z        if self.rot_z               else 0) |
            (SEQ_DATA_TYPE_POS_X        if self.pos_x               else 0) |
            (SEQ_DATA_TYPE_POS_Y        if self.pos_y               else 0) |
            (SEQ_DATA_TYPE_POS_Z        if self.pos_z               else 0) |
            (SEQ_DATA_TYPE_SCALE_X      if self.scale_x             else 0) |
            (SEQ_DATA_TYPE_SCALE_Y      if self.scale_y             else 0) |
            (SEQ_DATA_TYPE_SCALE_Z      if self.scale_z             else 0) |
            (SEQ_DATA_TYPE_COMPRESSED   if self.compressed_data     else 0) |
            (SEQ_DATA_TYPE_INITIAL_ONLY if self.initial_frame_only  else 0)
            )

    @property
    def framesize(self):
        return sum((
            bool(self.rot_x),   bool(self.rot_y),   bool(self.rot_z),
            bool(self.pos_x),   bool(self.pos_y),   bool(self.pos_z),
            bool(self.scale_x), bool(self.scale_y), bool(self.scale_z)
            ))

    @property
    def init_pos(self): return tuple(self._init_pos)
    @init_pos.setter
    def init_pos(self, val):
        if len(val) != 3:
            raise ValueError("init_pos must be an iterable")
        for n in val:
            if not isinstance(n, (int, float)):
                raise ValueError("init_pos must contain only numbers.")
        self.init_pos = tuple(val)

    @property
    def node_type(self):
        return self._node_type
    @node_type.setter
    def node_type(self, val):
        if val not in G3DNode.NODE_TYPES:
            raise ValueError(f"Invalid node_type '{val}'")
        self._node_type = val


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
