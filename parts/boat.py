# -*- coding: utf-8 -*-
"""Czesc: drewniana lodka wioslowa (dinghy) ploaca na tafli morza.

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, poziom morza y=0.
Os kadluba biegnie wzdluz Z, bryla symetryczna wzgledem x=0; lodka ploa w
osi (0, 0, 0), wiec assembler przesuwa ja w XZ na docelowa pozycje.

Konstrukcja (CONTRACT_VERSION = 2, asercje check_parts.check_boat):
  * dno (kil) zanurzone pod tafla -> min-Y < -0.05,
  * burty (gorna krawedz kadluba) wystaja nad wode -> max-Y > 0.3,
  * >= 2 lawki (material 'bench*') w roznych miejscach kadluba (thwarty).
Kadlub to podwojnie zaostrzony ksztalt: stacje wzdluz Z o polszerokosci
malejacej do zera na dziobie i rufie (frac = z / (length/2)), z linia kilu
schodzaca najnizej w srodku. Kazdy pas burty dostaje wlasny material-odcien
(deterministyczny jitter barwy per scianka — wymog realizmu parts/README.md).

Parametry (wszystkie opcjonalne, maja sensowne domysly):
  length     - dlugosc kadluba wzdluz Z (domyslnie 4.0),
  beam       - szerokosc kadluba wzdluz X (domyslnie 1.5),
  depth      - glebokosc zanurzenia kilu pod y=0 (domyslnie 0.30),
  gunwale_y  - wysokosc gornej krawedzi burty nad woda (domyslnie 0.45),
  hull_color - kolor kadluba (r, g, b) w [0, 1] (domyslnie cieple drewno),
  seats      - liczba lawek-thwartow (domyslnie 3, min 2),
  seat_color - kolor lawek (r, g, b) w [0, 1],
  seed       - ziarno losowosci (delikatna wariacja odcienia klepek/lawek).

Grupy (kazda z wlasnymi, LOKALNYMI wierzcholkami 0-based):
  hull   - kadlub z pasow burt (materialy 'hull_i'),
  thwarts- poprzeczne lawki wioslarza (materialy 'bench_i').
"""

import random


def _new_group(name, colors):
    return {"name": name, "vertices": [], "faces": [], "colors": dict(colors)}


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


def build(**params):
    length = float(params.get("length", 4.0))
    beam = float(params.get("beam", 1.5))
    depth = abs(float(params.get("depth", 0.30)))     # kil zanurzony o tyle
    gunwale_y = float(params.get("gunwale_y", 0.45))  # burta nad woda
    hull_color = tuple(_clamp01(c) for c in params.get("hull_color", (0.62, 0.30, 0.20)))
    seat_color = tuple(_clamp01(c) for c in params.get("seat_color", (0.70, 0.58, 0.38)))
    seats = max(2, int(params.get("seats", 3)))
    rng = random.Random(params.get("seed", 20240612))

    hl = length / 2.0
    hb = beam / 2.0
    stations = 13  # liczba przekrojow wzdluz Z (parzysta-srodkowa stacja w frac=0)

    def half_width(frac):
        return hb * (1.0 - frac * frac) ** 0.5

    def keel_y(frac):
        # kil najnizej w srodku (-depth), wynurza sie do y=0 na koncach
        return -depth * (1.0 - frac * frac)

    # --- hull: pasy burt port/starboard miedzy kolejnymi stacjami ---
    hull = _new_group("hull", {})
    zs = [-hl + length * i / (stations - 1) for i in range(stations)]
    fracs = [z / hl for z in zs]
    # wierzcholki: dla kazdej stacji port-burta, starboard-burta, kil
    port = [_add(hull, -half_width(f), gunwale_y, z) for f, z in zip(fracs, zs)]
    star = [_add(hull, half_width(f), gunwale_y, z) for f, z in zip(fracs, zs)]
    keel = [_add(hull, 0.0, keel_y(f), z) for f, z in zip(fracs, zs)]
    for i in range(stations - 1):
        mat = "hull_%d" % i
        shade = 0.85 + 0.15 * rng.random()
        hull["colors"][mat] = tuple(_clamp01(c * shade) for c in hull_color)
        # pas lewej i prawej burty (od krawedzi przez kil)
        hull["faces"].append((mat, (port[i], keel[i], keel[i + 1], port[i + 1])))
        hull["faces"].append((mat, (star[i], star[i + 1], keel[i + 1], keel[i])))

    # --- thwarts: poprzeczne lawki wioslarza w roznych miejscach kadluba ---
    thwarts = _new_group("thwarts", {})
    seat_y0, seat_y1 = 0.12, 0.22
    seat_hz = 0.09  # polowa dlugosci lawki wzdluz Z
    for k in range(seats):
        # rozlozone od dziobu ku rufie, ale nie na samych koncach (frac w +-0.7)
        frac = -0.7 + 1.4 * k / (seats - 1)
        zc = frac * hl
        w = half_width(frac) * 0.78  # lawka wezsza niz burta w tym przekroju
        mat = "bench_%d" % k
        shade = 0.88 + 0.12 * rng.random()
        thwarts["colors"][mat] = tuple(_clamp01(c * shade) for c in seat_color)
        thwarts["faces"].extend(
            (mat, f) for f in _box(
                thwarts, -w, w, seat_y0, seat_y1, zc - seat_hz, zc + seat_hz))

    return [hull, thwarts]


CONTRACT_VERSION = 2
