#!/usr/bin/env python3
import os
import tkinter.filedialog
import tkinter as tk
import time
import zlib

from tkinter import *
from traceback import format_exc
from gdl.compilation import ps2_wad_compiler


COMPRESSION_LEVELS = {
    "0 (No compression)":         zlib.Z_NO_COMPRESSION,
    "1 (fastest, largest size)":  zlib.Z_BEST_SPEED,
    "6 (best size for speed)":    zlib.Z_DEFAULT_COMPRESSION,
    "9 (slowest, smallest size)": zlib.Z_BEST_COMPRESSION,
    }


class Ps2WadCompiler(Tk):
    curr_dir = "."
    debug = False
    
    def __init__(self, **options):
        Tk.__init__(self, **options)
        
        self.title("PS2 WAD Tool V1.0.0")
        self.minsize(500, 250)
        self.resizable(1, 0)

        self.wad_dirpath  = StringVar(self)
        self.wad_filepath = StringVar(self)
        self.compression_level = StringVar(self, "0 (No compression)")

        self.use_parallel_processing = BooleanVar(self, True)
        self.use_internal_names      = BooleanVar(self, True)
        self.use_compression_names   = BooleanVar(self, True)
        self.overwrite               = BooleanVar(self, False)

        self.wad_filepath_frame = LabelFrame(self, text="WAD filepath")
        self.wad_dirpath_frame  = LabelFrame(self, text="WAD directory")
        self.compile_frame      = LabelFrame(self, text="")
        self.settings_frame     = LabelFrame(self, text="Settings")

        self.wad_dirpath_field = Entry(self.wad_dirpath_frame, textvariable=self.wad_dirpath)
        self.wad_dirpath_field.config(width=46)
        self.wad_filepath_field = Entry(self.wad_filepath_frame, textvariable=self.wad_filepath)
        self.wad_filepath_field.config(width=46)

        # Add the buttons
        self.btn_compile_wad = Button(
            self.compile_frame, text="Compile WAD", width=20,
            command=lambda *a, **kw: self._compile_wad()
            )
        self.btn_decompile_wad = Button(
            self.compile_frame, text="Decompile WAD", width=20,
            command=lambda *a, **kw: self._decompile_wad()
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
            self.settings_frame, text='Use filenames built into WAD',
            variable=self.use_internal_names, onvalue=1, offvalue=0
            )
        self.use_compression_names_button = Checkbutton(
            self.settings_frame, text='Use file compress list',
            variable=self.use_compression_names, onvalue=1, offvalue=0
            )

        self.compress_level_label = Label(self.settings_frame, text="Compression level")
        self.compress_level_menu = OptionMenu(
            self.settings_frame, self.compression_level, *sorted(COMPRESSION_LEVELS.keys())
            )

        # pack the outer frames
        self.wad_filepath_frame.pack(padx=(10,10), pady=(5,0), side='top', fill='both')
        self.wad_dirpath_frame.pack(padx=(10,10), pady=(5,0), side='top', fill='both')
        self.compile_frame.pack(padx=(10,10), pady=(5,0), side='top', fill='both')
        self.settings_frame.pack(padx=(10,10), pady=(5,0), side='top', fill='both')

        # configure the grids for each frame
        for frame, columns in ([self.wad_filepath_frame, 1],
                               [self.wad_dirpath_frame, 1],
                               [self.compile_frame, 2],
                               [self.settings_frame, 4],
                               ):
            for i in range(columns):
                frame.columnconfigure(i, weight=1)

        # grid position each widget
        self.wad_dirpath_field.grid(row=0, column=0, sticky="we", padx=5, pady=5)
        self.wad_filepath_field.grid(row=0, column=0, sticky="we", padx=5, pady=5)

        self.btn_compile_wad.grid(row=1, column=0, sticky="we", padx=5, pady=5)
        self.btn_decompile_wad.grid(row=1, column=1, sticky="we", padx=5, pady=5)

        # grid the settings
        y = 0
        for lbl, menu, radio in (
                (self.compress_level_label, self.compress_level_menu, self.use_internal_names_button),
                #(None, None, self.use_compression_names_button),
                (None, None, self.parallel_processing_button),
                (None, None, self.overwrite_button),
            ):
            if lbl:
                lbl.grid(row=y, column=0, sticky="we", padx=2, pady=5)
            if menu:
                menu.grid(row=y, column=1, sticky="we", padx=2, pady=5)
            if radio:
                radio.grid(row=y, column=2, sticky="w", padx=20, pady=5)
            y += 1

    def get_ps2_wad_compiler(self, **kwargs):
        kwargs.update(
            wad_dirpath = self.wad_dirpath.get(),
            wad_filepath = self.wad_filepath.get(),
            overwrite = self.overwrite.get(),
            parallel_processing = self.use_parallel_processing.get(),
            use_internal_names = self.use_internal_names.get(),
            compression_level = COMPRESSION_LEVELS.get(self.compression_level.get(), zlib.Z_NO_COMPRESSION)
            )
        return ps2_wad_compiler.Ps2WadCompiler(**kwargs)

    def select_wad_folder(self):
        if folderpath:
            self.curr_dir = folderpath.replace('/','\\')
            self.wad_dirpath.set(self.curr_dir)

    def _compile_wad(self):
        wad_dirpath = self.wad_dirpath.get()
        if not wad_dirpath:
            wad_dirpath = tkinter.filedialog.askdirectory(
                initialdir=self.curr_dir, title="Select the folder to compile into a WAD"
                )

        if not wad_dirpath:
            return

        self.wad_dirpath.set(wad_dirpath)
        self.curr_dir = os.path.dirname(self.wad_dirpath.get())

        wad_filepath = self.wad_filepath.get()
        if not wad_filepath:
            wad_filepath = tkinter.filedialog.asksaveasfilename(
                initialdir=self.curr_dir, title="Select the file to save the WAD to",
                filetypes=[("PS2 WAD", "*.BIN"), ("all files", "*")],
                defaultextension=".BIN"
                )

        if not wad_filepath:
            return

        self.wad_filepath.set(wad_filepath)
        self.curr_dir = os.path.dirname(self.wad_filepath.get())

        start = time.time()
        try:
            print('Compiling...')
            compiler = self.get_ps2_wad_compiler()
            compiler.compile_wad()
        except Exception:
            print(format_exc())

        print('Finished. Took %s seconds.\n' % (time.time() - start))

    def _decompile_wad(self):
        wad_filepath = self.wad_filepath.get()
        if not wad_filepath:
            wad_filepath = tkinter.filedialog.askopenfilename(
                initialdir=self.curr_dir, title="Select the WAD to decompile",
                filetypes=[("PS2 WAD", "*.BIN"), ("all files", "*")]
                )

        if not wad_filepath:
            return

        self.wad_filepath.set(wad_filepath)
        self.curr_dir = os.path.dirname(self.wad_filepath.get())

        wad_dirpath = self.wad_dirpath.get()
        if not wad_dirpath:
            wad_dirpath = tkinter.filedialog.askdirectory(
                initialdir=self.curr_dir, title="Select the folder to extract the WAD files to"
                )

        if not wad_dirpath:
            return

        self.wad_dirpath.set(wad_dirpath)
        self.curr_dir = os.path.dirname(self.wad_dirpath.get())

        start = time.time()
        try:
            print('Decompiling...')
            decompiler = self.get_ps2_wad_compiler()
            decompiler.extract_files_to_disk()
        except Exception:
            print(format_exc())

        print('Finished. Took %s seconds.\n' % (time.time() - start))


if __name__ == '__main__':
    Ps2WadCompiler().mainloop()
