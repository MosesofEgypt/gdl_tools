#!/usr/bin/env python3
import tkinter.filedialog
import tkinter as tk
import time

from tkinter import *
from traceback import format_exc
from gdl import crucible
from gdl.defs.rom import rom_def

BUILD_TARGETS = {
    "PlayStation2": "ps2",
    "Gamecube":     "ngc",
    "Xbox":         "xbox",
    }
MOD_EXTRACT_FORMATS = {
    "Wavefront OBJ": "obj",
    #"Collada DAE":   "dae",
    }
TEX_EXTRACT_FORMATS = {
    "PNG": "png",
    "Targa TGA": "tga",
    "DirectDraw DDS": "dds",
    }
META_EXTRACT_FORMATS = {
    "YAML": "yaml",
    "JSON": "json",
    }

class CrucibleApp(Tk):
    curr_dir = "."
    debug = False
    
    def __init__(self, **options):
        Tk.__init__(self, **options)
        
        self.title("Crucible V1.1.0")
        self.geometry("400x100+0+0")
        self.minsize(500, 300)
        self.resizable(1, 0)

        self.target_dir = StringVar(self)

        self.build_target        = StringVar(self, "PlayStation2")
        self.mod_extract_format  = StringVar(self, "Wavefront OBJ")
        self.tex_extract_format  = StringVar(self, "PNG")
        self.meta_extract_format = StringVar(self, "YAML")
        self.use_parallel_processing = BooleanVar(self, True)
        self.optimize_texture_format = BooleanVar(self, True)
        self.force_recompile_cache   = BooleanVar(self, False)
        self.overwrite               = BooleanVar(self, False)

        self.folder_frame   = LabelFrame(self, text="Objects directory")
        self.actions_frame  = LabelFrame(self, text="", relief=FLAT)
        self.settings_frame = LabelFrame(self, text="Settings")
        self.debug_actions_frame = LabelFrame(self, text="Debug")
        
        self.folder_field = Entry(self.folder_frame, textvariable=self.target_dir)
        self.folder_field.config(width=46, state=DISABLED)

        # Add the buttons
        self.btn_select_folder = Button(
            self.folder_frame, text="...", width=4,
            command=self.select_folder
            )

        self.btn_compile_textures = Button(
            self.debug_actions_frame, text="Compile textures", width=20,
            command=lambda *a, **kw: self._do_compile(textures=True)
            )
        self.btn_compile_models = Button(
            self.debug_actions_frame, text="Compile models", width=20,
            command=lambda *a, **kw: self._do_compile(models=True)
            )
        self.btn_compile_cache = Button(
            self.debug_actions_frame, text="Compile cache files", width=20,
            command=lambda *a, **kw: self._do_compile(cache=True)
            )
        self.btn_decompile_sources = Button(
            self.debug_actions_frame, text="Decompile asset sources", width=20,
            command=lambda *a, **kw: self._do_decompile(cache=True)
            )
        self.btn_decompile_cache = Button(
            self.debug_actions_frame, text="Decompile asset cache", width=20,
            command=lambda *a, **kw: self._do_decompile(source=True)
            )

        self.btn_compile_all = Button(
            self.actions_frame, text="Compile cache files", width=20,
            command=lambda *a, **kw: self._do_compile(cache=True, models=True, textures=True)
            )
        self.btn_decompile_all = Button(
            self.actions_frame, text="Decompile cache files", width=20,
            command=lambda *a, **kw: self._do_decompile(cache=True, source=True)
            )

        self.build_target_label = Label(self.settings_frame, text="Build target")
        self.mod_format_label   = Label(self.settings_frame, text="Model format")
        self.tex_format_label   = Label(self.settings_frame, text="Texture format")
        self.meta_format_label  = Label(self.settings_frame, text="Metadata format")

        self.build_target_menu = OptionMenu(
            self.settings_frame, self.build_target, *sorted(BUILD_TARGETS.keys())
            )
        self.mod_format_menu   = OptionMenu(
            self.settings_frame, self.mod_extract_format, *sorted(MOD_EXTRACT_FORMATS.keys())
            )
        self.tex_format_menu   = OptionMenu(
            self.settings_frame, self.tex_extract_format, *sorted(TEX_EXTRACT_FORMATS.keys())
            )
        self.meta_format_menu  = OptionMenu(
            self.settings_frame, self.meta_extract_format, *sorted(META_EXTRACT_FORMATS.keys())
            )
        self.parallel_processing_button = Checkbutton(
            self.settings_frame, text='Use parallel processing',
            variable=self.use_parallel_processing, onvalue=1, offvalue=0
            )
        self.optimize_texture_format_button = Checkbutton(
            self.settings_frame, text='Optimize texture formats',
            variable=self.optimize_texture_format, onvalue=1, offvalue=0
            )
        self.force_recompile_button = Checkbutton(
            self.settings_frame, text='Force full recompile',
            variable=self.force_recompile_cache, onvalue=1, offvalue=0
            )
        self.overwrite_button = Checkbutton(
            self.settings_frame, text='Overwrite on decompile',
            variable=self.overwrite, onvalue=1, offvalue=0
            )

        # pack the outer frames
        self.folder_frame.pack(padx=(10,10), side='top', fill='both')
        self.settings_frame.pack(padx=(10,10), side='top', fill='both')
        self.actions_frame.pack(padx=(10,10), side='top', fill='both', expand=True)

        self.folder_field.pack(side='left', fill='x', expand=True, padx=5, pady=5)
        self.btn_select_folder.pack(side='right', padx=5, pady=5)

        # configure the grids for each frame
        for i in range(4):
            self.settings_frame.columnconfigure(i, weight=1)

        for i in range(2):
            self.actions_frame.columnconfigure(i, weight=1)

        for i in range(6):
            self.debug_actions_frame.columnconfigure(i, weight=1)

        # grid position each widget
        self.btn_compile_all.grid(row=1, column=0, sticky="we", padx=2, pady=2)
        self.btn_decompile_all.grid(row=1, column=1, sticky="we", padx=2, pady=2)

        self.btn_compile_textures.grid(row=0, column=0, sticky="we", columnspan=2, padx=2, pady=2)
        self.btn_compile_models.grid(row=0, column=2, sticky="we", columnspan=2, padx=2, pady=2)
        self.btn_compile_cache.grid(row=0, column=4, sticky="we", columnspan=2, padx=2, pady=2)
        self.btn_decompile_sources.grid(row=1, column=0, sticky="we", columnspan=3, padx=2, pady=2)
        self.btn_decompile_cache.grid(row=1, column=3, sticky="we", columnspan=3, padx=2, pady=2)

        # grid the settings
        y = 0
        for lbl, menu, radio in (
                (self.build_target_label, self.build_target_menu, self.parallel_processing_button),
                (self.mod_format_label, self.mod_format_menu, self.optimize_texture_format_button),
                (self.tex_format_label, self.tex_format_menu, self.force_recompile_button),
                (self.meta_format_label, self.meta_format_menu, self.overwrite_button),
            ):
            lbl.grid(row=y, column=0, sticky="we", padx=2)
            menu.grid(row=y, column=1, sticky="we", padx=2)
            radio.grid(row=y, column=2, sticky="w", padx=20, pady=10)
            y += 1


        if self.debug:
            self.debug_actions_frame.pack(padx=(10,10), pady=(5,0), side='top', fill='both')

    def get_crucible_instance(self, **kwargs):
        build_target = BUILD_TARGETS.get(self.build_target.get(), "ps2")
        kwargs.update(
            target_dir = self.target_dir.get(),
            build_ngc_files = (build_target == "ngc"),
            build_ps2_files = (build_target == "ps2" or build_target == "xbox"),
            build_texdef_cache = (build_target == "ps2"),
            optimize_texture_format = self.optimize_texture_format.get(),
            force_recompile = self.force_recompile_cache.get(),
            overwrite = self.overwrite.get(),
            )
        return crucible.Crucible(**kwargs)

    def select_folder(self):
        folderpath = tkinter.filedialog.askdirectory(
            initialdir=self.curr_dir, title="Select the folder containing objects.ps2/ngc")
        if folderpath:
            self.curr_dir = folderpath.replace('/','\\')
            self.target_dir.set(self.curr_dir)

    def _do_compile(self, models=False, textures=False, cache=False):
        if not self.target_dir.get():
            return

        start = time.time()
        try:
            compiler = self.get_crucible_instance(
                parallel_processing = self.use_parallel_processing.get()
                )
            if textures:
                print('Compiling textures...')
                compiler.compile_textures()

            if models:
                print('Compiling models...')
                compiler.compile_models()

            if cache:
                print('Compiling cache files...')
                compiler.compile_cache()

        except Exception:
            print(format_exc())

        print('Finished. Took %s seconds.\n' % (time.time() - start))

    def _do_decompile(self, cache=False, source=False):
        if not self.target_dir.get():
            return

        start = time.time()
        try:
            print('Decompiling...')

            build_target = BUILD_TARGETS.get(self.build_target.get(), "ps2")
            mod_asset_types  = []
            tex_asset_types  = []
            meta_asset_types = []

            if cache:
                mod_asset_types.append("g3d")
                tex_asset_types.append("gtn" if build_target == "ngc" else "gtx")

            if source:
                mod_asset_types.append(MOD_EXTRACT_FORMATS.get(self.mod_extract_format.get(), "obj"))
                tex_asset_types.append(TEX_EXTRACT_FORMATS.get(self.tex_extract_format.get(), "png"))

            meta_asset_types.append(META_EXTRACT_FORMATS.get(self.meta_extract_format.get(), "yaml"))

            decompiler = self.get_crucible_instance(
                parallel_processing=self.use_parallel_processing.get(),
            )
            decompiler.extract_assets(
                mod_asset_types = mod_asset_types,
                tex_asset_types = tex_asset_types,
                meta_asset_types = meta_asset_types,
                )
        except Exception:
            print(format_exc())

        print('Finished. Took %s seconds.\n' % (time.time() - start))


if __name__ == '__main__':
    CrucibleApp().mainloop()

#from gdl.metadata.messages import decompile_messages_metadata
#test = rom_def.build(filepath="C:/Users/Moses/Desktop/gauntlet_modding/ps2_data/TEXT/JAPANESE.ROM")
#decompile_messages_metadata(
#    test, "C:/Users/Moses/Desktop/gauntlet_modding/ps2_data/TEXT/JAPANESE", overwrite=True
#    )
#asdf = rom_def.build()
#asdf.filepath = "C:/Users/Moses/Desktop/gauntlet_modding/ps2_data/TEXT/TEST.ROM"
#asdf.add_fonts(test.get_fonts())
#asdf.add_messages(test.get_messages())
#asdf.add_message_lists(test.get_message_lists())
#asdf.serialize(temp=False)
