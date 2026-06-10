# fixture known-good: głazy (zamknięte bryły, deterministyczne z seeda)
import random

CONTRACT_VERSION = 2


def _box(g, x0, x1, y0, y1, z0, z1, mat):
    b = len(g["vertices"])
    g["vertices"] += [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
                      (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
    for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
              (1, 2, 6, 5), (3, 0, 4, 7)):
        g["faces"].append((mat, tuple(b + i for i in q)))


def build(count=3, seed=7):
    rng = random.Random(seed)
    out = []
    for k in range(count):
        g = {"name": "rock_%d" % (k + 1), "vertices": [], "faces": [],
             "colors": {"rock_0": (0.45, 0.44, 0.42), "rock_1": (0.50, 0.49, 0.46)}}
        w = 0.4 + rng.random() * 0.8
        h = 0.3 + rng.random() * 0.6
        d = 0.4 + rng.random() * 0.8
        _box(g, -w, w, 0.0, h, -d, d, "rock_%d" % (k % 2))
        out.append(g)
    return out
