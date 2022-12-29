import os
import tempfile
import panda3d

from traceback import format_exc
from supyr_struct.defs.bitmaps.dds import dds_def

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


def g3d_texture_to_p3d_texture(g3d_texture):
    p3d_texture = panda3d.core.Texture()
    dds_tempfile = tempfile.NamedTemporaryFile("wb")
    tex0_tempfile = dds_tempfile.name

    arby = g3d_texture.to_arbytmap_instance()
    dds_tempfiles = arby.save_to_file(
        output_path=dds_tempfile.name, ext="dds",
        overwrite=True, mipmaps=False
        )
    if not dds_tempfiles:
        return p3d_texture

    tex0_tempfile = str(dds_tempfiles[0])
    ifile_stream = panda3d.core.IFileStream()
    ifile_stream.open(tex0_tempfile)
    p3d_texture.readDds(ifile_stream, tex0_tempfile)
    
    try:
        os.unlink(tex0_tempfile)
        dds_tempfile.close()
    except Exception:
        print(format_exc())
        print(f"Could not clean up temp files: '{dds_tempfile.name}', '{tex0_tempfile}'")
    return p3d_texture
