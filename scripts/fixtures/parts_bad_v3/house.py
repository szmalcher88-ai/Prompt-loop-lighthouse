# fixture known-bad: archetypy domu NIEODRÓŻNIALNE (ignoruje parametr)
import importlib.util
import pathlib

CONTRACT_VERSION = 3

_p = pathlib.Path(__file__).resolve().parent.parent / "parts_good_v3" / "house.py"
_spec = importlib.util.spec_from_file_location("good_house_v3", _p)
_good = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_good)


def build(archetype="timber", **params):
    return _good.build(archetype="timber")   # zawsze ta sama geometria
