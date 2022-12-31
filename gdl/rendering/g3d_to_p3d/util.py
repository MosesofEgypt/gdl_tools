import array
import os
import panda3d

from traceback import format_exc
from supyr_struct.defs.bitmaps.dds import dds_def

from arbytmap import arby, format_defs as fd
from ...compilation.g3d import constants as g3d_const
from ...defs.anim import anim_ps2_def
from ...defs.objects import objects_ps2_def
from ...defs.worlds import worlds_ps2_def


def load_objects_dir_files(objects_dir):
    anim_tag    = None
    worlds_tag  = None
    objects_tag = None
    textures_filepath = ""

    anim_filename     = ""
    worlds_filename   = ""
    objects_filename_ps2  = ""
    textures_filename_ps2 = ""
    objects_filename_ngc  = ""
    textures_filename_ngc = ""

    for _, __, files in os.walk(objects_dir):
        for filename in files:
            filetype, ext = os.path.splitext(filename.lower())
            if ext not in (".ps2", ".ngc"):
                continue

            if filetype == "anim":
                anim_filename = filename
            elif filetype == "worlds":
                worlds_filename = filename
            elif filetype == "objects":
                if ext == ".ngc":
                    objects_filename_ngc = filename
                else:
                    objects_filename_ps2 = filename
            elif filetype == "textures":
                if ext == ".ngc":
                    textures_filename_ngc = filename
                else:
                    textures_filename_ps2 = filename

        break

    is_ngc = textures_filename_ngc and objects_filename_ngc

    objects_filename  = objects_filename_ngc  if is_ngc else objects_filename_ps2
    textures_filename = textures_filename_ngc if is_ngc else textures_filename_ps2

    if anim_filename:
        try:
            anim_tag = anim_ps2_def.build(filepath=os.path.join(objects_dir, anim_filename))
        except Exception:
            print(format_exc())

    if worlds_filename:
        try:
            worlds_tag = worlds_ps2_def.build(filepath=os.path.join(objects_dir, worlds_filename))
        except Exception:
            print(format_exc())

    if objects_filename:
        try:
            objects_tag = objects_ps2_def.build(filepath=os.path.join(objects_dir, objects_filename))
        except Exception:
            print(format_exc())

    if textures_filename:
        textures_filepath = os.path.join(objects_dir, textures_filename)

    return dict(
        objects_tag = objects_tag,
        anim_tag    = anim_tag,
        worlds_tag  = worlds_tag,
        textures_filepath = textures_filepath,
        is_ngc = is_ngc
        )


def g3d_texture_to_dds(g3d_texture):
    # only the first one for now
    palette = g3d_texture.palette
    texture = g3d_texture.textures[0]

    dds_tag = dds_def.build()

    dds_header = dds_tag.data.header
    pfmt_head  = dds_header.dds_pixelformat

    dds_header.width  = g3d_texture.width
    dds_header.height = g3d_texture.height
    dds_header.depth  = 1

    dds_header.flags.linearsize = False
    dds_header.flags.pitch = True

    monochrome = g3d_texture.format_name in g3d_const.MONOCHROME_FORMATS
    pfmt_head.flags.rgb_space = not pfmt_head.flags.alpha_only
    pfmt_head.flags.has_alpha = g3d_texture.flags & g3d_const.GTX_FLAG_HAS_ALPHA

    if monochrome:
        # making monochrome into 24bpp color
        pfmt_head.rgb_bitcount = 8
        pfmt_head.flags.has_alpha = False
    elif g3d_texture.format_name not in g3d_const.PALETTE_SIZES:
        # non-palettized texture
        pfmt_head.rgb_bitcount = g3d_const.PIXEL_SIZES[g3d_texture.format_name]
    else:
        # palettized texture. need to depalettize
        pfmt_head.rgb_bitcount = g3d_const.PALETTE_SIZES[g3d_texture.format_name] * 8

        # create a new array to hold the pixels after we unpack them
        depal_texture = bytearray(4 * len(texture))

        if arby.fast_arbytmap:
            arby.arbytmap_ext.depalettize_bitmap(
                depal_texture, texture, palette, 4)
        else:
            for i, index in enumerate(texture):
                depal_texture[i*4:(i+1*4)] = palette[index*4:(index+1)*4]

        texture = depal_texture

    pfmt_head.flags.four_cc = False
    masks   = fd.CHANNEL_MASKS[g3d_texture.arbytmap_format]
    offsets = fd.CHANNEL_OFFSETS[g3d_texture.arbytmap_format]

    if monochrome:
        pfmt_head.a_bitmask = 0
        pfmt_head.r_bitmask = masks[0] << offsets[0]
        pfmt_head.g_bitmask = masks[0] << offsets[0]
        pfmt_head.b_bitmask = masks[0] << offsets[0]
    else:
        if pfmt_head.flags.has_alpha:
            pfmt_head.a_bitmask = masks[0] << offsets[0]

        pfmt_head.r_bitmask = masks[1] << offsets[1]
        pfmt_head.g_bitmask = masks[2] << offsets[2]
        pfmt_head.b_bitmask = masks[3] << offsets[3]

    dds_header.pitch_or_linearsize = (
        dds_header.width * pfmt_head.rgb_bitcount + 7
        ) // 8

    # TODO: implement mipmaps
    dds_header.mipmap_count = 0
    dds_header.caps.complex = False
    dds_header.caps.mipmaps = False
    dds_header.flags.mipmaps = False

    dds_tag.data.pixel_data = bytes(texture)
    return dds_tag


def g3d_texture_to_p3d_texture(g3d_texture):
    p3d_texture = panda3d.core.Texture()

    dds_tag  = g3d_texture_to_dds(g3d_texture)
    dds_data = dds_tag.data.serialize()

    data_stream = panda3d.core.StringStream()
    data_stream.setData(dds_data)

    p3d_texture.readDds(data_stream)
    return p3d_texture
