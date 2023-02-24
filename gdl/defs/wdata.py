from supyr_struct.defs.tag_def import TagDef
from .objs.wad import WadTag
from ..common_descs import *
from ..field_types import *

def get(): return wdata_def

enemy_data_lump = Lump('enemy_datas',
    SUB_STRUCT=Struct('enemy_data',
        SEnum32("type", *ENEMY_TYPES),
        UEnum32("subtype",
            ("none",          0x0),
            ("ankle_biter",   0x1),
            ("generator_pri", 0x2), # used as main enemy in most levels(GUESS)
            ("generator_sec", 0x3), # used as main enemy in few/one levels(GUESS)
            ("aux",           0x4), # uses "aux" folder(doesn't seem to determine ranged/not)
            ("mini_boss",     0x5), # uses different dir depending on level/name
            ("main_boss",     0x9),
            ("special_l2",    0xC), # uses strength suffixed dirname(used in TEMPLE.WAD)
            ("special_l3",    0xD), # uses strength suffixed dirname(used in HELL.WAD)
            ),
        StrNntLatin1("audname", SIZE=8),
        StrNntLatin1("name", SIZE=8),
        SIZE=24
        ),
    DYN_NAME_PATH='.type.enum_name', WIDGET=DynamicArrayFrame
    )

bosscam_data_lump = Lump('bosscam_datas',
    SUB_STRUCT=Struct('bosscam_data',
        Bool32("flags",
            "track_boss",
            "stay_in_front",
            "stay_in_back",
            "watch_boss",
            "track_all",
            "watch_mode2",
            "unused1",
            "unused2",
            "zoom_in",
            "zoom_out",
            ),
        Float("max_yaw", UNIT_SCALE=UNIT_SCALE_RAD_TO_DEG),
        Float("cos_max_yaw"),

        Float("min_dist"),
        Float("min_pdist"),

        Float("max_dist"),
        Float("max_pdist"),

        Struct("pitch", INCLUDE=radian_float_min_max),

        QStruct("min_attn", INCLUDE=xyz_float),
        QStruct("max_attn", INCLUDE=xyz_float),
        QStruct("key_attn", INCLUDE=xyz_float), # window shard?
        QStruct("wiz_attn", INCLUDE=xyz_float), # sumner?
        SIZE=84
        )
    )

camera_data_lump = Lump('camera_datas',
    SUB_STRUCT=Struct('camera_data',
        SInt16("yaw_dir"),
        SInt16("pitch_dir"),
        Float("dp"),
        Float("min_pitch", UNIT_SCALE=UNIT_SCALE_RAD_TO_DEG),

        QStruct("min", INCLUDE=xyz_float),
        QStruct("max", INCLUDE=xyz_float),

        SInt8("limits"),
        SInt8("start_event"),

        SInt16("att_cam"),
        Float("att_data"),
        Struct("radius", INCLUDE=float_min_max),
        SInt16("enemy_max"),
        SInt16("special_radius"),

        Float("max_pitch", UNIT_SCALE=UNIT_SCALE_RAD_TO_DEG),
        Float("pitch_sub", UNIT_SCALE=UNIT_SCALE_RAD_TO_DEG),
        Float("pitch_mul"),
        Float("pitch_add", UNIT_SCALE=UNIT_SCALE_RAD_TO_DEG),

        Float("dist_mul_add"),
        Float("dist_mul_fac"),
        Struct("dist_mul", INCLUDE=float_min_max),

        Float("smooth"),
        Struct("yaw", INCLUDE=radian_float_min_max),
        Struct("boss_radius", INCLUDE=float_min_max),
        SIZE=108
        )
    )

sound_data_lump = Lump('sound_datas',
    SUB_STRUCT=Struct('sound_data',
        StrNntLatin1("name", SIZE=16),
        SInt32("idx"),
        SInt16("volume"),
        SInt16("priority"),
        SIZE=24
        ),
    DYN_NAME_PATH='.name', WIDGET=DynamicArrayFrame
    )

audio_data_lump = Lump('audio_datas',
    SUB_STRUCT=Struct('audio_data',
        StrNntLatin1("bank", SIZE=16),
        SInt16("enter_sound"),
        SInt16("hit_sound"),
        SInt32("name_sound"),
        StrNntLatin1("stream", SIZE=16),
        SInt16("area_count"),
        SInt16("stereo"),
        SInt16Array("part_counts", SIZE=2*8),
        SIZE=60
        ),
    DYN_NAME_PATH='.bank', WIDGET=DynamicArrayFrame
    )

map_data_lump = Lump('map_datas',
    SUB_STRUCT=Struct('map_data',
        QStruct("offset", INCLUDE=xy_float),
        Array("dash",
            SUB_STRUCT=QStruct("offset", INCLUDE=xy_float),
            SIZE=8
            ),
        SIZE=72
        )
    )

fog_data = Struct("fog_data",
    UEnum8("type",
        # TODO: figure out if this is correct
        "none",
        "exp",
        "exp2",
        "linear",
        ),
    QStruct("color", INCLUDE=bgr_uint8),
    Float("intensity"),
    Float("density"),
    QStruct("amount", INCLUDE=float_min_max),
    Float("near_w"),
    Float("far_w"),
    SIZE=28
    )

