
# EXPERIMENTAL!!! borrowing halo ce animation
# format if the reclaimer module is available
try:
    from reclaimer.animation import jma as halo_anim
    del halo_anim
    JMM_SUPPORT = JMS_SUPPORT = True
except ModuleNotFoundError:
    JMM_SUPPORT = JMS_SUPPORT = False

# the extensions used on the objects, textures, anim, and worlds files
PS2_EXTENSION = 'ps2'
NGC_EXTENSION = 'ngc'
ARC_EXTENSION = 'rom'
DC_EXTENSION  = 'rom'

PS2_WAD_UNKNOWN_EXTENSION = "unk"
PS2_WAD_INTERNAL_NAMES_EXTENSION = "names"

PS2_WAD_FILENAME = "wad.bin"

# set up the filepaths and foldernames that textures, animations,
# models, and definitions will be extracted to and imported from.
DATA_FOLDERNAME   = 'assets'
IMPORT_FOLDERNAME = '__g3d_cache'
EXPORT_FOLDERNAME = 'source' # deprecated

METADATA_ASSET_EXTENSIONS = (
    "yaml",
    "yml",
    "json",
    )
ANIMATION_ASSET_EXTENSIONS = ()
ANIMATION_ASSET_EXTENSIONS += ("jmm",) if JMM_SUPPORT else ()
ACTOR_ASSET_EXTENSIONS = ()
ACTOR_ASSET_EXTENSIONS += ("jms",) if JMM_SUPPORT else ()
MODEL_ASSET_EXTENSIONS = (
    "obj",
    #"dae",
    )
COLLISION_ASSET_EXTENSIONS = (
    "obj",
    #"dae",
    )
TEXTURE_ASSET_EXTENSIONS = (
    "tga",
    "dds",
    "png",
    )
ARC_HDD_FILE_EXTENSIONS = (
    "fnt",
    "3df",
    "rom",
    "wad",
    "bnk",
    "raw",
    "sbi",
    "", # no extension
    )
DC_ROMDISK_FILE_EXTENSIONS = (
    "fnt",
    "rom",
    "wad",
    "bnk",
    "str",
    "bin",
    "drv",
    "da",
    "m1v",
    "pvr",
    "txt",
    )
PS2_WAD_FILE_EXTENSIONS = (
    "ads",
    "fnt",
    "irx",
    "ps2",
    "rom",
    "vbk",
    "wad",
    PS2_WAD_UNKNOWN_EXTENSION,
    PS2_WAD_INTERNAL_NAMES_EXTENSION,
    )

WAD_LUMP_TYPES = frozenset((
    'ITEM',
    'SFXX', 'DAMG', 'PDAT',
    'DESC', 'ADDA', 'NODE', 'MOVE', 'PTRN', 'TYPE',
    'ANIM', 'PROP', 'TEXM',
    'FONT', 'TEXT', 'TOFF', 'STRS', 'LOFF', 'LIST', 'DEFS', 'SDEF', 'LDEF',
    'ENMY', 'BCAM', 'CAMS', 'SNDS', 'AUDS', 'MAPS', 'LEVL', 'WRLD'
    ))
