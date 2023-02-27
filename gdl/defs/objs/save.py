from math import sqrt
from .xboxsave import *

GDL_SIGKEY =  (b'\x04\x60\x07\x75\xB9\x14\xBF\xE3\x09\xAE'+
               b'\x40\x83\x70\xF1\x8E\xEA\xC0\xD7\xF9\x61')
EXP_LIN_RATE = 4600 # exp per level after level 60
EXP_CUTOFF = 165200
LEVEL_CUTOFF = 60


def level_to_exp(level):
    level = max(0, level)
    if level > LEVEL_CUTOFF:
        return int(round((level - LEVEL_CUTOFF) * 4600 + EXP_CUTOFF))
    return int(round((level * 30 + 1000) * (level - 1)))


def exp_to_level(exp):
    exp = max(0, exp)
    if exp > EXP_CUTOFF:
        return (exp - EXP_CUTOFF) / 4600 + LEVEL_CUTOFF
    # solve quadratic equation to get this
    return sqrt(exp/30 + 100/3 + 9409/36) - 97/6


class GdlSaveTag(XboxSaveTag):
    sigkey  = GDL_SIGKEY

    def _calculate_internal_values(self, to_internal=False):
        for char_attr in self.data.save_data.character_attrs:
            if to_internal:
                char_attr.exp = level_to_exp(char_attr.level)
            else:
                char_attr.level = exp_to_level(char_attr.exp)

    def parse(self, **kwargs):
        super().parse(**kwargs)
        self._calculate_internal_values(to_internal=False)

    def serialize(self, **kwargs):
        self._calculate_internal_values(to_internal=True)
        super().serialize(**kwargs)
