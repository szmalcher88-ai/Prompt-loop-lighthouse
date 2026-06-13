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

# Domy (>= 9) rozstawione w GRONACH (nie pierscieniem) na tarasach wyspy wokol
# latarni — layout wg sekcji v4(a) check_scene i wzorca scripts/fixtures/
# gen_scene_v4.py. Trzy grona o roznej licznosci (4 / 3 / 2 = 9 domow): grono A
# (NW, taras srodkowy), B (E przy mostku/turni), C (N przy brzegu, dolny taras).
# W gronie domy stoja ciasno (pitch 6.5 m -> kazdy ma sasiada <= 7.5 m, brak
# singletonow), a grona sa od siebie oddalone, wiec ich centroidy daja duzy
# rozrzut promienia domow od wspolnego centroidu (CoV ~0.28 >= 0.15 — anty-
# pierscien). Pitch 6.5 m przy footprintach <= 5.6 m trzyma AABB w XZ rozlaczne
# (miedzy soba i z latarnia). Trzy archetypy (parts/house.py v3): timber / stone
# / two_story uzyte po 3 razy, w grupach house_<k>_<archetyp>. Kazda instancja
# rozni sie archetypem albo wymiarami i kolorami (sciany + dach + szyby) —
# asercja v2 "domy parami rozne" (check_scene); w obrebie archetypu wymiary
# (width, depth) sa parami rozne.
_HOUSE_PITCH = 6.5
# Grono = (kotwica, [offsety lokalne]); offsety w siatce o kroku _HOUSE_PITCH.
_HOUSE_CLUSTERS = [
    ((-19.0, 5.0), [(0.0, 0.0), (_HOUSE_PITCH, 0.0),
                    (0.0, _HOUSE_PITCH), (_HOUSE_PITCH, _HOUSE_PITCH)]),   # A: 4
    ((14.0, -3.0), [(0.0, 0.0), (_HOUSE_PITCH, 0.0), (0.0, _HOUSE_PITCH)]),  # B: 3
    ((-3.0, 18.0), [(0.0, 0.0), (_HOUSE_PITCH, 0.0)]),                       # C: 2
]
_HOUSE_LAYOUT = [(ax + ox, az + oz) for (ax, az), offs in _HOUSE_CLUSTERS
                 for (ox, oz) in offs]
_HOUSE_SPECS = [
    {"archetype": "timber", "width": 5.6, "depth": 4.8,
     "wall_color": (0.85, 0.80, 0.70), "roof_color": (0.55, 0.20, 0.15),
     "window_color": (0.52, 0.68, 0.80), "seed": 11},
    {"archetype": "stone", "width": 5.4, "depth": 4.8,
     "wall_color": (0.60, 0.58, 0.54), "roof_color": (0.40, 0.28, 0.22),
     "window_color": (0.58, 0.72, 0.82), "seed": 12},
    {"archetype": "two_story", "width": 5.2, "depth": 4.2,
     "wall_color": (0.78, 0.74, 0.66), "roof_color": (0.30, 0.36, 0.40),
     "window_color": (0.50, 0.66, 0.78), "seed": 13},
    {"archetype": "timber", "width": 5.2, "depth": 4.6,
     "wall_color": (0.82, 0.56, 0.46), "roof_color": (0.48, 0.16, 0.12),
     "window_color": (0.60, 0.74, 0.84), "seed": 14},
    {"archetype": "stone", "width": 5.6, "depth": 4.4,
     "wall_color": (0.56, 0.55, 0.52), "roof_color": (0.34, 0.30, 0.20),
     "window_color": (0.54, 0.70, 0.80), "seed": 15},
    {"archetype": "two_story", "width": 5.6, "depth": 4.6,
     "wall_color": (0.88, 0.84, 0.62), "roof_color": (0.58, 0.24, 0.18),
     "window_color": (0.56, 0.71, 0.83), "seed": 16},
    {"archetype": "timber", "width": 5.4, "depth": 5.0,
     "wall_color": (0.80, 0.72, 0.60), "roof_color": (0.50, 0.22, 0.16),
     "window_color": (0.53, 0.69, 0.81), "seed": 17},
    {"archetype": "stone", "width": 5.0, "depth": 4.6,
     "wall_color": (0.62, 0.60, 0.56), "roof_color": (0.38, 0.30, 0.24),
     "window_color": (0.55, 0.71, 0.79), "seed": 18},
    {"archetype": "two_story", "width": 4.8, "depth": 4.0,
     "wall_color": (0.74, 0.78, 0.72), "roof_color": (0.32, 0.34, 0.28),
     "window_color": (0.51, 0.67, 0.80), "seed": 19},
]
HOUSES = []
for _k, (_spec, (_x, _z)) in enumerate(zip(_HOUSE_SPECS, _HOUSE_LAYOUT)):
    HOUSES.append({"x": _x, "z": _z, "archetype": _spec["archetype"], "params": _spec})

