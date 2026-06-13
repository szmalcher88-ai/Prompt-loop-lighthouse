#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test renderera bramy (standalone). Lokalizuje Blendera, renderuje minimalną
scenę OBJ (-> exit 0) i sprawdza, że pusta/brakująca scena daje FAIL.

Blender jest wolny (~kilka-kilkanaście s) — to NIE jest część verify_commands
pętli, tylko self-test infrastruktury bramy, uruchamiany ręcznie / przy bramie.

Lokalizacja Blendera: env BLENDER_BIN, potem PATH, potem typowe ścieżki Windows.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RENDER = ROOT / "scripts" / "render_blender.py"

GOOD_OBJ = """mtllib mini.mtl
o terrain
v -10 0 -10
v 10 0 -10
v 10 0 10
v -10 0 10
usemtl ground
f 1 2 3 4
o tower
v -1 0.0 -1
v 1 0.0 -1
v 1 0.0 1
v -1 0.0 1
v -1 9.0 -1
v 1 9.0 -1
v 1 9.0 1
v -1 9.0 1
usemtl stone
f 5 6 7 8
f 9 10 11 12
f 5 6 10 9
f 7 8 12 11
f 6 7 11 10
f 8 5 9 12
"""

GOOD_MTL = "newmtl ground\nKd 0.4 0.5 0.3\n\nnewmtl stone\nKd 0.8 0.2 0.2\n"
EMPTY_OBJ = "# pusty model — brak geometrii\no nothing\n"


def locate_blender():
    env = os.environ.get("BLENDER_BIN")
    if env and Path(env).exists():
        return env
    on_path = shutil.which("blender")
    if on_path:
        return on_path
    import glob
    for pat in (r"C:\Program Files\Blender Foundation\*\blender.exe",
                r"C:\Program Files (x86)\Blender Foundation\*\blender.exe"):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def run_render(blender, obj_path, out_dir):
    p = subprocess.run(
        [blender, "--background", "--python", str(RENDER), "--",
         str(obj_path), str(out_dir)],
        capture_output=True, text=True, timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    blender = locate_blender()
    if not blender:
        print("FAIL: nie znaleziono Blendera (ustaw BLENDER_BIN albo dodaj do PATH)")
        return 1
    print("blender: %s" % blender)

    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "mini.obj").write_text(GOOD_OBJ, encoding="utf-8")
        (tmp / "mini.mtl").write_text(GOOD_MTL, encoding="utf-8")
        (tmp / "empty.obj").write_text(EMPTY_OBJ, encoding="utf-8")

        t0 = time.monotonic()
        rc, out = run_render(blender, tmp / "mini.obj", tmp / "out_good")
        dt = time.monotonic() - t0
        ok_good = rc == 0 and "OK:" in out and (tmp / "out_good" / "main.png").exists()
        print("  %s  minimalna scena -> exit 0 (%.1fs)" % ("PASS" if ok_good else "FAIL", dt))
        if not ok_good:
            failures.append("known-good: rc=%s\n%s" % (rc, out[-800:]))

        rc2, out2 = run_render(blender, tmp / "nie_ma.obj", tmp / "out_missing")
        ok_missing = rc2 != 0 and "FAIL:" in out2
        print("  %s  brakujący OBJ -> FAIL" % ("PASS" if ok_missing else "FAIL"))
        if not ok_missing:
            failures.append("known-bad (missing): rc=%s\n%s" % (rc2, out2[-400:]))

        rc3, out3 = run_render(blender, tmp / "empty.obj", tmp / "out_empty")
        ok_empty = rc3 != 0 and "FAIL:" in out3
        print("  %s  pusta scena -> FAIL" % ("PASS" if ok_empty else "FAIL"))
        if not ok_empty:
            failures.append("known-bad (empty): rc=%s\n%s" % (rc3, out3[-400:]))

    if failures:
        print("FAIL — test_render_blender (%d problemów):" % len(failures))
        for f in failures:
            print("  - " + f)
        return 1
    print("OK: render_blender renderuje poprawną scenę i odrzuca pustą/brakującą "
          "(czas renderu ~%.1fs — gate-only, poza verify_commands)." % dt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
