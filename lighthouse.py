#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proceduralny generator modelu 3D latarni morskiej (Wavefront OBJ + MTL).

Uruchomiony przez `python lighthouse.py` zapisuje out/lighthouse.obj oraz
out/lighthouse.mtl. Uklad Y-up, jednostki ~metry, os wiezy w (x=0, z=0).
Czesci modelu jako nazwane grupy `o`:
  base    - skalisty cokol siegajacy dolu modelu,
  tower   - cylindryczna wieza zwezajaca sie ku gorze (pasy z 2 materialow),
  gallery - galeryjka z balustrada pod laterna,
  lantern - przeszklona laterna,
  roof    - stozkowy dach (najwyzszy punkt modelu),
  door    - drzwi w dolnej czesci wiezy.

Czysty Python, stdlib-only (math, random, pathlib).
"""

import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"

N = 32  # segmenty obwodu (wymagane min. 24)

verts = []  # (x, y, z); indeksy w OBJ sa 1-based
parts = []  # [(nazwa, [(material, [[idx, ...], ...]), ...]), ...]


def add_vert(x, y, z):
    verts.append((x, y, z))
    return len(verts)  # 1-based indeks


def ring(y, r, n=N):
    out = []
    for k in range(n):
        a = 2.0 * math.pi * k / n
        out.append(add_vert(r * math.cos(a), y, r * math.sin(a)))
    return out


def rocky_ring(y, r, n=N):
    out = []
    for k in range(n):
        a = 2.0 * math.pi * k / n
        rr = r * (1.0 + random.uniform(-0.08, 0.12))
        out.append(add_vert(rr * math.cos(a), y, rr * math.sin(a)))
    return out


def band(lower, upper):
    """Pas czworokatow laczacy dwa pierscienie o tej samej liczbie segmentow."""
    n = len(lower)
    faces = []
    for k in range(n):
        a, b = lower[k], lower[(k + 1) % n]
        c, d = upper[(k + 1) % n], upper[k]
        faces.append([a, b, c, d])
    return faces


def cap(ring_idxs, y, up=True):
    """Wachlarz trojkatow domykajacy pierscien (czubek w osi)."""
    c = add_vert(0.0, y, 0.0)
    n = len(ring_idxs)
    faces = []
    for k in range(n):
        a, b = ring_idxs[k], ring_idxs[(k + 1) % n]
        faces.append([c, a, b] if up else [c, b, a])
    return faces


def box_faces(x0, x1, y0, y1, z0, z1):
    v = [
        add_vert(x0, y0, z0), add_vert(x1, y0, z0),
        add_vert(x1, y0, z1), add_vert(x0, y0, z1),
        add_vert(x0, y1, z0), add_vert(x1, y1, z0),
        add_vert(x1, y1, z1), add_vert(x0, y1, z1),
    ]
    return [
        [v[0], v[1], v[2], v[3]],  # dol
        [v[4], v[7], v[6], v[5]],  # gora
        [v[0], v[4], v[5], v[1]],  # przod -z
        [v[1], v[5], v[6], v[2]],  # bok +x
        [v[2], v[6], v[7], v[3]],  # tyl +z
        [v[3], v[7], v[4], v[0]],  # bok -x
    ]


def build():
    random.seed(20240611)

    # --- base: skalisty cokol (y 0..2), siega dolu modelu ---
    b0 = rocky_ring(0.0, 3.2)
    b1 = rocky_ring(1.0, 3.0)
    b2 = ring(2.0, 2.4)
    base_faces = (band(b0, b1) + band(b1, b2)
                  + cap(b0, 0.0, up=False) + cap(b2, 2.0, up=True))
    parts.append(("base", [("stone", base_faces)]))

    # --- tower: zwezajaca sie wieza (y 2..18) z naprzemiennymi pasami ---
    t_lo, t_hi = 2.0, 18.0
    r_bot, r_top = 2.2, 1.4
    rings_n = 8
    tower_rings = []
    for i in range(rings_n):
        frac = i / (rings_n - 1)
        y = t_lo + (t_hi - t_lo) * frac
        r = r_bot + (r_top - r_bot) * frac
        tower_rings.append(ring(y, r))
    tower_chunks = []
    for i in range(rings_n - 1):
        mtl = "stripe_red" if i % 2 == 0 else "stripe_white"
        tower_chunks.append((mtl, band(tower_rings[i], tower_rings[i + 1])))
    parts.append(("tower", tower_chunks))

    # --- gallery: galeryjka (wspornikowy deck + balustrada) pod laterna ---
    g_in = ring(17.9, 1.5)
    g_out = ring(18.3, 2.6)
    deck = (band(g_in, g_out)
            + cap(g_out, 18.3, up=True) + cap(g_in, 17.9, up=False))
    p_lo = ring(18.3, 2.55)
    p_hi = ring(19.0, 2.55)
    tr_lo = ring(19.0, 2.65)
    tr_hi = ring(19.15, 2.65)
    rail = (band(p_lo, p_hi) + band(p_hi, tr_lo)
            + band(tr_lo, tr_hi) + cap(tr_hi, 19.15, up=True))
    parts.append(("gallery", [("metal", deck + rail)]))

    # --- lantern: przeszklona laterna (y 19.15..21.8) ---
    l0 = ring(19.15, 1.5)
    l1 = ring(20.5, 1.55)
    l2 = ring(21.8, 1.5)
    lantern = band(l0, l1) + band(l1, l2) + cap(l0, 19.15, up=False)
    parts.append(("lantern", [("glass", lantern)]))

    # --- roof: stozkowy dach z czubkiem w najwyzszym punkcie modelu ---
    r_eave = ring(22.0, 1.85)
    apex = add_vert(0.0, 25.0, 0.0)
    roof = []
    for k in range(N):
        roof.append([apex, r_eave[k], r_eave[(k + 1) % N]])
    roof += cap(r_eave, 22.0, up=False)
    parts.append(("roof", [("roof_mtl", roof)]))

    # --- door: drzwi w dolnej czesci wiezy (+X) ---
    door = box_faces(2.0, 2.4, 2.2, 4.6, -0.5, 0.5)
    parts.append(("door", [("door_mtl", door)]))


MATERIALS = [
    ("stone", (0.45, 0.42, 0.38)),
    ("stripe_red", (0.78, 0.12, 0.10)),
    ("stripe_white", (0.92, 0.92, 0.90)),
    ("metal", (0.30, 0.32, 0.34)),
    ("glass", (0.55, 0.75, 0.85)),
    ("roof_mtl", (0.20, 0.45, 0.35)),
    ("door_mtl", (0.25, 0.16, 0.08)),
]


def write_mtl(path):
    lines = ["# Latarnia morska - materialy", ""]
    for name, (r, g, b) in MATERIALS:
        lines.append("newmtl %s" % name)
        lines.append("Ka %.3f %.3f %.3f" % (r, g, b))
        lines.append("Kd %.3f %.3f %.3f" % (r, g, b))
        lines.append("Ks 0.100 0.100 0.100")
        lines.append("Ns 16.0")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_obj(path, mtl_name):
    lines = ["# Latarnia morska - model proceduralny (Y-up, metry)",
             "mtllib %s" % mtl_name, ""]
    for x, y, z in verts:
        lines.append("v %.6f %.6f %.6f" % (x, y, z))
    lines.append("")
    for name, chunks in parts:
        lines.append("o %s" % name)
        for mtl, faces in chunks:
            lines.append("usemtl %s" % mtl)
            for f in faces:
                lines.append("f " + " ".join(str(i) for i in f))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    build()
    OUT.mkdir(parents=True, exist_ok=True)
    write_mtl(OUT / "lighthouse.mtl")
    write_obj(OUT / "lighthouse.obj", "lighthouse.mtl")
    print("Zapisano %s (%d wierzcholkow, %d grup)."
          % (OUT / "lighthouse.obj", len(verts), len(parts)))


if __name__ == "__main__":
    main()
