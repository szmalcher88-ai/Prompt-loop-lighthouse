#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dowód bloku TERRAIN (M4). Terrain to nie zwykły builder — to fundament
geometryczny, którego eksport NIESIE INTERFEJS WYSOKOŚCI: checker czyta z niego
wysokość terenu w danym XZ (nearest_terrain_y), a od tego wiszą wszystkie
asercje posadowienia/styku kolejnych części.

Dowód (3 rzeczy):
  1. terrain_bpy buduje się i eksportuje DETERMINISTYCZNIE (dwa buildy = hash).
  2. INTERFEJS WYSOKOŚCI: dla kilku znanych XZ wysokość odczytana z
     wyeksportowanej geometrii == wysokość parametryczna z tarasów (parts/
     terrain.py.height) ORAZ == wysokość, którą raportował terrain OBJ
     (migracja zachowuje interfejs CO DO BAJTA — inaczej posadowienie migałoby
     dopiero przy domach, dwa bloki za późno).
  3. known-bad: płaski teren -> interfejs wysokości pada (checker to wykrywa).

Standalone: python scripts/test_terrain_bpy.py
"""

import glob
import hashlib
import importlib.util
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TERR_BPY = ROOT / "parts" / "terrain_bpy.py"
OUT = ROOT / "out" / "terrain.obj"

# reużycie parametrycznej wysokości terenu OBJ (źródło prawdy interfejsu)
_spec = importlib.util.spec_from_file_location("terrain_obj", ROOT / "parts" / "terrain.py")
terrain_obj = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(terrain_obj)

# punkty kontrolne na osi +X (rmax policzalne pewnie), przez RÓŻNE tarasy.
# Oczekiwanie = wartość parametryczna height() (czyli "z parametrów tarasów");
# nie hardkodujemy strefy — sprawdzamy, że eksport NIESIE tę parametryczną
# wysokość i że punkty pokrywają >= 3 różne poziomy (interfejs rozróżnia tarasy).
TEST_POINTS = [
    (0.0, 0.0, "plateau latarni"),
    (22.0, 0.0, "taras środkowy"),
    (30.0, 0.0, "taras dolny"),
    (40.0, 0.0, "rampa brzegowa"),
    (30.0, -6.0, "turnia"),
]


def locate_blender():
    env = os.environ.get("BLENDER_BIN")
    if env and Path(env).exists():
        return env
    p = shutil.which("blender")
    if p:
        return p
    for pat in (r"C:\Program Files\Blender Foundation\*\blender.exe",):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def digest(path):
    h = hashlib.sha256()
    for p in (path, path.with_suffix(".mtl")):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line.startswith("#") and not line.startswith("mtllib"):
                    h.update(line.encode("utf-8") + b"\n")
    return h.hexdigest()


def terrain_verts_from_obj(path):
    verts, cur = [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        p = raw.split()
        if not p:
            continue
        if p[0] in ("o", "g"):
            cur = p[1]
        elif p[0] == "v" and (cur is None or cur.startswith("terrain")):
            verts.append((float(p[1]), float(p[2]), float(p[3])))
    return verts


def nearest_y(verts, x, z):
    return min(verts, key=lambda v: (v[0] - x) ** 2 + (v[2] - z) ** 2)[1]


def build_solo(blender):
    p = subprocess.run([blender, "--background", "--python", str(ROOT / "scripts" / "bpy_build.py"),
                        "--", str(TERR_BPY), str(OUT)], capture_output=True, text=True, timeout=300)
    out = (p.stdout or "") + (p.stderr or "")
    return any(l.startswith("OK:") for l in out.splitlines()), out


def check_height_interface(verts, ref_verts):
    """Zwraca (ok, komunikaty). Sprawdza, że wysokość z eksportu == parametryczna
    (z parametrów tarasów) == terrain OBJ dla punktów kontrolnych, oraz że punkty
    pokrywają >= 3 różne poziomy (interfejs rozróżnia tarasy, nie stała)."""
    msgs = []
    sampled_levels = []
    for x, z, label in TEST_POINTS:
        sampled = nearest_y(verts, x, z)
        param = terrain_obj.height(x, z)
        ref = nearest_y(ref_verts, x, z)
        sampled_levels.append(round(sampled, 1))
        if abs(sampled - param) > 0.6:
            msgs.append("%s (%.0f,%.0f): eksport %.2f != parametryczna z tarasów %.2f"
                        % (label, x, z, sampled, param))
        if abs(sampled - ref) > 1e-4:
            msgs.append("%s (%.0f,%.0f): eksport bpy %.4f != terrain OBJ %.4f "
                        "(migracja ZMIENIŁA interfejs wysokości!)" % (label, x, z, sampled, ref))
    if len(set(sampled_levels)) < 3:
        msgs.append("punkty kontrolne nie pokrywają >= 3 różnych tarasów (%s) — "
                    "interfejs nie rozróżnia poziomów?" % sampled_levels)
    return (not msgs), msgs


def main():
    blender = locate_blender()
    if not blender:
        print("FAIL: nie znaleziono Blendera (ustaw BLENDER_BIN)")
        return 1

    ok1, out1 = build_solo(blender)
    if not ok1:
        print("FAIL: bpy_build terrain #1:\n%s" % out1[-800:])
        return 1
    d1 = digest(OUT)
    verts = terrain_verts_from_obj(OUT)

    ok2, out2 = build_solo(blender)
    if not ok2:
        print("FAIL: bpy_build terrain #2:\n%s" % out2[-800:])
        return 1
    d2 = digest(OUT)

    # referencja: geometria terrain OBJ (parts/terrain.py) — Y-up bez Blendera
    ref_verts = [tuple(v) for v in terrain_obj.build()[0]["vertices"]]

    problems = []
    if d1 != d2:
        problems.append("NIEDETERMINIZM terrain: %s != %s" % (d1[:12], d2[:12]))
    ok_h, msgs = check_height_interface(verts, ref_verts)
    problems += msgs

    # known-bad: płaski teren (wysokości wyzerowane) -> interfejs musi paść
    flat = [(v[0], 0.0, v[2]) for v in verts]
    bad_ok, _ = check_height_interface(flat, ref_verts)
    if bad_ok:
        problems.append("known-bad: płaski teren PRZESZEDŁ interfejs wysokości (checker ślepy)")

    if problems:
        print("FAIL — blok terrain (%d problemów):" % len(problems))
        for p in problems:
            print("  - " + p)
        return 1
    print("OK: terrain_bpy deterministyczny (hash %s); interfejs wysokości "
          "dowiedziony — eksport == parametryczne tarasy == terrain OBJ dla %d "
          "punktów kontrolnych; płaski teren odrzucony." % (d1[:12], len(TEST_POINTS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
