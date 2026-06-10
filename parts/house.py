# -*- coding: utf-8 -*-
"""Czesc: parametryczny dom mieszkalny jako zestaw nazwanych grup (kontrakt v2).

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, os bryly w (x=0, z=0).
Cokol/fundament siega podstawy domu (najnizszy element); sciany staja na nim.

Parametry (wszystkie opcjonalne, maja sensowne domysly):
  width       - szerokosc scian wzdluz X (domyslnie 6.0),
  depth       - glebokosc scian wzdluz Z (domyslnie 5.0),
  height      - wysokosc scian (domyslnie 3.0); calkowita wysokosc = height +
                wzniesienie dachu i miesci sie w [2, 15],
  wall_color  - kolor scian (r, g, b) w [0, 1] (domyslnie piaskowy),
  roof_color  - kolor dachu (r, g, b) w [0, 1] (domyslnie ceglasty),
  window_color- kolor szyb (r, g, b) w [0, 1] (domyslnie szklisty blekit),
  seed        - ziarno losowosci (jitter odcienia scian + przesuniecie drzwi).

Grupy (kazda z wlasnymi, LOKALNYMI wierzcholkami 0-based):
  foundation - cokol/fundament siegajacy podstawy (material 'foundation'),
  walls      - prostopadloscienne sciany z jitterem odcienia (material 'wall_i'),
  roof       - dwuspadowy dach (material 'roof', centroid powyzej scian),
  chimney    - komin wystajacy ponad kalenice (material 'chimney'),
  windows    - okna: ramy (material 'frame') + szyby (material 'glass'),
  door       - drzwi siegajace podloza domu (material 'door').

Weryfikator check_parts.check_house (v1): wysokosc w [2, 15]; scianki dachu
('roof') z centroidem powyzej scian; drzwi ('door') siegajace podloza.
check_house_v2 (CONTRACT_VERSION >= 2): >= 2 szyby 'glass*'/'window*';
>= 4 scianki ram 'frame*'; komin 'chimney*' >= 0.2 m ponad kalenica;
fundament 'foundation*'/'plinth*' siegajacy podstawy. Losowosc tylko przez `seed`.
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


def _box_shaded(g, base_name, base_color, rng, x0, x1, y0, y1, z0, z1):
    """Box z deterministycznym jitterem odcienia per scianka (realizm wg
    parts/README.md): kazda z 6 plaszczyzn dostaje wlasny material 'base_k'."""
    for k, f in enumerate(_box(g, x0, x1, y0, y1, z0, z1)):
        mat = "%s_%d" % (base_name, k)
        if mat not in g["colors"]:
            shade = 0.9 + 0.1 * rng.random()
            g["colors"][mat] = tuple(_clamp01(c * shade) for c in base_color)
        g["faces"].append((mat, f))


def build(**params):
    width = float(params.get("width", 6.0))
    depth = float(params.get("depth", 5.0))
    wall_h = float(params.get("height", 3.0))
    wall_color = tuple(_clamp01(c) for c in params.get("wall_color", (0.82, 0.78, 0.70)))
    roof_color = tuple(_clamp01(c) for c in params.get("roof_color", (0.52, 0.18, 0.14)))
    window_color = tuple(_clamp01(c) for c in params.get("window_color", (0.55, 0.70, 0.80)))
    rng = random.Random(params.get("seed", 20240611))

    hx, hz = width / 2.0, depth / 2.0
    overhang = 0.3
    roof_rise = 2.0          # wzniesienie kalenicy ponad sciany
    ridge_y = wall_h + roof_rise
    plinth_bottom = -0.3     # cokol siega ponizej podstawy scian (y=0)

    groups = []

    # --- foundation: cokol siegajacy podstawy domu (najnizszy element) ---
    foundation = _new_group("foundation", {"foundation": (0.45, 0.45, 0.47)})
    foundation["faces"] = [("foundation", f) for f in _box(
        foundation, -hx - 0.08, hx + 0.08, plinth_bottom, 0.2, -hz - 0.08, hz + 0.08)]
    groups.append(foundation)

    # --- walls: prostopadloscienne sciany (y 0..wall_h), jitter odcienia ---
    walls = _new_group("walls", {})
    _box_shaded(walls, "wall", wall_color, rng, -hx, hx, 0.0, wall_h, -hz, hz)
    groups.append(walls)

    # --- roof: dwuspadowy dach z kalenica wzdluz osi X ---
    roof = _new_group("roof", {"roof": roof_color})
    xe, ze = hx + overhang, hz + overhang
    ye, ry = wall_h, ridge_y
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

    # --- chimney: komin wystajacy ponad kalenice (>= 0.2 m) ---
    chimney = _new_group("chimney", {"chimney": (0.45, 0.22, 0.18)})
    cxh = hx * 0.4
    chimney["faces"] = [("chimney", f) for f in _box(
        chimney, cxh - 0.22, cxh + 0.22, wall_h, ridge_y + 0.4, -0.22, 0.22)]
    groups.append(chimney)

    # --- windows: okna na scianie tylnej (+z) — ramy 'frame' + szyby 'glass' ---
    windows = _new_group("windows", {"frame": (0.92, 0.92, 0.90), "glass": window_color})
    win_w = min(0.9, width * 0.18)
    win_h = 0.8
    cy = wall_h * 0.5
    for sx in (-width * 0.25, width * 0.25):
        # rama (framuga) — nieco wieksza, lekko wystaje na zewnatrz (+z)
        windows["faces"].extend(("frame", f) for f in _box(
            windows, sx - (win_w + 0.14) / 2.0, sx + (win_w + 0.14) / 2.0,
            cy - (win_h + 0.14) / 2.0, cy + (win_h + 0.14) / 2.0,
            hz - 0.02, hz + 0.05))
        # szyba — w obrysie ramy, lekko z przodu, by byla widoczna
        windows["faces"].extend(("glass", f) for f in _box(
            windows, sx - win_w / 2.0, sx + win_w / 2.0,
            cy - win_h / 2.0, cy + win_h / 2.0, hz + 0.02, hz + 0.07))
    groups.append(windows)

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

CONTRACT_VERSION = 2
