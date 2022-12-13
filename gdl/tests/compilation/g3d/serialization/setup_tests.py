# Insert this module into any test package to allow running
# tests from there. This module will simply look for the root
# of the package tree, which should be "gdl". It will insert
# its parent into sys.path, which will allow running tests as
# if they were run from outside the package root.
import pathlib, sys
import pytest

pth = pathlib.Path(__file__)
while pth.name and pth.name.lower() != "gdl":
    pth = pth.parent

if sys.path[0] != str(pth.parent):
    sys.path.insert(0, str(pth.parent))
