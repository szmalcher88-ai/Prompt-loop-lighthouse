# -*- coding: utf-8 -*-
"""Czesc: WYSPA — tarasowy teren z klifami, zatoczka i turnia (kontrakt v3).

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, poziom morza y=0.

Kontrakt v3 (CONTRACT_VERSION = 3, asercje scripts/check_parts.check_terrain_v3,
gwiazda polarna: ART_DIRECTION.md, wzorzec scripts/fixtures/parts_good_v3):
to nie pas wybrzeza, lecz WYSPA otoczona woda — caly obrys siatki lezy pod
woda (y < 0). Lad to 20-75% wierzcholkow. Teren wznosi sie TARASAMI ku osi
latarni (0, 0): >= 3 poziomy plaskie rozdzielone uskokami, w sumie >= 8 miejsc
klifowych o uskoku >= 2.5 m. Od strony -Z w obrys lądu wcina sie ZATOCZKA z
plaska plaza (material 'sand') co najmniej 2 m w glab obrysu. Pod kapliczke
wyrasta osobna TURNIA (lokalne wzniesienie obok masywu). Wysokosci w [-3, 20].

Os elipsy wyspy: polosie A (X), B (Z). Zatoczka otwiera sie ku -Z.

Parametry (opcjonalne): nx, nz — gestosc siatki (domyslnie 51 x 41).
Grupa 'terrain' z materialami: seabed (dno), sand (plaza), grass (zielen),
rock_face (sciany klifow / wyzsze tarasy).
"""

import math

CONTRACT_VERSION = 3

A, B = 40.0, 30.0          # polosie wyspy (X, Z)
TURNIA = (30.0, -6.0)      # turnia pod kapliczke (rozlaczna przez przelecz)


def height(x, z):
    """Wysokosc terenu w (x, z): tarasy ku osi (0,0), zatoczka od -Z, turnia."""
    r = math.hypot(x / A, z / B)
    ang = math.degrees(math.atan2(-z, x))      # zatoczka od -Z (ang ~ +90)
    if r >= 1.0:
        h = -1.8                               # otwarte morze wokol wyspy
    elif r >= 0.95:
        h = -0.8                               # plycizna przybrzezna
    elif 55.0 <= ang <= 125.0 and 0.55 <= r < 0.95:
        h = 0.3                                # plaza zatoczki (od -Z)
    elif r >= 0.75:
        h = 0.5                                # brzeg / niski taras
    elif r >= 0.55:
        h = 2.5                                # taras dolny
    elif r >= 0.35:
        h = 5.5                                # taras srodkowy
    else:
        h = 9.0                                # plateau latarni
    d = math.hypot(x - TURNIA[0], z - TURNIA[1])
    if d < 6.0:
        h = max(h, 6.5 * (1.0 - d / 6.0) + 0.5)  # turnia jako lokalne wzniesienie
    return h


def build(**params):
    nx = int(params.get("nx", 51))
    nz = int(params.get("nz", 41))
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
            cx = (xs[i] + xs[i + 1]) / 2
            cz = (zs[j] + zs[j + 1]) / 2
            h = height(cx, cz)
            ang = math.degrees(math.atan2(-cz, cx))
            r = math.hypot(cx / A, cz / B)
            if h < 0:
                mat = "seabed"
            elif 58.0 <= ang <= 122.0 and 0.63 <= r <= 0.88 and h <= 1.2:
                mat = "sand"   # pas plazy odsuniety od granic stref (y w [-0.1, 1.2])
            elif h >= 4.0:
                mat = "rock_face"
            else:
                mat = "grass"
            g["faces"].append((mat, quad))
    return [g]
