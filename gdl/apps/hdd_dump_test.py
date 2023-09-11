#!/usr/bin/env python3

filepath   = r"C:\Users\Moses\Desktop\gauntlet_modding\arcade\gauntleg.raw"
output_dir = r"C:\Users\Moses\Desktop\gauntlet_modding\arcade\gauntleg_disc2"
disc       = 2


# don't run if not being executed as a script
if __name__ == "__main__":
    from traceback import format_exc

    try:
        import sys
        import pathlib

        # hack to allow running within import dir
        sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
        from gdl.compilation.arcade_hdd import dump_hdd

        dump_hdd(filepath=filepath, output_dir=output_dir, disc=disc)
    except Exception:
        print(format_exc())
        input()

