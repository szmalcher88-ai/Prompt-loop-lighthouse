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
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
PARTS = ROOT / "parts"

MTL_NAME = "town.mtl"
OBJ_NAME = "town.obj"

# Geometria wyspy (parts/terrain.py v3): elipsa o polosiach A (X), B (Z).
# Pozycje na wyspie wyznaczamy po wspolrzednych eliptycznych (r, phi), tak jak
# wzorzec scripts/fixtures/gen_scene_v3.py: r=0 to os latarni (0,0), r=1 to
# linia brzegowa. Zatoczka z plaza otwiera sie ku -Z.
ISLAND_A, ISLAND_B = 40.0, 30.0


def _ell(r, phi_deg):
    """Punkt (x, z) na wyspie: promien r (0..1) i kat phi w stopniach."""
    a = math.radians(phi_deg)
    return (ISLAND_A * r * math.cos(a), ISLAND_B * r * math.sin(a))

# O ile cokol latarni zatapia sie w szczycie wzniesienia (estetyka, nie wplywa
# na to, ze latarnia pozostaje najwyzszym elementem sceny).
LIGHTHOUSE_EMBED = 0.8

# Domy (>= 9) rozstawione pierscieniem na tarasie srodkowym wyspy (r=0.45 ->
# teren y=5.5) wokol latarni. Trzy archetypy (parts/house.py v3): timber / stone
# / two_story uzyte po 3 razy, w grupach nazwanych house_<k>_<archetyp>. Phi co
# 40 stopni daje rozlaczne AABB w XZ (miedzy soba i z latarnia) oraz kazdemu
# domowi sasiada <= 12 m. Kazda instancja rozni sie archetypem albo wymiarami i
# kolorami (sciany + dach + szyby) — asercja v2 "domy parami rozne" (check_scene).
_HOUSE_RING_R = 0.45
_HOUSE_SPECS = [
    {"archetype": "timber", "width": 6.0, "depth": 5.0,
     "wall_color": (0.85, 0.80, 0.70), "roof_color": (0.55, 0.20, 0.15),
     "window_color": (0.52, 0.68, 0.80), "seed": 11},
    {"archetype": "stone", "width": 6.6, "depth": 5.4,
     "wall_color": (0.60, 0.58, 0.54), "roof_color": (0.40, 0.28, 0.22),
     "window_color": (0.58, 0.72, 0.82), "seed": 12},
    {"archetype": "two_story", "width": 5.6, "depth": 4.6,
     "wall_color": (0.78, 0.74, 0.66), "roof_color": (0.30, 0.36, 0.40),
     "window_color": (0.50, 0.66, 0.78), "seed": 13},
    {"archetype": "timber", "width": 6.6, "depth": 4.6,
     "wall_color": (0.82, 0.56, 0.46), "roof_color": (0.48, 0.16, 0.12),
     "window_color": (0.60, 0.74, 0.84), "seed": 14},
    {"archetype": "stone", "width": 7.0, "depth": 5.8,
     "wall_color": (0.56, 0.55, 0.52), "roof_color": (0.34, 0.30, 0.20),
     "window_color": (0.54, 0.70, 0.80), "seed": 15},
    {"archetype": "two_story", "width": 6.0, "depth": 5.0,
     "wall_color": (0.88, 0.84, 0.62), "roof_color": (0.58, 0.24, 0.18),
     "window_color": (0.56, 0.71, 0.83), "seed": 16},
    {"archetype": "timber", "width": 5.6, "depth": 5.4,
     "wall_color": (0.80, 0.72, 0.60), "roof_color": (0.50, 0.22, 0.16),
     "window_color": (0.53, 0.69, 0.81), "seed": 17},
    {"archetype": "stone", "width": 6.2, "depth": 5.0,
     "wall_color": (0.62, 0.60, 0.56), "roof_color": (0.38, 0.30, 0.24),
     "window_color": (0.55, 0.71, 0.79), "seed": 18},
    {"archetype": "two_story", "width": 5.2, "depth": 4.2,
     "wall_color": (0.74, 0.78, 0.72), "roof_color": (0.32, 0.34, 0.28),
     "window_color": (0.51, 0.67, 0.80), "seed": 19},
]
HOUSES = []
for _k, _spec in enumerate(_HOUSE_SPECS):
    _x, _z = _ell(_HOUSE_RING_R, _k * 40.0)
    HOUSES.append({"x": _x, "z": _z, "archetype": _spec["archetype"], "params": _spec})

