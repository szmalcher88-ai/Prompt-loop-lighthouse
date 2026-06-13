#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Renderer BRAMY (Blender headless) — forma oświetlona dla ludzkiego oka.

To NIE jest weryfikator pętli (matplotlib render_test zostaje w verify_commands).
Blender jest wolny i biega WYŁĄCZNIE po biegu / przy bramie. Semantyka geometrii
pozostaje w check_scene; tu chodzi o czytelność formy w świetle (cienie modelują
tarasy — to był sens M2.5).

Uruchom:
  blender --background --python scripts/render_blender.py
  blender --background --python scripts/render_blender.py -- <obj> <out_dir>

Silnik: EEVEE (deterministyczny w praktyce; NIE Cycles). Gdy headless EEVEE
zawiedzie, fallback na Workbench z cieniami (w pełni deterministyczny, też
modeluje formę). Determinizm: tolerancyjny — dwa rendery różnią się < próg.
Zapis: out/renders_blender/*.png.

Kontrakt wyjścia (parsowalny przez test_render_blender.py):
  ostatnia linia "OK: ..." (exit 0) lub "FAIL: ..." (exit 1).
"""

import math
import os
import sys

ROOT = None
try:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    ROOT = os.getcwd()
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import gate_cameras as gc  # noqa: E402

RES_X, RES_Y = 960, 720
FILL_BAND = {"main": (0.12, 0.92), "profile": (0.05, 0.85), "bay": (0.10, 0.92)}
DET_MEAN_TOL = 2.0 / 255.0     # średnia różnica per kanał
DET_FRAC_OK = 0.99             # frakcja pikseli w tolerancji


def _die(code, msg):
    print(("OK: " if code == 0 else "FAIL: ") + msg, flush=True)
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(code)


def parse_args():
    argv = sys.argv
    extra = argv[argv.index("--") + 1:] if "--" in argv else []
    obj = extra[0] if len(extra) > 0 else os.path.join(ROOT, "out", "town.obj")
    out_dir = extra[1] if len(extra) > 1 else os.path.join(ROOT, "out", "renders_blender")
    return obj, out_dir


def obj_to_blender(p):
    # import OBJ z up_axis='Y': Blender_co = (x, -z, y)
    return (p[0], -p[2], p[1])


def setup_scene(bpy, obj_path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not os.path.exists(obj_path):
        _die(1, "brak pliku OBJ: %s" % obj_path)
    try:
        bpy.ops.wm.obj_import(filepath=obj_path, up_axis="Y", forward_axis="NEGATIVE_Z")
    except Exception as e:  # noqa: BLE001
        _die(1, "import OBJ nie powiódł się: %r" % e)
    verts = []
    import mathutils  # noqa: E402
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        m = ob.matrix_world
        for c in ob.bound_box:
            w = m @ mathutils.Vector(c)
            # z powrotem do OBJ Y-up: (x, z, -y) odwrotność obj_to_blender
            verts.append((w.x, w.z, -w.y))
    if not verts:
        _die(1, "scena nie zawiera geometrii po imporcie")
    return verts


def add_light(bpy):
    import mathutils
    # słońce zachodzące: ciepłe, nisko nad horyzontem
    sun_data = bpy.data.lights.new("sun", type="SUN")
    sun_data.energy = 3.2
    sun_data.color = (1.0, 0.78, 0.55)
    sun_data.angle = math.radians(2.0)
    sun = bpy.data.objects.new("sun", sun_data)
    bpy.context.collection.objects.link(sun)
    # kierunek: nisko (≈18° nad horyzontem), z boku — cienie modelują tarasy
    sun.rotation_euler = mathutils.Euler((math.radians(62), 0.0, math.radians(35)), "XYZ")
    # miękkie wypełnienie nieba
    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.62, 0.72, 0.85, 1.0)
        bg.inputs[1].default_value = 0.5
    bpy.context.scene.world = world


def add_camera(bpy, name, pos_obj, tgt_obj, fov_deg):
    import mathutils
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens_unit = "FOV"
    cam_data.angle = math.radians(fov_deg)
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.collection.objects.link(cam)
    pos = mathutils.Vector(obj_to_blender(pos_obj))
    tgt = mathutils.Vector(obj_to_blender(tgt_obj))
    cam.location = pos
    cam.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
    return cam


def set_engine(bpy):
    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            used = eng
            break
        except (TypeError, Exception):  # noqa: BLE001
            used = None
    if used is None:
        scene.render.engine = "BLENDER_WORKBENCH"
        used = "BLENDER_WORKBENCH"
    try:
        if "EEVEE" in used:
            scene.eevee.taa_render_samples = 16
            scene.eevee.use_shadows = True
        elif used == "BLENDER_WORKBENCH":
            scene.display.shading.light = "STUDIO"
            scene.display.shading.show_shadows = True
            scene.display.shading.show_cavity = True
            scene.display.shading.color_type = "MATERIAL"
    except Exception:  # noqa: BLE001
        pass
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    return used


def render_to(bpy, cam, path):
    scene = bpy.context.scene
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def load_pixels(bpy, path):
    img = bpy.data.images.load(path, check_existing=False)
    px = list(img.pixels)  # RGBA flat, 0..1
    bpy.data.images.remove(img)
    return px


def fill_fraction(px):
    # tło = kolor lewego-górnego piksela (niebo); liczymy frakcję pikseli odmiennych
    n = len(px) // 4
    if n == 0:
        return 0.0
    # piksel (0,0) to dolny-lewy w Blenderze; bierzemy róg jako próbkę nieba
    bg = px[0:3]
    diff = 0
    step = max(1, n // 40000)  # próbkowanie dla szybkości
    sampled = 0
    for i in range(0, n, step):
        r, g, b = px[i * 4], px[i * 4 + 1], px[i * 4 + 2]
        sampled += 1
        if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > 0.08:
            diff += 1
    return diff / max(sampled, 1)


def determinism_diff(px1, px2):
    n = min(len(px1), len(px2))
    if n == 0:
        return 1.0, 0.0
    tot = 0.0
    within = 0
    pixels = n // 4
    step = max(1, pixels // 40000)
    sampled = 0
    for i in range(0, pixels, step):
        sampled += 1
        d = (abs(px1[i*4] - px2[i*4]) + abs(px1[i*4+1] - px2[i*4+1])
             + abs(px1[i*4+2] - px2[i*4+2])) / 3.0
        tot += d
        if d <= DET_MEAN_TOL:
            within += 1
    return tot / max(sampled, 1), within / max(sampled, 1)


def main():
    try:
        import bpy
    except ImportError:
        _die(1, "uruchom przez: blender --background --python scripts/render_blender.py")
    obj_path, out_dir = parse_args()
    os.makedirs(out_dir, exist_ok=True)

    verts = setup_scene(bpy, obj_path)
    center, radius_xz, height = gc.bounds_metrics(verts)
    add_light(bpy)
    engine = set_engine(bpy)
    print("[render_blender] silnik: %s, %d wierzch. bbox, R=%.1f H=%.1f"
          % (engine, len(verts), radius_xz, height), flush=True)

    cams = {}
    for spec in gc.CAMERAS:
        pos = gc.camera_position(center, radius_xz, height, spec)
        tgt = gc.camera_target(center, height, spec)
        cams[spec["name"]] = add_camera(bpy, spec["name"], pos, tgt, spec["fov"])

    problems = []
    for spec in gc.CAMERAS:
        name = spec["name"]
        path = os.path.join(out_dir, name + ".png")
        render_to(bpy, cams[name], path)
        if not os.path.exists(path):
            problems.append("%s: render nie zapisał pliku" % name)
            continue
        frac = fill_fraction(load_pixels(bpy, path))
        lo, hi = FILL_BAND[name]
        if not (lo <= frac <= hi):
            problems.append("%s: wypełnienie kadru %.1f%% poza pasmem %d-%d%%"
                            % (name, frac * 100, lo * 100, hi * 100))

    # determinizm: render główny po raz drugi i porównanie tolerancyjne
    p_a = os.path.join(out_dir, "main.png")
    p_b = os.path.join(out_dir, "_main_det.png")
    render_to(bpy, cams["main"], p_b)
    mean_d, frac_ok = determinism_diff(load_pixels(bpy, p_a), load_pixels(bpy, p_b))
    try:
        os.remove(p_b)
    except OSError:
        pass
    if frac_ok < DET_FRAC_OK:
        problems.append("determinizm: tylko %.2f%% pikseli w tolerancji (< %.0f%%), "
                        "średnia różnica %.4f" % (frac_ok * 100, DET_FRAC_OK * 100, mean_d))

    if problems:
        for p in problems:
            print("  - " + p, flush=True)
        _die(1, "render_blender: %d problemów" % len(problems))
    _die(0, "%d ujęć bramy w %s (silnik %s, determinizm %.2f%% w tol.)"
         % (len(gc.CAMERAS), out_dir, engine, frac_ok * 100))


if __name__ == "__main__":
    main()
