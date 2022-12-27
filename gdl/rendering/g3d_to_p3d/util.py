import os

from traceback import format_exc

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
    objects_filename  = ""
    textures_filename = ""

    for _, __, files in os.walk(objects_dir):
        for filename in files:
            if filename.lower() == "anim.ps2":
                anim_filename = filename
            elif filename.lower() == "objects.ps2":
                objects_filename = filename
            elif filename.lower() == "textures.ps2":
                textures_filename = filename
            elif filename.lower() == "worlds.ps2":
                worlds_filename = filename

        break

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
        )
