import struct

from . import constants
from .model_cache import Ps2ModelCache, XboxModelCache, GamecubeModelCache,\
     DreamcastModelCache, ArcadeModelCache, AssetCache
from .. import util

# ensure they're all no more than 4 characters since we use them as the cache_type
for ext in (constants.ANIMATION_CACHE_EXTENSION, ):
    assert len(ext) <= 4

ANIM_CACHE_VER  = 0x0001

# flags


ANIM_CACHE_HEADER_STRUCT = struct.Struct('<')


class AnimationCache(AssetCache):
    cache_type = constants.ANIMATION_CACHE_EXTENSION
    cache_type_version = ANIM_CACHE_VER
    expected_cache_type_versions = frozenset((
        (constants.ANIMATION_CACHE_EXTENSION,  ANIM_CACHE_VER),
        ))

    def parse(self, rawdata):
        super().parse(rawdata)

    def serialize(self):
        self.cache_type_version = ANIM_CACHE_VER

        cache_header_rawdata = super().serialize()
        return cache_header_rawdata
