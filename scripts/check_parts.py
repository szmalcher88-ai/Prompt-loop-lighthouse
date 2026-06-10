#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Weryfikator części modelu (parts/*.py) — sygnał prawdy pętli.

Kontrakt (parts/README.md): build(**params) -> list grup
  {"name": str, "vertices": [(x,y,z)...], "faces": [(material, (i0,i1,...))...],
   "colors": {material: (r,g,b)}}

Kontrakt warunkowy: część, której nie ma, nie jest sprawdzana;
brak katalogu parts/ lub pusty katalog = zielony baseline.

Asercje wspólne: struktura, niepuste, poprawne indeksy, brak NaN/inf,
deterministyczność (dwa build() identyczne), budżet z budgets.json.
Asercje specyficzne per typ części — sekcje poniżej (terrain/water/
lighthouse/house/pier). Moduł o innej nazwie dostaje tylko wspólne.

Użycie: python scripts/check_parts.py [katalog_parts]   # argv do testów
"""

import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "parts"
BUDGETS = ROOT / "budgets.json"

errors = []


def err(part, msg):
    errors.append("[%s] %s" % (part, msg))


def load_module(path):
    spec = importlib.util.spec_from_file_location("part_" + path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def all_vertices(groups):
    return [v for g in groups for v in g["vertices"]]


def faces_with_material(groups, predicate):
    """Wierzchołki ścianek, których materiał spełnia predykat."""
    out = []
    for g in groups:
        for mat, idxs in g["faces"]:
            if predicate(mat):
                out.extend(g["vertices"][i] for i in idxs)
    return out


def centroid_y(verts):
    return sum(v[1] for v in verts) / len(verts)


def check_common(name, groups, budget):
    if not isinstance(groups, list) or not groups:
        err(name, "build() musi zwrócić niepustą listę grup")
        return False
    total_v = total_f = 0
    for g in groups:
        for key in ("name", "vertices", "faces", "colors"):
            if key not in g:
                err(name, "grupa bez klucza %r" % key)
                return False
        if not g["vertices"] or not g["faces"]:
            err(name, "grupa %s: puste vertices/faces" % g["name"])
            return False
        for v in g["vertices"]:
            if len(v) != 3 or any(not math.isfinite(c) for c in v):
                err(name, "grupa %s: zły wierzchołek %r" % (g["name"], v))
                return False
        n = len(g["vertices"])
        for mat, idxs in g["faces"]:
            if len(idxs) < 3:
                err(name, "grupa %s: ścianka < 3 indeksów" % g["name"])
                return False
            if any(not (0 <= i < n) for i in idxs):
                err(name, "grupa %s: indeks poza zakresem" % g["name"])
                return False
            if mat not in g["colors"]:
                err(name, "grupa %s: materiał %r bez koloru w colors" % (g["name"], mat))
                return False
        for mat, rgb in g["colors"].items():
            if len(rgb) != 3 or any(not (0.0 <= c <= 1.0) for c in rgb):
                err(name, "kolor %r poza [0,1]" % mat)
                return False
        total_v += n
        total_f += len(g["faces"])
    if total_v > budget["max_vertices"]:
        err(name, "budżet wierzchołków przekroczony (%d > %d)" % (total_v, budget["max_vertices"]))
    if total_f > budget["max_faces"]:
        err(name, "budżet ścianek przekroczony (%d > %d)" % (total_f, budget["max_faces"]))
    return True


def extent(verts, axis):
    vals = [v[axis] for v in verts]
    return max(vals) - min(vals)


def check_terrain(name, groups):
    verts = all_vertices(groups)
    if extent(verts, 0) < 40 or extent(verts, 2) < 40:
        err(name, "teren za mały: wymagany zakres XZ >= 40 m w obu osiach")
    ys = [v[1] for v in verts]
    if min(ys) < -2 or max(ys) > 12:
        err(name, "wysokości terenu poza zakresem [-2, 12] (jest %.2f..%.2f)" % (min(ys), max(ys)))
    if max(ys) - min(ys) < 1.0:
        err(name, "brak wzniesienia: max-min wysokości < 1 m")


def check_water(name, groups):
    verts = all_vertices(groups)
    bad = [v for v in verts if abs(v[1]) > 1e-6]
    if bad:
        err(name, "woda nie jest taflą na y=0 (%d wierzchołków poza, np. %r)" % (len(bad), bad[0]))
    if extent(verts, 0) < 20 or extent(verts, 2) < 20:
        err(name, "tafla za mała: wymagany zakres XZ >= 20 m")


def check_lighthouse(name, groups):
    verts = all_vertices(groups)
    ys = [v[1] for v in verts]
    height = max(ys) - min(ys)
    if not (10 <= height <= 200):
        err(name, "wysokość latarni %.2f poza zakresem [10, 200]" % height)
    tower = [g for g in groups if "tower" in g["name"]]
    if not tower:
        err(name, "brak grupy zawierającej 'tower'")
        return
    tverts = all_vertices(tower)
    t_lo = min(v[1] for v in tverts)
    t_hi = max(v[1] for v in tverts)

    def radius(frac_lo, frac_hi):
        xs = [v for v in tverts if frac_lo <= (v[1] - t_lo) / max(t_hi - t_lo, 1e-9) <= frac_hi]
        cx = sum(v[0] for v in tverts) / len(tverts)
        cz = sum(v[2] for v in tverts) / len(tverts)
        return max((math.hypot(v[0] - cx, v[2] - cz) for v in xs), default=0.0)

    if not radius(0.75, 1.0) < radius(0.0, 0.25) * 0.95:
        err(name, "wieża nie zwęża się ku górze")


def check_house(name, groups):
    verts = all_vertices(groups)
    ys = [v[1] for v in verts]
    height = max(ys) - min(ys)
    if not (2 <= height <= 15):
        err(name, "wysokość domu %.2f poza zakresem [2, 15]" % height)
    roof = faces_with_material(groups, lambda m: "roof" in m or "dach" in m)
    door = faces_with_material(groups, lambda m: "door" in m or "drzwi" in m)
    walls = faces_with_material(groups, lambda m: not any(
        k in m for k in ("roof", "dach", "door", "drzwi")))
    if not roof:
        err(name, "brak ścianek z materiałem dachu (nazwa zawierająca 'roof')")
    if not door:
        err(name, "brak ścianek z materiałem drzwi (nazwa zawierająca 'door')")
    if roof and walls and centroid_y(roof) <= centroid_y(walls):
        err(name, "dach nie jest powyżej ścian (centroidy: dach %.2f, ściany %.2f)"
            % (centroid_y(roof), centroid_y(walls)))
    if door and min(v[1] for v in door) - min(ys) > 0.5:
        err(name, "drzwi nie sięgają podłoża domu (luka > 0.5 m)")


def check_pier(name, groups):
    verts = all_vertices(groups)
    below = [v for v in verts if v[1] < -0.2]
    above = [v for v in verts if v[1] > 0.0]
    if not below:
        err(name, "pale nie sięgają poniżej wody (brak wierzchołków y < -0.2)")
    if len(above) < 0.5 * len(verts):
        err(name, "większość pomostu powinna być nad wodą y=0")


SPECIFIC = {
    "terrain": check_terrain,
    "water": check_water,
    "lighthouse": check_lighthouse,
    "house": check_house,
    "pier": check_pier,
}


def main():
    if not PARTS_DIR.is_dir():
        print("OK: katalog %s nie istnieje (zielony baseline)." % PARTS_DIR.name)
        return 0
    modules = sorted(p for p in PARTS_DIR.glob("*.py") if p.stem != "__init__")
    if not modules:
        print("OK: brak modułów części (zielony baseline).")
        return 0

    budgets = json.loads(BUDGETS.read_text(encoding="utf-8"))["parts"]
    for path in modules:
        name = path.stem
        try:
            mod = load_module(path)
        except Exception as e:
            err(name, "import nieudany: %r" % e)
            continue
        if not hasattr(mod, "build"):
            err(name, "brak funkcji build()")
            continue
        try:
            groups = mod.build()
            groups2 = mod.build()
        except Exception as e:
            err(name, "build() rzucił wyjątek: %r" % e)
            continue
        if groups != groups2:
            err(name, "build() niedeterministyczny: dwa wywołania różnią się")
            continue
        budget = budgets.get(name, budgets["default"])
        if not check_common(name, groups, budget):
            continue
        if name in SPECIFIC:
            SPECIFIC[name](name, groups)

    if errors:
        print("FAIL — check_parts (%d problemów):" % len(errors))
        for e in errors:
            print("  - " + e)
        return 1
    print("OK: wszystkie części (%s) przechodzą kontrole." % ", ".join(p.stem for p in modules))
    return 0


if __name__ == "__main__":
    sys.exit(main())
