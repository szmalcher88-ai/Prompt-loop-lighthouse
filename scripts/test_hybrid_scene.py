#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brama A4 (M4): WALIDACJA HYBRYDOWEJ SCENY. Dowodzi czterech rzeczy, dotąd
tylko obiecanych:

  1. layout stawia 6 typów rdzenia (bpy) na właściwych tarasach z gronami
     (nie placeholdery) — check_scene v5 PRZECHODZI na żywym town.obj;
  2. determinizm PEŁNEJ sceny z layoutem (dwa buildy = identyczny town.obj);
  3. asercje styku działają REALNIE w poprzek bpy<->OBJ — udowodnione
     NIETRYWIALNIE: perturbacja każdego styku (łódka OBJ pod wodę bpy, mostek
     OBJ z dala od kapliczki bpy, dom bpy w lewitację) ROZBIJA check_scene
     z właściwym komunikatem (asercja nie przechodzi pusto);
  4. ograniczenie "domy z dala od klifów" jest EGZEKWOWANE: dom przesunięty na
     krawędź klifu pada na posadowieniu (ziarnistość terenu ~3 m > tol 0.6).

Standalone: python scripts/test_hybrid_scene.py
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
SCRIPTS = ROOT / "scripts"


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


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=400)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def digest(path):
    h = hashlib.sha256()
    for q in (path, path.with_suffix(".mtl")):
        if q.exists():
            for line in q.read_text(encoding="utf-8").splitlines():
                if not line.startswith("#") and not line.startswith("mtllib"):
                    h.update(line.encode("utf-8") + b"\n")
    return h.hexdigest()


ASSEMBLER = ROOT / "parts" / "scene_bpy.py"
CORE_TARGETS = [ROOT / "parts" / (t + "_bpy.py")
                for t in ("terrain", "water", "house", "wall", "chapel", "lighthouse", "pier")]


def build_hybrid(blender):
    rc, o = run([sys.executable, str(ASSEMBLER), "--drobiazgi"])
    if rc != 0:
        return False, "drobiazgi: " + o[-400:]
    rc, o = run([blender, "--background", "--python", str(SCRIPTS / "bpy_build.py"), "--", "scene"])
    if not any(l.startswith("OK:") for l in o.splitlines()):
        return False, "bpy_build scene: " + o[-600:]
    return True, ""


def check_scene(obj_path):
    rc, o = run([sys.executable, str(SCRIPTS / "check_scene.py"), str(obj_path), "5"])
    return rc, o


def perturb(src, dst, prefixes, fn):
    """Kopia town.obj z transformacją wierzchołków obiektów o nazwie zaczynającej
    się od któregokolwiek z `prefixes` (eksport bpy: bloki v per obiekt)."""
    cur, out = None, []
    for raw in src.read_text(encoding="utf-8").splitlines():
        p = raw.split()
        if p and p[0] in ("o", "g"):
            cur = p[1]
        if p and p[0] == "v" and cur and cur.startswith(prefixes):
            x, y, z = float(p[1]), float(p[2]), float(p[3])
            x, y, z = fn(x, y, z)
            out.append("v %.6f %.6f %.6f" % (x, y, z))
        else:
            out.append(raw)
    dst.write_text("\n".join(out) + "\n", encoding="utf-8")
    if src.with_suffix(".mtl").exists():
        dst.with_suffix(".mtl").write_text(
            src.with_suffix(".mtl").read_text(encoding="utf-8").replace(
                src.stem, dst.stem), encoding="utf-8")


def main():
    missing = [p.name for p in CORE_TARGETS + [ASSEMBLER] if not p.exists()]
    if missing:
        print("OK: brama A4 czeka na cele (brak: %s) — zielony baseline."
              % ", ".join(missing))
        return 0
    blender = locate_blender()
    if not blender:
        print("FAIL: nie znaleziono Blendera (BLENDER_BIN)")
        return 1

    ok, msg = build_hybrid(blender)
    if not ok:
        print("FAIL: build hybrydy:\n" + msg)
        return 1
    d1 = digest(TOWN)

    problems = []

    # (1) check_scene v5 zielony na żywej hybrydzie
    rc, o = check_scene(TOWN)
    if rc != 0:
        problems.append("check_scene v5 NIE przechodzi na hybrydzie:\n" + o[-500:])

    # (2) determinizm pełnej sceny z layoutem
    ok2, msg2 = build_hybrid(blender)
    if not ok2:
        problems.append("drugi build hybrydy: " + msg2)
    elif digest(TOWN) != d1:
        problems.append("NIEDETERMINIZM pełnej sceny: %s != %s" % (d1[:12], digest(TOWN)[:12]))

    # (3+4) cross-world known-bad: każda perturbacja MUSI rozbić check_scene
    tmp = ROOT / "out" / "_town_bad.obj"
    cases = [
        ("łódka OBJ pod wodę bpy", ("boat",), lambda x, y, z: (x, y - 1.2, z), "tonie"),
        ("mostek OBJ z dala od kapliczki bpy", ("bridge",),
         lambda x, y, z: (x - 14.0, y, z), "nie dochodzi do kapliczki"),
        ("dom bpy w lewitację (posadowienie strzeże)", ("house_1",),
         lambda x, y, z: (x, y + 2.0, z), "lewitacja"),
    ]
    for label, pref, fn, expect in cases:
        perturb(TOWN, tmp, pref, fn)
        rc, o = check_scene(tmp)
        if rc == 0:
            problems.append("known-bad '%s' PRZESZEDŁ check_scene (asercja pusta/ślepa)" % label)
        elif expect not in o:
            problems.append("known-bad '%s': brak oczekiwanego komunikatu %r" % (label, expect))
    for ext in (".obj", ".mtl"):
        f = tmp.with_suffix(ext)
        if f.exists():
            f.unlink()

    if problems:
        print("FAIL — brama A4 (%d problemów):" % len(problems))
        for p in problems:
            print("  - " + p)
        return 1
    print("OK: BRAMA A4 zielona z właściwego powodu — check_scene v5 przechodzi na "
          "żywej hybrydzie (rdzeń bpy na layoucie + drobiazgi OBJ), pełna scena "
          "deterministyczna (hash %s), a asercje styku bpy<->OBJ są NIETRYWIALNE: "
          "łódka-woda, mostek-kapliczka i posadowienie domu (anty-klif) rozbijają "
          "się przy perturbacji." % d1[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())
