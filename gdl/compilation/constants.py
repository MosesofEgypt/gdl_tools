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
IMPORT_FOLDERNAME = 'cache'
EXPORT_FOLDERNAME = 'source'

METADATA_ASSET_EXTENSIONS = (
    "yaml",
    "yml",
    "json",
    )
ANIMATION_ASSET_EXTENSIONS = (
    )
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
