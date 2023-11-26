import panda3d

from . import util
from ..assets.texture import Texture
from ...compilation.g3d import constants as g3d_const
from ...compilation.g3d.serialization.texture import G3DTexture
from ...compilation.g3d.serialization import texture_util
from ...compilation.g3d.texture import bitmap_to_texture_cache


def load_textures_from_objects_tag(
        objects_tag, textures_filepath, is_ngc=False
        ):
    textures = {}
    try:
        objects_tag.load_texdef_names()
    except Exception:
        # oh well...
        pass

    _, texture_assets = objects_tag.get_cache_names()
    texture_names = {
        asset["index"]: asset["name"] for asset in texture_assets.values()
        }
    objects = objects_tag.data.objects
    bitmaps = objects_tag.data.bitmaps
    obj_ver = objects_tag.data.version_header.version.enum_name

    with open(textures_filepath, "rb") as f:
        for i, name in texture_names.items():
            if i < 0:
                # NOTE: we use negative indices in the bitmap_assets to indicate
                #       that the name was taken from a dreamcast lightmap, and
                #       doesn't actually have a bitmap block tied to this bitmap.
                try:
                    bitm = getattr(objects[-(i+1)].model_data, "lightmap_header", None)
                    if (obj_ver == "v0" and (
                        getattr(bitm, "dc_lm_sig1", None) != g3d_const.DC_LM_HEADER_SIG1 or
                        getattr(bitm, "dc_lm_sig2", None) != g3d_const.DC_LM_HEADER_SIG2
                        )):
                        continue
                except Exception:
                    continue
            else:
                bitm = bitmaps[i]

            flags = getattr(bitm, "flags", None)
            if (getattr(flags, "external", False) or
                getattr(bitm, "frame_count", 0) > 0):
                # empty placeholder texture
                p3d_texture = panda3d.core.Texture()
                force_alpha = False
                format_name = (
                    bitm.format.enum_name
                    if hasattr(bitm, "format") else
                    ""
                    )
            else:
                g3d_texture = G3DTexture()
                try:
                    g3d_texture.import_g3d(bitmap_to_texture_cache(bitm, f, is_ngc))
                except (ValueError, AttributeError):
                    # invalid bitmap
                    pass

                format_name = g3d_texture.format_name
                # applies to arcade and dreamcast
                force_alpha = obj_ver in ("v0", "v1") and g3d_texture.has_alpha

                if not g3d_texture.textures:
                    continue

                p3d_texture = util.g3d_texture_to_p3d_texture(g3d_texture)

            p3d_texture.setWrapU(
                panda3d.core.SamplerState.WM_clamp if getattr(flags, "clamp_u", False) else
                panda3d.core.SamplerState.WM_repeat)
            p3d_texture.setWrapV(
                panda3d.core.SamplerState.WM_clamp if getattr(flags, "clamp_v", False) else
                panda3d.core.SamplerState.WM_repeat)

            texture = Texture(
                name=name, signed_alpha=texture_util.is_alpha_signed(format_name),
                p3d_texture=p3d_texture, force_model_alpha=force_alpha
                )

            # in some instances we need to reference textures by
            # index, while in others we need to reference by name
            textures[name]  = texture
            textures[i]     = texture

    return textures