level_data_lump = Lump('level_datas',
    SUB_STRUCT=Struct('level_data',
        Bool32("flags",
            "stun_wave",
            "hurt_wave",
            "time_wave",
            "player_light",
            ),
        SInt16("enabled"),
        SInt16("setup"),
        StrNntLatin1("name", SIZE=4),
        SInt16("wave_time"),
        SInt16("dummy"),
        StrNntLatin1("prep", SIZE=4),
        StrNntLatin1("title", SIZE=16),
        StrNntLatin1("audbank", SIZE=16),
        StrNntLatin1("movie", SIZE=16),
        SEnum32("boss_type", *ENEMY_TYPES),
        SInt32("early_enemies"),
        QStruct("enemy_types",
            # seems like the first defined enemy of each subtype gets used
            # for that purpose. This is based on ghost and zombie are defined
            # in G4, but only ghost is used(ghost is defined before zombie)
            # The "special" generator type seems to spawn from
            # all valid "generator" palette enemy types
            SInt16("enemy_0"),
            SInt16("enemy_1"),
            SInt16("enemy_2"),
            SInt16("enemy_3"),
            SInt16("enemy_4"),
            SInt16("enemy_5"),
            ),
        SInt16("camera_idx"),
        SInt16("audio_idx"),
        SInt16("map_idx"),
        Pad(2),
        Pointer32("camera_data"),
        Pointer32("audio_data"),
        Pointer32("map_data"),
        Pointer32("bosscam_data"),
        fog_data,
        SInt16("boss_camera_index"),
        SInt16("max_enemies"),
        SEnum16("rune",
            "none",
            *RUNESTONES
            ),
        SEnum16("legend", *LEGEND_ITEMS),
        Float("music_volume"),
        Float("sound_volume"),
        Float("p_level"),
        Float("xp_multiplier"),
        Float("damage_multiplier"),
        Float("difficulty"),
        Float("enemy_health"),
        Float("enemy_speed"),
        Float("enemy_vision_radius"),
        Float("enemy_attack"),
        Float("enemy_damage"),
        Float("enemy_move_rate"),
        Float("enemy_move_speed"),
        Float("enemy_move_acceleration"),
        Float("gen_health"),
        Float("gen_rate"),
        Float("gen_max"),
        Float("trap_rate"),
        Float("trap_damage"),
        SInt32("shop_max_gold"),
        SInt32("shop_max_kills"),
        SInt32("shop_max_exp"),
        Float("ambient"),
        Float("light_dir", INCLUDE=bgr_float),
        Float("light_color_fp", INCLUDE=bgr_float),
        Float("light_inten"),
        SIZE=268
        ),
    DYN_NAME_PATH='.name', WIDGET=DynamicArrayFrame
    )

world_data_lump = Lump('world_datas',
    SUB_STRUCT=Struct('world_data',
        SEnum32("type", *WAVE_TYPES),
        StrNntLatin1("wave_name", SIZE=16),
        SInt16("boss_key"),  # doesn't determine the boss key(most WDATAs have wrong values)
        SInt16("curr_level"),
        SInt16("num_levels"),
        SInt16("num_sounds"),
        Pointer32("level_data_pointer", VISIBLE=False),
        Pointer32("enemy_data_pointer", VISIBLE=False),
        Pointer32("camera_data_pointer", VISIBLE=False),
        Pointer32("audio_data_pointer", VISIBLE=False),
        Pointer32("sound_data_pointer", VISIBLE=False),
        Pointer32("map_data_pointer", VISIBLE=False),
        Pointer32("boss_cam_data_pointer", VISIBLE=False),
        SIZE=56
        ),
    DYN_NAME_PATH='.wave_name', WIDGET=DynamicArrayFrame
    )

wdata_lump_headers = lump_headers(
    {NAME:'enmy', VALUE:lump_fcc('ENMY'), GUI_NAME:'enemy type'},
    {NAME:'bcam', VALUE:lump_fcc('BCAM'), GUI_NAME:'boss camera'},
    {NAME:'cams', VALUE:lump_fcc('CAMS'), GUI_NAME:'cameras'},
    {NAME:'snds', VALUE:lump_fcc('SNDS'), GUI_NAME:'sounds'},
    {NAME:'auds', VALUE:lump_fcc('AUDS'), GUI_NAME:'audio streams'},
    {NAME:'maps', VALUE:lump_fcc('MAPS'), GUI_NAME:'maps'},
    {NAME:'levl', VALUE:lump_fcc('LEVL'), GUI_NAME:'level details'},
    {NAME:'wrld', VALUE:lump_fcc('WRLD'), GUI_NAME:'world description'},
    )
wdata_lumps_array = lumps_array(
    enmy = enemy_data_lump,
    bcam = bosscam_data_lump,
    cams = camera_data_lump,
    snds = sound_data_lump,
    auds = audio_data_lump,
    maps = map_data_lump,
    levl = level_data_lump,
    wrld = world_data_lump,
    )

wdata_def = TagDef("wdata",
    wad_header,
    wdata_lump_headers,
    wdata_lumps_array,
    ext=".wad", endian="<", tag_cls=WadTag
    )
