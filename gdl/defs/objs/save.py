from math import sqrt
from supyr_struct.buffer import BytearrayBuffer
from .xboxsave import *

GDL_SIGKEY =  (b'\x04\x60\x07\x75\xB9\x14\xBF\xE3\x09\xAE'+
               b'\x40\x83\x70\xF1\x8E\xEA\xC0\xD7\xF9\x61')
EXP_LIN_RATE = 4600 # exp per level after level 60
EXP_CUTOFF = 165200
LEVEL_CUTOFF = 60


def level_to_exp(level):
    level = max(0, level)
    if level > LEVEL_CUTOFF:
        return int(round((level - LEVEL_CUTOFF) * EXP_LIN_RATE + EXP_CUTOFF))
    return int(round((level * 30 + 1000) * (level - 1)))


def exp_to_level(exp):
    exp = max(0, exp)
    if exp > EXP_CUTOFF:
        return round((exp - EXP_CUTOFF) / EXP_LIN_RATE + LEVEL_CUTOFF, 10)
    # solve quadratic equation to get this
    return round(sqrt(exp/30 + 100/3 + 9409/36) - 97/6, 10)


class GdlSaveTag(Tag):
    def calculate_internal_values(self, to_internal=False):
        for char_attr in self.data.save_data.character_attrs:
            if to_internal and char_attr.level is not None:
                char_attr.exp = level_to_exp(char_attr.level)
            elif char_attr.exp is not None:
                char_attr.level = exp_to_level(char_attr.exp)


class GdlXboxSaveTag(GdlSaveTag, XboxSaveTag):
    sigkey = GDL_SIGKEY


class GdlPs2SaveTag(GdlSaveTag):
    pass


class GdlNgcSaveTag(GdlSaveTag):

    def calc_internal_data(self):
        save_data = self.data.gci_block_data.save_data
        # copy data from saves into dir infos
        for i, save in enumerate(save_data.saves):
            if len(save_data.dir_infos) <= i:
                save_data.dir_infos.append()

            dir_info = save_data.dir_infos[i]
            if save.level_total:
                dir_info.level_total = save.level_total
                dir_info.last_character_type.data = save.last_character_type.data
                dir_info.name = save.name
            else:
                dir_info.level_total = -1
                dir_info.last_character_type.data = -1
                dir_info.name = "Empty"

        # calculate checksums
        save_data.integrity_header.checksum = 0
        rawdata = save_data.serialize(buffer=BytearrayBuffer())
        save_data.integrity_header.checksum = sum(rawdata) & 0xFFFF 

    def serialize(self, **kwargs):
        self.calc_internal_data()
        return super().serialize(**kwargs)
