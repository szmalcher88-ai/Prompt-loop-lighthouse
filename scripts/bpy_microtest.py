#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FAZA 0 (M3-migracja) — bramka wejścia idź/nie-idź.

Cały zwrot na bpy stoi i upada na tym, czy Blender headless potrafi BUDOWAĆ
I EKSPORTOWAĆ (nie tylko renderować). Test: sześcian -> Bevel -> Subdivision
Surface -> eksport do out/microtest.obj z ZAAPLIKOWANYMI modyfikatorami;
sprawdź, że wierzchołków przybyło (modyfikatory zadziałały na eksporcie).

Uruchom: blender --background --python scripts/bpy_microtest.py
Kontrakt wyjścia: ostatnia linia "PASS: ..." (exit 0) lub "FAIL: ..." (exit 1).
"""

import os
import sys


def _die(code, msg):
    print(("PASS: " if code == 0 else "FAIL: ") + msg, flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def main():
    try:
        import bpy
    except ImportError:
        _die(1, "brak modułu bpy — uruchom przez blender --background --python")

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "out")
    os.makedirs(out_dir, exist_ok=True)
    obj_path = os.path.join(out_dir, "microtest.obj")
    if os.path.exists(obj_path):
        os.remove(obj_path)

    ver = bpy.app.version_string
    bpy.ops.wm.read_factory_settings(use_empty=True)

    try:
        bpy.ops.mesh.primitive_cube_add(size=2.0)
    except Exception as e:  # noqa: BLE001
        _die(1, "nie udało się utworzyć sześcianu: %r" % e)
    cube = bpy.context.active_object
    base_verts = len(cube.data.vertices)

    try:
        bev = cube.modifiers.new(name="Bevel", type="BEVEL")
        bev.width = 0.15
        bev.segments = 2
        sub = cube.modifiers.new(name="Subdiv", type="SUBSURF")
        sub.levels = 2
        sub.render_levels = 2
    except Exception as e:  # noqa: BLE001
        _die(1, "nie udało się dodać modyfikatorów (Bevel/Subsurf): %r" % e)

    try:
        bpy.ops.wm.obj_export(filepath=obj_path, apply_modifiers=True,
                              export_selected_objects=False)
    except Exception as e:  # noqa: BLE001
        _die(1, "eksport OBJ nie powiódł się: %r" % e)

    if not os.path.exists(obj_path):
        _die(1, "eksport nie utworzył pliku %s" % obj_path)

    exported_verts = sum(1 for line in open(obj_path, encoding="utf-8")
                         if line.startswith("v "))
    if exported_verts <= base_verts:
        _die(1, "modyfikatory NIE zadziałały na eksporcie (wierzchołki %d <= baza %d)"
             % (exported_verts, base_verts))

    _die(0, "Blender %s | sześcian bazowy %d wierzch. -> po Bevel+Subsurf (zaaplik.) "
         "%d wierzch. w out/microtest.obj | build+export headless DZIAŁA"
         % (ver, base_verts, exported_verts))


if __name__ == "__main__":
    main()
