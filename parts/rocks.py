# -*- coding: utf-8 -*-
"""Czesc: glaz nadmorski — nieregularna, zamknieta bryla (elipsoida z szumem).

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry. Podstawa glazu w y=0
(assembler sadzi glaz na terenie przesuwajac go w XZ i w Y do wysokosci
terenu, jak drzewa). Os glazu w (0, 0).

Konstrukcja (CONTRACT_VERSION = 2, asercje check_parts.check_rocks):
  * BRYLA ZAMKNIETA — wszystkie wierzcholki uzyte w ze sciankach
    (used == set(range(len(vertices)))),
  * niezerowe wymiary w 3 osiach (extent w X, Y, Z >= 0.1 m),
  * >= 8 wierzcholkow na glaz,
  * deterministycznie z seeda (random.Random(seed)).
Glaz to siatka typu UV-sfera (dwa bieguny + pierscienie szerokosci) sciagnieta
do elipsoidy (rx, ry, rz) i zaburzona per-wierzcholek szumem ze ziarna, wiec
to nieregularny otoczak, nie idealna kula. Podstawa (min-Y) wyrownana do y=0,
z lekkim "zatopieniem" by glaz wygladal na wkopany w grunt. Kazda scianka
dostaje wlasny material-odcien (deterministyczny jitter barwy per scianka —
wymog realizmu parts/README.md), wiec zadne dwie sasiednie plaszczyzny nie sa
identyczne.

Parametry (wszystkie opcjonalne, maja sensowne domysly):
  radius     - bazowy promien glazu (domyslnie 1.0; trzymany >= 0.3),
  scale_x/y/z- spłaszczenie elipsoidy w osiach (domyslnie 1.0 / 0.7 / 0.9),
  seg        - liczba poludnikow (domyslnie 7, min 5),
  rings      - liczba podzialow szerokosci (domyslnie 3, min 2; daje rings-1
               pierscieni wewnetrznych + 2 bieguny),
  roughness  - amplituda szumu per-wierzcholek (domyslnie 0.18),
  embed      - zatopienie podstawy ponizej y=0 (domyslnie 0.06),
  color      - kolor glazu (r, g, b) w [0, 1] (domyslnie szary kamien),
  seed       - ziarno losowosci (ksztalt szumu + wariacja odcieni).

Grupa (LOKALNE wierzcholki 0-based):
  rock - pojedyncza zamknieta bryla (materialy 'rock_k').
"""

import math
import random


def _clamp01(c):
    return max(0.0, min(1.0, float(c)))


def build(**params):
    radius = max(0.3, abs(float(params.get("radius", 1.0))))
    rx = radius * float(params.get("scale_x", 1.0))
    ry = radius * float(params.get("scale_y", 0.7))
    rz = radius * float(params.get("scale_z", 0.9))
    seg = max(5, int(params.get("seg", 7)))        # poludniki
    rings = max(2, int(params.get("rings", 3)))    # podzialy szerokosci
    rough = abs(float(params.get("roughness", 0.18)))
    embed = abs(float(params.get("embed", 0.06)))
    color = tuple(_clamp01(c) for c in params.get("color", (0.50, 0.48, 0.45)))
    rng = random.Random(params.get("seed", 20240614))

    # --- pozycje wierzcholkow: bieguny + (rings-1) pierscieni wewnetrznych ---
    raw = []  # surowe (x, y, z) przed wyrownaniem podstawy do y=0

    inner = []  # listy indeksow (do raw) kolejnych pierscieni od gory ku dolowi
    for ri in range(1, rings):
        theta = math.pi * ri / rings              # 0 = gora, pi = dol
        ring = []
        for j in range(seg):
            phi = 2.0 * math.pi * j / seg
            jr = 1.0 + rough * 2.0 * (rng.random() - 0.5)   # szum promienia
            jy = 1.0 + rough * (rng.random() - 0.5)         # szum wysokosci
            x = rx * math.sin(theta) * math.cos(phi) * jr
            y = ry * math.cos(theta) * jy
            z = rz * math.sin(theta) * math.sin(phi) * jr
            ring.append(len(raw))
            raw.append([x, y, z])
        inner.append(ring)

    top = len(raw)
    raw.append([0.0, ry * (1.0 + rough * (rng.random() - 0.5)), 0.0])
    bottom = len(raw)
    raw.append([0.0, -ry * (1.0 + rough * (rng.random() - 0.5)), 0.0])

    # --- wyrownanie podstawy: min-Y -> -embed (lekkie zatopienie w gruncie) ---
    min_y = min(p[1] for p in raw)
    shift = -embed - min_y
    vertices = [(float(p[0]), float(p[1] + shift), float(p[2])) for p in raw]

    # --- scianki domykajace bryle: czapa gorna, pasy, czapa dolna ---
    faces = []  # listy krotek indeksow (bez materialu jeszcze)
    for j in range(seg):
        faces.append((top, inner[0][j], inner[0][(j + 1) % seg]))
    for k in range(len(inner) - 1):
        a_ring, b_ring = inner[k], inner[k + 1]
        for j in range(seg):
            jn = (j + 1) % seg
            faces.append((a_ring[j], a_ring[jn], b_ring[jn], b_ring[j]))
    last = inner[-1]
    for j in range(seg):
        faces.append((bottom, last[(j + 1) % seg], last[j]))

    # --- per-scianka odcien (deterministyczny jitter barwy) ---
    group = {"name": "rock", "vertices": vertices, "faces": [], "colors": {}}
    for k, face in enumerate(faces):
        mat = "rock_%d" % k
        shade = 0.82 + 0.18 * rng.random()
        group["colors"][mat] = tuple(_clamp01(c * shade) for c in color)
        group["faces"].append((mat, tuple(face)))

    return [group]


CONTRACT_VERSION = 2