# Lodki (czesc parts/boat.py). Trzy role pod uklad wyspy (zatoczka od -Z, pomost
# w osi x=0 o srodku XZ ~ (0, -31)):
#   boat_1 — wyciagnieta na PIASEK plazy zatoczki: centroid nad ladem (teren
#            > 0.05), assembler sadzi ja na terenie (flaga "beach") jak inne
#            czesci ladowe -> sekcja zatoczki check_scene v3,
#   boat_2 — cumuje tuz przy pomoscie (< 6 m od jego srodka),
#   boat_3 — dryfuje na otwartej wodzie po stronie -Z (> 10 m od pomostu).
# boat_2/boat_3 pokrywaja asercje v2 (styk z pomostem + otwarta woda). Kazda
# instancja rozni sie wymiarami, kolorem i seedem (zakaz idealnych kopii).
BOATS = [
    {"x": -3.0, "z": -19.0, "beach": True,
     "params": {"length": 3.0, "beam": 1.2, "depth": 0.24, "gunwale_y": 0.40,
                "hull_color": (0.70, 0.46, 0.24), "seat_color": (0.74, 0.62, 0.42),
                "seats": 2, "seed": 23}},
    {"x": 3.5, "z": -33.0,
     "params": {"length": 3.6, "beam": 1.35, "depth": 0.26, "gunwale_y": 0.42,
                "hull_color": (0.60, 0.28, 0.18), "seat_color": (0.72, 0.60, 0.40),
                "seats": 2, "seed": 21}},
    {"x": 22.0, "z": -34.0,
     "params": {"length": 4.4, "beam": 1.7, "depth": 0.34, "gunwale_y": 0.50,
                "hull_color": (0.30, 0.40, 0.52), "seat_color": (0.66, 0.56, 0.42),
                "seats": 3, "seed": 22}},
]

# Pomost zatoczki (parts/pier.py v3) jako dwa wspolliniowe przesla wzdluz osi
# x=0. Czesc buduje przeslo lokalne z=0 (morski koniec, polery) .. z=length
# (ladowy koniec); dz przesuwa je w scene. pier_1 to segment ladowy (dz=-31 ->
# z -31..-24), pier_2 morski (dz=-38 -> z -38..-31); razem ciagly poklad
# z -38..-24, identyczny zasieg jak pojedynczy pomost (boaty cumuja wzgledem
# srodka ~ (0, -31)).
PIERS = [
    {"dz": -31.0, "params": {"length": 7.0, "bays": 4, "seed": 51}},
    {"dz": -38.0, "params": {"length": 7.0, "bays": 4, "seed": 52}},
]

# Gorna powierzchnia pokladu pomostu nad tafla (deck_y=0.4 w parts/pier.py);
# rekwizyty stawiamy podstawa na tej wysokosci.
DECK_TOP = 0.4

