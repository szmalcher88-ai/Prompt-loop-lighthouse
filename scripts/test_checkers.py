#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Weryfikator weryfikatorów — domyka pętlę zaufania sygnału prawdy.

Każdy checker (check_parts / check_scene / render_test) jest uruchamiany
na fixture'ach known-good i known-bad (scripts/fixtures/):
  good -> exit 0; bad -> exit 1 z sensownym komunikatem.
Zepsuty checker = skorumpowany sygnał prawdy całego projektu.

Użycie: python scripts/test_checkers.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
FX = SCRIPTS / "fixtures"

failures = []


def run(script, *args):
    p = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def expect(label, script, args, want_rc, must_contain=None):
    rc, out = run(script, *args)
    if rc != want_rc:
        failures.append("%s: oczekiwano exit %d, jest %d\n%s" % (label, want_rc, rc, out))
    elif must_contain and must_contain not in out:
        failures.append("%s: w komunikacie brak %r\n%s" % (label, must_contain, out))
    else:
        print("  PASS  %s" % label)


def main():
    print("check_parts (kontrakt v1):")
    expect("parts known-good -> 0", "check_parts.py", [FX / "parts_good"], 0)
    expect("parts known-bad  -> 1", "check_parts.py", [FX / "parts_bad"], 1,
           must_contain="y=0")

    print("check_parts (kontrakt v2 + nowe typy):")
    expect("parts v2 known-good -> 0 (pier/terrain/house/boat/tree/rocks/path)",
           "check_parts.py", [FX / "parts_good_v2"], 0)
    expect("parts v2 known-bad: pomost za krótki", "check_parts.py",
           [FX / "parts_bad_v2"], 1, must_contain="za krótki")
    expect("parts v2 known-bad: dom bez okien", "check_parts.py",
           [FX / "parts_bad_v2"], 1, must_contain="okien")

    print("check_scene (v1):")
    expect("scene known-good -> 0", "check_scene.py", [FX / "scene_good.obj"], 0)
    expect("scene known-bad  -> 1", "check_scene.py", [FX / "scene_bad.obj"], 1,
           must_contain="lewitacja")

    print("check_scene (v2):")
    expect("scene v2 known-good -> 0", "check_scene.py",
           [FX / "scene_good_v2.obj", 2], 0)
    expect("scene v2 known-bad: brak łodzi", "check_scene.py",
           [FX / "scene_bad_v2.obj", 2], 1, must_contain="łodzi")
    expect("scene v2 known-bad: domy identyczne", "check_scene.py",
           [FX / "scene_bad_v2.obj", 2], 1, must_contain="identyczne")
    expect("scene v2: stara scena (wyspa) NIE przechodzi v2", "check_scene.py",
           [FX / "scene_good.obj", 2], 1, must_contain="v2")

    print("render_test:")
    with tempfile.TemporaryDirectory() as tmp:
        expect("render known-good -> 0", "render_test.py", [FX / "scene_good.obj", tmp], 0)
    with tempfile.TemporaryDirectory() as tmp:
        expect("render known-bad  -> 1", "render_test.py", [FX / "scene_empty.obj", tmp], 1,
               must_contain="pusty")
    with tempfile.TemporaryDirectory() as tmp:
        expect("render v2 known-good -> 0 (wypełnienie kadru w pasmie)",
               "render_test.py", [FX / "scene_good_v2.obj", tmp, 2], 0)
    with tempfile.TemporaryDirectory() as tmp:
        expect("render v2 known-bad: kadr luźny (scena rozrzedzona)", "render_test.py",
               [FX / "scene_sparse.obj", tmp, 2], 1, must_contain="kadru")

    if failures:
        print("FAIL — test_checkers (%d problemów):" % len(failures))
        for f in failures:
            print("  - " + f)
        return 1
    print("OK: wszystkie checkery rozróżniają known-good od known-bad.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
