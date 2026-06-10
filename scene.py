# -*- coding: utf-8 -*-
"""Assembler sceny: sklada miasteczko nad morzem z czesci w parts/.

Kontrakt parts/README.md: kazda czesc eksportuje build(**params) -> lista grup
(deterministycznie, zero I/O). Tutaj scalamy grupy w jeden model: przesuwamy
indeksy wierzcholkow, przesuwamy geometrie w przestrzeni, nadajemy grupom
prefiksy nazw (terrain*, water*, lighthouse*, house_1..house_N, pier*) oraz
namespace'ujemy materialy per czesc/instancja (np. house_1_wall), po czym
zapisujemy out/town.obj + out/town.mtl (mtllib/usemtl, >= 5 materialow).

Rozmieszczenie (sygnal prawdy: scripts/check_scene.py):
  * latarnia na wzniesieniu w osi (0, 0) i jest najwyzszym elementem sceny,
  * woda to tafla na y=0 (czesc water, bez przesuniecia w Y),
  * domy posadowione na terenie (min-Y domu == wysokosc najblizszego
    wierzcholka terenu) i nie w wodzie (teren pod domem >= 0),
  * rozlaczne AABB w XZ domow i latarni,
  * pomost wchodzi w morze poza krawedzia ladu.

Uklad Y-up, jednostki ~metry, poziom morza y=0. Czysty stdlib.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
PARTS = ROOT / "parts"

MTL_NAME = "town.mtl"
OBJ_NAME = "town.obj"

# O ile cokol latarni zatapia sie w szczycie wzniesienia (estetyka, nie wplywa
# na to, ze latarnia pozostaje najwyzszym elementem sceny).
LIGHTHOUSE_EMBED = 0.8

# Domy o zroznicowanych parametrach rozstawione wzdluz wybrzeza w dwoch rzedach
# (z=9 / z=15) tak, aby ich AABB w XZ byly rozlaczne miedzy soba i z latarnia.
HOUSES = [
    {"x": -18.0, "z": 9.0,
     "params": {"width": 5.0, "depth": 4.0, "height": 2.6,
                "wall_color": (0.85, 0.80, 0.70), "seed": 11}},
    {"x": -10.0, "z": 15.0,
     "params": {"width": 6.0, "depth": 5.0, "height": 3.0,
                "wall_color": (0.72, 0.62, 0.52), "seed": 12}},
    {"x": -2.0, "z": 9.0,
     "params": {"width": 5.5, "depth": 4.5, "height": 2.8,
                "wall_color": (0.68, 0.74, 0.80), "seed": 13}},
    {"x": 6.0, "z": 15.0,
     "params": {"width": 6.5, "depth": 5.0, "height": 3.2,
                "wall_color": (0.82, 0.56, 0.46), "seed": 14}},
    {"x": 14.0, "z": 9.0,
     "params": {"width": 5.0, "depth": 5.5, "height": 2.7,
                "wall_color": (0.60, 0.70, 0.56), "seed": 15}},
    {"x": 20.0, "z": 15.0,
     "params": {"width": 5.0, "depth": 4.0, "height": 3.4,
                "wall_color": (0.88, 0.84, 0.62), "seed": 16}},
]


def _load_part(stem):
    path = PARTS / (stem + ".py")
    spec = importlib.util.spec_from_file_location("_part_" + stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _translate(groups, dx, dy, dz):
    """Przesuwa wszystkie wierzcholki grup o (dx, dy, dz)."""
    for g in groups:
        g["vertices"] = [(x + dx, y + dy, z + dz) for (x, y, z) in g["vertices"]]
    return groups


def _namespace_materials(groups, prefix):
    """Nadaje materialom prefiks (np. wall -> house_1_wall), by uniknac
    kolizji nazw miedzy czesciami i pozwolic na rozne kolory per instancja."""
    for g in groups:
        remap = {m: prefix + "_" + m for m in g["colors"]}
        g["colors"] = {remap[m]: rgb for m, rgb in g["colors"].items()}
        g["faces"] = [(remap[m], idxs) for (m, idxs) in g["faces"]]
    return groups


def _merge(groups, name):
    """Scala kilka grup w jedna (lokalne indeksy przesuniete), nadaje nazwe."""
    verts, faces, colors = [], [], {}
    for g in groups:
        off = len(verts)
        verts.extend(g["vertices"])
        for mat, idxs in g["faces"]:
            faces.append((mat, tuple(off + i for i in idxs)))
        colors.update(g["colors"])
    return {"name": name, "vertices": verts, "faces": faces, "colors": colors}


def _centroid_xz(group):
    vs = group["vertices"]
    n = len(vs)
    return (sum(v[0] for v in vs) / n, sum(v[2] for v in vs) / n)


def _nearest_terrain_y(tverts, x, z):
    """Wysokosc najblizszego (w XZ) wierzcholka terenu — tak jak check_scene."""
    return min(tverts, key=lambda v: (v[0] - x) ** 2 + (v[2] - z) ** 2)[1]


def assemble():
    """Buduje liste grup sceny (z prefiksami i materialami namespaced)."""
    scene = []

    # --- teren: pas wybrzeza, baza do posadowienia reszty ---
    terrain = _load_part("terrain").build()
    _namespace_materials(terrain, "terrain")
    terrain[0]["name"] = "terrain"
    tverts = [v for g in terrain for v in g["vertices"]]
    scene.extend(terrain)

    # --- woda: tafla na y=0, rozciagnieta poza krawedz ladu (otacza wyspe) ---
    water = _load_part("water").build(size=80.0, cells=16)
    _namespace_materials(water, "water")
    water[0]["name"] = "water"
    scene.extend(water)

    # --- latarnia: na szczycie wzniesienia w osi (0, 0), najwyzszy element ---
    lighthouse = _load_part("lighthouse").build()
    _namespace_materials(lighthouse, "lighthouse")
    ty_center = _nearest_terrain_y(tverts, 0.0, 0.0)
    _translate(lighthouse, 0.0, ty_center - LIGHTHOUSE_EMBED, 0.0)
    for g in lighthouse:
        g["name"] = "lighthouse_" + g["name"]
    scene.extend(lighthouse)

    # --- domy: scalone w pojedyncze grupy house_i, posadowione na terenie ---
    house_mod = _load_part("house")
    for i, spec in enumerate(HOUSES, start=1):
        prefix = "house_%d" % i
        groups = house_mod.build(**spec["params"])
        _namespace_materials(groups, prefix)
        house = _merge(groups, prefix)
        _translate([house], spec["x"], 0.0, spec["z"])
        cx, cz = _centroid_xz(house)
        ty = _nearest_terrain_y(tverts, cx, cz)
        _translate([house], 0.0, ty, 0.0)
        scene.append(house)

    # --- pomost: wchodzi w morze poza poludniowa krawedzia ladu (-Z) ---
    pier = _load_part("pier").build()
    _namespace_materials(pier, "pier")
    _translate(pier, 0.0, 0.0, -36.0)
    for g in pier:
        g["name"] = "pier_" + g["name"]
    scene.extend(pier)

    return scene


def collect_materials(groups):
    """Materialy w kolejnosci pierwszego uzycia: nazwa -> (r, g, b)."""
    mats = {}
    for g in groups:
        for name, rgb in g["colors"].items():
            if name not in mats:
                mats[name] = rgb
    return list(mats.items())


def write_mtl(path, materials):
    lines = ["# Miasteczko nad morzem - materialy", ""]
    for name, (r, g, b) in materials:
        lines.append("newmtl %s" % name)
        lines.append("Ka %.3f %.3f %.3f" % (r, g, b))
        lines.append("Kd %.3f %.3f %.3f" % (r, g, b))
        lines.append("Ks 0.100 0.100 0.100")
        lines.append("Ns 16.0")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_obj(path, groups, mtl_name):
    lines = ["# Miasteczko nad morzem - scena proceduralna (Y-up, metry)",
             "mtllib %s" % mtl_name, ""]
    # Wierzcholki wszystkich grup z przesunieciem indeksow (OBJ jest 1-based).
    offsets = []
    base = 0
    for g in groups:
        offsets.append(base)
        for x, y, z in g["vertices"]:
            lines.append("v %.6f %.6f %.6f" % (x, y, z))
        base += len(g["vertices"])
    lines.append("")
    for gi, g in enumerate(groups):
        lines.append("o %s" % g["name"])
        off = offsets[gi]
        current_mtl = None
        for mtl, idxs in g["faces"]:
            if mtl != current_mtl:
                lines.append("usemtl %s" % mtl)
                current_mtl = mtl
            lines.append("f " + " ".join(str(off + i + 1) for i in idxs))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    groups = assemble()
    materials = collect_materials(groups)
    OUT.mkdir(parents=True, exist_ok=True)
    write_mtl(OUT / MTL_NAME, materials)
    write_obj(OUT / OBJ_NAME, groups, MTL_NAME)
    total_v = sum(len(g["vertices"]) for g in groups)
    total_f = sum(len(g["faces"]) for g in groups)
    print("Zapisano %s (%d grup, %d wierzcholkow, %d scianek, %d materialow)."
          % (OUT / OBJ_NAME, len(groups), total_v, total_f, len(materials)))


if __name__ == "__main__":
    main()

SCENE_VERSION = 1