# Beczki (parts/prop_barrel.py) i skrzynie (parts/prop_crate.py) rozstawione na
# pokladzie obu przesel (x w obrysie +-1.2, z wzdluz pomostu). Kazda instancja
# ma inny seed i wymiary (zakaz idealnych kopii); leza w obrysie pomostu, wiec
# <= 5 m od niego (check_scene v3: pomost albo nabrzeze).
BARRELS = [
    {"x": -0.9, "z": -25.5, "params": {"seed": 201, "height": 0.9, "radius": 0.32}},
    {"x": 0.9, "z": -26.5, "params": {"seed": 202, "height": 1.0, "radius": 0.30}},
    {"x": -0.8, "z": -36.0, "params": {"seed": 203, "height": 0.85, "radius": 0.33}},
    {"x": 0.85, "z": -34.5, "params": {"seed": 204, "height": 0.95, "radius": 0.34}},
]
CRATES = [
    {"x": 0.75, "z": -24.5, "params": {"seed": 211, "width": 0.7, "depth": 0.7, "height": 0.7}},
    {"x": -0.75, "z": -30.5, "params": {"seed": 212, "width": 0.6, "depth": 0.8, "height": 0.6}},
    {"x": 0.6, "z": -37.0, "params": {"seed": 213, "width": 0.8, "depth": 0.6, "height": 0.75}},
]

