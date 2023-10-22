import os
from traceback import format_exc

from ..defs.rom import rom_def, rom_arcade_def
from .metadata import messages as metadata_comp
from .util import get_is_arcade_wad

class MessagesCompiler:
    target_dir = "."
    target_filenames = ()

    overwrite       = False
    individual_meta = True
    target_arcade   = False

    serialize_cache_files = True
    
    def __init__(self, **kwargs):
        # simple initialization setup where kwargs are
        # copied into the attributes of this new class
        for k, v in kwargs.items():
            setattr(self, k, v)

    def compile(self):
        target_filenames = list(self.target_filenames)
        if not os.path.isdir(self.target_dir):
            return
        elif not target_filenames:
            for root, dirnames, _ in os.walk(self.target_dir):
                target_filenames.extend(dirnames)
                break

        rom_tags = []
        for dirname in target_filenames:
            dirpath = os.path.join(self.target_dir, dirname)
            try:
                metadata = metadata_comp.compile_messages_metadata(dirpath)

                if self.target_arcade:
                    rom_tag = rom_arcade_def.build()
                else:
                    rom_tag = rom_def.build()

                rom_tag.filepath = dirpath + ".ROM"
                rom_tag.add_fonts(metadata["fonts"])
                rom_tag.add_messages(metadata["messages"])
                rom_tag.add_message_lists(metadata["message_lists"])
                if self.serialize_cache_files:
                    rom_tag.serialize(temp=False)

                rom_tags.append(rom_tag)
            except Exception:
                print(format_exc())

        return rom_tags

    def decompile(self, **kwargs):
        target_filenames = list(self.target_filenames)
        if not os.path.isdir(self.target_dir):
            return
        elif not target_filenames:
            for root, _, filenames in os.walk(self.target_dir):
                for filename in filenames:
                    if os.path.splitext(filename)[-1].upper() == ".ROM":
                        target_filenames.append(filename)
                break

        for filename in target_filenames:
            filepath = os.path.join(self.target_dir, filename)
            try:
                if get_is_arcade_wad(filepath):
                    rom_tag = rom_arcade_def.build(filepath=filepath)
                else:
                    rom_tag = rom_def.build(filepath=filepath)

                decompile_kwargs = dict(
                    overwrite=self.overwrite,
                    individual_meta=self.individual_meta
                    )
                decompile_kwargs.update(kwargs)
                metadata_comp.decompile_messages_metadata(
                    rom_tag, os.path.splitext(filepath)[0], **decompile_kwargs
                    )
            except Exception:
                print(format_exc())
