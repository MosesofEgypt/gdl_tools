#!/usr/bin/env python3
import os
import tkinter.filedialog
import tkinter as tk
import time

from tkinter import *
from traceback import format_exc
from gdl.compilation import ps2_wad_compiler


class Ps2WadCompiler(Tk):
    curr_dir = "."
    debug = False
    
    def __init__(self, **options):
        Tk.__init__(self, **options)
        
        self.title("PS2 WAD Tool V1.0.0")
        self.minsize(500, 250)
        self.resizable(1, 0)

        self.wad_dirpath = StringVar(self)
        self.wad_filepath = StringVar(self)

        self.use_parallel_processing = BooleanVar(self, True)
        self.use_internal_names      = BooleanVar(self, True)
        self.overwrite               = BooleanVar(self, False)

        self.wad_filepath_frame = LabelFrame(self, text="WAD filepath")
        self.wad_dirpath_frame  = LabelFrame(self, text="WAD directory")
        self.compile_frame      = LabelFrame(self, text="")
        self.settings_frame     = LabelFrame(self, text="Settings")

        self.wad_dirpath_field = Entry(self.wad_filepath_frame, textvariable=self.wad_dirpath)
        self.wad_dirpath_field.config(width=46, state=DISABLED)
        self.wad_filepath_field = Entry(self.wad_dirpath_frame, textvariable=self.wad_filepath)
        self.wad_filepath_field.config(width=46, state=DISABLED)

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
        self.use_internal_names_button = Checkbutton(
            self.settings_frame, text='Use filenames built into WAD',
            variable=self.use_internal_names, onvalue=1, offvalue=0
            )
        self.overwrite_button = Checkbutton(
            self.settings_frame, text='Overwrite on extract',
            variable=self.overwrite, onvalue=1, offvalue=0
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
                               [self.settings_frame, 2],
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
        for checkbuttons in (
                (self.parallel_processing_button, self.use_internal_names_button),
                (self.overwrite_button, None),
            ):
            x = 0
            for checkbutton in checkbuttons:
                if checkbutton:
                    checkbutton.grid(row=y, column=x, sticky="w", padx=20, pady=0)

                x += 1
            y += 1

    def get_ps2_wad_compiler(self, **kwargs):
        kwargs.update(
            wad_dirpath = self.wad_dirpath.get(),
            wad_filepath = self.wad_filepath.get(),
            overwrite = self.overwrite.get(),
            parallel_processing = self.use_parallel_processing.get(),
            use_internal_names = self.use_internal_names.get(),
            )
        return ps2_wad_compiler.Ps2WadCompiler(**kwargs)

    def select_wad_folder(self):
        if folderpath:
            self.curr_dir = folderpath.replace('/','\\')
            self.wad_dirpath.set(self.curr_dir)

    def _compile_wad(self):
        wad_dirpath = tkinter.filedialog.askdirectory(
            initialdir=self.curr_dir, title="Select the folder to compile into a WAD"
            )
        if not wad_dirpath:
            return

        self.wad_dirpath.set(wad_dirpath.replace('/','\\'))
        self.curr_dir = os.path.dirname(self.wad_dirpath.get())

        wad_filepath = tkinter.filedialog.asksaveasfilename(
            initialdir=self.curr_dir, title="Select the file to save the WAD to",
            filetypes=[("PS2 WAD", "*.BIN"), ("all files", "*")]
            )
        if not wad_filepath:
            return

        self.wad_filepath.set(wad_filepath.replace('/','\\'))
        self.curr_dir = os.path.dirname(self.wad_filepath.get())

        start = time.time()
        try:
            print('Compiling...')
        except Exception:
            print(format_exc())

        print('Finished. Took %s seconds.\n' % (time.time() - start))

    def _decompile_wad(self):
        wad_filepath = tkinter.filedialog.askopenfilename(
            initialdir=self.curr_dir, title="Select the WAD to decompile",
            filetypes=[("PS2 WAD", "*.BIN"), ("all files", "*")]
            )
        if not wad_filepath:
            return

        self.wad_filepath.set(wad_filepath.replace('/','\\'))
        self.curr_dir = os.path.dirname(self.wad_filepath.get())

        wad_dirpath = tkinter.filedialog.askdirectory(
            initialdir=self.curr_dir, title="Select the folder to extract the WAD files to"
            )
        if not wad_dirpath:
            return

        self.wad_dirpath.set(wad_dirpath.replace('/','\\'))
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