# Zagajnik sosen na tarasie dolnym wyspy (czesc parts/tree.py). Domy stoja na
# tarasie srodkowym (r=0.45 -> teren y=5.5); sosny sadzimy o jeden taras nizej,
# na pierscieniu y=2.5 wyspy (r=0.6..0.75). Po przejsciu terenu na wyspe (v3)
# zagajnik dosuwamy do r=0.70 i ustawiamy na luku od strony lądu (z > 0), z dala
# od zatoczki (-Z) oraz od krzewow przydomowych w pierscieniu zabudowy. Kazda
# sosna ma inna wysokosc, promien korony i seed (zakaz idealnych kopii);
# assembler sadzi ja na terenie (min-Y == wysokosc najblizszego wierzcholka
# terenu). Grupy tree_i.
_TREE_SPOTS = [
    (0.70, 25.0), (0.70, 52.0), (0.70, 79.0), (0.70, 106.0),
    (0.70, 133.0), (0.70, 160.0), (0.70, 175.0),
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


# Krzewy przydomowe (czesc parts/bush.py). Po przejsciu zabudowy na grona
# sadzimy krzewy przy domach: krzew k tuz obok domu _HOUSE_LAYOUT[k] (offset
# (2.2, 1.0) m), wiec lezy ~2.4 m od domu (<= 10 m od najblizszego — check_scene
# v3), wsrod zabudowy grona. Kazda instancja rozni sie wysokoscia, szerokoscia,
# kolorem i seedem (zakaz idealnych kopii); assembler sadzi ja na terenie (min-Y
# == wysokosc najblizszego wierzcholka terenu) jak domy/sosny. Grupy bush_1..bush_N.
_BUSH_PARAMS = [
    {"height": 1.1, "width": 0.9, "leaf_color": (0.24, 0.42, 0.20), "seed": 301},
    {"height": 0.8, "width": 1.0, "leaf_color": (0.28, 0.46, 0.22), "seed": 302},
    {"height": 1.3, "width": 0.85, "leaf_color": (0.20, 0.38, 0.18), "seed": 303},
    {"height": 0.95, "width": 1.1, "leaf_color": (0.26, 0.44, 0.24), "seed": 304},
    {"height": 1.15, "width": 0.95, "leaf_color": (0.22, 0.40, 0.19), "seed": 305},
    {"height": 0.7, "width": 0.8, "leaf_color": (0.30, 0.48, 0.26), "seed": 306},
    {"height": 1.25, "width": 1.05, "leaf_color": (0.21, 0.39, 0.21), "seed": 307},
    {"height": 0.9, "width": 0.9, "leaf_color": (0.27, 0.45, 0.23), "seed": 308},
]
BUSHES = [{"x": _HOUSE_LAYOUT[_k][0] + 2.2, "z": _HOUSE_LAYOUT[_k][1] + 1.0,
           "params": _p}
          for _k, _p in enumerate(_BUSH_PARAMS)]


# Glazy wokol wyspy (czesc parts/rocks.py). Otaczaja wyspe rafowym pierscieniem
# W WODZIE POZA OBRYSEM wyspy (r=1.05 -> otwarte morze y=-1.8, teren < -0.2 pod
# kazdym centroidem), wieksze breaching wystaja ponad tafle, mniejsze tworza
# podwodna rafe. Pierscien (>= 8 glazow w wodzie, lacznie >= 10) pokrywa sekcje
# pierscienia skal check_scene v3. Kazdy glaz rozni sie promieniem, splaszcze-
# niem, kolorem i seedem (zakaz idealnych kopii); assembler sadzi go na terenie
# (min-Y == wysokosc najblizszego wierzcholka terenu) jak drzewa/domy. Grupy
# rock_1..rock_N.
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
ROCKS = [{"x": _ell(1.05, 30.0 * k)[0], "z": _ell(1.05, 30.0 * k)[1], "params": p}
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

# Mur oporowy i schody (czesc parts/wall.py). Teren wyspy to tarasy (plateau
# latarni y=9, pierscien zabudowy y=5.5, taras dolny y=2.5, ...). Kamienne mury
# i schody stoja w LUKACH MIEDZY GRONAMI domow — tak, by ZADNA bryla stair*/
# wall* nie przenikala AABB domu (sekcja v5(a) check_scene: przenikanie na 3
# osiach > 0.3 m to kolizja dom-infrastruktura). Pozycje sa jawne (x, z) zamiast
# po elipsie, bo grona zabudowy nie leza juz na regularnym pierscieniu.
#
# Mury (wall_1, wall_2) biegna stycznie do krawedzi tarasu (rot wokol Y),
# posadowione podstawa na terenie. Schody (stair_1) lacza DWA tarasy: bieg
# przecina krawedz tarasu (5.5 -> 2.5) przy x=9, z~18.5; jego wysokosc rowna
# przyrostowi terenu miedzy koncami footprintu, dno spoczywa na dolnym tarasie,
# a szczyt siega gornego (sekcja v5(a): styk z dwoma poziomami, tol 0.7 m).
WALLS = [
    {"x": 15.0, "z": 18.5, "rot": 0.0,
     "params": {"length": 8.0, "height": 1.6, "thickness": 0.6, "seed": 71}},
    {"x": 8.0, "z": 7.0, "rot": 0.0,
     "params": {"length": 6.0, "height": 1.8, "thickness": 0.6, "seed": 72}},
]
# edge_z: wspolrzedna Z krawedzi tarasu, ktora bieg ma przeciac (footprint
# rozciaga sie symetrycznie po obu jej stronach, na dwa rozne poziomy terenu).
STAIRS = [
    {"x": 9.0, "edge_z": 18.5,
     "params": {"n_steps": 8, "step_run": 0.42, "step_width": 1.8, "seed": 73}},
]

# Kapliczka i mostek (czesci parts/chapel.py, parts/bridge.py). Kapliczka stoi na
# osobnej TURNI, ktora terrain.py v3 wyrasta przy (30, -6) — lokalne wzniesienie
# y~7 m (>= 3 m pod kapliczka), rozlaczne z masywem zabudowy przez przelecz
# (siodlo terenu ~2.5 m, >= 1.5 m nizej niz konce) i odlegle >= 6 m od
# najblizszego domu z pierscienia (house_1 przy phi=0, x~18). Mostek linowy
# biegnie wzdluz +X (srodek w x=22): jego turniowy koniec (x~25) jest <= 5 m od
# kapliczki (obrys turni od x~28.5), a wioskowy koniec (x~19) <= 6 m od house_1.
# Mostek unosimy o lift ponad teren, by zwisajace liny nie zapadaly sie w grunt.
CHAPEL = {
    "x": 30.0, "z": -6.0,
    "params": {"seed": 81, "wall_color": (0.88, 0.85, 0.78),
               "roof_color": (0.42, 0.20, 0.15), "cross_color": (0.28, 0.24, 0.20)},
}
BRIDGE = {
    "x": 22.0, "z": -5.0, "rot": 0.0, "lift": 0.7,
    "params": {"span": 6.0, "half_spread": 0.6, "sag": 0.6, "seed": 91},
}


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

    # --- pomosty: dwa wspolliniowe segmenty (pier_1, pier_2) z plazy zatoczki
    # (-Z) POZA obrys wyspy w otwarte morze ---
    # Teren (terrain v3) to wyspa; zatoczka z plaza otwiera sie ku -Z, a plaza
    # przy osi x=0 siega do z~-28 (r=0.95). Pomost dzielimy na dwa wspolliniowe
    # przesla (os x=0, lokalne z=0..7 kazde): segment ladowy pier_1 (z -31..-24)
    # styka sie z plaza (ladowy koniec z=-24, <= 2 m od lądu), a segment morski
    # pier_2 (z -38..-31) siega otwartej wody poza obrysem wyspy (morski koniec
    # z=-38, >= 8 m od najblizszego wierzcholka terenu o y > 0.05). Razem >= 2
    # grupy pier* (check_scene v3) i niezmienione asercje v2 (styk + zasieg).
    pier_mod = _load_part("pier")
    for i, spec in enumerate(PIERS, start=1):
        prefix = "pier_%d" % i
        groups = pier_mod.build(**spec["params"])
        _namespace_materials(groups, prefix)
        seg = _merge(groups, prefix)
        _translate([seg], 0.0, 0.0, spec["dz"])
        scene.append(seg)

    # --- rekwizyty portowe: beczki (barrel_i) i skrzynie (crate_i) stoja na
    # pokladzie pomostu (DECK_TOP nad tafla), w obrebie obrysu przesel, wiec
    # kazdy jest <= 5 m od pomostu (check_scene v3). Kazda instancja rozni sie
    # wymiarami i seedem (zakaz idealnych kopii). ---
    barrel_mod = _load_part("prop_barrel")
    for i, spec in enumerate(BARRELS, start=1):
        prefix = "barrel_%d" % i
        groups = barrel_mod.build(**spec["params"])
        _namespace_materials(groups, prefix)
        prop = _merge(groups, prefix)
        _translate([prop], spec["x"], DECK_TOP, spec["z"])
        scene.append(prop)
    crate_mod = _load_part("prop_crate")
    for i, spec in enumerate(CRATES, start=1):
        prefix = "crate_%d" % i
        groups = crate_mod.build(**spec["params"])
        _namespace_materials(groups, prefix)
        prop = _merge(groups, prefix)
        _translate([prop], spec["x"], DECK_TOP, spec["z"])
        scene.append(prop)

    # --- lodki: scalone w pojedyncze grupy boat_i. Lodki na wodzie ploa na
    # tafli (bez przesuniecia w Y — kadlub ma juz kil pod y=0 i burty nad woda);
    # lodka z flaga "beach" jest wyciagnieta na piasek, wiec assembler sadzi ja
    # na terenie (przesuwa w Y do wysokosci najblizszego wierzcholka terenu). ---
    boat_mod = _load_part("boat")
    for i, spec in enumerate(BOATS, start=1):
        prefix = "boat_%d" % i
        groups = boat_mod.build(**spec["params"])
        _namespace_materials(groups, prefix)
        boat = _merge(groups, prefix)
        _translate([boat], spec["x"], 0.0, spec["z"])
        if spec.get("beach"):
            cx, cz = _centroid_xz(boat)
            _translate([boat], 0.0, _nearest_terrain_y(tverts, cx, cz), 0.0)
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

    # --- krzewy: scalone w pojedyncze grupy bush_i, posadzone na terenie
    # (jak sosny) w przerwach pierscienia zabudowy. ---
    bush_mod = _load_part("bush")
    for i, spec in enumerate(BUSHES, start=1):
        prefix = "bush_%d" % i
        groups = bush_mod.build(**spec["params"])
        _namespace_materials(groups, prefix)
        bush = _merge(groups, prefix)
        _translate([bush], spec["x"], 0.0, spec["z"])
        cx, cz = _centroid_xz(bush)
        ty = _nearest_terrain_y(tverts, cx, cz)
        _translate([bush], 0.0, ty, 0.0)
        scene.append(bush)

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

    # --- mury oporowe: segmenty wzdluz krawedzi tarasu w lukach miedzy gronami
    # domow, obrocone stycznie (rot wokol Y) i osadzone podstawa (y=0) na
    # wysokosci najblizszego wierzcholka terenu. Pozycje (x, z) dobrane tak, by
    # AABB muru nie przenikalo zadnego domu (v5(a)). Grupy wall_1, wall_2. ---
    wall_mod = _load_part("wall")
    for i, spec in enumerate(WALLS, start=1):
        prefix = "wall_%d" % i
        groups = wall_mod.build(include_stairs=False, **spec["params"])
        _namespace_materials(groups, prefix)
        seg = _merge(groups, prefix)
        _rotate_y([seg], spec["rot"])
        _translate([seg], spec["x"], 0.0, spec["z"])
        cx, cz = _centroid_xz(seg)
        _translate([seg], 0.0, _nearest_terrain_y(tverts, cx, cz), 0.0)
        scene.append(seg)

    # --- schody: bieg laczacy DWA tarasy (include_wall=False). Czesc buduje
    # stopnie wzdluz +Z (szczyt przy duzym z); odbijamy je o 180 wokol Y, by
    # szczyt wypadl po stronie GORNEGO tarasu (mniejsze z), a footprint przecial
    # krawedz edge_z symetrycznie. Wysokosc biegu = przyrost terenu miedzy
    # koncami (step_rise = delta/n_steps), dno osadzone na dolnym tarasie ->
    # szczyt siega gornego (v5(a): styk z dwoma poziomami). Grupa stair_1. ---
    for i, spec in enumerate(STAIRS, start=1):
        prefix = "stair_%d" % i
        n = int(spec["params"]["n_steps"])
        run = float(spec["params"]["step_run"])
        sx, edge_z = spec["x"], spec["edge_z"]
        half = n * run / 2.0
        g_high = _nearest_terrain_y(tverts, sx, edge_z - half)  # gorny taras (male z)
        g_low = _nearest_terrain_y(tverts, sx, edge_z + half)   # dolny taras (duze z)
        rise = max(1.0, g_high - g_low)
        groups = wall_mod.build(include_wall=False, step_rise=rise / n, **spec["params"])
        _namespace_materials(groups, prefix)
        seg = _merge(groups, prefix)
        _rotate_y([seg], 180.0)                  # szczyt (lokalne +Z) -> male z
        _translate([seg], sx, g_low, edge_z + half)
        scene.append(seg)

    # --- kapliczka: na turni (wyniesione plateau) z dala od zabudowy,
    # posadowiona na terenie (podstawa y=0 == wysokosc najblizszego wierzcholka
    # terenu). Grupa chapel_1. ---
    chapel_mod = _load_part("chapel")
    groups = chapel_mod.build(**CHAPEL["params"])
    _namespace_materials(groups, "chapel_1")
    chapel = _merge(groups, "chapel_1")
    _translate([chapel], CHAPEL["x"], 0.0, CHAPEL["z"])
    cx, cz = _centroid_xz(chapel)
    _translate([chapel], 0.0, _nearest_terrain_y(tverts, cx, cz), 0.0)
    scene.append(chapel)

    # --- mostek linowy: od turni kapliczki ku zabudowie wioski, uniesiony nad
    # teren o lift, by liny ze zwisem nie zapadaly sie w grunt. Grupa bridge_1. ---
    bridge_mod = _load_part("bridge")
    groups = bridge_mod.build(**BRIDGE["params"])
    _namespace_materials(groups, "bridge_1")
    bridge = _merge(groups, "bridge_1")
    _rotate_y([bridge], BRIDGE["rot"])
    _translate([bridge], BRIDGE["x"], 0.0, BRIDGE["z"])
    cx, cz = _centroid_xz(bridge)
    _translate([bridge], 0.0, _nearest_terrain_y(tverts, cx, cz) + BRIDGE["lift"], 0.0)
    scene.append(bridge)

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

SCENE_VERSION = 4
