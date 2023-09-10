import os

from pprint import pprint
from traceback import format_exc

from gdl.defs.arcade_hdd import read_file_headers, arcade_hdd_def

disc = 0

filepath = r"C:\Users\Moses\Desktop\gauntlet_modding\arcade\gauntdl.raw"

file_headers = read_file_headers(filepath=filepath, disc=disc)
