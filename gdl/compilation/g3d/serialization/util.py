from supyr_struct.buffer import BytearrayBuffer
from ...util import *


class FixedBytearrayBuffer(BytearrayBuffer):
    __slots__ = ('_pos',)
    def __init__(self, *args):
        self._pos = 0
