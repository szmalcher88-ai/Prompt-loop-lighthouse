# fixture known-bad: pomost v2 ZA KRÓTKI (reszta kontraktu spełniona)
import importlib.util
import pathlib

CONTRACT_VERSION = 2

_p = pathlib.Path(__file__).resolve().parent.parent / "parts_good_v2" / "pier.py"
_spec = importlib.util.spec_from_file_location("good_pier_fixture", _p)
_good = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_good)


def build(**params):
    return _good.build(length=8.0)
