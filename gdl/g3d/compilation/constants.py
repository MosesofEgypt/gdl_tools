from ..serialization.constants import *

ANIMATION_CACHE_EXTENSION   = "g4d"
MODEL_CACHE_EXTENSION       = "g3d"
TEXTURE_CACHE_EXTENSION_PS2 = "gtx"
TEXTURE_CACHE_EXTENSION_NGC = "gtn"
TEXTURE_CACHE_EXTENSION  = TEXTURE_CACHE_EXTENSION_PS2
TEXTURE_CACHE_EXTENSIONS = (
    TEXTURE_CACHE_EXTENSION_PS2,
    TEXTURE_CACHE_EXTENSION_NGC
    )

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
TEXTURE_ASSET_EXTENSIONS = (
    "tga",
    "dds",
    "png",
    )

# set up the filepaths and foldernames that textures, animations,
# models, and definitions will be extracted to and imported from.
DATA_FOLDERNAME   = 'assets'
IMPORT_FOLDERNAME = 'cache'
EXPORT_FOLDERNAME = 'source'

ANIM_FOLDERNAME       = 'animations'
MOD_FOLDERNAME        = 'objects'
TEX_FOLDERNAME        = 'bitmaps'
SHARED_TEX_FOLDERNAME = 'shared_textures'

PS2_OBJECTS_FILENAME = 'objects.ps2'
NGC_OBJECTS_FILENAME = 'objects.ngc'
PS2_TEXTURES_FILENAME = 'textures.ps2'
NGC_TEXTURES_FILENAME = 'textures.ngc'
OBJECTS_FILENAME   = PS2_TEXTURES_FILENAME
TEXTURES_FILENAME  = PS2_TEXTURES_FILENAME
TEXDEF_FILENAME    = 'texdef.ps2'
MISSING_ASSET_NAME = "__MISSING"
UNNAMED_ASSET_NAME = "__UNNAMED"
LIGHTMAP_NAME      = "LIGHTMAP"

OBJECT_FLAG_NAMES = (
    "tex2", "sharp", "blur", "chrome",
    "alpha", "sort_a", "sort", "error",
    "pre_lit", "lmap_lit", "norm_lit", "dyn_lit"
    )

BITMAP_FLAG_NAMES = (
    "halfres", "see_alpha", "clamp_u", "clamp_v",
    "animation", "external", "tex_shift",
    "has_alpha", "invalid", "dual_tex"
    )