# Lodki na tafli morza (czesc parts/boat.py). Pomost zatoczki (os x=0) wychodzi
# ku -Z poza obrys wyspy; jego srodek w XZ to okolo (0, -31). boat_1 cumuje tuz
# przy pomoscie (< 6 m od jego srodka), boat_2 dryfuje na otwartej wodzie po
# stronie -Z (> 10 m od pomostu). Kazda instancja rozni sie wymiarami, kolorem
# i seedem (zakaz idealnych kopii).
BOATS = [
    {"x": 3.5, "z": -33.0,
     "params": {"length": 3.6, "beam": 1.35, "depth": 0.26, "gunwale_y": 0.42,
                "hull_color": (0.60, 0.28, 0.18), "seat_color": (0.72, 0.60, 0.40),
                "seats": 2, "seed": 21}},
    {"x": 22.0, "z": -34.0,
     "params": {"length": 4.4, "beam": 1.7, "depth": 0.34, "gunwale_y": 0.50,
                "hull_color": (0.30, 0.40, 0.52), "seat_color": (0.66, 0.56, 0.42),
                "seats": 3, "seed": 22}},
]

# Zagajnik sosen na tarasie dolnym wyspy (czesc parts/tree.py). Domy stoja na
# tarasie srodkowym (r=0.52), wiec sosny sadzimy nieco nizej (r=0.65 -> teren
# y=2.5) na luku od strony lądu, z dala od zatoczki. Kazda sosna ma inna
# wysokosc, promien korony i seed (zakaz idealnych kopii); assembler sadzi ja
# na terenie (min-Y == wysokosc najblizszego wierzcholka terenu). Grupy tree_i.
_TREE_SPOTS = [
    (0.65, 30.0), (0.65, 55.0), (0.65, 80.0), (0.65, 105.0),
    (0.65, 130.0), (0.65, 155.0), (0.65, 200.0),
]
_TREE_PARAMS = [
    {"height": 6.4, "base_radius": 1.5, "layers": 3, "seed": 31},
    {"height": 4.6, "base_radius": 1.1, "layers": 3, "seed": 32},
    {"height": 7.2, "base_radius": 1.7, "layers": 4, "seed": 33},
    {"height": 5.2, "base_radius": 1.2, "layers": 3, "seed": 34},
    {"height": 6.0, "base_radius": 1.4, "layers": 3, "seed": 35},
    {"height": 4.0, "base_radius": 1.0, "layers": 2, "seed": 36},
    {"height": 5.8, "base_radius": 1.35, "layers": 3, "seed": 37},
]
TREES = [{"x": _ell(r, phi)[0], "z": _ell(r, phi)[1], "params": p}
         for (r, phi), p in zip(_TREE_SPOTS, _TREE_PARAMS)]


# Glazy wokol wyspy (czesc parts/rocks.py). Otaczaja wyspe pierscieniem tuz przy
# linii brzegowej (r=0.98 -> plycizna y=-0.8), wystajac ponad tafle. Kazdy glaz
# rozni sie promieniem, splaszczeniem, kolorem i seedem (zakaz idealnych kopii);
# assembler sadzi go na terenie (min-Y == wysokosc najblizszego wierzcholka
# terenu) jak drzewa/domy. Grupy rock_1..rock_N.
_ROCK_PARAMS = [
    {"radius": 1.1, "scale_y": 0.65, "color": (0.52, 0.50, 0.47), "seed": 41},
    {"radius": 0.8, "scale_y": 0.7, "color": (0.46, 0.45, 0.43), "seed": 42},
    {"radius": 1.4, "scale_y": 0.6, "color": (0.55, 0.52, 0.48), "seed": 43},
    {"radius": 0.9, "scale_y": 0.72, "color": (0.48, 0.47, 0.45), "seed": 44},
    {"radius": 1.2, "scale_y": 0.64, "color": (0.50, 0.48, 0.44), "seed": 45},
    {"radius": 0.7, "scale_y": 0.75, "color": (0.44, 0.43, 0.42), "seed": 46},
    {"radius": 1.3, "scale_y": 0.6, "color": (0.53, 0.51, 0.47), "seed": 47},
    {"radius": 0.95, "scale_y": 0.68, "color": (0.47, 0.46, 0.44), "seed": 48},
    {"radius": 1.15, "scale_y": 0.66, "color": (0.51, 0.49, 0.46), "seed": 49},
    {"radius": 1.6, "scale_y": 0.7, "color": (0.49, 0.47, 0.44), "seed": 50},
    {"radius": 1.5, "scale_y": 0.72, "color": (0.54, 0.51, 0.47), "seed": 51},
    {"radius": 1.35, "scale_y": 0.68, "color": (0.46, 0.45, 0.43), "seed": 52},
]
ROCKS = [{"x": _ell(0.98, 30.0 * k)[0], "z": _ell(0.98, 30.0 * k)[1], "params": p}
         for k, p in enumerate(_ROCK_PARAMS)]


