# fixture known-bad: dom v2 BEZ OKIEN (reszta kontraktu spełniona)
import importlib.util
import pathlib

CONTRACT_VERSION = 2

_p = pathlib.Path(__file__).resolve().parent.parent / "parts_good_v2" / "house.py"
_spec = importlib.util.spec_from_file_location("good_house_fixture", _p)
_good = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_good)


def build(**params):
    groups = _good.build()
    for g in groups:
        g["faces"] = [f for f in g["faces"] if f[0] != "glass"]
    return groups
