import struct

NCC_TABLE_STRUCT = struct.Struct('<16B 8I')
#   NOTE: a and b coeff are 9-bit signed ints packed into lowest 27 bits
#   uint8  y_coeff[16]
#   uint32 ab_coeffs[8]

def quantize_rgb_888_to_yiq_888(r, g, b):
    # TODO: write this
    return (r + g + b) / 3, 0, 0


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
        raise NotImplementedError()
        y = [0] * 16
        a = [0] * 12
        b = [0] * 12

        # TODO: write this. look at _txPixQuantize_YIQ422 in swlibs/texus2/lib/ncc.c
        # Step 1: convert entire texture from RGB888 to YIQ888
        # Step 2: while converting, track histogram of each YIQ value
        # Step 3: determine Y/I/Q min/max from ignoring upper/lower X% of values
        # Step 4: calculate YAB table from min/max bounds
        # NOTE: this won't work well if resources are extracted and then
        #       recompressed as YIQ, as the A and B ranges will keep shrinking.
        #       need to include flag in metadata to prevent discarding values.
        self.y = tuple(y)
        self.a = tuple(a)
        self.b = tuple(b)

    def import_from_rawdata(self, rawdata):
        ncc_values = NCC_TABLE_STRUCT.unpack(rawdata)
        coeffs = []

        for packed_vals in ncc_values[16: 24]:
            coeffs.append((packed_vals >> 18) & 0x1FF)
            if coeffs[-1] & 0x100: coeffs[-1] -= 0x200

            coeffs.append((packed_vals >> 9) & 0x1FF)
            if coeffs[-1] & 0x100: coeffs[-1] -= 0x200

            coeffs.append(packed_vals & 0x1FF)
            if coeffs[-1] & 0x100: coeffs[-1] -= 0x200

        self.y = tuple(ncc_values[0: 16])
        self.a = tuple(coeffs[ 0: 12])
        self.b = tuple(coeffs[12: 24])

    def export_to_rawdata(self):
        ab_packed = []
        ab_unpacked = (*self.a, *self.b)
        for i in range(0, 24, 3):
            val0, val1, val2 = ab_unpacked[i: i+3]
            if val0 < 0: val0 += 0x200
            if val1 < 0: val1 += 0x200
            if val2 < 0: val2 += 0x200
            ab_packed.append((val0 << 18) | (val1 << 9) | val2)

        return NCC_TABLE_STRUCT.pack(*self.y, *ab_packed)
