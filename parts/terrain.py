# -*- coding: utf-8 -*-
"""Czesc: pas wybrzeza (teren) jako siatka w plaszczyznie XZ.

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, poziom morza y=0.

Geometria: regularna siatka kwadratow w XZ o zakresie >= 40 m w obu osiach,
w wiekszosci plaska tuz nad poziomem morza, z lagodnym landowym wzniesieniem
oraz wybrzuszeniem pod latarnia (os x=0, z=0) wyrastajacym od strony morza
(-Z). Wysokosci pozostaja w zakresie [-2, 12] m. Dolne partie (plaza) dostaja
material piasku, wyzsze - trawy.
"""

import math


def _height(x, z, half, size):
    """Wysokosc terenu w punkcie (x, z); plaski lekki spadek + wzniesienie."""
    # Lagodny wzrost od strony morza (-Z) w glab ladu (+Z): 0.25 .. ~0.95 m.
    base = 0.25 + 0.70 * (z + half) / size
    # Wybrzuszenie pod latarnia: gaussowski pagorek w osi wiezy (0, 0).
    hill = 2.40 * math.exp(-(x * x + z * z) / (2.0 * 7.0 ** 2))
    return base + hill


def build(**params):
    size = float(params.get("size", 48.0))   # zakres XZ w metrach (>= 40)
    cells = int(params.get("cells", 24))      # podzialy siatki na os
    half = size / 2.0
    step = size / cells
    cols = cells + 1

    verts = []
    for i in range(cols):            # wzdluz Z
        z = -half + i * step
        for j in range(cols):        # wzdluz X
            x = -half + j * step
            verts.append((x, _height(x, z, half, size), z))

    sand_faces = []
    grass_faces = []
    for i in range(cells):
        for j in range(cells):
            a = i * cols + j
            b = a + 1
            c = a + cols + 1
            d = a + cols
            quad = (a, d, c, b)  # CCW patrzac z gory -> normalna ku +Y
            avg_y = (verts[a][1] + verts[b][1]
                     + verts[c][1] + verts[d][1]) / 4.0
            (grass_faces if avg_y >= 0.5 else sand_faces).append(quad)

    faces = ([("sand", q) for q in sand_faces]
             + [("grass", q) for q in grass_faces])

    group = {
        "name": "terrain",
        "vertices": verts,
        "faces": faces,
        "colors": {
            "sand": (0.80, 0.72, 0.52),
            "grass": (0.36, 0.52, 0.30),
        },
    }
    return [group]

CONTRACT_VERSION = 1
