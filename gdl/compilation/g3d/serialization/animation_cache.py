import struct

from . import constants
from .asset_cache import AssetCache
from .. import util

# ensure they're all no more than 4 characters since we use them as the cache_type
for ext in (constants.ANIMATION_CACHE_EXTENSION_NGC, constants.ANIMATION_CACHE_EXTENSION_PS2,
            constants.ANIMATION_CACHE_EXTENSION_XBOX, constants.ANIMATION_CACHE_EXTENSION_DC,
            constants.ANIMATION_CACHE_EXTENSION_ARC):
    assert len(ext) <= 4

ANIM_CACHE_VER  = 0x0001

# flags


ANIM_CACHE_HEADER_STRUCT = struct.Struct('<')


class AnimationCache(AssetCache):
    cache_type_version  = ANIM_CACHE_VER

    def parse(self, rawdata):
        super().parse(rawdata)

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
