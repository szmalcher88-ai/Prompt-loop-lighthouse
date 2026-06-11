# fixture known-bad: mostek BEZ ZWISU (liny idealnie poziome)
import importlib.util
import pathlib

CONTRACT_VERSION = 3

_p = pathlib.Path(__file__).resolve().parent.parent / "parts_good_v3" / "bridge.py"
_spec = importlib.util.spec_from_file_location("good_bridge_v3", _p)
_good = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_good)


def build(**params):
    groups = _good.build()
    for g in groups:
        g["vertices"] = [(x, (2.0 if y > 1.2 else y), z)   # liny wyprostowane
                         for (x, y, z) in g["vertices"]]
    return groups
