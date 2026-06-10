# -*- coding: utf-8 -*-
"""Czesc: parametryczny dom mieszkalny jako zestaw nazwanych grup.

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, dom stoi na y=0,
os bryly w (x=0, z=0).

Parametry (wszystkie opcjonalne, maja sensowne domysly):
  width      - szerokosc scian wzdluz X (domyslnie 6.0),
  depth      - glebokosc scian wzdluz Z (domyslnie 5.0),
  height     - wysokosc scian (domyslnie 3.0); calkowita wysokosc = height +
               wzniesienie dachu i miesci sie w [2, 15],
  wall_color - kolor scian (r, g, b) w [0, 1] (domyslnie piaskowy),
  seed       - ziarno losowosci (delikatne przesuniecie drzwi w osi X).

Grupy (kazda z wlasnymi, LOKALNYMI wierzcholkami 0-based):
  walls - prostopadloscienne sciany (material bez "roof"/"door"),
  roof  - dwuspadowy dach (material zawiera "roof", centroid powyzej scian),
  door  - drzwi siegajace podloza domu (material zawiera "door").

Weryfikator check_parts.check_house wymaga: wysokosc w [2, 15]; scianki dachu
(material z "roof") z centroidem powyzej scian; scianki drzwi (material z
"door") siegajace podloza (luka <= 0.5 m). Losowosc wylacznie przez `seed`.
"""

import random


def _new_group(name, colors):
    return {"name": name, "vertices": [], "faces": [], "colors": dict(colors)}


def _add(g, x, y, z):
    g["vertices"].append((float(x), float(y), float(z)))
    return len(g["vertices"]) - 1  # indeks 0-based, lokalny dla grupy


def _box(g, x0, x1, y0, y1, z0, z1):
    v = [
        _add(g, x0, y0, z0), _add(g, x1, y0, z0),
        _add(g, x1, y0, z1), _add(g, x0, y0, z1),
        _add(g, x0, y1, z0), _add(g, x1, y1, z0),
        _add(g, x1, y1, z1), _add(g, x0, y1, z1),
    ]
    return [
        (v[0], v[1], v[2], v[3]),  # dol
        (v[4], v[7], v[6], v[5]),  # gora
        (v[0], v[4], v[5], v[1]),  # przod -z
        (v[1], v[5], v[6], v[2]),  # bok +x
        (v[2], v[6], v[7], v[3]),  # tyl +z
        (v[3], v[7], v[4], v[0]),  # bok -x
    ]


def _clamp01(c):
    return max(0.0, min(1.0, float(c)))


def build(**params):
    width = float(params.get("width", 6.0))
    depth = float(params.get("depth", 5.0))
    wall_h = float(params.get("height", 3.0))
    wall_color = tuple(_clamp01(c) for c in params.get("wall_color", (0.82, 0.78, 0.70)))
    rng = random.Random(params.get("seed", 20240611))

    hx, hz = width / 2.0, depth / 2.0
    overhang = 0.3
    roof_rise = 2.0  # wzniesienie kalenicy ponad sciany

    groups = []

    # --- walls: prostopadloscienne sciany (y 0..wall_h) ---
    walls = _new_group("walls", {"wall": wall_color})
    walls["faces"] = [("wall", f) for f in _box(walls, -hx, hx, 0.0, wall_h, -hz, hz)]
    groups.append(walls)

    # --- roof: dwuspadowy dach z kalenica wzdluz osi X ---
    roof = _new_group("roof", {"roof": (0.52, 0.18, 0.14)})
    xe, ze = hx + overhang, hz + overhang
    ye, ry = wall_h, wall_h + roof_rise
    e0 = _add(roof, -xe, ye, -ze)  # okap przod, lewy
    e1 = _add(roof, xe, ye, -ze)   # okap przod, prawy
    e2 = _add(roof, -xe, ye, ze)   # okap tyl, lewy
    e3 = _add(roof, xe, ye, ze)    # okap tyl, prawy
    r0 = _add(roof, -xe, ry, 0.0)  # kalenica, lewa
    r1 = _add(roof, xe, ry, 0.0)   # kalenica, prawa
    roof["faces"] = [
        ("roof", (e0, e1, r1, r0)),  # polac przednia (-z)
        ("roof", (e3, e2, r0, r1)),  # polac tylna (+z)
        ("roof", (e0, r0, e2)),      # szczyt lewy (-x)
        ("roof", (e1, e3, r1)),      # szczyt prawy (+x)
    ]
    groups.append(roof)

    # --- door: drzwi przy scianie przedniej (-z), siegajace podloza ---
    door = _new_group("door", {"door": (0.30, 0.18, 0.09)})
    door_w = min(1.0, width * 0.3)
    door_h = min(2.1, wall_h * 0.85)
    span = max(0.0, hx - door_w / 2.0 - 0.3)
    cx = rng.uniform(-span, span)  # determinizm: ten sam seed -> ta sama pozycja
    door["faces"] = [("door", f) for f in _box(
        door, cx - door_w / 2.0, cx + door_w / 2.0,
        0.0, door_h, -hz - 0.06, -hz + 0.02)]
    groups.append(door)

    return groups
