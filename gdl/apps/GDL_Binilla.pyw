#!/usr/bin/env python3

# don't run if not being executed as a script
if __name__ == "__main__":
    from traceback import format_exc

    try:
        import sys
        import pathlib

        # hack to allow running within import dir
        sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
        from gdl.gdl_binilla.app_window import GdlBinilla

        main_window = GdlBinilla(debug=3, curr_dir=pathlib.Path.cwd())
        main_window.mainloop()
    except Exception:
        print(format_exc())
        input()