# Sciezka piesza (czesc parts/path.py). Trasa (wezly XZ) wiedzie od ladowego
# konca pomostu na plazy zatoczki (os x=0, z~-24) tarasami w gore do rejonu
# latarni na plateau (os 0, 0). Assembler dopasowuje wysokosc kazdego
# wierzcholka wstegi do terenu (min odleglosc od najblizszego wierzcholka
# terenu), wiec sciezka pokonuje tarasy przylegajac do zbocza. Grupa path.
PATH_ROUTE = [
    (0.0, -22.0),    # rejon pomostu (ladowy koniec na plazy, z~-24)
    (1.0, -15.0),    # wyjscie z zatoczki na taras dolny
    (1.5, -8.0),     # taras srodkowy
    (0.5, -2.0),
    (0.0, 0.0),      # rejon latarni (plateau, os 0, 0)
]

# Mur oporowy i schody (czesc parts/wall.py). Tarasy wyspy opadaja od plateau
# latarni (r=0) ku linii brzegowej; kamienne mury podtrzymuja krawedz tarasu
# miedzy pierscieniem domow (r=0.52) a tarasem dolnym (r=0.65), a schody lacza
# te poziomy. Segmenty stoja w lukach miedzy domami (phi domow: 20/59/98/137/
# 176/215), kazdy obrocony stycznie do krawedzi (phi+90) i posadowiony na
# terenie jak pozostale czesci. Grupy wall_1, wall_2 (mur) oraz stair_1 (bieg).
_WALL_R = 0.585
WALLS = [
    {"phi": 78.0, "params": {"length": 9.0, "height": 1.6, "thickness": 0.6, "seed": 71}},
    {"phi": 157.0, "params": {"length": 8.0, "height": 1.8, "thickness": 0.6, "seed": 72}},
]
STAIRS = [
    {"phi": 117.0, "params": {"n_steps": 8, "step_rise": 0.22, "step_run": 0.4,
                              "step_width": 1.8, "seed": 73}},
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


def _rotate_y(groups, deg):
    """Obraca wszystkie wierzcholki grup o kat deg (stopnie) wokol osi Y."""
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    for g in groups:
        g["vertices"] = [(x * ca + z * sa, y, -x * sa + z * ca)
                         for (x, y, z) in g["vertices"]]
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

    # --- teren: wyspa (terrain v3), baza do posadowienia reszty ---
    terrain = _load_part("terrain").build()
    _namespace_materials(terrain, "terrain")
    terrain[0]["name"] = "terrain"
    tverts = [v for g in terrain for v in g["vertices"]]
    scene.extend(terrain)

    # --- woda: tafla na y=0, rozciagnieta poza krawedz ladu (otacza wyspe) ---
    water = _load_part("water").build(size=100.0, cells=20)
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

    # --- domy: scalone w pojedyncze grupy house_<k>_<archetyp>, posadowione na
    # terenie. Nazwa niesie archetyp (timber/stone/two_story) wg parts/house.py v3. ---
    house_mod = _load_part("house")
    for i, spec in enumerate(HOUSES, start=1):
        prefix = "house_%d_%s" % (i, spec["archetype"])
        groups = house_mod.build(**spec["params"])
        _namespace_materials(groups, prefix)
        house = _merge(groups, prefix)
        _translate([house], spec["x"], 0.0, spec["z"])
        cx, cz = _centroid_xz(house)
        ty = _nearest_terrain_y(tverts, cx, cz)
        _translate([house], 0.0, ty, 0.0)
        scene.append(house)

    # --- pomost: z plazy zatoczki (-Z) POZA obrys wyspy w otwarte morze ---
    # Teren (terrain v3) to wyspa; zatoczka z plaza otwiera sie ku -Z, a plaza
    # przy osi x=0 siega do z~-28 (r=0.95). Pomost (lokalne z=0..length=14, os
    # x=0) przesuwamy o -38, by jego ladowy koniec (z=14 -> scena z=-24) lezal
    # na plazy (<= 2 m od lądu), a morski koniec (z=0 -> scena z=-38) siegal
    # otwartej wody poza obrysem wyspy (>= 8 m od najblizszego wierzcholka
    # terenu o y > 0.05). Asercje check_scene v2: styk z plaza ORAZ zasieg w morze.
    pier = _load_part("pier").build()
    _namespace_materials(pier, "pier")
    _translate(pier, 0.0, 0.0, -38.0)
    for g in pier:
        g["name"] = "pier_" + g["name"]
    scene.extend(pier)

    # --- lodki: scalone w pojedyncze grupy boat_i, ploa na tafli (bez prze-
    # suniecia w Y — kadlub ma juz kil pod y=0 i burty nad woda). ---
    boat_mod = _load_part("boat")
    for i, spec in enumerate(BOATS, start=1):
        prefix = "boat_%d" % i
        groups = boat_mod.build(**spec["params"])
        _namespace_materials(groups, prefix)
        boat = _merge(groups, prefix)
        _translate([boat], spec["x"], 0.0, spec["z"])
        scene.append(boat)

    # --- sosny: scalone w pojedyncze grupy tree_i, posadzone na terenie
    # (jak domy: min-Y == wysokosc najblizszego wierzcholka terenu). ---
    tree_mod = _load_part("tree")
    for i, spec in enumerate(TREES, start=1):
        prefix = "tree_%d" % i
        groups = tree_mod.build(**spec["params"])
        _namespace_materials(groups, prefix)
        tree = _merge(groups, prefix)
        _translate([tree], spec["x"], 0.0, spec["z"])
        cx, cz = _centroid_xz(tree)
        ty = _nearest_terrain_y(tverts, cx, cz)
        _translate([tree], 0.0, ty, 0.0)
        scene.append(tree)

    # --- glazy: scalone w pojedyncze grupy rock_i, posadowione na terenie
    # (jak drzewa: min-Y == wysokosc najblizszego wierzcholka terenu) wzdluz
    # linii brzegowej i na klifie. ---
    rock_mod = _load_part("rocks")
    for i, spec in enumerate(ROCKS, start=1):
        prefix = "rock_%d" % i
        groups = rock_mod.build(**spec["params"])
        _namespace_materials(groups, prefix)
        rock = _merge(groups, prefix)
        _translate([rock], spec["x"], 0.0, spec["z"])
        cx, cz = _centroid_xz(rock)
        ty = _nearest_terrain_y(tverts, cx, cz)
        _translate([rock], 0.0, ty, 0.0)
        scene.append(rock)

    # --- sciezka: wstega od rejonu pomostu przez miasteczko do latarni.
    # Wysokosc kazdego wierzcholka dopasowana do terenu (Y = wysokosc
    # najblizszego wierzcholka terenu + drobny luz), wiec sciezka przylega do
    # zbocza i plazy zamiast lewitowac (sekcja sciezki w check_scene v2). ---
    path = _load_part("path").build(waypoints=PATH_ROUTE, width=1.8, seed=61)
    _namespace_materials(path, "path")
    for g in path:
        g["name"] = "path"
        g["vertices"] = [(x, _nearest_terrain_y(tverts, x, z) + 0.05, z)
                         for (x, y, z) in g["vertices"]]
    scene.extend(path)

    # --- mury oporowe: segmenty wzdluz krawedzi tarasu, posadowione na terenie.
    # Czesc wall.py zwraca mur i schody; tu bierzemy sam mur (include_stairs=
    # False), obracamy stycznie do krawedzi (phi+90) i osadzamy podstawe (y=0)
    # na wysokosci najblizszego wierzcholka terenu. Grupy wall_1, wall_2. ---
    wall_mod = _load_part("wall")
    for i, spec in enumerate(WALLS, start=1):
        prefix = "wall_%d" % i
        groups = wall_mod.build(include_stairs=False, **spec["params"])
        _namespace_materials(groups, prefix)
        seg = _merge(groups, prefix)
        x, z = _ell(_WALL_R, spec["phi"])
        _rotate_y([seg], spec["phi"] + 90.0)
        _translate([seg], x, 0.0, z)
        cx, cz = _centroid_xz(seg)
        _translate([seg], 0.0, _nearest_terrain_y(tverts, cx, cz), 0.0)
        scene.append(seg)

    # --- schody: bieg laczacy poziomy tarasow (include_wall=False), obrocony
    # stycznie i posadowiony na terenie jak mury. Grupa stair_1. ---
    for i, spec in enumerate(STAIRS, start=1):
        prefix = "stair_%d" % i
        groups = wall_mod.build(include_wall=False, **spec["params"])
        _namespace_materials(groups, prefix)
        seg = _merge(groups, prefix)
        x, z = _ell(_WALL_R, spec["phi"])
        _rotate_y([seg], spec["phi"] + 90.0)
        _translate([seg], x, 0.0, z)
        cx, cz = _centroid_xz(seg)
        _translate([seg], 0.0, _nearest_terrain_y(tverts, cx, cz), 0.0)
        scene.append(seg)

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

SCENE_VERSION = 2
