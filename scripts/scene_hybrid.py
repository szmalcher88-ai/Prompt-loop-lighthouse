# -*- coding: utf-8 -*-
"""A4 — layout-driven assembler HYBRYDY (M4): rdzeń przez buildery bpy na
pozycjach z layoutu scene.py, drobiazgi z ręcznego OBJ.

Wspólny layout = scene.py (działający v5). Tu:
  * core_placements() — dla 6 typów rdzenia (terrain/water/lighthouse/house/
    wall/stair/chapel) zwraca: builder bpy, parametry, finalną pozycję
    (w przestrzeni Blendera) i nazwę. Pozycje wyznaczone TĄ SAMĄ metodą co
    scene.py (posadowienie na terenie przez _nearest_terrain_y z parts/terrain.py
    — eksport bpy terenu == te wysokości, dowiedzione w bloku terrain).
  * write_drobiazgi() — buduje scenę OBJ (scene.assemble()) i zapisuje TYLKO
    grupy drobiazgów do out/drobiazgi.obj (pier/boat/bridge/bush/tree/rock/
    path/barrel/crate); rdzeń pomija (idzie przez bpy).

Transform pozycji: część bpy ma wierzchołki Y-up -> Blender (x,-z,y); eksport
up_axis='Y' odtwarza OBJ Y-up. Ustawienie obiektu na pozycji OBJ (X,Y,Z)
wymaga location Blendera = (X, -Z, Y).
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS = ROOT / "parts"

# rdzeń (bpy) vs drobiazg (OBJ) — po prefiksie nazwy grupy w scene.assemble()
CORE_PREFIXES = ("terrain", "water", "lighthouse", "house", "wall", "stair", "chapel")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


scene = _load(ROOT / "scene.py", "scene_obj")
terrain_obj = _load(PARTS / "terrain.py", "terrain_obj_h")
house_obj = _load(PARTS / "house.py", "house_obj_h")


def _tverts():
    return [v for g in terrain_obj.build() for v in g["vertices"]]


def _loc(x, y, z):
    """Pozycja OBJ (x,y,z) -> location obiektu w Blenderze."""
    return (x, -z, y)


def _centroid_xz(groups):
    vs = [v for g in groups for v in g["vertices"]]
    return (sum(v[0] for v in vs) / len(vs), sum(v[2] for v in vs) / len(vs))


def core_placements():
    """Lista placementów rdzenia: dict(builder, params, loc, rot_z, prefix/rename)."""
    tv = _tverts()
    ny = lambda x, z: scene._nearest_terrain_y(tv, x, z)  # noqa: E731
    P = []

    # teren i woda — w origin (teren to baza wysokości)
    P.append(dict(builder=PARTS / "terrain_bpy.py", params={}, loc=(0, 0, 0),
                  rot_z=0.0, rename={"terrain": "terrain"}))
    P.append(dict(builder=PARTS / "water_bpy.py", params=dict(size=100.0, cells=20),
                  loc=(0, 0, 0), rot_z=0.0, rename={"water": "water"}))

    # latarnia — na szczycie w osi (0,0), prefiks lighthouse_
    tyc = ny(0.0, 0.0)
    P.append(dict(builder=PARTS / "lighthouse_bpy.py", params={},
                  loc=_loc(0.0, tyc - scene.LIGHTHOUSE_EMBED, 0.0), rot_z=0.0,
                  prefix="lighthouse_"))

    # domy — grona na tarasach; posadowienie na terenie pod centroidem (jak scene.py)
    for i, h in enumerate(scene.HOUSES, start=1):
        name = "house_%d_%s" % (i, h["archetype"])
        lcx, lcz = _centroid_xz(house_obj.build(**h["params"]))
        ty = ny(h["x"] + lcx, h["z"] + lcz)
        P.append(dict(builder=PARTS / "house_bpy.py",
                      params=dict(h["params"], name=name),
                      loc=_loc(h["x"], ty, h["z"]), rot_z=0.0, rename={name: name}))

    # mury oporowe — w lukach między gronami, posadowione na terenie
    for i, w in enumerate(scene.WALLS, start=1):
        name = "wall_%d" % i
        params = dict(w["params"], include_stairs=False)
        seg = scene._merge(_part("wall").build(**params), name)
        # centroid po rotacji+translacji jak scene.py
        scene._rotate_y([seg], w["rot"])
        scene._translate([seg], w["x"], 0.0, w["z"])
        cx, cz = scene._centroid_xz(seg)
        ty = ny(cx, cz)
        P.append(dict(builder=PARTS / "wall_bpy.py", params=params,
                      loc=_loc(w["x"], ty, w["z"]), rot_z=w["rot"], rename={"wall": name}))

    # schody — bieg łączący dwa tarasy (jak scene.py)
    for i, s in enumerate(scene.STAIRS, start=1):
        name = "stair_%d" % i
        n = int(s["params"]["n_steps"])
        run = float(s["params"]["step_run"])
        sx, edge_z = s["x"], s["edge_z"]
        half = n * run / 2.0
        g_high = ny(sx, edge_z - half)
        g_low = ny(sx, edge_z + half)
        rise = max(1.0, g_high - g_low)
        params = dict(s["params"], include_wall=False, step_rise=rise / n)
        P.append(dict(builder=PARTS / "wall_bpy.py", params=params,
                      loc=_loc(sx, g_low, edge_z + half), rot_z=180.0,
                      rename={"stairs": name}))

    # kapliczka — na turni
    ch = scene.CHAPEL
    chapel_mod = _part("chapel")
    cg = scene._merge(chapel_mod.build(**ch["params"]), "chapel_1")
    scene._translate([cg], ch["x"], 0.0, ch["z"])
    ccx, ccz = scene._centroid_xz(cg)
    ty = ny(ccx, ccz)
    P.append(dict(builder=PARTS / "chapel_bpy.py", params=ch["params"],
                  loc=_loc(ch["x"], ty, ch["z"]), rot_z=0.0, rename={"chapel": "chapel_1"}))
    return P


def _part(stem):
    return _load(PARTS / (stem + ".py"), "_p_" + stem)


def write_drobiazgi(path=None):
    path = Path(path) if path else ROOT / "out" / "drobiazgi.obj"
    groups = scene.assemble()
    drob = [g for g in groups if not g["name"].startswith(CORE_PREFIXES)]
    path.parent.mkdir(parents=True, exist_ok=True)
    mats = scene.collect_materials(drob)
    scene.write_mtl(path.with_suffix(".mtl"), mats)
    scene.write_obj(path, drob, path.with_suffix(".mtl").name)
    print("OK: %s (%d grup drobiazgów)" % (path, len(drob)))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--drobiazgi":
        sys.exit(write_drobiazgi(sys.argv[2] if len(sys.argv) > 2 else None))
    # podgląd placementów rdzenia (bez Blendera)
    for p in core_placements():
        print(p["rename"] if "rename" in p else p["prefix"], "->", p["loc"], "rot", p["rot_z"])
