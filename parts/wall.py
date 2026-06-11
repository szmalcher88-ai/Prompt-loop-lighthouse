# -*- coding: utf-8 -*-
"""Czesc: kamienny mur oporowy z wkomponowanymi schodami (kontrakt v3).

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, poziom morza y=0.
Mur biegnie wzdluz lokalnej osi X, grubosc wzdluz Z; schody wznosza sie
wzdluz +Z, stopnie narastaja w +Y. Podstawa muru i schodow lezy na y=0
(assembler scene.py sadzi czesc na terenie krawedzi tarasu).

Konstrukcja (CONTRACT_VERSION = 3, asercje check_parts.check_wall):
  * mur z kamiennych bloczkow w kursach z przesunieciem (material 'stone_i'),
    >= 8 scianek 'wall*'/'stone*', wysokosc >= 0.5 m,
  * schody: osobne stopnie (material 'step_i') narastajace w pionie, >= 6
    poziomow stopni pokonujacych roznice >= 1 m.

Parametry (wszystkie opcjonalne, maja sensowne domysly):
  length        - dlugosc muru wzdluz X (domyslnie 9.0),
  height        - wysokosc muru (domyslnie 1.6),
  thickness     - grubosc muru wzdluz Z (domyslnie 0.6),
  n_steps       - liczba stopni schodow (domyslnie 8),
  step_rise     - wysokosc pojedynczego stopnia (domyslnie 0.22),
  step_run      - glebokosc stopnia wzdluz Z (domyslnie 0.4),
  step_width    - szerokosc biegu schodow wzdluz X (domyslnie 1.8),
  stone_color   - bazowy kolor kamienia (r, g, b) w [0, 1],
  step_color    - bazowy kolor stopni (r, g, b) w [0, 1],
  seed          - ziarno losowosci (delikatny jitter odcienia per bloczek),
  include_wall  - czy zwrocic grupe muru (domyslnie True),
  include_stairs- czy zwrocic grupe schodow (domyslnie True).

Grupy (kazda z wlasnymi, LOKALNYMI wierzcholkami 0-based):
  wall   - kamienne bloczki muru oporowego (material 'stone_i'),
  stairs - kamienne stopnie schodow (material 'step_i').
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


def _wall_group(length, height, thickness, stone_color, rng):
    """Mur oporowy z kamiennych bloczkow ulozonych w kursach z przesunieciem."""
    g = _new_group("wall")
    tones = _tones(g, "stone", stone_color, 5, rng)
    course_h = 0.4
    rows = max(2, int(round(height / course_h)))
    ch = height / rows
    block_len = 1.0
    z0, z1 = -thickness / 2.0, thickness / 2.0
    for r in range(rows):
        y0, y1 = r * ch, (r + 1) * ch
        stagger = block_len / 2.0 if r % 2 else 0.0
        x = -length / 2.0 - stagger
        while x < length / 2.0 - 1e-6:
            xa = max(x, -length / 2.0)
            xb = min(x + block_len, length / 2.0)
            if xb - xa > 0.05:
                mat = tones[rng.randrange(len(tones))]
                g["faces"].extend((mat, f) for f in _box(g, xa, xb, y0, y1, z0, z1))
            x += block_len
    return g


def _stairs_group(n_steps, step_rise, step_run, step_width, step_color, rng):
    """Bieg schodow: kazdy stopien to osobny bloczek narastajacy w +Y i +Z."""
    g = _new_group("stairs")
    tones = _tones(g, "step", step_color, 3, rng)
    hx = step_width / 2.0
    for i in range(n_steps):
        # stopien stoi na ziemi i siega do (i+1)*rise -> bryla schodow narasta
        y0, y1 = 0.0, (i + 1) * step_rise
        z0, z1 = i * step_run, (i + 1) * step_run
        mat = tones[i % len(tones)]
        g["faces"].extend((mat, f) for f in _box(g, -hx, hx, y0, y1, z0, z1))
    return g


def build(**params):
    length = float(params.get("length", 9.0))
    height = float(params.get("height", 1.6))
    thickness = float(params.get("thickness", 0.6))
    n_steps = max(6, int(params.get("n_steps", 8)))
    step_rise = float(params.get("step_rise", 0.22))
    step_run = float(params.get("step_run", 0.4))
    step_width = float(params.get("step_width", 1.8))
    stone_color = tuple(_clamp01(c) for c in params.get("stone_color", (0.55, 0.53, 0.49)))
    step_color = tuple(_clamp01(c) for c in params.get("step_color", (0.60, 0.58, 0.54)))
    include_wall = bool(params.get("include_wall", True))
    include_stairs = bool(params.get("include_stairs", True))
    rng = random.Random(params.get("seed", 70))

    groups = []
    if include_wall:
        groups.append(_wall_group(length, height, thickness, stone_color, rng))
    if include_stairs:
        groups.append(_stairs_group(n_steps, step_rise, step_run, step_width, step_color, rng))
    return groups


CONTRACT_VERSION = 3
