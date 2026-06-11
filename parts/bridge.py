# -*- coding: utf-8 -*-
"""Czesc: mostek linowy z deskami (kontrakt v3).

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, poziom morza y=0.
Mostek biegnie wzdluz lokalnej osi X; dwie liny nosne rozciagniete sa wzdluz
przesla i opadaja lukiem (zwis) ku srodkowi, a deski pomostu leza na linach.
Konce lin sa na y=0, srodek przesla najnizej (assembler scene.py sadzi mostek
miedzy turnia kapliczki a poziomem wioski).

Konstrukcja (CONTRACT_VERSION = 3, asercje check_parts.check_bridge):
  * >= 2 liny nosne (material 'rope_0') rozstawione >= 0.4 m w poprzek przesla,
    ze zwisem >= 0.2 m (srodek nizej niz konce),
  * przeslo >= 4 m,
  * >= 8 desek pomostu (material 'plank_i') ulozonych w poprzek.

Parametry (wszystkie opcjonalne, maja sensowne domysly):
  span         - dlugosc przesla wzdluz X (domyslnie 6.0),
  half_spread  - polowa rozstawu lin w poprzek (Z, domyslnie 0.6),
  sag          - glebokosc zwisu lin w srodku przesla (domyslnie 0.6),
  rope_radius  - polgrubosc liny (domyslnie 0.05),
  plank_count  - liczba desek pomostu (domyslnie 11),
  segments     - liczba segmentow liny wzdluz przesla (domyslnie 14),
  rope_color   - bazowy kolor lin (r, g, b) w [0, 1],
  plank_color  - bazowy kolor desek (r, g, b) w [0, 1],
  seed         - ziarno losowosci (delikatny jitter odcienia desek).

Grupa (z wlasnymi, LOKALNYMI wierzcholkami 0-based):
  bridge - liny nosne ('rope_0') + deski pomostu ('plank_i').
"""

import random


def _new_group(name):
    return {"name": name, "vertices": [], "faces": [], "colors": {}}


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


def _tones(g, prefix, base, n, rng):
    """Rejestruje n materialow-odcieni 'prefix_i' z deterministycznym jitterem
    barwy wokol koloru bazowego (realizm wg parts/README.md). Zwraca ich nazwy."""
    names = []
    for i in range(n):
        mat = "%s_%d" % (prefix, i)
        jitter = tuple((rng.random() - 0.5) * 0.07 for _ in range(3))
        g["colors"][mat] = tuple(_clamp01(base[k] + jitter[k]) for k in range(3))
        names.append(mat)
    return names


def build(**params):
    span = float(params.get("span", 6.0))
    hs = float(params.get("half_spread", 0.6))
    sag = float(params.get("sag", 0.6))
    rr = float(params.get("rope_radius", 0.05))
    plank_count = max(8, int(params.get("plank_count", 11)))
    segments = max(6, int(params.get("segments", 14)))
    rope_color = tuple(_clamp01(c) for c in params.get("rope_color", (0.42, 0.34, 0.20)))
    plank_color = tuple(_clamp01(c) for c in params.get("plank_color", (0.55, 0.40, 0.26)))
    rng = random.Random(params.get("seed", 90))

    g = _new_group("bridge")
    g["colors"]["rope_0"] = tuple(_clamp01(c) for c in rope_color)
    plank_tones = _tones(g, "plank", plank_color, 3, rng)

    half = span / 2.0

    def sag_y(x):
        """Wysokosc liny w punkcie x: luk zwisu, 0 na koncach, -sag w srodku."""
        t = (x + half) / span
        return -sag * (1.0 - (2.0 * t - 1.0) ** 2)

    # --- liny nosne: rurki kwadratowe podazajace za lukiem zwisu ('rope_0') ---
    for z_c in (-hs, hs):
        prev = None
        for i in range(segments + 1):
            x = -half + span * i / segments
            yc = sag_y(x)
            ring = [
                _add(g, x, yc + rr, z_c - rr),
                _add(g, x, yc + rr, z_c + rr),
                _add(g, x, yc - rr, z_c + rr),
                _add(g, x, yc - rr, z_c - rr),
            ]
            if prev is not None:
                for k in range(4):
                    a, b = prev[k], prev[(k + 1) % 4]
                    c, d = ring[(k + 1) % 4], ring[k]
                    g["faces"].append(("rope_0", (a, b, c, d)))
            prev = ring

    # --- deski pomostu: poprzeczne klepki lezace na linach ('plank_i') ---
    ph = 0.12          # polszerokosc deski wzdluz przesla
    thick = 0.07       # grubosc deski
    z0, z1 = -(hs + 0.1), (hs + 0.1)
    for j in range(plank_count):
        x = -half + span * (j + 0.5) / plank_count
        yc = sag_y(x)
        mat = plank_tones[j % len(plank_tones)]
        for f in _box(g, x - ph, x + ph, yc, yc + thick, z0, z1):
            g["faces"].append((mat, f))

    return [g]


CONTRACT_VERSION = 3
