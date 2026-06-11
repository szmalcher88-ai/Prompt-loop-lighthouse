# -*- coding: utf-8 -*-
"""Czesc: skrzynia portowa (rekwizyt) — kontrakt v3.

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, poziom morza y=0.
Skrzynia stoi podstawa na y=0 (assembler scene.py stawia ja na pokladzie
pomostu albo na nabrzezu).

Konstrukcja (CONTRACT_VERSION = 3, asercje check_parts.check_prop_crate):
  * kazdy wymiar (X, Y, Z) w przedziale [0.4, 1.3] m,
  * >= 4 listwy (material 'slat_i'/'trim'): scianki skrzyni jako deski oraz
    pionowe kantowki na naroznikach.

Geometria: prostopadloscienny korpus o szesciu sciankach-deskach ('slat_i')
z deterministycznym jitterem odcienia, wzmocniony czterema pionowymi listwami
naroznikowymi ('trim').

Parametry (wszystkie opcjonalne, maja sensowne domysly):
  width       - szerokosc wzdluz X (domyslnie 0.7),
  depth       - glebokosc wzdluz Z (domyslnie 0.7),
  height      - wysokosc wzdluz Y (domyslnie 0.7),
  crate_color - bazowy kolor drewna (r, g, b) w [0, 1],
  seed        - ziarno losowosci (delikatny jitter odcienia desek).

Grupa (z wlasnymi, LOKALNYMI wierzcholkami 0-based):
  crate - scianki-deski ('slat_i') i listwy naroznikowe ('trim').
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
    width = float(params.get("width", 0.7))
    depth = float(params.get("depth", 0.7))
    height = float(params.get("height", 0.7))
    crate_color = tuple(_clamp01(c) for c in params.get("crate_color", (0.58, 0.44, 0.28)))
    rng = random.Random(params.get("seed", 210))

    g = _new_group("crate")
    slat_tones = _tones(g, "slat", crate_color, 4, rng)
    g["colors"]["trim"] = tuple(_clamp01(c * 0.82) for c in crate_color)

    hw, hd = width / 2.0, depth / 2.0

    # --- korpus: szesc scianek-desek z osobnym odcieniem ('slat_i') ---
    for i, f in enumerate(_box(g, -hw, hw, 0.0, height, -hd, hd)):
        g["faces"].append((slat_tones[i % len(slat_tones)], f))

    # --- listwy naroznikowe: pionowe kantowki na czterech krawedziach ('trim') ---
    t = 0.05
    for sx in (-hw, hw):
        for sz in (-hd, hd):
            for f in _box(g, sx - t / 2.0, sx + t / 2.0, 0.0, height,
                          sz - t / 2.0, sz + t / 2.0):
                g["faces"].append(("trim", f))

    return [g]


CONTRACT_VERSION = 3
