from supyr_struct.buffer import BytearrayBuffer, BytesBuffer
from supyr_struct.blocks.union_block import UnionBlock

# seeking is broken in supyr(can't seek to start)
BytesBuffer.seek = BytearrayBuffer.seek

class FixedBytearrayBuffer(BytearrayBuffer):
    __slots__ = ('_pos',)
    def __init__(self, *args):
        self._pos = 0
        bytearray.__init__(self, *args)


def fixed_union_block_flush(self):
    u_node = object.__getattribute__(self, 'u_node')
    u_index = object.__getattribute__(self, 'u_index')
    desc = object.__getattribute__(self, 'desc')
    assert u_index is not None, (
        "Cannot flush a UnionBlock that has no active member.")

    try:
        u_desc = u_node.desc
    except AttributeError:
        u_desc = desc[u_index]

    u_type = u_desc['TYPE']
    self._pos = 0
    object.__setattr__(self, 'u_index', None)
    if u_type.endian == '>' and u_type.f_endian in '=>':
        u_type.serializer(u_node, self, None, self, 0,
                          desc.get('SIZE', 0) - u_desc.get('SIZE', u_type.size))
    else:
        u_type.serializer(u_node, self, None, self)

    object.__setattr__(self, 'u_index', u_index)

UnionBlock.flush = fixed_union_block_flush
