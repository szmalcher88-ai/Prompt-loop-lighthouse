# -*- coding: utf-8 -*-
"""Czesc: beczka portowa (rekwizyt) — kontrakt v3.

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, poziom morza y=0.
Beczka stoi pionowo, podstawa na y=0 (assembler scene.py stawia ja na pokladzie
pomostu albo na nabrzezu).

Konstrukcja (CONTRACT_VERSION = 3, asercje check_parts.check_prop_barrel):
  * wysokosc (zakres Y) w przedziale [0.6, 1.3] m,
  * przekroj obly: zakresy X i Z niemal rowne (max <= 1.4 * min),
  * >= 24 wierzcholki (walec wieloboczny, nie kanciasta bryla),
  * >= 2 obrecze (material 'hoop_i') na roznych wysokosciach.

Geometria: klepki (staves) tworza pobrzuszony walec o trzech obreczach
wierzcholkow (dol / srodek z wybrzuszeniem / gora), zamkniety denkami (lid),
opasany trzema metalowymi obreczami (hoop_0..2) na roznych wysokosciach.

Parametry (wszystkie opcjonalne, maja sensowne domysly):
  height     - wysokosc beczki (domyslnie 0.9),
  radius     - promien przy denkach (domyslnie 0.32),
  bulge      - dodatkowy promien wybrzuszenia w polowie wysokosci (domyslnie 0.04),
  sides      - liczba klepek na obwodzie (domyslnie 12),
  wood_color - bazowy kolor drewna (r, g, b) w [0, 1],
  hoop_color - kolor obreczy (r, g, b) w [0, 1],
  seed       - ziarno losowosci (delikatny jitter odcienia klepek).

Grupa (z wlasnymi, LOKALNYMI wierzcholkami 0-based):
  barrel - klepki ('stave_i'), denka ('lid'), obrecze ('hoop_i').
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
    height = float(params.get("height", 0.9))
    radius = float(params.get("radius", 0.32))
    bulge = float(params.get("bulge", 0.04))
    sides = max(8, int(params.get("sides", 12)))
    wood_color = tuple(_clamp01(c) for c in params.get("wood_color", (0.52, 0.34, 0.20)))
    hoop_color = tuple(_clamp01(c) for c in params.get("hoop_color", (0.28, 0.25, 0.22)))
    rng = random.Random(params.get("seed", 200))

    g = _new_group("barrel")
    stave_tones = _tones(g, "stave", wood_color, 3, rng)
    g["colors"]["lid"] = tuple(_clamp01(c * 0.9) for c in wood_color)

    def ring_radius(t):
        # 0..1 wzdluz wysokosci: promien rosnie ku srodkowi (wybrzuszenie beczki)
        return radius + bulge * math.sin(math.pi * t)

    def circle(y, r):
        return [_add(g, r * math.cos(2.0 * math.pi * k / sides), y,
                     r * math.sin(2.0 * math.pi * k / sides))
                for k in range(sides)]

    # --- klepki: trzy obrecze wierzcholkow (dol, srodek, gora) i sciany miedzy ---
    fracs = (0.0, 0.5, 1.0)
    rings = [circle(t * height, ring_radius(t)) for t in fracs]
    for ri in range(len(rings) - 1):
        lower, upper = rings[ri], rings[ri + 1]
        for k in range(sides):
            k2 = (k + 1) % sides
            mat = stave_tones[k % len(stave_tones)]
            g["faces"].append((mat, (lower[k], lower[k2], upper[k2], upper[k])))

    # --- denka: dolne (y=0) i gorne (y=height) jako wachlarz trojkatow ---
    for y, r, up in ((0.0, ring_radius(0.0), False), (height, ring_radius(1.0), True)):
        c = _add(g, 0.0, y, 0.0)
        ring = circle(y, r)
        for k in range(sides):
            k2 = (k + 1) % sides
            face = (c, ring[k], ring[k2]) if up else (c, ring[k2], ring[k])
            g["faces"].append(("lid", face))

    # --- obrecze: trzy metalowe pasy na roznych wysokosciach ('hoop_i') ---
    band = 0.04
    for hi, frac in enumerate((0.2, 0.5, 0.8)):
        y = frac * height
        r = ring_radius(frac) + 0.015
        mat = "hoop_%d" % hi
        g["colors"][mat] = tuple(_clamp01(c) for c in hoop_color)
        low = circle(y - band, r)
        high = circle(y + band, r)
        for k in range(sides):
            k2 = (k + 1) % sides
            g["faces"].append((mat, (low[k], low[k2], high[k2], high[k])))

    return [g]


CONTRACT_VERSION = 3
