from supyr_struct.defs.tag_def import TagDef
from ..common_descs import *
from ..field_types import *

def get(): return pdata_def

player_datas_lump = Lump('player_datas',
    SUB_STRUCT=Container('player_data',
        SInt16('num_sfx'),
        SInt16('num_damage'),
        Pointer32('plyr_sfx'),
        Pointer32('plyr_damage'),

        SInt16('turbo_a_close'),
        SInt16('turbo_a_low'),
        SInt16('turbo_a_step'),
        SInt16('turbo_a_360'),
        SInt16('turbo_a_throw'),
        SInt16('turbo_b'),
        SInt16('turbo_c1'),
        SInt16('turbo_c2'),
        SInt16('combo1'),
        SInt16('combo2'),
        SInt16('combo_hit'),
        SInt16('victory'),
        SInt32('init_flag'),

        QStruct('strength', INCLUDE=stat_range),
        QStruct('speed', INCLUDE=stat_range),
        QStruct('armor', INCLUDE=stat_range),
        QStruct('magic', INCLUDE=stat_range),

        Float('height'),
        Float('width'),
        Float('attny'),
        Float('coly'),
        Float('powerup_time'),
        QStruct('weapon_offset',   INCLUDE=xyz_float),
        Array('weapon_fx_offsets',
              SIZE=10, SUB_STRUCT=Struct("weapon_fx_offset", INCLUDE=xyz_float)
              ),
        Array('weapon_fx_scales',
              SIZE=10, SUB_STRUCT=Struct("weapon_fx_scale", INCLUDE=xyz_float)
              ),
        QStruct('turbo_a_offset', INCLUDE=xyz_float),
        QStruct('familiar_offset', INCLUDE=xyz_float),
        QStruct('familiar_proj_offset', INCLUDE=xyz_float),
        LFloat('streak_fwd_mul'),
        ),
    )

pdata_lump_headers = lump_headers(
    {NAME:'sfxx', VALUE:lump_fcc('SFXX'), GUI_NAME:'sound/visual fx'},
    {NAME:'damg', VALUE:lump_fcc('DAMG'), GUI_NAME:'attack damage'},
    {NAME:'pdat', VALUE:lump_fcc('PDAT'), GUI_NAME:'player data'},
    )
pdata_lumps_array = lumps_array(
    sfxx = effects_lump,
    damg = damages_lump,
    pdat = player_datas_lump,
    )

pdata_def = TagDef("pdata",
    wad_header,
    pdata_lump_headers,
    pdata_lumps_array,
    ext=".wad",
    )
