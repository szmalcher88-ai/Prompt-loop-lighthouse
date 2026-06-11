# fixture known-bad: wyspa BEZ TARASÓW (jedno plateau; reszta v3 spełniona)
import importlib.util
import math
import pathlib

CONTRACT_VERSION = 3

_p = pathlib.Path(__file__).resolve().parent.parent / "parts_good_v3" / "terrain.py"
_spec = importlib.util.spec_from_file_location("good_terrain_v3", _p)
_good = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_good)


def build(**params):
    groups = _good.build()
    for g in groups:
        g["vertices"] = [(x, (2.5 if y > 0.05 else y), z)   # spłaszczenie lądu
                         for (x, y, z) in g["vertices"]]
    return groups
