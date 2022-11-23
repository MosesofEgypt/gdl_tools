from supyr_struct.field_types import *
from supyr_struct.defs.constants import *
from supyr_struct.util import *


def sub_objects_size(node=None, parent=None, attr_index=None,
                     rawdata=None, new_value=None, *args, **kwargs):
    if new_value is None:
        return max(node.parent.parent.sub_objects_count - 1, 0)
    # NOTE: don't include a settter here. we'll let the models
    #       array handle setting the value to an appropriate amount


def qword_size(node=None, parent=None, attr_index=None,
               rawdata=None, new_value=None, *args, **kwargs):
    if node and parent is None:
        parent = node.parent
    if new_value is not None:
        parent.qword_count = (new_value + 8)//16 - 1
    return (parent.qword_count + 1)*16 - 8


def lump_parser(self, desc, node=None, parent=None, attr_index=None,
                      rawdata=None, root_offset=0, offset=0, **kwargs):
    if node is None:
        node = (desc.get(NODE_CLS, self.node_cls)
                     (desc, parent=parent, init_attrs=rawdata is None))
        parent[attr_index] = node
        
    b_desc  = desc['SUB_STRUCT']
    b_f_type = b_desc['TYPE']

    if attr_index is not None and desc.get('POINTER') is not None:
        offset = node.get_meta('POINTER', **kwargs)

    list.__delitem__(node, slice(None, None, None))
    kwargs.update(root_offset=root_offset, parent=node, rawdata=rawdata)

    for i in range(node.get_size()):
        #need to append a new entry to the block
        list.append(node, None)
        offset = b_f_type.parser(b_desc, attr_index=i, offset=offset, **kwargs)

    return offset


LumpArray = FieldType(base=Array, name='LumpArray', parser=lump_parser)
