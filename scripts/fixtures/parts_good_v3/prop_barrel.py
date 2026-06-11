# fixture known-good: beczka (obła bryła z obręczami)
import math

CONTRACT_VERSION = 3


def build(radius=0.35, height=1.0, sides=8):
    g = {"name": "prop_barrel", "vertices": [], "faces": [], "colors": {
        "barrel_wood": (0.50, 0.36, 0.22), "hoop": (0.30, 0.30, 0.32)}}

    def ring(y, r):
        idx = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            idx.append(len(g["vertices"]))
            g["vertices"].append((r * math.cos(a), y, r * math.sin(a)))
        return idx

    rows = [(0.0, radius * 0.9), (0.25, radius), (0.75, radius), (1.0, radius * 0.9)]
    rings = [ring(y * height, r) for y, r in rows]
    for lo, hi in zip(rings, rings[1:]):
        for k in range(sides):
            g["faces"].append(("barrel_wood",
                               (lo[k], lo[(k + 1) % sides], hi[(k + 1) % sides], hi[k])))
    g["faces"].append(("barrel_wood", tuple(rings[0])))
    g["faces"].append(("barrel_wood", tuple(reversed(rings[-1]))))
    for hy in (0.25, 0.75):      # obręcze: wąski pas wokół kadłuba
        lo = ring(hy * height - 0.03, radius + 0.02)
        hi = ring(hy * height + 0.03, radius + 0.02)
        for k in range(sides):
            g["faces"].append(("hoop", (lo[k], lo[(k + 1) % sides],
                                        hi[(k + 1) % sides], hi[k])))
    return [g]
