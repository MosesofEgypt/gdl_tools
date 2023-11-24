#!/usr/bin/env python3
import os
import pathlib
import tkinter.filedialog
import tkinter as tk
import time
import zlib

from tkinter import *
from traceback import format_exc
from ..compilation import dc_rom_compiler
from ..compilation import ps2_wad_compiler
from ..compilation import arcade_hdd_compiler
from ..compilation.ps2_wad.util import is_ps2_wadbin
from ..compilation.dc_rom.util import is_dc_sizes_rom
from ..compilation.arcade_hdd.util import is_arcade_hdd, is_arcade_chd

COMP_LEVEL_NONE = "0 (No compression)"
COMP_LEVEL_FAST = "1 (fastest, largest size)"
COMP_LEVEL_DEF  = "6 (best size for speed)"
COMP_LEVEL_BEST = "9 (slowest, smallest size)"

HDD_DISC_SELECT_0 = "Disc 0"
HDD_DISC_SELECT_1 = "Disc 1"
HDD_DISC_SELECT_2 = "Disc 2"

COMPRESSION_LEVELS = {
    COMP_LEVEL_NONE: zlib.Z_NO_COMPRESSION,
    COMP_LEVEL_FAST: zlib.Z_BEST_SPEED,
    COMP_LEVEL_DEF:  zlib.Z_DEFAULT_COMPRESSION,
    COMP_LEVEL_BEST: zlib.Z_BEST_COMPRESSION,
    }

HDD_DISC_SELECT = {
    HDD_DISC_SELECT_0: 0,
    HDD_DISC_SELECT_1: 1,
    HDD_DISC_SELECT_2: 2,
    }


