import panda3d

from . import util
from ..assets.texture import Texture
from ..assets.animation import TextureAnimation


def load_texmods_from_anim_tag(anim_tag, textures):
    seq_tex_anims    = {}
    actor_tex_anims  = {}
    global_tex_anims = {}
    atrees = anim_tag.data.atrees

    for i, texmod in enumerate(anim_tag.data.texmods):
        reverse = False
        loop    = True
        if texmod.atree in range(len(atrees)):
            atree      = atrees[texmod.atree]
            sequences  = atree.atree_header.atree_data.atree_sequences
            actor_name = atree.name.upper().strip()
            anim_name  = ""
            if texmod.seq_index in range(len(sequences)):
                sequence  = sequences[texmod.seq_index]
                anim_name = sequence.name.upper().strip()
                reverse   = bool(sequence.flags.play_reversed)
                loop      = bool(sequence.repeat.data)
                tex_anims = seq_tex_anims.setdefault(actor_name, {}).setdefault(anim_name, {})
            else:
                tex_anims = actor_tex_anims.setdefault(actor_name, {})
        else:
            tex_anims = global_tex_anims
            anim_name = ""

        tex_anim = tex_anims.setdefault(texmod.name, TextureAnimation(
            name=anim_name, tex_name=texmod.name, loop=loop, reverse=reverse
            ))
        texmod_type = texmod.type.transform.enum_name

        frame_rate      = 30 / (texmod.frame_count if texmod.frame_count else 1)
        tex_swap_rate   = 30 / max(1, texmod.frames_per_tex)
        transform_start = (texmod.start_frame / 30) * frame_rate

        if texmod_type == "mip_blend":
            # NOTE: this isn't utilized in any files in the game, so
            #       it's not likely this is actually implemented
            pass
        elif texmod_type in ("fade_in", "fade_out"):
            tex_anim.fade_rate  = frame_rate * (-1 if texmod_type in "fade_out" else 1)
            tex_anim.fade_start = transform_start
        elif texmod_type == "scroll_u":
            tex_anim.scroll_rate_u = frame_rate # scroll opposite direction
            tex_anim.fade_start = transform_start # TODO: determine if this is used here
        elif texmod_type == "scroll_v":
            tex_anim.scroll_rate_v = -frame_rate
            tex_anim.fade_start = transform_start # TODO: determine if this is used here
        elif texmod_type == "external":
            # global textures in each texmod seem to be loaded in a
            # global scope, such that any "external" texture in another
            # resource will use it, no matter what file it was defined in.
            tex_anim.external = True
        else:
            texture_frames = []
            for j in range(texmod.type.source_index.idx,
                           texmod.type.source_index.idx + abs(texmod.frame_count)):
                if j in textures:
                    texture_frames.append(textures[j])
                else:
                    # TODO: throw an error about missing frame textures
                    pass

            tex_anim.frame_rate  = tex_swap_rate
            tex_anim.start_frame = texmod.tex_start_frame
            tex_anim.frame_data  = texture_frames

    return dict(
        actor_anims=actor_tex_anims,
        seq_anims=seq_tex_anims,
        global_anims=global_tex_anims
        )
