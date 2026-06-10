# -*- coding: utf-8 -*-
"""Czesc: drewniany pomost na palach wchodzacy w morze.

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, poziom morza y=0.
Os pomostu biegnie wzdluz Z (od brzegu z=0 w glab morza), os bryly w x=0.

Konstrukcja: deski pokladu leza nad woda (y > 0), wsparte na palach
wbijanych w dno, ktore siegaja ponizej tafli (y < -0.2). Wiekszosc
wierzcholkow nalezy do pokladu nad woda.

Parametry (wszystkie opcjonalne, maja sensowne domysly):
  length     - dlugosc pomostu wzdluz Z (domyslnie 12.0),
  width      - szerokosc pokladu wzdluz X (domyslnie 3.0),
  deck_y     - wysokosc gornej powierzchni desek nad woda (domyslnie 0.4),
  planks     - liczba desek pokladu wzdluz X (domyslnie 5),
  bays       - liczba przesel pali wzdluz Z (domyslnie 4),
  deck_color - kolor desek (r, g, b) w [0, 1] (domyslnie cieple drewno),
  seed       - ziarno losowosci (delikatna wariacja odcienia pali).

Grupy (kazda z wlasnymi, LOKALNYMI wierzcholkami 0-based):
  deck  - deski pokladu (boxy nad woda),
  piles - pionowe pale siegajace ponizej y=-0.2.

Weryfikator check_parts.check_pier wymaga: istnieja wierzcholki y < -0.2
(pale pod woda) oraz >= 50% wszystkich wierzcholkow ma y > 0 (poklad nad
woda). Losowosc wylacznie przez `seed`.
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
    length = float(params.get("length", 12.0))
    width = float(params.get("width", 3.0))
    deck_y = float(params.get("deck_y", 0.4))
    planks = max(1, int(params.get("planks", 5)))
    bays = max(1, int(params.get("bays", 4)))
    deck_color = tuple(_clamp01(c) for c in params.get("deck_color", (0.55, 0.40, 0.24)))
    rng = random.Random(params.get("seed", 20240612))

    hx = width / 2.0
    deck_thick = 0.2          # grubosc desek pokladu
    deck_bottom = deck_y - deck_thick  # dolna plaszczyzna desek (nad woda)
    plank_gap = 0.04          # szczelina miedzy deskami
    pile_w = 0.3              # przekroj pala
    pile_bottom = -0.8        # pale siegaja ponizej -0.2 (pod wode)

    groups = []

    # --- deck: deski biegnace wzdluz Z, leza nad woda (y > 0) ---
    deck = _new_group("deck", {"deck": deck_color})
    span = width - plank_gap * (planks - 1)
    plank_w = span / planks
    for i in range(planks):
        x0 = -hx + i * (plank_w + plank_gap)
        x1 = x0 + plank_w
        deck["faces"].extend(
            ("deck", f) for f in _box(deck, x0, x1, deck_bottom, deck_y, 0.0, length))
    groups.append(deck)

    # --- piles: pionowe pale wbite w dno, siegaja ponizej y=-0.2 ---
    piles = _new_group("piles", {"pile": (0.34, 0.24, 0.15)})
    base = piles["colors"]["pile"]
    # delikatna, deterministyczna wariacja odcienia pali
    shade = 0.9 + 0.1 * rng.random()
    piles["colors"]["pile"] = tuple(_clamp01(c * shade) for c in base)
    px = hx - pile_w / 2.0     # pale przy krawedziach pokladu
    for j in range(bays + 1):
        cz = length * j / bays
        z0 = min(max(cz - pile_w / 2.0, 0.0), length - pile_w)
        z1 = z0 + pile_w
        for sx in (-px, px):
            piles["faces"].extend(
                ("pile", f) for f in _box(
                    piles, sx - pile_w / 2.0, sx + pile_w / 2.0,
                    pile_bottom, deck_bottom, z0, z1))
    groups.append(piles)

    return groups

CONTRACT_VERSION = 1