class GdlArchiveTool(Tk):
    curr_dir = "."
    debug = False
    
    def __init__(self, **options):
        Tk.__init__(self, **options)
        
        self.title("GDL Archive Tool V1.2.0")
        self.minsize(600, 250)
        self.resizable(1, 0)

        self.target_dirpath  = StringVar(self)
        self.target_filepath = StringVar(self)
        self.compression_level = StringVar(self, COMP_LEVEL_NONE)
        self.hdd_disc_select = StringVar(self, HDD_DISC_SELECT_0)

        self.use_parallel_processing = BooleanVar(self, True)
        self.use_internal_names      = BooleanVar(self, True)
        self.use_compression_names   = BooleanVar(self, True)
        self.overwrite               = BooleanVar(self, False)

        self.target_filepath_frame = LabelFrame(self, text="HDD/WAD.BIN or SIZES.ROM filepath")
        self.target_dirpath_frame  = LabelFrame(self, text="Directory to compile from/decompile to")
        self.compile_frame         = LabelFrame(self, text="")
        self.settings_frame        = LabelFrame(self, text="Settings")

        self.target_dirpath_field = Entry(self.target_dirpath_frame, textvariable=self.target_dirpath)
        self.target_dirpath_field.config(width=46)
        self.target_filepath_field = Entry(self.target_filepath_frame, textvariable=self.target_filepath)
        self.target_filepath_field.config(width=46)

        # Add the buttons
        self.btn_compile_wadbin = Button(
            self.compile_frame, text="Compile PS2 WAD", width=20,
            command=lambda *a, **kw: self._compile(make_wadbin=True)
            )
        self.btn_compile_dc_rom = Button(
            self.compile_frame, text="Compile Dreamcast ROM", width=20,
            command=lambda *a, **kw: self._compile(make_rom=True)
            )
        self.btn_compile_hdd = Button(
            self.compile_frame, text="Compile Arcade HDD", width=20,
            command=lambda *a, **kw: self._compile(make_hdd=True)
            )
        self.btn_decompile = Button(
            self.compile_frame, text="Decompile archive", width=20,
            command=lambda *a, **kw: self._decompile()
            )

        self.parallel_processing_button = Checkbutton(
            self.settings_frame, text='Use parallel processing',
            variable=self.use_parallel_processing, onvalue=1, offvalue=0
            )
        self.overwrite_button = Checkbutton(
            self.settings_frame, text='Overwrite',
            variable=self.overwrite, onvalue=1, offvalue=0
            )
        self.use_internal_names_button = Checkbutton(
            self.settings_frame, text='Use filenames built into PS2 WAD',
            variable=self.use_internal_names, onvalue=1, offvalue=0
            )
        self.use_compression_names_button = Checkbutton(
            self.settings_frame, text='Use PS2 WAD file compress list',
            variable=self.use_compression_names, onvalue=1, offvalue=0
            )

        self.compress_level_label = Label(self.settings_frame, text="PS2 compression level")
        self.compress_level_menu = OptionMenu(
            self.settings_frame, self.compression_level, *sorted(COMPRESSION_LEVELS.keys())
            )

        self.hdd_disc_select_label = Label(self.settings_frame, text="Arcade disc select")
        self.hdd_disc_select_menu = OptionMenu(
            self.settings_frame, self.hdd_disc_select, *sorted(HDD_DISC_SELECT.keys())
            )

        # pack the outer frames
        self.target_filepath_frame.pack(padx=(10,10), pady=(5,0), side='top', fill='both')
        self.target_dirpath_frame.pack(padx=(10,10), pady=(5,0), side='top', fill='both')
        self.compile_frame.pack(padx=(10,10), pady=(5,0), side='top', fill='both')
        self.settings_frame.pack(padx=(10,10), pady=(5,0), side='top', fill='both')

        # configure the grids for each frame
        for frame, columns in ([self.target_filepath_frame, 1],
                               [self.target_dirpath_frame, 1],
                               [self.compile_frame, 2],
                               [self.settings_frame, 4],
                               ):
            for i in range(columns):
                frame.columnconfigure(i, weight=1)

        # grid position each widget
        self.target_dirpath_field.grid(row=0, column=0, sticky="we", padx=5, pady=5)
        self.target_filepath_field.grid(row=0, column=0, sticky="we", padx=5, pady=5)

        self.btn_compile_wadbin.grid(row=1, column=0, sticky="we", padx=5, pady=5)
        self.btn_compile_dc_rom.grid(row=1, column=1, sticky="we", padx=5, pady=5)
        self.btn_compile_hdd.grid(row=1, column=2, sticky="we", padx=5, pady=5)
        self.btn_decompile.grid(row=2, column=0, sticky="we", padx=5, pady=5, columnspan=3)

        # grid the settings
        y = 0
        for lbl, menu, radio in (
                (self.compress_level_label, self.compress_level_menu, self.use_internal_names_button),
                (self.hdd_disc_select_label, self.hdd_disc_select_menu, self.parallel_processing_button),
                (None, None, self.overwrite_button),
                #(None, None, self.use_compression_names_button),
            ):
            if lbl:
                lbl.grid(row=y, column=0, sticky="we", padx=2, pady=5)
            if menu:
                menu.grid(row=y, column=1, sticky="we", padx=2, pady=5)
            if radio:
                radio.grid(row=y, column=2, sticky="w", padx=20, pady=5)
            y += 1

    def get_ps2_compiler(self, **kwargs):
        kwargs.update(
            wad_dirpath = self.target_dirpath.get(),
            wad_filepath = self.target_filepath.get(),
            overwrite = self.overwrite.get(),
            parallel_processing = self.use_parallel_processing.get(),
            use_internal_names = self.use_internal_names.get(),
            compression_level = COMPRESSION_LEVELS.get(self.compression_level.get(), zlib.Z_NO_COMPRESSION)
            )
        return ps2_wad_compiler.Ps2WadCompiler(**kwargs)

    def get_dc_rom_compiler(self, **kwargs):
        kwargs.update(
            dirpath = self.target_dirpath.get(),
            sizes_filepath = self.target_filepath.get(),
            overwrite = self.overwrite.get(),
            parallel_processing = self.use_parallel_processing.get(),
            )
        return dc_rom_compiler.DcRomCompiler(**kwargs)

    def get_arcade_compiler(self, **kwargs):
        kwargs.update(
            hdd_dirpath = self.target_dirpath.get(),
            hdd_filepath = self.target_filepath.get(),
            overwrite = self.overwrite.get(),
            disc = HDD_DISC_SELECT.get(self.hdd_disc_select.get(), 0),
            parallel_processing = self.use_parallel_processing.get(),
            )
        return arcade_hdd_compiler.ArcadeHddCompiler(**kwargs)

    def select_target_folder(self):
        if folderpath:
            self.curr_dir = folderpath.replace('/','\\')
            self.target_dirpath.set(self.curr_dir)

    def _compile(self, make_wadbin=False, make_hdd=False, make_rom=False):
        target = (
            "WAD.BIN"   if make_wadbin else
            "SIZES.ROM" if make_rom    else
            "HDD"       if make_hdd    else
            ""
            )
        if make_hdd:
            print("Error: Compiling Arcade HDD is not supported yet.")
            return

        target_dirpath = self.target_dirpath.get()
        if not target_dirpath:
            target_dirpath = tkinter.filedialog.askdirectory(
                initialdir=self.curr_dir,
                title=f"Select the folder to compile into a {target}"
                )

        if not target_dirpath:
            return

        self.target_dirpath.set(target_dirpath)
        self.curr_dir = str(pathlib.Path(target_dirpath).parent)

        target_filepath = self.target_filepath.get()
        if not target_filepath:
            target_filepath = tkinter.filedialog.asksaveasfilename(
                initialdir=self.curr_dir,
                title=f"Select the file to save the {target} to",
                filetypes=[
                    (("PS2 WAD.BIN", "*.BIN")           if make_wadbin else
                     ("Dreamcast SIZES.ROM", "*.ROM")   if make_rom else
                     ("Arcade HDD", "*")
                     ),
                    ("all files", "*")
                    ],
                defaultextension=".BIN"
                )

        if not target_filepath:
            return

        if make_rom:
            target_filepath = pathlib.Path(target_filepath)
            if target_filepath.name.lower() == "disk.rom":
                target_filepath = target_filepath.with_name("SIZES.ROM")

            target_filepath = target_filepath.as_posix()

        self.target_filepath.set(target_filepath)
        self.curr_dir = str(pathlib.Path(target_filepath).parent)

        start = time.time()
        try:
            print('Compiling...')
            if make_wadbin:
                compiler = self.get_ps2_compiler()
            elif make_rom:
                compiler = self.get_dc_rom_compiler()
            else:
                compiler = self.get_arcade_compiler()

            compiler.compile()
        except Exception:
            print(format_exc())

        print('Finished. Took %s seconds.\n' % (time.time() - start))

    def _decompile(self):
        target_filepath = self.target_filepath.get()
        if not target_filepath:
            target_filepath = tkinter.filedialog.askopenfilename(
                initialdir=self.curr_dir,
                title="Select the WAD/HDD/ROM archive to decompile",
                filetypes=[("all files", "*")]
                )

        if not target_filepath:
            return

        target_filepath = pathlib.Path(target_filepath)
        if target_filepath.name.lower() == "disk.rom":
            for root, _, files in os.walk(target_filepath.parent):
                for filename in files:
                    if filename.lower() == "sizes.rom":
                        target_filepath = target_filepath.with_name(filename)
                        break
                break

        target_filepath = target_filepath.as_posix()

        is_wadbin = is_sizes_rom = is_hdd = False
        if is_ps2_wadbin(target_filepath):
            is_wadbin = True
        elif is_arcade_chd(target_filepath):
            print(f"Error: CHD must first be decompressed to a raw HDD with chdman.")
            return
        elif is_arcade_hdd(target_filepath):
            is_hdd = True
        elif is_dc_sizes_rom(target_filepath):
            is_sizes_rom = True
        else:
            print(f"Error: The file does not appear to be an Arcade HDD, PS2 WAD, or Dreamcast ROM.")
            return

        self.target_filepath.set(target_filepath)
        self.curr_dir = str(pathlib.Path(target_filepath).parent)

        target_dirpath = self.target_dirpath.get()
        if not target_dirpath:
            target_dirpath = tkinter.filedialog.askdirectory(
                initialdir=self.curr_dir,
                title="Select the folder to extract the files to"
                )

        if not target_dirpath:
            return

        self.target_dirpath.set(target_dirpath)
        self.curr_dir = str(pathlib.Path(target_dirpath).parent)

        start = time.time()
        try:
            print('Decompiling...')
            if is_wadbin:
                decompiler = self.get_ps2_compiler()
            elif is_sizes_rom:
                decompiler = self.get_dc_rom_compiler()
            else:
                decompiler = self.get_arcade_compiler()
                decompiler.load_hdd()

            decompiler.extract_files_to_disk()
        except Exception:
            print(format_exc())

        print('Finished. Took %s seconds.\n' % (time.time() - start))
