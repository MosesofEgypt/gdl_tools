from supyr_struct.buffer import BytearrayBuffer


def calculate_padding(buffer_len, stride):
    return (stride-(buffer_len%stride)) % stride


class FixedBytearrayBuffer(BytearrayBuffer):
    __slots__ = ('_pos',)
    def __init__(self, *args):
        self._pos = 0
