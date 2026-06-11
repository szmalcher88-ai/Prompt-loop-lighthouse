# -*- coding: utf-8 -*-
"""Czesc: krzew (niska zielen przydomowa) — kontrakt v3.

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, podstawa krzewu w y=0
(assembler scene.py sadzi go na terenie miedzy zabudowa, przesuwajac w XZ
i w Y do wysokosci terenu).

Konstrukcja (CONTRACT_VERSION = 3, asercje check_parts.check_bush):
  * wysokosc (extent w osi Y) w przedziale [0.5, 1.5] m,
  * zielen — material 'leaves_i' (substring 'leaves'/'bush'/'green'),
  * >= 12 wierzcholkow,
  * >= 3 rozne poziomy wysokosci (round(y, 1)) — nieregularna bryla.

Geometria: kilka nakladajacych sie platow (lobes) — kazdy to niskopoligonowa,
zniekształcona kula z deterministycznym jitterem promienia i wysokosci
wierzcholkow. Glowny plat rozpieta pelna wysokosc krzewu (bieguny na y=0 i y=H),
boczne platy (nizsze, przesuniete w XZ) daja nieregularny obrys i listowie na
roznych poziomach. Kazda scianka dostaje wlasny material-odcien zieleni
(deterministyczny jitter barwy per scianka — wymog realizmu parts/README.md).

Parametry (wszystkie opcjonalne, maja sensowne domysly):
  height     - calkowita wysokosc krzewu (domyslnie 1.0; trzymana w [0.6, 1.4]),
  width      - szerokosc bryly w XZ (domyslnie 0.9),
  leaf_color - bazowy kolor listowia (r, g, b) w [0, 1] (domyslnie zielen),
  seed       - ziarno losowosci (jitter ksztaltu i odcieni).

Grupa (z wlasnymi, LOKALNYMI wierzcholkami 0-based):
  bush - platy listowia (materialy 'leaves_i').
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
        jitter = tuple((rng.random() - 0.5) * 0.10 for _ in range(3))
        g["colors"][mat] = tuple(_clamp01(base[k] + jitter[k]) for k in range(3))
        names.append(mat)
    return names


def _lobe(g, cx, cy, cz, rx, ry, rz, tones, rng, fi, seg=6, rings=2):
    """Dokleja do grupy jeden plat: niskopoligonowa kula (bieguny dol/gora +
    'rings' pierscieni poludnikowych) ze zniekształceniem promienia i wysokosci
    wierzcholkow. fi to biezacy licznik scianek (rotacja odcieni). Zwraca nowe fi."""
    bottom = _add(g, cx, cy - ry, cz)
    top = _add(g, cx, cy + ry, cz)
    rows = []
    for i in range(rings):
        theta = math.pi * (i + 1) / (rings + 1)   # 0..pi miedzy biegunami
        ring_y = cy - ry * math.cos(theta)
        rad = math.sin(theta)
        row = []
        for j in range(seg):
            ang = 2.0 * math.pi * j / seg
            jr = 1.0 + (rng.random() - 0.5) * 0.35
            x = cx + rx * rad * math.cos(ang) * jr
            z = cz + rz * rad * math.sin(ang) * jr
            yj = ring_y + (rng.random() - 0.5) * 0.08
            row.append(_add(g, x, yj, z))
        rows.append(row)
    # czasza dolna: biegun -> pierwszy pierscien
    for j in range(seg):
        g["faces"].append((tones[fi % len(tones)],
                           (bottom, rows[0][(j + 1) % seg], rows[0][j])))
        fi += 1
    # pasy miedzy pierscieniami
    for i in range(rings - 1):
        a, b = rows[i], rows[i + 1]
        for j in range(seg):
            j2 = (j + 1) % seg
            g["faces"].append((tones[fi % len(tones)], (a[j], a[j2], b[j2], b[j])))
            fi += 1
    # czasza gorna: ostatni pierscien -> biegun
    for j in range(seg):
        g["faces"].append((tones[fi % len(tones)],
                           (top, rows[-1][j], rows[-1][(j + 1) % seg])))
        fi += 1
    return fi


def build(**params):
    height = float(params.get("height", 1.0))
    height = max(0.6, min(1.4, height))           # twardy zakres kontraktu
    width = abs(float(params.get("width", 0.9)))
    leaf_color = tuple(_clamp01(c) for c in params.get("leaf_color", (0.24, 0.42, 0.20)))
    rng = random.Random(params.get("seed", 300))

    g = _new_group("bush")
    tones = _tones(g, "leaves", leaf_color, 5, rng)
    rx = rz = width / 2.0

    # Glowny plat rozpieta pelna wysokosc (bieguny dokladnie na y=0 i y=H, wiec
    # extent w Y == height niezaleznie od jitteru pierscieni — determinizm zakresu).
    fi = _lobe(g, 0.0, height / 2.0, 0.0, rx, height / 2.0, rz, tones, rng, 0)
    # Boczne platy: nizsze i przesuniete w XZ — nieregularny obrys, listowie na
    # roznych poziomach (mieszcza sie w [0, H], wiec nie zmieniaja zakresu wys.).
    fi = _lobe(g, rx * 0.6, height * 0.40, -rz * 0.3,
               rx * 0.6, height * 0.32, rz * 0.6, tones, rng, fi)
    fi = _lobe(g, -rx * 0.5, height * 0.45, rz * 0.4,
               rx * 0.55, height * 0.34, rz * 0.55, tones, rng, fi)

    return [g]


CONTRACT_VERSION = 3
