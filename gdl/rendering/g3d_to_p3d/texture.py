import panda3d

from . import util
from ..assets.texture import Texture
from ...compilation.g3d import constants as g3d_const
from ...compilation.g3d.serialization.texture import G3DTexture, is_alpha_signed


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

    with open(textures_filepath, "rb") as f:
        for index, name in texture_names.items():
            bitm = objects_tag.data.bitmaps[index]
            format_name = bitm.format.enum_name
            if getattr(bitm.flags, "external", False) or bitm.frame_count > 0:
                # empty placeholder texture
                p3d_texture = panda3d.core.Texture()
            else:
                f.seek(bitm.tex_pointer)
                g3d_texture = G3DTexture()
                try:
                    g3d_texture.import_gtx(
                        input_buffer=f, headerless=True, is_ngc=is_ngc, 
                        format_name=bitm.format.enum_name, flags=bitm.flags.data,
                        width=bitm.width, height=bitm.height,
                        )
                except ValueError:
                    # invalid bitmap
                    continue

                p3d_texture = util.g3d_texture_to_p3d_texture(g3d_texture)

            p3d_texture.setWrapU(
                panda3d.core.SamplerState.WM_clamp if getattr(bitm.flags, "clamp_u", False) else
                panda3d.core.SamplerState.WM_repeat)
            p3d_texture.setWrapV(
                panda3d.core.SamplerState.WM_clamp if getattr(bitm.flags, "clamp_v", False) else
                panda3d.core.SamplerState.WM_repeat)

            texture = Texture(
                name=name, signed_alpha=is_alpha_signed(format_name),
                p3d_texture=p3d_texture
                )

            # in some instances we need to reference textures by
            # index, while in others we need to reference by name
            textures[name]  = texture
            textures[index] = texture

    return textures
