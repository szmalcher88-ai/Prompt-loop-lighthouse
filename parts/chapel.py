# -*- coding: utf-8 -*-
"""Czesc: przydrozna kapliczka na turni (kontrakt v3).

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, poziom morza y=0.
Bryla stoi podstawa na y=0 (assembler scene.py sadzi czesc na terenie turni).

Konstrukcja (CONTRACT_VERSION = 3, asercje check_parts.check_chapel):
  * mala murowana bryla (material 'wall_i') mniejsza od domow: plan <= 25 m2,
  * czterospadowy daszek (material 'roof_i') wienczacy bryle — najwyzszy
    element konstrukcji poza sygnaturka,
  * sygnaturka/krzyz (material 'cross_0') jako najwyzszy punkt kapliczki,
  * cala kapliczka nizsza niz 7 m.

Parametry (wszystkie opcjonalne, maja sensowne domysly):
  width        - szerokosc bryly w planie (X i Z, domyslnie 2.4),
  wall_height  - wysokosc scian (domyslnie 2.4),
  roof_height  - wysokosc daszku ponad sciany (domyslnie 1.4),
  overhang     - okap daszku poza obrys scian (domyslnie 0.25),
  spire_height - wysokosc sygnaturki/krzyza ponad kalenice (domyslnie 0.9),
  wall_color   - bazowy kolor tynku scian (r, g, b) w [0, 1],
  roof_color   - bazowy kolor daszku (r, g, b) w [0, 1],
  cross_color  - bazowy kolor sygnaturki (r, g, b) w [0, 1],
  seed         - ziarno losowosci (delikatny jitter odcienia per scianka).

Grupa (z wlasnymi, LOKALNYMI wierzcholkami 0-based):
  chapel - bryla + daszek + sygnaturka (materialy 'wall_i'/'roof_i'/'cross_0').
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
    width = float(params.get("width", 2.4))
    wall_h = float(params.get("wall_height", 2.4))
    roof_h = float(params.get("roof_height", 1.4))
    overhang = float(params.get("overhang", 0.25))
    spire_h = float(params.get("spire_height", 0.9))
    wall_color = tuple(_clamp01(c) for c in params.get("wall_color", (0.86, 0.83, 0.76)))
    roof_color = tuple(_clamp01(c) for c in params.get("roof_color", (0.46, 0.22, 0.16)))
    cross_color = tuple(_clamp01(c) for c in params.get("cross_color", (0.30, 0.26, 0.22)))
    rng = random.Random(params.get("seed", 80))

    g = _new_group("chapel")
    wall_tones = _tones(g, "wall", wall_color, 4, rng)
    roof_tones = _tones(g, "roof", roof_color, 3, rng)
    g["colors"]["cross_0"] = tuple(_clamp01(c) for c in cross_color)

    hw = width / 2.0

    # --- bryla scian: prosty murowany szescian (material 'wall_i') ---
    for f in _box(g, -hw, hw, 0.0, wall_h, -hw, hw):
        g["faces"].append((wall_tones[rng.randrange(len(wall_tones))], f))

    # --- czterospadowy daszek: piramida z okapem, wienczy bryle ('roof_i') ---
    hr = hw + overhang
    apex_y = wall_h + roof_h
    c0 = _add(g, -hr, wall_h, -hr)
    c1 = _add(g, hr, wall_h, -hr)
    c2 = _add(g, hr, wall_h, hr)
    c3 = _add(g, -hr, wall_h, hr)
    apex = _add(g, 0.0, apex_y, 0.0)
    for a, b in ((c0, c1), (c1, c2), (c2, c3), (c3, c0)):
        g["faces"].append((roof_tones[rng.randrange(len(roof_tones))], (a, b, apex)))

    # --- sygnaturka: krzyz na kalenicy, najwyzszy punkt kapliczki ('cross_0') ---
    cross_base = apex_y
    cross_top = apex_y + spire_h
    t = 0.07  # polgrubosc ramion krzyza
    for f in _box(g, -t, t, cross_base, cross_top, -t, t):           # pion
        g["faces"].append(("cross_0", f))
    bar_y = cross_base + spire_h * 0.62
    for f in _box(g, -0.35, 0.35, bar_y - t, bar_y + t, -t, t):      # ramie poziome
        g["faces"].append(("cross_0", f))

    return [g]


CONTRACT_VERSION = 3
