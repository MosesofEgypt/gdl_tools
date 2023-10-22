from supyr_struct.defs.tag_def import TagDef
from .objs.wad import WadTag
from .shop import item_lump
from .wdata import enemy_data_lump, bosscam_data_lump, camera_data_lump,\
    sound_data_lump, audio_data_lump, map_data_lump, level_data_lump,\
    world_data_lump, level_data_arcade_lump, enemy_data_arcade_lump
from .pdata import effects_lump, damages_lump, player_data_lump,\
    effects_arcade_lump, player_data_arcade_lump
from .rom import font_lump, string_data_lump, string_offsets_lump,\
    messages_lump, message_list_indices_lump, message_lists_lump,\
    defs_data_lump, message_def_offsets_lump, message_list_def_offsets_lump
from ..common_descs import lumps_array, lump_headers, lump_fcc, wad_header

def get(): return wad_def, wad_arcade_def


lump_types = (
    dict(NAME='item', VALUE=lump_fcc('ITEM'), GUI_NAME='shop items'),

    dict(NAME='sfxx', VALUE=lump_fcc('SFXX'), GUI_NAME='sound/visual fx'),
    dict(NAME='damg', VALUE=lump_fcc('DAMG'), GUI_NAME='attack damage'),
    dict(NAME='pdat', VALUE=lump_fcc('PDAT'), GUI_NAME='player data'),

    dict(NAME='desc', VALUE=lump_fcc('DESC'), GUI_NAME='????'),
    dict(NAME='adda', VALUE=lump_fcc('ADDA'), GUI_NAME='????'),
    dict(NAME='node', VALUE=lump_fcc('NODE'), GUI_NAME='????'),
    dict(NAME='move', VALUE=lump_fcc('MOVE'), GUI_NAME='????'),
    dict(NAME='ptrn', VALUE=lump_fcc('PTRN'), GUI_NAME='????'),
    dict(NAME='type', VALUE=lump_fcc('TYPE'), GUI_NAME='????'),

    dict(NAME='anim', VALUE=lump_fcc('ANIM'), GUI_NAME='????'),
    dict(NAME='prop', VALUE=lump_fcc('PROP'), GUI_NAME='????'),
    dict(NAME='texm', VALUE=lump_fcc('TEXM'), GUI_NAME='????'),

    dict(NAME='font', VALUE=lump_fcc('FONT'), GUI_NAME='font'),
    dict(NAME='text', VALUE=lump_fcc('TEXT'), GUI_NAME='string data'),
    dict(NAME='toff', VALUE=lump_fcc('TOFF'), GUI_NAME='string offsets'),
    dict(NAME='strs', VALUE=lump_fcc('STRS'), GUI_NAME='messages'),
    dict(NAME='loff', VALUE=lump_fcc('LOFF'), GUI_NAME='message list indices'),
    dict(NAME='list', VALUE=lump_fcc('LIST'), GUI_NAME='message lists'),
    dict(NAME='defs', VALUE=lump_fcc('DEFS'), GUI_NAME='def data'),
    dict(NAME='sdef', VALUE=lump_fcc('SDEF'), GUI_NAME='message def offsets'),
    dict(NAME='ldef', VALUE=lump_fcc('LDEF'), GUI_NAME='message list def offsets'),

    dict(NAME='enmy', VALUE=lump_fcc('ENMY'), GUI_NAME='enemy type'),
    dict(NAME='bcam', VALUE=lump_fcc('BCAM'), GUI_NAME='boss camera'),
    dict(NAME='cams', VALUE=lump_fcc('CAMS'), GUI_NAME='cameras'),
    dict(NAME='snds', VALUE=lump_fcc('SNDS'), GUI_NAME='sounds'),
    dict(NAME='auds', VALUE=lump_fcc('AUDS'), GUI_NAME='audio streams'),
    dict(NAME='maps', VALUE=lump_fcc('MAPS'), GUI_NAME='maps'),
    dict(NAME='levl', VALUE=lump_fcc('LEVL'), GUI_NAME='level details'),
    dict(NAME='wrld', VALUE=lump_fcc('WRLD'), GUI_NAME='world description'),
    )
lump_structs = {
    "item": item_lump,

    "sfxx": effects_lump,
    "damg": damages_lump,
    "pdat": player_data_lump,

    #"desc": ????,
    #"adda": ????,
    #"node": ????,
    #"move": ????,
    #"ptrn": ????,
    #"type": ????,

    #"anim": ????,
    #"prop": ????,
    #"texm": ????,

    "font": font_lump,
    "text": string_data_lump,
    "toff": string_offsets_lump,
    "strs": messages_lump,
    "loff": message_list_indices_lump,
    "list": message_lists_lump,
    "defs": defs_data_lump,
    "sdef": message_def_offsets_lump,
    "ldef": message_list_def_offsets_lump,

    "enmy": enemy_data_lump,
    "bcam": bosscam_data_lump,
    "cams": camera_data_lump,
    "snds": sound_data_lump,
    "auds": audio_data_lump,
    "maps": map_data_lump,
    "levl": level_data_lump,
    "wrld": world_data_lump,
    }
arcade_lump_structs = dict(lump_structs)
arcade_lump_structs.update(
    enmy = enemy_data_arcade_lump,
    levl = level_data_arcade_lump,
    sfxx = effects_arcade_lump,
    pdat = player_data_arcade_lump,
    )

wad_def = TagDef("wad",
    wad_header,
    lump_headers(*lump_types),
    lumps_array(**lump_structs),
    ext=".wad", endian="<", tag_cls=WadTag
    )

wad_arcade_def = TagDef("wad_arcade",
    wad_header,
    lump_headers(*lump_types, extra_size_field=False),
    lumps_array(**arcade_lump_structs),
    ext=".wad", endian="<", tag_cls=WadTag
    )
