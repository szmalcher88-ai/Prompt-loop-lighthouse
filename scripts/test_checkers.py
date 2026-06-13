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

    print("check_parts (kontrakt v3 + podłoga wersji):")
    expect("parts v3 known-good -> 0 (terrain/house/wall/chapel/bridge/propsy/bush)",
           "check_parts.py", [FX / "parts_good_v3"], 0)
    expect("parts v3 known-bad: wyspa bez tarasów", "check_parts.py",
           [FX / "parts_bad_v3"], 1, must_contain="tarasowych")
    expect("parts v3 known-bad: archetypy nieodróżnialne", "check_parts.py",
           [FX / "parts_bad_v3"], 1, must_contain="nieodróżnialne")
    expect("parts v3 known-bad: mostek bez zwisu", "check_parts.py",
           [FX / "parts_bad_v3"], 1, must_contain="zwisu")
    expect("parts known-bad: wersja poniżej podłogi (LESSON-003)", "check_parts.py",
           [FX / "parts_bad_floor", "--floor"], 1, must_contain="podłogi")

    print("check_scene (v3):")
    expect("scene v3 known-good -> 0", "check_scene.py",
           [FX / "scene_good_v3.obj", 3], 0)
    expect("scene v3 known-bad: brak kapliczki", "check_scene.py",
           [FX / "scene_bad_v3.obj", 3], 1, must_contain="kaplic")
    expect("scene v3 known-bad: łódka nie na plaży", "check_scene.py",
           [FX / "scene_bad_v3.obj", 3], 1, must_contain="plaż")
    expect("scene v3: scena v2 (pas wybrzeża) NIE przechodzi v3", "check_scene.py",
           [FX / "scene_good_v2.obj", 3], 1, must_contain="v3")

    print("check_scene (v4 — wyspa wg referencji):")
    expect("scene v4 known-good -> 0 (organiczny obrys, grona, kapliczka w kadrze)",
           "check_scene.py", [FX / "scene_good_v4.obj", 4], 0)
    expect("scene v4 known-bad: regularny pierścień domów", "check_scene.py",
           [FX / "scene_bad_v4_ring.obj", 4], 1, must_contain="pierścień")
    expect("scene v4 known-bad: obrys prostokątny/gładki", "check_scene.py",
           [FX / "scene_bad_v4_rect.obj", 4], 1, must_contain="organiczny brzeg")
    expect("scene v4 known-bad: kapliczka poza kadrem głównym", "check_scene.py",
           [FX / "scene_bad_v4_chapel.obj", 4], 1, must_contain="przeciwnej stronie")
    expect("scene v4: scena v3 NIE przechodzi v4 (pierścień/elipsa)", "check_scene.py",
           [FX / "scene_good_v3.obj", 4], 1, must_contain="v4")

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
    with tempfile.TemporaryDirectory() as tmp:
        expect("render v3 known-good -> 0 (kadr w pasmie 30-70)", "render_test.py",
               [FX / "scene_good_v3.obj", tmp, 3], 0)
    with tempfile.TemporaryDirectory() as tmp:
        expect("render v3 known-bad: kadr luźny", "render_test.py",
               [FX / "scene_sparse.obj", tmp, 3], 1, must_contain="kadru")

    if failures:
        print("FAIL — test_checkers (%d problemów):" % len(failures))
        for f in failures:
            print("  - " + f)
        return 1
    print("OK: wszystkie checkery rozróżniają known-good od known-bad.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
