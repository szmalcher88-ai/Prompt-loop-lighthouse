#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cienki wrapper generatora latarni morskiej (Wavefront OBJ + MTL).

Geometria mieszka w parts/lighthouse.py (kontrakt parts/README.md: build()
zwraca liste grup, zero I/O). Tutaj tylko scalamy grupy w jeden plik:
uruchomiony przez `python lighthouse.py` zapisuje out/lighthouse.obj oraz
out/lighthouse.mtl. Nazwy grup (base/tower/gallery/lantern/roof/door) i
materialy pasow pochodza z czesci; weryfikator scripts/check_lighthouse.py
pozostaje zielony bez modyfikacji.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
PART = ROOT / "parts" / "lighthouse.py"

MTL_NAME = "lighthouse.mtl"


def _load_part():
    spec = importlib.util.spec_from_file_location("_lighthouse_part", PART)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def collect_materials(groups):
    """Materialy w kolejnosci pierwszego uzycia: nazwa -> (r, g, b)."""
    mats = {}
    for g in groups:
        for name, rgb in g["colors"].items():
            if name not in mats:
                mats[name] = rgb
    return list(mats.items())


def write_mtl(path, materials):
    lines = ["# Latarnia morska - materialy", ""]
    for name, (r, g, b) in materials:
        lines.append("newmtl %s" % name)
        lines.append("Ka %.3f %.3f %.3f" % (r, g, b))
        lines.append("Kd %.3f %.3f %.3f" % (r, g, b))
        lines.append("Ks 0.100 0.100 0.100")
        lines.append("Ns 16.0")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_obj(path, groups, mtl_name):
    lines = ["# Latarnia morska - model proceduralny (Y-up, metry)",
             "mtllib %s" % mtl_name, ""]
    # Wierzcholki wszystkich grup z przesunieciem indeksow (OBJ jest 1-based).
    offsets = []
    base = 0
    for g in groups:
        offsets.append(base)
        for x, y, z in g["vertices"]:
            lines.append("v %.6f %.6f %.6f" % (x, y, z))
        base += len(g["vertices"])
    lines.append("")
    for gi, g in enumerate(groups):
        lines.append("o %s" % g["name"])
        off = offsets[gi]
        current_mtl = None
        for mtl, idxs in g["faces"]:
            if mtl != current_mtl:
                lines.append("usemtl %s" % mtl)
                current_mtl = mtl
            lines.append("f " + " ".join(str(off + i + 1) for i in idxs))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    groups = _load_part().build()
    materials = collect_materials(groups)
    OUT.mkdir(parents=True, exist_ok=True)
    write_mtl(OUT / MTL_NAME, materials)
    write_obj(OUT / "lighthouse.obj", groups, MTL_NAME)
    total_v = sum(len(g["vertices"]) for g in groups)
    print("Zapisano %s (%d wierzcholkow, %d grup)."
          % (OUT / "lighthouse.obj", total_v, len(groups)))


if __name__ == "__main__":
    main()
