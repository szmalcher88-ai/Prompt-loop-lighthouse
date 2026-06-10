# -*- coding: utf-8 -*-
"""Czesc: sosna (drzewo iglaste) — pien + warstwowa, stozkowa korona.

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, podstawa pnia w y=0
(assembler sadzi drzewo na terenie przesuwajac je w XZ i w Y do wysokosci
terenu). Os drzewa w (0, 0).

Konstrukcja (CONTRACT_VERSION = 2, asercje check_parts.check_tree):
  * calkowita wysokosc w zakresie [3, 8] m (extent w osi Y),
  * pien — material 'bark*' (substring 'trunk'/'bark'),
  * korona — material 'needle*' (substring 'leaves'/'crown'/'needle')
    polozona POWYZEJ pnia (centroid korony > centroid pnia),
  * korona zweza sie ku gorze: promien w gornych 30% wysokosci korony jest
    wyraznie mniejszy niz w dolnych 30% (warstwa szczytowa konczy sie
    wierzcholkiem o promieniu ~0).
Korona to K nakladajacych sie stozkow (skirts) o malejacym promieniu bazy ku
gorze; szczyt najwyzszej warstwy siega calkowitej wysokosci drzewa. Kazda
scianka dostaje wlasny material-odcien (deterministyczny jitter barwy per
scianka — wymog realizmu parts/README.md), wiec zadne dwie sasiednie
plaszczyzny nie sa identyczne.

Parametry (wszystkie opcjonalne, maja sensowne domysly):
  height       - calkowita wysokosc drzewa (domyslnie 5.0; trzymana w [3, 8]),
  trunk_frac   - udzial pnia w wysokosci (domyslnie 0.30),
  trunk_radius - polszerokosc pnia (domyslnie 0.12),
  base_radius  - promien dolnej warstwy korony (domyslnie 0.24 * height),
  layers       - liczba warstw stozkowych korony (domyslnie 3, min 2),
  bark_color   - kolor pnia (r, g, b) w [0, 1] (domyslnie brazowa kora),
  needle_color - kolor igliwia (r, g, b) w [0, 1] (domyslnie ciemna zielen),
  seed         - ziarno losowosci (delikatna wariacja odcieni).

Grupy (kazda z LOKALNYMI wierzcholkami 0-based):
  trunk - pien (czworoboczny slup, materialy 'bark_i'),
  crown - warstwowa korona iglasta (materialy 'needle_i_j').
"""

import math
import random


def _new_group(name):
    return {"name": name, "vertices": [], "faces": [], "colors": {}}


def _add(g, x, y, z):
    g["vertices"].append((float(x), float(y), float(z)))
    return len(g["vertices"]) - 1  # indeks 0-based, lokalny dla grupy


def _clamp01(c):
    return max(0.0, min(1.0, float(c)))


def build(**params):
    height = float(params.get("height", 5.0))
    height = max(3.0, min(8.0, height))           # twardy zakres kontraktu
    trunk_frac = float(params.get("trunk_frac", 0.30))
    trunk_radius = abs(float(params.get("trunk_radius", 0.12)))
    base_radius = abs(float(params.get("base_radius", 0.24 * height)))
    layers = max(2, int(params.get("layers", 3)))
    bark_color = tuple(_clamp01(c) for c in params.get("bark_color", (0.42, 0.27, 0.16)))
    needle_color = tuple(_clamp01(c) for c in params.get("needle_color", (0.16, 0.34, 0.18)))
    rng = random.Random(params.get("seed", 20240613))

    trunk_top = trunk_frac * height
    crown_bottom = trunk_top
    crown_height = height - crown_bottom

    # --- pien: czworoboczny slup od y=0 do trunk_top (per-scianka odcien) ---
    trunk = _new_group("trunk")
    r = trunk_radius
    lo = [_add(trunk, x, 0.0, z) for x, z in
          ((-r, -r), (r, -r), (r, r), (-r, r))]
    hi = [_add(trunk, x, trunk_top, z) for x, z in
          ((-r, -r), (r, -r), (r, r), (-r, r))]
    walls = [(lo[k], lo[(k + 1) % 4], hi[(k + 1) % 4], hi[k]) for k in range(4)]
    walls.append((hi[0], hi[1], hi[2], hi[3]))  # gora pnia (pod korona)
    for k, face in enumerate(walls):
        mat = "bark_%d" % k
        shade = 0.80 + 0.20 * rng.random()
        trunk["colors"][mat] = tuple(_clamp01(c * shade) for c in bark_color)
        trunk["faces"].append((mat, face))

    # --- korona: warstwowe stozki o malejacym promieniu bazy ku gorze ---
    crown = _new_group("crown")
    seg = 8
    for i in range(layers):
        t = i / layers
        base_y = crown_bottom + crown_height * t * 0.85
        base_r = base_radius * (1.0 - 0.65 * t)
        apex_y = crown_bottom + crown_height * (i + 1) / layers
        ring = []
        for j in range(seg):
            ang = 2.0 * math.pi * j / seg
            ring.append(_add(crown, base_r * math.cos(ang), base_y,
                             base_r * math.sin(ang)))
        apex = _add(crown, 0.0, apex_y, 0.0)
        for j in range(seg):
            mat = "needle_%d_%d" % (i, j)
            shade = 0.78 + 0.22 * rng.random()
            crown["colors"][mat] = tuple(_clamp01(c * shade) for c in needle_color)
            crown["faces"].append((mat, (ring[j], ring[(j + 1) % seg], apex)))

    return [trunk, crown]


CONTRACT_VERSION = 2
