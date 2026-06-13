#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pipeline build->export (M3-migracja) — assembler bpy.

Czyści scenę bpy, importuje builder części, woła build(seed), eksportuje
całość do OBJ Z ZAAPLIKOWANYMI modyfikatorami (deterministycznie). To jedyny
punkt, który eksportuje — części same nie zapisują plików (kontrakt bpy,
parts/README.md).

Uruchom:
  blender --background --python scripts/bpy_build.py
  blender --background --python scripts/bpy_build.py -- <builder.py> <out.obj> [seed]

Domyślnie builder = parts/lighthouse_bpy.py, wyjście = out/lighthouse.obj.
Kontrakt wyjścia: ostatnia linia "OK: ..." (exit 0) lub "FAIL: ..." (exit 1).
"""

import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _die(code, msg):
    print(("OK: " if code == 0 else "FAIL: ") + msg, flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def main():
    try:
        import bpy
    except ImportError:
        _die(1, "brak bpy — uruchom przez blender --background --python scripts/bpy_build.py")

    argv = sys.argv
    extra = argv[argv.index("--") + 1:] if "--" in argv else []
    builder_path = extra[0] if len(extra) > 0 else os.path.join(ROOT, "parts", "lighthouse_bpy.py")
    out_obj = extra[1] if len(extra) > 1 else os.path.join(ROOT, "out", "lighthouse.obj")
    seed = int(extra[2]) if len(extra) > 2 else 0

    if not os.path.exists(builder_path):
        _die(1, "brak buildera: %s" % builder_path)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    spec = importlib.util.spec_from_file_location("bpy_builder", builder_path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        if not hasattr(mod, "build"):
            _die(1, "builder %s nie ma funkcji build(seed=0)" % os.path.basename(builder_path))
        mod.build(seed=seed)
    except Exception as e:  # noqa: BLE001
        _die(1, "build() zawiódł: %r" % e)

    if not any(o.type == "MESH" for o in bpy.context.scene.objects):
        _die(1, "scena pusta po build() — brak geometrii")

    os.makedirs(os.path.dirname(out_obj), exist_ok=True)
    if os.path.exists(out_obj):
        os.remove(out_obj)
    try:
        bpy.ops.wm.obj_export(
            filepath=out_obj, apply_modifiers=True, export_selected_objects=False,
            export_materials=True, export_triangulated_mesh=False,
            export_normals=True, export_uv=False,
        )
    except Exception as e:  # noqa: BLE001
        _die(1, "eksport OBJ zawiódł: %r" % e)

    if not os.path.exists(out_obj):
        _die(1, "eksport nie utworzył %s" % out_obj)
    nv = sum(1 for line in open(out_obj, encoding="utf-8") if line.startswith("v "))
    _die(0, "zbudowano %s (%d wierzch., modyfikatory zaaplikowane)" % (out_obj, nv))


if __name__ == "__main__":
    main()
