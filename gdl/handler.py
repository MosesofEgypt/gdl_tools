import os
import pathlib

from binilla.handler import Handler
from .field_types import *
from .defs.objs.tag import GdlTag
from . import util

class GdlHandler(Handler):
    default_defs_path = "gdl.defs"

    def get_def_id(self, filepath):
        filepath = pathlib.Path(filepath)
        name    = filepath.stem.lower()
        ext     = filepath.suffix.lower()

        # I know this is hacky, shutup. midway didnt play "nice"
        if ext in ('.ps2', '.ngc', ".rom") and name in (
                "anim", "objects", "texdef", "worlds"
                ):
            return name
        elif ext in ('.xbe', '.dol', '.fnt'):
            return ext[1:]
        elif name + ext == "slus_200.47":
            return "slus"
        elif ext in ('.wad', '.rom'):
            if ext == '.wad':
                if name in ('arc','dwf','fal','hye',
                            'jac','jes','kni','med',
                            'min','ogr','sor','tig',
                            'uni','val','war','wiz'):
                    def_id = 'pdata'
                elif name in ('battle','castle','desert','dream',
                              'forest','hell','ice','mount','secret',
                              'sky','temple','test','tower','town'):
                    def_id = 'wdata'
                elif name in ('lich','dragon','pboss', 'chimera',
                              'gar_eagl','gar_lion','gar_serp',
                              'drider','djinn','yeti','wraith',
                              'skorne1','skorne2','garm',
                              'general','golem','golemf', 'golemi',
                              'critter' # dreamcast has some weird files
                              ):
                    def_id = 'critter'
                elif name == 'shop':
                    def_id = 'shop'
                else:
                    def_id = "wad"
            elif name.startswith("index") and len(name) == 6:
                def_id = "arcade_save_index"
            elif name.startswith("passport") and len(name) == 9:
                # NOTE: can't tell the difference between gdl and gleg
                #       passport save files, so just default to gdl here
                def_id = "arcade_gdl_save_file"
            elif name.startswith("hstable_") and len(name) == 9:
                # NOTE: not implemented
                def_id = "high_score_table"
            elif name in ("aud_data", "audatps2"):
                # NOTE: not implemented
                def_id = "audio_data"
            elif name in ("colworlds", "dummy"):
                def_id = None
            else:
                def_id = 'messages'

            if util.get_is_arcade_wad(filepath):
                def_id = f"{def_id}_arcade"

            return def_id
        elif ext in self.id_ext_map.values():
            for def_id in self.id_ext_map:
                if self.id_ext_map[def_id].lower() == ext:
                    return def_id

    def index_tags(self, directory=None, def_ids_to_index=None):
        if directory is None:
            directory = self.tagsdir

        count = 0
        for root, _, files in os.walk(directory):
            for filename in files:
                filepath = pathlib.Path(root, filename)
                def_id = self.get_def_id(filepath)
                if def_id is None:
                    continue
                elif def_ids_to_index and def_id not in def_ids_to_index:
                    continue

                self.tags.setdefault(def_id, {})
                self.tags[def_id][filepath] = None
                count += 1

        return count
