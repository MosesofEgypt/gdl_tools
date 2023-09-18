import struct

NCC_TABLE_STRUCT = struct.Struct('<16B 8I')
#   NOTE: a and b coeff are 9-bit signed ints packed into lowest 27 bits
#   uint8  y_coeff[16]
#   uint32 ab_coeffs[8]

class NccTable:
    y = None
    a = None
    b = None
    def __init__(self, y=(0, )*16, a=(0, )*12, b=(0, )*12):
        assert len(y) == 16
        assert len(a) == 12
        assert len(b) == 12
        self.y = tuple(y)
        self.a = tuple(a)
        self.b = tuple(b)

    def calculate_from_pixels(self, pixels):
        y = [0] * 16
        a = [0] * 12
        b = [0] * 12

        # TODO: write this
        self.y = tuple(y)
        self.a = tuple(a)
        self.b = tuple(b)

    def import_from_rawdata(self, rawdata):
        unpacked_data = NCC_TABLE_STRUCT.unpack(rawdata)
        packed_coeffs = unpacked_data[16: 24]
        coeffs = [0]*24
        for i, packed_vals in enumerate(packed_coeffs):
            for j in range(3):
                val = packed_vals & 0x1FF
                if val & 0x100:
                    val -= 0x200

                coeffs[i*3 + 2 - j] = val
                packed_vals >>= 9

        self.y = tuple(unpacked_data[0: 16])
        self.a = tuple(coeffs[ 0: 12])
        self.b = tuple(coeffs[12: 24])

    def export_to_rawdata(self):
        a_packed = []
        b_packed = []
        # TODO: write this once packing format is uncovered
        '''
        for unpacked_vals, packed_vals_arr in [
                (self.a, a_packed),
                (self.b, b_packed)
                ]:
            for i in range(0, 12, 3):
                packed_val = 0
                for j in range(3):
                    val = unpacked_vals[i + j]
                    if val < 0: # if signed
                        val += 0x200

                    packed_val |= (val & 0x1FF) << (j * 9)

                packed_vals_arr.append(packed_val)
        '''

        return NCC_TABLE_STRUCT.pack(*self.y, *a_packed, *b_packed)
