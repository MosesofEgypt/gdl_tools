import struct

from . import constants
from .asset_cache import AssetCache
from .model_cache import ModelCache
from .texture_cache import TextureCache
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
    model_cache_type    = None
    texture_cache_type  = None

    @property
    def model_cache_class(self):
        return ModelCache.get_cache_class_from_cache_type(
            self.model_cache_type
            )
    @property
    def texture_cache_class(self):
        return TextureCache.get_cache_class_from_cache_type(
            self.texture_cache_type
            )

    def parse(self, rawdata):
        super().parse(rawdata)

    def serialize(self):
        self.cache_type_version = ANIM_CACHE_VER

        cache_header_rawdata = super().serialize()
        return cache_header_rawdata


class Ps2AnimationCache(AnimationCache):
    cache_type          = constants.ANIMATION_CACHE_EXTENSION_PS2
    model_cache_type    = constants.MODEL_CACHE_EXTENSION_PS2
    texture_cache_type  = constants.TEXTURE_CACHE_EXTENSION_PS2


class XboxAnimationCache(Ps2AnimationCache):
    cache_type          = constants.ANIMATION_CACHE_EXTENSION_XBOX
    model_cache_type    = constants.MODEL_CACHE_EXTENSION_XBOX
    texture_cache_type  = constants.TEXTURE_CACHE_EXTENSION_XBOX


class GamecubeAnimationCache(Ps2AnimationCache):
    cache_type          = constants.ANIMATION_CACHE_EXTENSION_NGC
    model_cache_type    = constants.MODEL_CACHE_EXTENSION_NGC
    texture_cache_type  = constants.TEXTURE_CACHE_EXTENSION_NGC


class DreamcastAnimationCache(AnimationCache):
    cache_type          = constants.ANIMATION_CACHE_EXTENSION_DC
    model_cache_type    = constants.MODEL_CACHE_EXTENSION_DC
    texture_cache_type  = constants.TEXTURE_CACHE_EXTENSION_DC


class ArcadeAnimationCache(AnimationCache):
    cache_type          = constants.ANIMATION_CACHE_EXTENSION_ARC
    model_cache_type    = constants.MODEL_CACHE_EXTENSION_ARC
    texture_cache_type  = constants.TEXTURE_CACHE_EXTENSION_ARC


AnimationCache._sub_classes = {
    cls.cache_type: cls for cls in (
        Ps2AnimationCache, XboxAnimationCache, GamecubeAnimationCache,
        DreamcastAnimationCache, ArcadeAnimationCache
        )
    }
