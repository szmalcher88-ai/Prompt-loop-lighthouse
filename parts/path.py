# -*- coding: utf-8 -*-
"""Czesc: piesza sciezka (wstega) prowadzona po polilinii w plaszczyznie XZ.

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry. Sciezka jest plaska
wstega lezaca w y=0 (assembler dopasowuje wysokosc kazdego wierzcholka do
terenu, przesuwajac go w Y do wysokosci najblizszego wierzcholka terenu —
patrz sekcja sciezki w scripts/check_scene.py v2).

Konstrukcja (CONTRACT_VERSION = 2, asercje check_parts.check_path):
  * dlugosc os dluga >= 10 m (max z extentow XZ),
  * sciezka nie skacze w pionie: extent Y <= 4 m (tu plaska, extent Y = 0).
Wstega powstaje z polilinii: centroid resamplowany ze stalym krokiem, w kazdym
punkcie wyznaczana jest normalna pozioma i odsuwane sa krawedzie left/right o
polowe szerokosci. Kolejne przekroje laczy pas czworobokow. Kazda scianka
dostaje wlasny material-odcien (deterministyczny jitter barwy per scianka —
wymog realizmu parts/README.md).

Parametry (wszystkie opcjonalne, maja sensowne domysly):
  waypoints  - lista wezlow (x, z) trasy w XZ (domyslnie prosta polilinia
               o dlugosci > 10 m, by spelnic check_path samodzielnie),
  width      - szerokosc sciezki wzdluz normalnej (domyslnie 1.6),
  step       - krok resamplingu centroidu w metrach (domyslnie 1.5),
  path_color - kolor nawierzchni (r, g, b) w [0, 1] (domyslnie zwirowy bez),
  seed       - ziarno losowosci (delikatna wariacja odcieni klepek).

Grupy (z LOKALNYMI wierzcholkami 0-based):
  path - wstega nawierzchni (materialy 'path_i', po jednym na scianke).
"""

import math
import random

# Domyslna trasa: lagodna polilinia o dlugosci grubo ponad 10 m, by modul
# spelnial check_path takze przy wywolaniu bez parametrow (sygnal prawdy).
DEFAULT_WAYPOINTS = [(0.0, 0.0), (0.0, 5.0), (3.0, 11.0)]


def _clamp01(c):
    return max(0.0, min(1.0, float(c)))


def _resample(waypoints, step):
    """Probkuje polilinie XZ rownomiernie wzdluz dlugosci luku (krok ~ step)."""
    wp = [(float(x), float(z)) for x, z in waypoints]
    cum = [0.0]
    for (x0, z0), (x1, z1) in zip(wp, wp[1:]):
        cum.append(cum[-1] + math.hypot(x1 - x0, z1 - z0))
    total = cum[-1]
    n = max(1, int(round(total / step))) if total > 1e-9 else 1
    out = []
    for s_i in range(n + 1):
        s = total * s_i / n
        k = 1
        while k < len(cum) and cum[k] < s:
            k += 1
        k = min(k, len(wp) - 1)
        seg = cum[k] - cum[k - 1]
        t = 0.0 if seg < 1e-9 else (s - cum[k - 1]) / seg
        x = wp[k - 1][0] + t * (wp[k][0] - wp[k - 1][0])
        z = wp[k - 1][1] + t * (wp[k][1] - wp[k - 1][1])
        out.append((x, z))
    return out


def build(**params):
    waypoints = params.get("waypoints", DEFAULT_WAYPOINTS)
    width = abs(float(params.get("width", 1.6)))
    step = max(0.25, float(params.get("step", 1.5)))
    path_color = tuple(_clamp01(c) for c in params.get("path_color", (0.62, 0.58, 0.50)))
    rng = random.Random(params.get("seed", 20240614))

    pts = _resample(waypoints, step)
    m = len(pts)
    hw = width / 2.0

    def direction(i):
        if i == 0:
            a, b = pts[0], pts[min(1, m - 1)]
        elif i == m - 1:
            a, b = pts[m - 2], pts[m - 1]
        else:
            a, b = pts[i - 1], pts[i + 1]
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dz) or 1.0
        return dx / L, dz / L

    group = {"name": "path", "vertices": [], "faces": [], "colors": {}}
    verts = group["vertices"]
    for i, (x, z) in enumerate(pts):
        dx, dz = direction(i)
        nx, nz = -dz, dx                      # normalna pozioma do kierunku
        verts.append((x + hw * nx, 0.0, z + hw * nz))   # krawedz left (2i)
        verts.append((x - hw * nx, 0.0, z - hw * nz))   # krawedz right (2i+1)

    for i in range(m - 1):
        li, ri = 2 * i, 2 * i + 1
        lj, rj = 2 * i + 2, 2 * i + 3
        mat = "path_%d" % i
        shade = 0.85 + 0.15 * rng.random()
        group["colors"][mat] = tuple(_clamp01(c * shade) for c in path_color)
        group["faces"].append((mat, (li, lj, rj, ri)))

    return [group]


CONTRACT_VERSION = 2
