# -*- coding: utf-8 -*-
"""Czesc: pas wybrzeza (teren) jako siatka w plaszczyznie XZ.

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, poziom morza y=0.

Kontrakt v2 (CONTRACT_VERSION = 2, asercje w scripts/check_parts.py
check_terrain_v2): to nie wyspa, lecz PAS WYBRZEZA. Siatka rozciaga sie
>= 80 m w X i >= 60 m w Z; wiekszosc (>= 60%) wierzcholkow lezy na ladzie
(y > 0.05) po stronie +Z, a strona -Z opada pod wode (poziom morza y=0).
Linia brzegowa jest LUKOWA: faluje wzgledem cieciwy o >= 3 m. Tuz przy niej
ciagnie sie pas plazy (material 'sand') w wysokosciach [-0.1, 1.2]; glebsze
dno dostaje material 'seabed', wyzszy lad - 'grass'. Pod latarnia (os 0, 0)
wyrasta KLIF wzniesiony >= 2 m ponad mediane poziomu ladu (miasteczka).
Wysokosci pozostaja w zakresie [-2, 12] m.
"""

import math

# Polowy zakresu siatki (extent: 2*HALF -> 80 m w X, 60 m w Z).
HALF_X = 40.0
HALF_Z = 30.0

# Lukowa linia brzegowa: z brzegu = COAST_Z + COAST_AMP * cos(pi*x/HALF_X);
# wybrzusza sie ku ladowi po srodku, prostuje na skrzydlach -> odchylenie
# od cieciwy grubo ponad wymagane 3 m.
COAST_Z = -16.0
COAST_AMP = 5.0

LAND_SLOPE = 0.045   # lagodny wzrost w glab ladu (+Z)
SEA_SLOPE = 0.10     # opadanie dna ku otwartemu morzu (-Z)

# Klif pod latarnia: gaussowski pagorek w osi wiezy (0, 0).
CLIFF_H = 3.6
CLIFF_SIGMA = 6.0


def _height(x, z):
    """Wysokosc terenu w punkcie (x, z)."""
    coast = COAST_Z + COAST_AMP * math.cos(math.pi * x / HALF_X)
    d = z - coast                      # > 0 w glab ladu, < 0 ku morzu
    base = LAND_SLOPE * d if d >= 0 else SEA_SLOPE * d
    cliff = CLIFF_H * math.exp(-(x * x + z * z) / (2.0 * CLIFF_SIGMA ** 2))
    return base + cliff


def build(**params):
    half_x = float(params.get("half_x", HALF_X))
    half_z = float(params.get("half_z", HALF_Z))
    cells_x = int(params.get("cells_x", 40))   # podzialy wzdluz X
    cells_z = int(params.get("cells_z", 30))   # podzialy wzdluz Z
    step_x = (2.0 * half_x) / cells_x
    step_z = (2.0 * half_z) / cells_z
    cols = cells_x + 1

    verts = []
    for i in range(cells_z + 1):       # wzdluz Z
        z = -half_z + i * step_z
        for j in range(cols):          # wzdluz X
            x = -half_x + j * step_x
            verts.append((x, _height(x, z), z))

    sand_faces = []
    grass_faces = []
    seabed_faces = []
    for i in range(cells_z):
        for j in range(cells_x):
            a = i * cols + j
            b = a + 1
            c = a + cols + 1
            d = a + cols
            quad = (a, d, c, b)  # CCW patrzac z gory -> normalna ku +Y
            ys = (verts[a][1], verts[b][1], verts[c][1], verts[d][1])
            ymin, ymax = min(ys), max(ys)
            avg_y = sum(ys) / 4.0
            if ymin >= -0.1 and ymax <= 1.2:
                sand_faces.append(quad)        # pas plazy
            elif avg_y <= 0.25:
                seabed_faces.append(quad)      # dno pod woda
            else:
                grass_faces.append(quad)       # wyzszy lad + klif

    faces = ([("sand", q) for q in sand_faces]
             + [("seabed", q) for q in seabed_faces]
             + [("grass", q) for q in grass_faces])

    group = {
        "name": "terrain",
        "vertices": verts,
        "faces": faces,
        "colors": {
            "sand": (0.80, 0.72, 0.52),
            "seabed": (0.18, 0.30, 0.34),
            "grass": (0.36, 0.52, 0.30),
        },
    }
    return [group]

CONTRACT_VERSION = 2
