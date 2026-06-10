# -*- coding: utf-8 -*-
"""Czesc: latarnia morska jako zestaw nazwanych grup.

Kontrakt parts/README.md: build(**params) -> lista grup, deterministycznie,
zero I/O, czysty stdlib. Uklad Y-up, jednostki ~metry, os wiezy w (x=0, z=0).

Grupy (kazda z wlasnymi, LOKALNYMI wierzcholkami 0-based):
  base    - skalisty cokol siegajacy dolu modelu,
  tower   - cylindryczna wieza zwezajaca sie ku gorze (pasy z 2 materialow),
  gallery - galeryjka z balustrada pod laterna,
  lantern - przeszklona laterna,
  roof    - stozkowy dach (najwyzszy punkt modelu),
  door    - drzwi w dolnej czesci wiezy.

Weryfikator check_parts.check_lighthouse wymaga: wysokosc calosci w [10, 200],
grupa zawierajaca "tower" zwezajaca sie ku gorze. Losowosc (skalisty cokol)
wylacznie przez jawny parametr `seed`.
"""

import math
import random

N_DEFAULT = 32  # segmenty obwodu (wymagane min. 24 dla gladkiego walca)


def _new_group(name, colors):
    return {"name": name, "vertices": [], "faces": [], "colors": dict(colors)}


def _add(g, x, y, z):
    g["vertices"].append((float(x), float(y), float(z)))
    return len(g["vertices"]) - 1  # indeks 0-based, lokalny dla grupy


def _ring(g, y, r, n):
    out = []
    for k in range(n):
        a = 2.0 * math.pi * k / n
        out.append(_add(g, r * math.cos(a), y, r * math.sin(a)))
    return out


def _rocky_ring(g, rng, y, r, n):
    out = []
    for k in range(n):
        a = 2.0 * math.pi * k / n
        rr = r * (1.0 + rng.uniform(-0.08, 0.12))
        out.append(_add(g, rr * math.cos(a), y, rr * math.sin(a)))
    return out


def _band(lower, upper):
    """Pas czworokatow laczacy dwa pierscienie o tej samej liczbie segmentow."""
    n = len(lower)
    faces = []
    for k in range(n):
        a, b = lower[k], lower[(k + 1) % n]
        c, d = upper[(k + 1) % n], upper[k]
        faces.append((a, b, c, d))
    return faces


def _cap(g, ring_idxs, y, up=True):
    """Wachlarz trojkatow domykajacy pierscien (czubek w osi)."""
    c = _add(g, 0.0, y, 0.0)
    n = len(ring_idxs)
    faces = []
    for k in range(n):
        a, b = ring_idxs[k], ring_idxs[(k + 1) % n]
        faces.append((c, a, b) if up else (c, b, a))
    return faces


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


def build(**params):
    n = int(params.get("segments", N_DEFAULT))
    rng = random.Random(params.get("seed", 20240611))

    groups = []

    # --- base: skalisty cokol (y 0..2), siega dolu modelu ---
    base = _new_group("base", {"stone": (0.45, 0.42, 0.38)})
    b0 = _rocky_ring(base, rng, 0.0, 3.2, n)
    b1 = _rocky_ring(base, rng, 1.0, 3.0, n)
    b2 = _ring(base, 2.0, 2.4, n)
    base_faces = (_band(b0, b1) + _band(b1, b2)
                  + _cap(base, b0, 0.0, up=False) + _cap(base, b2, 2.0, up=True))
    base["faces"] = [("stone", f) for f in base_faces]
    groups.append(base)

    # --- tower: zwezajaca sie wieza (y 2..18) z naprzemiennymi pasami ---
    tower = _new_group("tower", {
        "stripe_red": (0.78, 0.12, 0.10),
        "stripe_white": (0.92, 0.92, 0.90),
    })
    t_lo, t_hi = 2.0, 18.0
    r_bot, r_top = 2.2, 1.4
    rings_n = 8
    tower_rings = []
    for i in range(rings_n):
        frac = i / (rings_n - 1)
        y = t_lo + (t_hi - t_lo) * frac
        r = r_bot + (r_top - r_bot) * frac
        tower_rings.append(_ring(tower, y, r, n))
    tower_faces = []
    for i in range(rings_n - 1):
        mtl = "stripe_red" if i % 2 == 0 else "stripe_white"
        for f in _band(tower_rings[i], tower_rings[i + 1]):
            tower_faces.append((mtl, f))
    tower["faces"] = tower_faces
    groups.append(tower)

    # --- gallery: galeryjka (wspornikowy deck + balustrada) pod laterna ---
    gallery = _new_group("gallery", {"metal": (0.30, 0.32, 0.34)})
    g_in = _ring(gallery, 17.9, 1.5, n)
    g_out = _ring(gallery, 18.3, 2.6, n)
    deck = (_band(g_in, g_out)
            + _cap(gallery, g_out, 18.3, up=True) + _cap(gallery, g_in, 17.9, up=False))
    p_lo = _ring(gallery, 18.3, 2.55, n)
    p_hi = _ring(gallery, 19.0, 2.55, n)
    tr_lo = _ring(gallery, 19.0, 2.65, n)
    tr_hi = _ring(gallery, 19.15, 2.65, n)
    rail = (_band(p_lo, p_hi) + _band(p_hi, tr_lo)
            + _band(tr_lo, tr_hi) + _cap(gallery, tr_hi, 19.15, up=True))
    gallery["faces"] = [("metal", f) for f in deck + rail]
    groups.append(gallery)

    # --- lantern: przeszklona laterna (y 19.15..21.8) ---
    lantern = _new_group("lantern", {"glass": (0.55, 0.75, 0.85)})
    l0 = _ring(lantern, 19.15, 1.5, n)
    l1 = _ring(lantern, 20.5, 1.55, n)
    l2 = _ring(lantern, 21.8, 1.5, n)
    lantern_faces = (_band(l0, l1) + _band(l1, l2) + _cap(lantern, l0, 19.15, up=False))
    lantern["faces"] = [("glass", f) for f in lantern_faces]
    groups.append(lantern)

    # --- roof: stozkowy dach z czubkiem w najwyzszym punkcie modelu ---
    roof = _new_group("roof", {"roof_mtl": (0.20, 0.45, 0.35)})
    r_eave = _ring(roof, 22.0, 1.85, n)
    apex = _add(roof, 0.0, 25.0, 0.0)
    roof_faces = []
    for k in range(n):
        roof_faces.append((apex, r_eave[k], r_eave[(k + 1) % n]))
    roof_faces += _cap(roof, r_eave, 22.0, up=False)
    roof["faces"] = [("roof_mtl", f) for f in roof_faces]
    groups.append(roof)

    # --- door: drzwi w dolnej czesci wiezy (+X) ---
    door = _new_group("door", {"door_mtl": (0.25, 0.16, 0.08)})
    door_faces = _box(door, 2.0, 2.4, 2.2, 4.6, -0.5, 0.5)
    door["faces"] = [("door_mtl", f) for f in door_faces]
    groups.append(door)

    return groups
