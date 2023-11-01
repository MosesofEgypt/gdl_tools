#!/usr/bin/env python3
import tkinter.filedialog
import tkinter as tk
import time

from tkinter import *
from traceback import format_exc
from ..compilation import objects_compiler, messages_compiler,\
     worlds_compiler
from ..compilation.g3d import constants as c

BUILD_TARGETS = {
    "PlayStation2": "ps2",
    "Gamecube":     "ngc",
    "Xbox":         "xbox",
    "Arcade":       "arcade",
    "Dreamcast":    "dreamcast",
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
        
        self.title("Crucible V1.3.0")
        self.minsize(500, 0)
        self.resizable(1, 0)

        self.target_objects_dir  = StringVar(self)
        self.target_worlds_dir   = StringVar(self)
        self.target_messages_dir = StringVar(self)

        self.build_target        = StringVar(self, "PlayStation2")
        self.mod_extract_format  = StringVar(self, "Wavefront OBJ")
        self.tex_extract_format  = StringVar(self, "PNG")
        self.meta_extract_format = StringVar(self, "YAML")
        self.use_parallel_processing = BooleanVar(self, True)
        self.optimize                = BooleanVar(self, True)
        self.force_recompile_cache   = BooleanVar(self, False)
        self.overwrite               = BooleanVar(self, False)

        self.objects_frame  = LabelFrame(self, text="Objects compilation")
        self.worlds_frame   = LabelFrame(self, text="Worlds compilation")
        self.messages_frame = LabelFrame(self, text="Messages compilation")
        self.settings_frame = LabelFrame(self, text="Settings")
        self.debug_actions_frame = LabelFrame(self, text="Debug")

        self.objects_folder_field = Entry(self.objects_frame, textvariable=self.target_objects_dir)
        self.objects_folder_field.config(width=46, state=DISABLED)
        self.worlds_folder_field = Entry(self.worlds_frame, textvariable=self.target_worlds_dir)
        self.worlds_folder_field.config(width=46, state=DISABLED)
        self.messages_folder_field = Entry(self.messages_frame, textvariable=self.target_messages_dir)
        self.messages_folder_field.config(width=46, state=DISABLED)

        # Add the buttons
        self.btn_select_objects_dir = Button(
            self.objects_frame, text="Select objects dir", width=20,
            command=self.select_objects_folder
            )
        self.btn_compile_objects_all = Button(
            self.objects_frame, text="Compile objects", width=20,
            command=lambda *a, **kw: self._compile_objects(cache=True, models=True, textures=True)
            )
        self.btn_decompile_objects_all = Button(
            self.objects_frame, text="Decompile objects", width=20,
            command=lambda *a, **kw: self._decompile_objects(cache=True, source=True)
            )

        self.btn_select_worlds_dir = Button(
            self.worlds_frame, text="Select worlds dir", width=20,
            command=self.select_worlds_folder
            )
        self.btn_compile_worlds_all = Button(
            self.worlds_frame, text="Compile worlds", width=20,
            command=lambda *a, **kw: self._compile_objects(
                cache=True, models=True, textures=True, world=True),
            state=DISABLED  # temporary
            )
        self.btn_decompile_worlds_all = Button(
            self.worlds_frame, text="Decompile worlds", width=20,
            command=lambda *a, **kw: self._decompile_objects(cache=True, source=True, world=True)
            )

        self.btn_select_messages_dir = Button(
            self.messages_frame, text="Select messages dir", width=20,
            command=self.select_messages_folder
            )
        self.btn_compile_messages = Button(
            self.messages_frame, text="Compile messages", width=20,
            command=lambda *a, **kw: self._compile_messages()
            )
        self.btn_decompile_messages = Button(
            self.messages_frame, text="Decompile messages", width=20,
            command=lambda *a, **kw: self._decompile_messages()
            )

        # DEBUG
        self.btn_compile_textures = Button(
            self.debug_actions_frame, text="Compile textures", width=20,
            command=lambda *a, **kw: self._compile_objects(textures=True)
            )
        self.btn_compile_models = Button(
            self.debug_actions_frame, text="Compile models", width=20,
            command=lambda *a, **kw: self._compile_objects(models=True)
            )
        self.btn_compile_cache = Button(
            self.debug_actions_frame, text="Compile cache files", width=20,
            command=lambda *a, **kw: self._compile_objects(cache=True)
            )
        self.btn_decompile_sources = Button(
            self.debug_actions_frame, text="Decompile asset sources", width=20,
            command=lambda *a, **kw: self._decompile_objects(source=True)
            )
        self.btn_decompile_cache = Button(
            self.debug_actions_frame, text="Decompile asset cache", width=20,
            command=lambda *a, **kw: self._decompile_objects(cache=True)
            )
        # DEBUG

        self.build_target_label = Label(self.settings_frame, text="Platform target")
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
        self.optimize_button = Checkbutton(
            self.settings_frame, text='Optimize models and textures',
            variable=self.optimize, onvalue=1, offvalue=0
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
        self.objects_frame.pack(padx=(10,10), pady=(5,0), side='top', fill='both')
        #self.worlds_frame.pack(padx=(10,10), pady=(5,0), side='top', fill='both')
        self.messages_frame.pack(padx=(10,10), pady=(5,0), side='top', fill='both')
        self.settings_frame.pack(padx=(10,10), pady=(5,0), side='top', fill='both')

        # configure the grids for each frame
        for frame, columns in ([self.objects_frame, 3],
                               [self.worlds_frame, 3],
                               [self.messages_frame, 3],
                               [self.settings_frame, 4],
                               [self.debug_actions_frame, 6],
                               ):
            for i in range(columns):
                frame.columnconfigure(i, weight=1)

        # grid position each widget
        self.objects_folder_field.grid(row=0, column=0, columnspan=3, sticky="we", padx=5, pady=5)
        self.btn_compile_objects_all.grid(row=1, column=0, sticky="we", padx=5, pady=5)
        self.btn_decompile_objects_all.grid(row=1, column=1, sticky="we", padx=5, pady=5)
        self.btn_select_objects_dir.grid(row=1, column=2, sticky="we", padx=5, pady=5)

        self.worlds_folder_field.grid(row=0, column=0, columnspan=3, sticky="we", padx=5, pady=5)
        self.btn_compile_worlds_all.grid(row=1, column=0, sticky="we", padx=5, pady=5)
        self.btn_decompile_worlds_all.grid(row=1, column=1, sticky="we", padx=5, pady=5)
        self.btn_select_worlds_dir.grid(row=1, column=2, sticky="we", padx=5, pady=5)

        self.messages_folder_field.grid(row=0, column=0, columnspan=3, sticky="we", padx=5, pady=5)
        self.btn_compile_messages.grid(row=1, column=0, sticky="we", padx=5, pady=5)
        self.btn_decompile_messages.grid(row=1, column=1, sticky="we", padx=5, pady=5)
        self.btn_select_messages_dir.grid(row=1, column=2, sticky="we", padx=5, pady=5)

        self.btn_compile_textures.grid(row=0, column=0, sticky="we", columnspan=2, padx=2, pady=2)
        self.btn_compile_models.grid(row=0, column=2, sticky="we", columnspan=2, padx=2, pady=2)
        self.btn_compile_cache.grid(row=0, column=4, sticky="we", columnspan=2, padx=2, pady=2)
        self.btn_decompile_sources.grid(row=1, column=0, sticky="we", columnspan=3, padx=2, pady=2)
        self.btn_decompile_cache.grid(row=1, column=3, sticky="we", columnspan=3, padx=2, pady=2)

        # grid the settings
        y = 0
        for lbl, menu, radio in (
                (self.build_target_label, self.build_target_menu, self.parallel_processing_button),
                (self.mod_format_label, self.mod_format_menu, self.force_recompile_button),
                (self.tex_format_label, self.tex_format_menu, self.overwrite_button),
                (self.meta_format_label, self.meta_format_menu, None),
            ):
            lbl.grid(row=y, column=0, sticky="we", padx=2)
            menu.grid(row=y, column=1, sticky="we", padx=2)
            if radio:
                radio.grid(row=y, column=2, sticky="w", padx=20, pady=10)
            y += 1


        if self.debug:
            self.debug_actions_frame.pack(padx=(10,10), pady=(5,0), side='top', fill='both')

    def get_objects_compiler(self, **kwargs):
        build_target = BUILD_TARGETS.get(self.build_target.get(), "ps2")
        kwargs.update(
            build_arcade_files          = (build_target == "arcade"),
            build_dreamcast_files       = (build_target == "dreamcast"),
            build_ngc_files             = (build_target == "ngc"),
            build_xbox_files            = (build_target == "xbox"),
            build_ps2_files             = (build_target == "ps2"),
            build_texdef_cache          = (build_target in ("ps2", "dreamcast")),
            optimize_models             = self.optimize.get(),
            optimize_textures           = self.optimize.get(),
            force_recompile             = self.force_recompile_cache.get(),
            overwrite                   = self.overwrite.get(),
            )
        if kwargs.pop("want_world_compiler", False):
            return worlds_compiler.WorldsCompiler(**kwargs)
        else:
            return objects_compiler.ObjectsCompiler(**kwargs)

    def get_messages_compiler(self, **kwargs):
        build_target = BUILD_TARGETS.get(self.build_target.get(), "ps2")
        kwargs.update(
            target_dir = self.target_messages_dir.get(),
            target_arcade = (build_target == "arcade"),
            overwrite = self.overwrite.get(),
            )
        return messages_compiler.MessagesCompiler(**kwargs)

    def select_objects_folder(self):
        folderpath = tkinter.filedialog.askdirectory(
            initialdir=self.curr_dir, title="Select the folder containing OBJECTS.PS2/NGC/ROM")
        if folderpath:
            self.curr_dir = folderpath.replace('/','\\')
            self.target_objects_dir.set(self.curr_dir)

    def select_worlds_folder(self):
        folderpath = tkinter.filedialog.askdirectory(
            initialdir=self.curr_dir, title="Select the folder containing WORLDS.PS2/NGC/ROM")
        if folderpath:
            self.curr_dir = folderpath.replace('/','\\')
            self.target_worlds_dir.set(self.curr_dir)

    def select_messages_folder(self):
        folderpath = tkinter.filedialog.askdirectory(
            initialdir=self.curr_dir, title="Select the folder containing the *.ROM messages")
        if folderpath:
            self.curr_dir = folderpath.replace('/','\\')
            self.target_messages_dir.set(self.curr_dir)

    def _compile_messages(self):
        if not self.target_messages_dir.get():
            return

        start = time.time()
        try:
            print('Compiling messages...')
            compiler = self.get_messages_compiler()
            compiler.compile()
        except Exception:
            print(format_exc())

        print('Finished. Took %s seconds.\n' % (time.time() - start))

    def _decompile_messages(self):
        if not self.target_messages_dir.get():
            return

        start = time.time()
        try:
            print('Decompiling...')

            meta_asset_type = META_EXTRACT_FORMATS.get(self.meta_extract_format.get(), "yaml")
            decompiler = self.get_messages_compiler()
            decompiler.decompile(asset_types=[meta_asset_type])
        except Exception:
            print(format_exc())

        print('Finished. Took %s seconds.\n' % (time.time() - start))

    def _compile_objects(self, models=False, textures=False, cache=False,
                         world=False, animations=False):
        target_dir = self.target_worlds_dir.get() if world else self.target_objects_dir.get()
        build_target = BUILD_TARGETS.get(self.build_target.get(), "ps2")
        if not target_dir:
            return
        elif build_target in ("arcade", "dreamcast"):
            print("Error: Compiling arcade and dreamcast cache files is not supported yet.")
            return

        start = time.time()
        try:
            compiler = self.get_objects_compiler(
                parallel_processing = self.use_parallel_processing.get(),
                want_world_compiler = world, target_dir=target_dir,
                )
            if textures:
                print('Compiling textures...')
                compiler.compile_textures()

            if animations:
                print('Compiling animations...')
                compiler.compile_animations()

            if models:
                print('Compiling models...')
                compiler.compile_models()

            if cache:
                print('Compiling cache files...')
                compiler.compile()

        except Exception:
            print(format_exc())

        print('Finished. Took %s seconds.\n' % (time.time() - start))

    def _decompile_objects(self, cache=False, source=False, world=False):
        target_dir = self.target_worlds_dir.get() if world else self.target_objects_dir.get()
        if not target_dir:
            return

        start = time.time()
        try:
            print('Decompiling...')

            build_target = BUILD_TARGETS.get(self.build_target.get(), "ps2")
            anim_asset_types = []
            mod_asset_types  = []
            tex_asset_types  = []

            if cache:
                anim_asset_types.append(c.ANIMATION_CACHE_EXTENSIOn)

                if build_target == "ngc":
                    mod_asset_types.append(c.MODEL_CACHE_EXTENSION_NGC)
                    tex_asset_types.append(c.TEXTURE_CACHE_EXTENSION_NGC)
                elif build_target == "xbox":
                    mod_asset_types.append(c.MODEL_CACHE_EXTENSION_XBOX)
                    tex_asset_types.append(c.TEXTURE_CACHE_EXTENSION_XBOX)
                elif build_target == "arcade":
                    mod_asset_types.append(c.MODEL_CACHE_EXTENSION_ARC)
                    tex_asset_types.append(c.TEXTURE_CACHE_EXTENSION_ARC)
                elif build_target == "dreamcast":
                    mod_asset_types.append(c.MODEL_CACHE_EXTENSION_DC)
                    tex_asset_types.append(c.TEXTURE_CACHE_EXTENSION_DC)
                else:
                    mod_asset_types.append(c.MODEL_CACHE_EXTENSION_PS2)
                    tex_asset_types.append(c.TEXTURE_CACHE_EXTENSION_PS2)

            if source:
                mod_asset_types.append(MOD_EXTRACT_FORMATS.get(self.mod_extract_format.get(), "obj"))
                tex_asset_types.append(TEX_EXTRACT_FORMATS.get(self.tex_extract_format.get(), "png"))

            meta_asset_type = META_EXTRACT_FORMATS.get(self.meta_extract_format.get(), "yaml")

            decompiler = self.get_objects_compiler(
                parallel_processing=self.use_parallel_processing.get(),
                want_world_compiler=world, target_dir=target_dir,
            )
            decompiler.decompile(
                anim_asset_types = anim_asset_types,
                mod_asset_types = mod_asset_types,
                tex_asset_types = tex_asset_types,
                meta_asset_types = [meta_asset_type]
                )
        except Exception:
            print(format_exc())

        print('Finished. Took %s seconds.\n' % (time.time() - start))
