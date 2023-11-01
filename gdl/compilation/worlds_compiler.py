import os

from ..defs.worlds import worlds_def
from .g3d import constants as c
from . import objects_compiler

class WorldsCompiler(objects_compiler.ObjectsCompiler):

    def compile(self):
        raise NotImplementedError("TODO")
