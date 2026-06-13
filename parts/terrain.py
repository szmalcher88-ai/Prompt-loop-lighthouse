# -*- coding: utf-8 -*-
"""Czesc: WYSPA — tarasowy teren z klifami, zatoczka i turnia (kontrakt v4).

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, poziom morza y=0.

Kontrakt v3 (asercje scripts/check_parts.check_terrain_v3, gwiazda polarna:
ART_DIRECTION.md): to nie pas wybrzeza, lecz WYSPA otoczona woda — caly obrys
siatki lezy pod woda (y < 0). Lad to 20-75% wierzcholkow. Teren wznosi sie
TARASAMI ku osi latarni (0, 0): >= 3 poziomy plaskie rozdzielone uskokami, w
sumie >= 8 miejsc klifowych o uskoku >= 2.5 m. Od strony -Z w obrys lądu wcina
sie ZATOCZKA z plaska plaza (material 'sand') co najmniej 2 m w glab obrysu.
Pod kapliczke wyrasta osobna TURNIA (lokalne wzniesienie obok masywu).
Wysokosci w [-3, 20].

Zaostrzenie v4 (CONTRACT_VERSION = 4, asercja scripts/check_scene v4 "b" na
zmontowanej scenie): obrys wyspy jest ORGANICZNY — promien brzegu rmax(theta)
to elipsa modulowana kilkoma harmonicznymi (wzorzec scripts/fixtures/
gen_scene_v4.py, r_organic), tak by linia brzegowa miala >= 8 lokalnych
ekstremow i CoV promienia >= 0.06. Pas brzegowy jest CIAGLA rampa wysokosci
(gesto spróbkowana linia y~0 we wszystkich sektorach), a wnetrze pozostaje
dyskretnymi tarasami z klifami (kontrakt v3 bez zmian).

Os elipsy wyspy: polosie A (X), B (Z). Zatoczka otwiera sie ku -Z.

Parametry (opcjonalne): nx, nz — gestosc siatki (domyslnie 101 x 81).
Grupa 'terrain' z materialami: seabed (dno), sand (plaza), grass (zielen),
rock_face (sciany klifow / wyzsze tarasy).
"""

import math

CONTRACT_VERSION = 4

A, B = 40.0, 30.0          # polosie wyspy (X, Z)
TURNIA = (30.0, -6.0)      # turnia pod kapliczke (rozlaczna przez przelecz)
COVE_DIR = -math.pi / 2.0  # zatoczka otwiera sie ku -Z


def r_organic(theta):
    """Organiczny mnoznik promienia brzegu: suma harmonicznych (freq 3/5/7/11)
    daje linie brzegowa z wieloma lokalnymi ekstremami (wzorzec gen_scene_v4)."""
    return (1.0 + 0.12 * math.sin(3 * theta + 0.6) + 0.11 * math.sin(5 * theta + 1.7)
            + 0.10 * math.sin(7 * theta + 0.2) + 0.06 * math.sin(11 * theta))


def _cove(theta):
    """Waga zatoczki (0..1) wokol kierunku -Z (gaussian po kacie)."""
    d = (theta - COVE_DIR + math.pi) % (2 * math.pi) - math.pi
    return math.exp(-(d / 0.45) ** 2)


def rmax(theta):
    """Promien brzegu wyspy w kierunku theta: elipsa * organicznosc, z wcieta
    zatoczka od -Z (obrys cofa sie ku srodkowi -> bay)."""
    base = A * B / math.hypot(B * math.cos(theta), A * math.sin(theta))
    return base * r_organic(theta) * (1.0 - 0.30 * _cove(theta))


def height(x, z):
    """Wysokosc terenu w (x, z): tarasy ku osi (0,0), ciagla rampa brzegowa,
    zatoczka z plaza od -Z, turnia."""
    d = math.hypot(x, z)
    theta = math.atan2(z, x)
    rr = d / rmax(theta)
    cove = _cove(theta)
    if cove > 0.4 and 0.48 <= rr <= 0.92:
        # zatoczka: lagodna plaza od wewnetrznej krawedzi (rr~0.48) ku wodzie
        # (rr~0.92) — ciagla, piaszczysta, wcieta w glab obrysu
        h = 0.05 + 0.6 * (0.92 - rr) / (0.92 - 0.48)
    elif rr >= 1.06:
        h = -1.8                               # otwarte morze wokol wyspy
    elif rr >= 0.80:
        # ciagla rampa brzegowa: gesto spróbkowana linia y~0 (organicznosc v4b)
        t = (rr - 0.80) / (1.06 - 0.80)
        h = 0.8 - 2.6 * t                      # 0.8 -> -1.8
    elif rr >= 0.60:
        h = 2.5                                # taras dolny
    elif rr >= 0.38:
        h = 5.5                                # taras srodkowy
    else:
        h = 9.0                                # plateau latarni
    dd = math.hypot(x - TURNIA[0], z - TURNIA[1])
    if dd < 6.0:
        h = max(h, 6.5 * (1.0 - dd / 6.0) + 0.5)  # turnia jako lokalne wzniesienie
    return h


def build(**params):
    nx = int(params.get("nx", 101))
    nz = int(params.get("nz", 81))
    xs = [-50.0 + 100.0 * i / (nx - 1) for i in range(nx)]
    zs = [-40.0 + 80.0 * j / (nz - 1) for j in range(nz)]
    g = {"name": "terrain", "vertices": [], "faces": [], "colors": {
        "rock_face": (0.48, 0.45, 0.40), "grass": (0.35, 0.50, 0.28),
        "sand": (0.80, 0.72, 0.50), "seabed": (0.22, 0.30, 0.36)}}
    for x in xs:
        for z in zs:
            g["vertices"].append((x, height(x, z), z))
    for i in range(nx - 1):
        for j in range(nz - 1):
            a = i * nz + j
            quad = (a, a + nz, a + nz + 1, a + 1)
            cy = [g["vertices"][k][1] for k in quad]
            hmin, hmax = min(cy), max(cy)
            cx = (xs[i] + xs[i + 1]) / 2
            cz = (zs[j] + zs[j + 1]) / 2
            theta = math.atan2(cz, cx)
            rr = math.hypot(cx, cz) / rmax(theta)
            cove = _cove(theta)
            if hmax < 0.0:
                mat = "seabed"
            elif cove > 0.4 and 0.50 <= rr <= 0.90 and -0.1 <= hmin and hmax <= 1.2:
                mat = "sand"   # plaza zatoczki (od -Z); cala scianka w pasie [-0.1,1.2]
            elif hmax >= 4.0:
                mat = "rock_face"
            else:
                mat = "grass"
            g["faces"].append((mat, quad))
    return [g]
