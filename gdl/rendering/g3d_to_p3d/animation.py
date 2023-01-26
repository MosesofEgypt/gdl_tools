import panda3d

from . import util
from ..assets.texture import Texture
from ..assets.animation import TextureAnimation


def load_texmods_from_anim_tag(anim_tag, textures, ext_textures):
    atree_tex_anims  = {}
    global_tex_anims = {}
    atrees = anim_tag.data.atrees

    for i, texmod in anim_tag.data.texmods:
        reverse = False
        loop    = True
        if texmod.atree >= 0 and texmod.seq_index >= 0:
            actor_name = ""
            seq_name   = ""
            if texmod.atree in range(len(atrees)):
                atree      = atrees[texmod.atree]
                sequences  = atree.atree_header.atree_data.atree_sequences
                actor_name = atree.name
                if texmod.seq_index in range(len(sequences)):
                    sequence = sequences[texmod.seq_index]
                    seq_name = sequence.name
                    reverse  = bool(sequence.flags.play_reversed)
                    loop     = bool(sequence.repeat.data)

            tex_anims = atree_tex_anims.setdefault(actor_name, {}).setdefault(seq_name, {})
        else:
            tex_anims = global_tex_anims
            
        tex_anim = tex_anims.setdefault(texmod.name, TextureAnimation(
            name=texmod.name, loop=loop, reverse=reverse
            ))
        texmod_type = texmod.type.transform.enum_name

        # subtract 1 to account for frame 0 being t=0
        frame_steps     = max(1, texmod.frame_count - 1)
        frame_rate      = 30 / frame_steps
        tex_swap_rate   = 30 / max(1, texmod.frames_per_tex)
        transform_start = (texmod.start_frame / 30) * frame_rate

        if texmod_type == "mip_blend":
            pass # TODO: figure this out
        elif texmod_type in ("fade_in", "fade_out"):
            tex_anim.fade_rate  = frame_rate * (-1 if texmod_type in "fade_out" else 1)
            tex_anim.fade_start = transform_start
        elif texmod_type == "scroll_h":
            tex_anim.scroll_rate_h = frame_rate
            tex_anim.fade_start = transform_start # TODO: determine if this is used here
        elif texmod_type == "scroll_v":
            tex_anim.scroll_rate_v = frame_rate
            tex_anim.fade_start = transform_start # TODO: determine if this is used here
        elif texmod_type == "external":
            pass # TODO: figure this out
        else:
            texture_frames = []
            for j in range(texmod.type.source_index.idx,
                           texmod.type.source_index.idx + abs(texmod.frame_count)):
                if j in textures:
                    texture_frames.append(textures[i])
                else:
                    # TODO: throw an error about missing frame textures
                    pass

            tex_anim.frame_rate  = frame_rate * tex_swap_rate
            tex_anim.start_frame = texmod.tex_start_frame
            tex_anim.frame_data  = texture_frames

    return atree_tex_anims, global_tex_anims
