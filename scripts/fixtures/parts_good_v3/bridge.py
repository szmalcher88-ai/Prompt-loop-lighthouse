# fixture known-good: mostek linowy (2 liny ze zwisem + deski)
import math

CONTRACT_VERSION = 3


def build(length=8.0, segments=10):
    g = {"name": "bridge", "vertices": [], "faces": [], "colors": {
        "rope": (0.55, 0.45, 0.30), "plank_0": (0.50, 0.36, 0.22),
        "plank_1": (0.46, 0.33, 0.20)}}

    def sag(t):
        return 2.0 - 0.55 * math.sin(math.pi * t)

    for side in (-0.5, 0.5):     # dwie liny nośne
        for s in range(segments):
            t0, t1 = s / segments, (s + 1) / segments
            b = len(g["vertices"])
            g["vertices"] += [(t0 * length, sag(t0), side - 0.03),
                              (t0 * length, sag(t0) + 0.06, side + 0.03),
                              (t1 * length, sag(t1) + 0.06, side + 0.03),
                              (t1 * length, sag(t1), side - 0.03)]
            g["faces"].append(("rope", (b, b + 1, b + 2, b + 3)))
    for s in range(segments):    # deski pomostu mostka
        t = (s + 0.5) / segments
        x = t * length
        y = sag(t) - 0.55
        b = len(g["vertices"])
        g["vertices"] += [(x - 0.25, y, -0.55), (x + 0.25, y, -0.55),
                          (x + 0.25, y, 0.55), (x - 0.25, y, 0.55)]
        g["faces"].append(("plank_%d" % (s % 2), (b, b + 1, b + 2, b + 3)))
    return [g]
