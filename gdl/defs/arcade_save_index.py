from supyr_struct.defs.tag_def import TagDef
from ..common_descs import *
from ..field_types import *

def get(): return arcade_save_index_def

password_index_entry = Struct("password_index_entry",
    StrNntLatin1("name", SIZE=2),
    StrNntLatin1("code", SIZE=3),
    UInt32('unknown'),
    UInt16('unknown_index'),
    SIZE=11
    )

arcade_save_index_def = TagDef("arcade_save_index",
    Struct('header',
        UInt32('zero'),
        UInt16('unknown_count0'),
        UInt16('unknown_count1'),
        ),
    Array('password_entries', SUB_STRUCT=password_index_entry, SIZE=1000),
    ext=".rom", endian=">" # strangely, big endian
    )
