# -*- coding: utf-8 -*-
"""Czesc: tafla morza jako plaska siatka w plaszczyznie XZ na poziomie y=0.

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, poziom morza y=0.

Geometria: regularna siatka kwadratow w XZ. Wszystkie wierzcholki dokladnie
na y=0 (poziom morza). Domyslny zakres pokrywa sie z terenem z parts/terrain.py
(size=48 m, XZ od -24 do 24), wiec tafla przylega do wybrzeza; wymagane przez
weryfikator minimum to 20x20 m w XZ.
"""


def build(**params):
    size = float(params.get("size", 48.0))   # zakres XZ w metrach (>= 20)
    cells = int(params.get("cells", 8))       # podzialy siatki na os
    half = size / 2.0
    step = size / cells
    cols = cells + 1

    verts = []
    for i in range(cols):            # wzdluz Z
        z = -half + i * step
        for j in range(cols):        # wzdluz X
            x = -half + j * step
            verts.append((x, 0.0, z))

    faces = []
    for i in range(cells):
        for j in range(cells):
            a = i * cols + j
            b = a + 1
            c = a + cols + 1
            d = a + cols
            faces.append(("sea", (a, d, c, b)))  # CCW z gory -> normalna ku +Y

    group = {
        "name": "water",
        "vertices": verts,
        "faces": faces,
        "colors": {
            "sea": (0.12, 0.34, 0.48),
        },
    }
    return [group]

CONTRACT_VERSION = 1
