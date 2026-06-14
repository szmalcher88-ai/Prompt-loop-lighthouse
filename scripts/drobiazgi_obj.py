#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assembler DROBIAZGÓW do ręcznego OBJ (M4 hybryda).

Drobiazgi (pier/boat/bridge/bush/tree/rocks) zostają na ręcznym OBJ w tej
rundzie; rdzeń (terrain/water/house/wall/chapel/lighthouse) migruje na bpy.
Ten skrypt składa drobiazgi z istniejących builderów części w jeden
out/drobiazgi.obj + .mtl, który scripts/bpy_build.py wczytuje do sceny bpy
i scala z rdzeniem do wspólnego town.obj.

Deterministyczny: stałe pozycje, brak losowości (seedy jawne, gdzie używane).
To NIE jest finalny layout — to nośnik dowodu, że hybryda bpy<->OBJ działa
i jest deterministyczna (A2). Realny layout dojdzie w bloku finałowym M4.

Użycie: python scripts/drobiazgi_obj.py [out.obj]
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS = ROOT / "parts"


def _load(stem):
    spec = importlib.util.spec_from_file_location("part_" + stem, PARTS / (stem + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _translate(groups, dx, dy, dz, rename=None):
    out = []
    for g in groups:
        out.append({
            "name": rename or g["name"],
            "vertices": [(x + dx, y + dy, z + dz) for (x, y, z) in g["vertices"]],
            "faces": g["faces"],
            "colors": g["colors"],
        })
    return out


def assemble():
    pier = _load("pier")
    boat = _load("boat")
    tree = _load("tree")
    rocks = _load("rocks")
    bridge = _load("bridge")
    bush = _load("bush")

    groups = []
    # pomosty (rot via gotowy build), na ujemnym Z
    groups += _translate(pier.build(), -8.0, 0.0, -30.0, rename="pier_1")
    groups += _translate(pier.build(), 8.0, 0.0, -30.0, rename="pier_2")
    # łodzie: jedna nad wodą (y=0), jedna dalej
    groups += _translate(boat.build(), -8.0, 0.0, -22.0, rename="boat_1")
    groups += _translate(boat.build(length=4.0), 18.0, 0.0, 14.0, rename="boat_2")
    # mostek
    groups += _translate(bridge.build(length=8.0), 14.0, 3.0, -6.0, rename="bridge_1")
    # drzewa
    for k in range(3):
        groups += _translate(tree.build(height=4.0 + 0.4 * k),
                             -14.0 + 6.0 * k, 0.0, 16.0, rename="tree_%d" % (k + 1))
    # krzewy
    for k in range(2):
        groups += _translate(bush.build(scale=0.9 + 0.1 * k),
                             -6.0 + 4.0 * k, 0.0, 6.0, rename="bush_%d" % (k + 1))
    # głazy (deterministyczne z seeda)
    rg = rocks.build(count=4, seed=7)
    for k, g in enumerate(rg):
        groups += _translate([g], -20.0 + 10.0 * k, 0.0, -34.0, rename="rock_%d" % (k + 1))
    return groups


def write_obj(path, groups, mtlname):
    mats = {}
    lines = ["mtllib %s" % mtlname]
    off = 1
    for g in groups:
        ns = {}
        for m, rgb in g["colors"].items():
            nm = "%s_%s" % (g["name"], m)
            ns[m] = nm
            mats[nm] = rgb
        lines.append("o " + g["name"])
        for v in g["vertices"]:
            lines.append("v %.4f %.4f %.4f" % v)
        cur = None
        for m, idxs in g["faces"]:
            if ns[m] != cur:
                cur = ns[m]
                lines.append("usemtl " + cur)
            lines.append("f " + " ".join(str(off + i) for i in idxs))
        off += len(g["vertices"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    mtl = []
    for nm, rgb in mats.items():
        mtl += ["newmtl " + nm, "Kd %.3f %.3f %.3f" % rgb, ""]
    (path.parent / mtlname).write_text("\n".join(mtl), encoding="utf-8")


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "out" / "drobiazgi.obj"
    out.parent.mkdir(parents=True, exist_ok=True)
    groups = assemble()
    write_obj(out, groups, out.with_suffix(".mtl").name)
    nv = sum(len(g["vertices"]) for g in groups)
    print("OK: %s (%d grup, %d wierzch.)" % (out, len(groups), nv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
