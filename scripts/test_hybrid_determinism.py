#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dowód bloku A2 (M4): hybrydowy build bpy<->OBJ jest deterministyczny i scala
oba światy w jeden town.obj.

Kroki:
  1. python scripts/drobiazgi_obj.py            -> out/drobiazgi.obj (świat OBJ)
  2. blender ... bpy_build.py -- scene  (x2)    -> out/town.obj (rdzeń bpy + OBJ)
  3. hash(town.obj) identyczny w obu buildach   -> determinizm pełnej hybrydy
  4. town.obj zawiera grupy RDZENIA bpy (tower/base/...) ORAZ DROBIAZGÓW OBJ
     (pier/boat/tree...) -> dowód, że hybryda faktycznie się scala.

Standalone (jak test_checkers): uruchom `python scripts/test_hybrid_determinism.py`.
"""

import glob
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOWN = ROOT / "out" / "town.obj"
# po wpięciu layoutu (A4) rdzeń ma prefiksy grup; sprawdzamy obecność typów
CORE_GROUPS = {"lighthouse", "terrain", "water", "house", "wall", "chapel"}  # bpy
OBJ_GROUPS = {"pier", "boat", "tree", "rock", "bridge", "bush"}              # ręczny OBJ


def locate_blender():
    env = os.environ.get("BLENDER_BIN")
    if env and Path(env).exists():
        return env
    p = shutil.which("blender")
    if p:
        return p
    for pat in (r"C:\Program Files\Blender Foundation\*\blender.exe",
                r"C:\Program Files (x86)\Blender Foundation\*\blender.exe"):
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


def groups_in(path):
    return {l.split()[1].split(".")[0].rsplit("_", 1)[0] if "_" in l else l.split()[1]
            for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("o ")}


def build_scene(blender):
    p = subprocess.run([blender, "--background", "--python", str(ROOT / "scripts" / "bpy_build.py"),
                        "--", "scene"], capture_output=True, text=True, timeout=300)
    out = (p.stdout or "") + (p.stderr or "")
    return any(l.startswith("OK:") for l in out.splitlines()), out


def main():
    blender = locate_blender()
    if not blender:
        print("FAIL: nie znaleziono Blendera (ustaw BLENDER_BIN)")
        return 1

    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "drobiazgi_obj.py")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL: drobiazgi_obj.py:\n%s" % (r.stdout + r.stderr))
        return 1

    ok1, out1 = build_scene(blender)
    if not ok1:
        print("FAIL: bpy_build scene #1:\n%s" % out1[-800:])
        return 1
    d1 = digest(TOWN)

    present = set()
    for raw in TOWN.read_text(encoding="utf-8").splitlines():
        if raw.startswith("o "):
            nm = raw.split()[1]
            for c in CORE_GROUPS | OBJ_GROUPS:
                if nm.startswith(c):
                    present.add(c)
    missing_core = CORE_GROUPS - present
    missing_obj = OBJ_GROUPS - present

    ok2, out2 = build_scene(blender)
    if not ok2:
        print("FAIL: bpy_build scene #2:\n%s" % out2[-800:])
        return 1
    d2 = digest(TOWN)

    problems = []
    if d1 != d2:
        problems.append("NIEDETERMINIZM hybrydy: %s != %s" % (d1[:12], d2[:12]))
    if missing_core:
        problems.append("brak grup RDZENIA bpy w town.obj: %s" % ", ".join(sorted(missing_core)))
    if missing_obj:
        problems.append("brak grup DROBIAZGÓW OBJ w town.obj: %s" % ", ".join(sorted(missing_obj)))

    if problems:
        print("FAIL — A2 hybryda (%d problemów):" % len(problems))
        for p in problems:
            print("  - " + p)
        return 1
    print("OK: hybryda bpy<->OBJ deterministyczna (hash %s); town.obj scala "
          "rdzeń bpy {%s} i drobiazgi OBJ {%s}."
          % (d1[:12], ",".join(sorted(CORE_GROUPS & present)),
             ",".join(sorted(OBJ_GROUPS & present))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
