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

sys.path.insert(0, str(SCRIPTS))
import geom  # noqa: E402

failures = []


def check(label, cond):
    if cond:
        print("  PASS  " + label)
    else:
        failures.append(label)
        print("  FAIL  " + label)


def test_geom_helpers():
    print("helpery geom (A2):")
    a = geom.aabb([(0, 0, 0), (2, 3, 4)])
    check("aabb -> (xmin..zmax)", a == (0, 2, 0, 3, 0, 4))
    b = (1, 3, 1, 4, 1, 5)
    check("penetrates: nachodzące bryły", geom.penetrates(a, b, 0.3))
    far = (10, 12, 0, 3, 0, 4)
    check("penetrates: rozłączne -> False", not geom.penetrates(a, far, 0.3))
    touch = (2, 4, 0, 3, 0, 4)            # styk ścianą (overlap 0 w X)
    check("penetrates: styk ścianą -> False", not geom.penetrates(a, touch, 0.3))
    check("distance_xz: rozłączne > 0", geom.distance_xz(a, far) > 7.9)
    check("distance_xz: nachodzące = 0", geom.distance_xz(a, b) == 0.0)
    check("rests_on: dno na h w tol", geom.rests_on(a, 0.2, 0.3))
    check("rests_on: dno poza tol -> False", not geom.rests_on(a, 1.0, 0.3))
    wide = (0, 10, 0, 1, 0, 2)
    check("long_axis: dłuższa X", geom.long_axis(wide) == "x")
    e0, e1 = geom.axis_ends_xz(wide)
    check("axis_ends_xz: końce wzdłuż X", e0 == (0, 1) and e1 == (10, 1))


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
    test_geom_helpers()
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

    print("check_lighthouse (bpy — tryb fixtury OBJ):")
    expect("lighthouse known-good -> 0 (forma bpy + materiały)", "check_lighthouse.py",
           [FX / "lighthouse_good.obj"], 0)
    expect("lighthouse known-bad: brak zwężenia wieży", "check_lighthouse.py",
           [FX / "lighthouse_bad_notaper.obj"], 1, must_contain="zwęża się ku górze")
    expect("lighthouse known-bad: za niska", "check_lighthouse.py",
           [FX / "lighthouse_bad_short.obj"], 1, must_contain="wysokość")
    expect("lighthouse known-bad: wieża jednolita (brak pasów — dług M3)",
           "check_lighthouse.py", [FX / "lighthouse_bad_uniform.obj"], 1,
           must_contain="naprzemiennych poziomych pasów")

    print("check_scene (v5 — relacje przestrzenne / styk):")
    expect("scene v5 known-good -> 0 (schody/łódka/mostek przylegają)",
           "check_scene.py", [FX / "scene_good_v5.obj", 5], 0)
    expect("scene v5 known-bad: schody przenikają dom", "check_scene.py",
           [FX / "scene_bad_v5_stair_pen.obj", 5], 1, must_contain="przenika")
    expect("scene v5 known-bad: schody nie sięgają górnego poziomu", "check_scene.py",
           [FX / "scene_bad_v5_stair_short.obj", 5], 1, must_contain="nie sięga górnego")
    expect("scene v5 known-bad: łódka zatopiona", "check_scene.py",
           [FX / "scene_bad_v5_boat_sunk.obj", 5], 1, must_contain="tonie")
    expect("scene v5 known-bad: ścieżka urywa się przed kapliczką", "check_scene.py",
           [FX / "scene_bad_v5_path_gap.obj", 5], 1, must_contain="nie dochodzi do kapliczki")
    expect("scene v5 known-bad: przyczółek mostka wisi w powietrzu", "check_scene.py",
           [FX / "scene_bad_v5_bridge_float.obj", 5], 1, must_contain="wisi nad gruntem")
    expect("scene v5: scena v4 NIE przechodzi v5 (brak styku)", "check_scene.py",
           [FX / "scene_good_v4.obj", 5], 1, must_contain="v5")

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
