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


def _export(bpy, out_obj):
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
    return sum(1 for line in open(out_obj, encoding="utf-8") if line.startswith("v "))


def _build_part(bpy, builder_path, seed, params=None):
    spec = importlib.util.spec_from_file_location("bpy_builder", builder_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "build"):
        _die(1, "builder %s nie ma funkcji build(seed=0)" % os.path.basename(builder_path))
    mod.build(seed=seed, **(params or {}))


# Rejestr rdzenia bpy (M4 hybryda): typ -> (builder_path, layout_positions).
# A2: tylko latarnia jest realna; pozostałe dojdą jako osobne bloki (terrain...).
# A2-... : rejestr typów rdzenia bpy. terrain/water/lighthouse — jedna instancja
# w pozycji kanonicznej. house/wall/chapel są MULTI-INSTANCJOWE (layout: pozycje,
# liczność, archetypy) — tu rejestrowane jako placeholder (jedna instancja);
# pełny layout-driven assembler wchodzi w bloku A4 (check sceny hybrydowej).
CORE_BUILDERS = {
    "terrain": os.path.join(ROOT, "parts", "terrain_bpy.py"),
    "water": os.path.join(ROOT, "parts", "water_bpy.py"),
    "house": os.path.join(ROOT, "parts", "house_bpy.py"),
    "lighthouse": os.path.join(ROOT, "parts", "lighthouse_bpy.py"),
}


def _build_scene(bpy, seed):
    """Hybryda: rdzeń w bpy + drobiazgi z ręcznego OBJ -> wspólny town.obj."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # rdzeń bpy (A2: latarnia; reszta dojdzie w kolejnych blokach)
    for typ, path in CORE_BUILDERS.items():
        if os.path.exists(path):
            try:
                _build_part(bpy, path, seed)
            except Exception as e:  # noqa: BLE001
                _die(1, "rdzeń %s: build() zawiódł: %r" % (typ, e))
    # drobiazgi z ręcznego OBJ (musi być wygenerowany wcześniej: drobiazgi_obj.py)
    drob = os.path.join(ROOT, "out", "drobiazgi.obj")
    if not os.path.exists(drob):
        _die(1, "brak out/drobiazgi.obj — uruchom najpierw python scripts/drobiazgi_obj.py")
    try:
        bpy.ops.wm.obj_import(filepath=drob, up_axis="Y", forward_axis="NEGATIVE_Z")
    except Exception as e:  # noqa: BLE001
        _die(1, "import drobiazgów OBJ zawiódł: %r" % e)
    out_obj = os.path.join(ROOT, "out", "town.obj")
    nv = _export(bpy, out_obj)
    core = sum(1 for o in bpy.context.scene.objects if o.type == "MESH")
    _die(0, "hybryda: town.obj (%d obiektów, %d wierzch.) — rdzeń bpy + drobiazgi OBJ" % (core, nv))


def main():
    try:
        import bpy
    except ImportError:
        _die(1, "brak bpy — uruchom przez blender --background --python scripts/bpy_build.py")

    argv = sys.argv
    extra = argv[argv.index("--") + 1:] if "--" in argv else []

    if extra and extra[0] == "scene":
        seed = int(extra[1]) if len(extra) > 1 else 0
        _build_scene(bpy, seed)
        return

    # tryb pojedynczej części (M3): builder + wyjście [+ seed] [+ key=value...]
    builder_path = extra[0] if len(extra) > 0 else os.path.join(ROOT, "parts", "lighthouse_bpy.py")
    out_obj = extra[1] if len(extra) > 1 else os.path.join(ROOT, "out", "lighthouse.obj")
    seed = int(extra[2]) if len(extra) > 2 and extra[2].isdigit() else 0
    params = {}
    for tok in extra[3:]:
        if "=" in tok:
            k, v = tok.split("=", 1)
            params[k] = v
    if not os.path.exists(builder_path):
        _die(1, "brak buildera: %s" % builder_path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        _build_part(bpy, builder_path, seed, params)
    except Exception as e:  # noqa: BLE001
        _die(1, "build() zawiódł: %r" % e)
    if not any(o.type == "MESH" for o in bpy.context.scene.objects):
        _die(1, "scena pusta po build() — brak geometrii")
    nv = _export(bpy, out_obj)
    _die(0, "zbudowano %s (%d wierzch., modyfikatory zaaplikowane)" % (out_obj, nv))


if __name__ == "__main__":
    main()
