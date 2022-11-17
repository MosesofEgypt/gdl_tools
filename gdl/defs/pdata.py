from supyr_struct.defs.tag_def import TagDef
from ..common_descs import *
from ..field_types import *

def get(): return pdata_def

lump_kw = {SIZE:lump_size, POINTER:lump_pointer}

#############################
'''individual lump structs'''
#############################

player_data = Container('player data',
    SInt16('num sfx'),
    SInt16('num damage'),
    Pointer32('plyr sfx'),
    Pointer32('plyr damage'),

    SInt16('turbo a close'),
    SInt16('turbo a low'),
    SInt16('turbo a step'),
    SInt16('turbo a 360'),
    SInt16('turbo a throw'),
    SInt16('turbo b'),
    SInt16('turbo c1'),
    SInt16('turbo c2'),
    SInt16('combo1'),
    SInt16('combo2'),
    SInt16('combo hit'),
    SInt16('victory'),
    SInt32('init flag'),

    QStruct('strength', INCLUDE=stat),
    QStruct('speed', INCLUDE=stat),
    QStruct('armor', INCLUDE=stat),
    QStruct('magic', INCLUDE=stat),

    Float('height'),
    Float('width'),
    Float('attny'),
    Float('coly'),
    Float('powerup time'),
    QStruct('weapon offset',   INCLUDE=xyz_float),
    Array('weapon fx offsets',
          SIZE=10, SUB_STRUCT=Struct("weapon fx offset", INCLUDE=xyz_float)
          ),
    Array('weapon fx scales',
          SIZE=10, SUB_STRUCT=Struct("weapon fx scale", INCLUDE=xyz_float)
          ),
    QStruct('turbo a offset', INCLUDE=xyz_float),
    QStruct('familiar offset', INCLUDE=xyz_float),
    QStruct('familiar proj offset', INCLUDE=xyz_float),
    LFloat('streak fwd mul'),
    )


'''lump block arrays'''
effects = Lump('effects',
    SUB_STRUCT=effect, **lump_kw
    )
damages = Lump('damages',
    SUB_STRUCT=damage, **lump_kw
    )
player_datas = Lump('player datas',
    SUB_STRUCT=player_data, **lump_kw
    )

pdata_def = TagDef("pdata",
    QStruct('wad header',
        UInt32('lump headers pointer'),
        UInt32('lump count', DEFAULT=3),
        Pad(8),
        VISIBLE=False,
        ),
    lump_headers,

    #these need to be in a container to have the same index
    #ordering as their headers in the lump_headers array
    Container('lumps',
        effects,
        damages,
        player_datas,
        ),

    ext=".wad",
    )
