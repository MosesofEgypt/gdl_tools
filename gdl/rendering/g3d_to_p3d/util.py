import array
import os
import panda3d

from traceback import format_exc
from supyr_struct.defs.bitmaps.dds import dds_def

from arbytmap import arby, format_defs as fd
from .systems.realm import load_realm_from_wdata_tag
from ...compilation.util import *
from ...compilation.g3d import constants as g3d_const
from ...compilation.g3d.serialization import arbytmap_ext,\
     texture_conversions, texture_util
from ...defs.anim import anim_def

from ...defs.objects import objects_def
from ...defs.worlds import worlds_def
from ...defs.wdata import wdata_def, wdata_arcade_def, wdata_dreamcast_def


def locate_dir(search_root, *folder_names):
    dir = ""

    folder_to_find = folder_names[0].lower()
    folder_names = folder_names[1:]
    for root, dirs, _ in os.walk(search_root):
        for dirname in dirs:
            if dirname.lower() != folder_to_find:
                continue

            dir = os.path.join(root, dirname)
            if folder_names:
                dir = locate_dir(dir, *folder_names)

            if dir: break
        break

    return dir

def locate_file(search_root, *folder_names, filename=None):
    if folder_names:
        search_root = locate_dir(search_root, *folder_names)

    filepath = ""

    if search_root:
        file_to_find = filename.lower()
        for root, _, files in os.walk(search_root):
            for filename in files:
                if filename.lower() != file_to_find:
                    continue

                filepath = os.path.join(root, file_to_find)
                break
            break

    return filepath


def load_realm_data(wdata_dir, realm_name="", is_dreamcast=False):
    main_realms = {}
    realms = {}
    realm_name = realm_name.upper().strip()

    for _, __, files in os.walk(wdata_dir):
        for filename in files:
            filetype, ext = os.path.splitext(filename.lower())
            if ext != ".wad":
                continue

            filepath        = os.path.join(wdata_dir, filename)
            is_arcade_wad   = get_is_arcade_wad(filepath)

            tagdef      = (
                wdata_def if not is_arcade_wad else
                wdata_dreamcast_def if is_dreamcast else
                wdata_arcade_def
                )
            wdata_tag   = tagdef.build(filepath=filepath)
            realm = load_realm_from_wdata_tag(wdata_tag=wdata_tag)
            realms_dict = realms if realm.type == "TEST" else main_realms
            if not realm:
                continue
            elif realm_name and realm_name != realm.name:
                continue
            elif realm.name in realms_dict:
                print(f"Warning: Duplicate realm of name '{realm.name}' found. Skipping.")
                continue
            else:
                realms_dict[realm.name] = realm
        break

    realms.update(main_realms)
    return realms


def load_objects_dir_files(objects_dir):
    anim_tag    = None
    worlds_tag  = None
    objects_tag = None

    dir_info = locate_objects_dir_files(objects_dir)

    if dir_info["anim_filepath"]:
        try:
            anim_tag = anim_def.build(filepath=dir_info["anim_filepath"])
        except Exception:
            print(format_exc())

    if dir_info["worlds_filepath"]:
        try:
            worlds_tag = worlds_def.build(filepath=dir_info["worlds_filepath"])
        except Exception:
            print(format_exc())

    if dir_info["objects_filepath"]:
        try:
            objects_tag = objects_def.build(filepath=dir_info["objects_filepath"])
        except Exception:
            print(format_exc())

    if objects_tag and anim_tag:
        objects_tag.anim_tag = anim_tag

    return dict(
        objects_tag = objects_tag,
        anim_tag    = anim_tag,
        worlds_tag  = worlds_tag,
        textures_filepath = dir_info["textures_filepath"],
        is_ngc = dir_info["is_ngc"]
        )


def g3d_texture_to_dds(g3d_texture):
    # only the first one for now
    arby        = g3d_texture.to_arbytmap_instance(include_mipmaps=True)
    palette     = g3d_texture.palette
    texture     = g3d_texture.textures[0]
    format_name = g3d_texture.format_name

    dds_tag = dds_def.build()

    dds_header = dds_tag.data.header
    pfmt_head  = dds_header.dds_pixelformat

    dds_header.width  = g3d_texture.width
    dds_header.height = g3d_texture.height
    dds_header.depth  = 1

    dds_header.flags.linearsize = False
    dds_header.flags.pitch = True

    pfmt_head.flags.four_cc = False
    pfmt_head.flags.rgb_space = True
    pfmt_head.flags.has_alpha = (
        False if g3d_texture.monochrome else g3d_texture.has_alpha
        )

    # convert specialized formats to something we can work with
    if g3d_texture.large_vq or g3d_texture.small_vq:
        # dreamcast texture. remove vector quantization
        (texture, ) = texture_util.dequantize_vq_textures(
            [texture], palette, g3d_texture.width, g3d_texture.height,
            g3d_const.PIXEL_SIZES[format_name]
            )
    elif format_name in (g3d_const.PIX_FMT_ABGR_3555_IDX_4_NGC,
                       g3d_const.PIX_FMT_ABGR_3555_IDX_8_NGC):
        format_name = g3d_const.PIX_FMT_ABGR_8888_IDX_8
        palette = texture_conversions.argb_3555_to_8888(palette)
    elif format_name in (g3d_const.PIX_FMT_ABGR_3555_NGC,
                         g3d_const.PIX_FMT_XBGR_3555_NGC):
        format_name = g3d_const.PIX_FMT_ABGR_8888
        texture = texture_conversions.argb_3555_to_8888(texture)
    elif format_name == g3d_const.PIX_FMT_AYIQ_8422:
        format_name = g3d_const.PIX_FMT_ABGR_8888
        texture = texture_conversions.ayiq_8422_to_argb_8888(
            texture, g3d_texture.ncc_table
            )
    elif format_name == g3d_const.PIX_FMT_YIQ_422:
        format_name = g3d_const.PIX_FMT_ABGR_8888
        texture = texture_conversions.yiq_422_to_xrgb_8888(
            texture, g3d_texture.ncc_table
            )
    elif g3d_texture.monochrome or g3d_texture.dualchrome:
        # 4-bit monochrome gets unpacked to 8-bit, so change format
        format_name = {
            g3d_const.PIX_FMT_A_4_IDX_4: g3d_const.PIX_FMT_A_8_IDX_8,
            g3d_const.PIX_FMT_I_4_IDX_4: g3d_const.PIX_FMT_I_8_IDX_8,
            g3d_const.PIX_FMT_AI_44:     g3d_const.PIX_FMT_AI_88,
            }.get(format_name, format_name)

    if g3d_texture.palettized:
        # palettized texture. need to depalettize
        pfmt_head.rgb_bitcount = g3d_const.PALETTE_SIZES[format_name] * 8
        (texture, ) = texture_util.depalettize_textures(
            [texture], palette, pfmt_head.rgb_bitcount // 8
            )
    else:
        pfmt_head.rgb_bitcount = g3d_const.PIXEL_SIZES[format_name]

    arby_format = texture_util.g3d_format_to_arby_format(
        format_name, pfmt_head.flags.has_alpha
        )

    masks   = fd.CHANNEL_MASKS[arby_format]
    offsets = fd.CHANNEL_OFFSETS[arby_format]
    if g3d_texture.dualchrome:
        masks   = (masks[0],)   + (masks[1],)*3
        offsets = (offsets[0],) + (offsets[1],)*3
    elif g3d_texture.monochrome:
        masks   = (0,) + (masks[0],)*3
        offsets = (0,) + (offsets[0],)*3

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
