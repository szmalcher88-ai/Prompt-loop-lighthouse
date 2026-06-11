# fixture known-good: krzew (nieregularna bryła zieleni)
CONTRACT_VERSION = 3


def _box(g, x0, x1, y0, y1, z0, z1, mat):
    b = len(g["vertices"])
    g["vertices"] += [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
                      (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
    for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
              (1, 2, 6, 5), (3, 0, 4, 7)):
        g["faces"].append((mat, tuple(b + i for i in q)))


def build(scale=1.0):
    g = {"name": "bush", "vertices": [], "faces": [], "colors": {
        "bush_0": (0.20, 0.38, 0.20), "bush_1": (0.16, 0.34, 0.18)}}
    s = scale
    _box(g, -0.5 * s, 0.3 * s, 0.0, 0.5 * s, -0.4 * s, 0.4 * s, "bush_0")
    _box(g, -0.2 * s, 0.55 * s, 0.3 * s, 0.8 * s, -0.3 * s, 0.25 * s, "bush_1")
    _box(g, -0.35 * s, 0.15 * s, 0.6 * s, 1.05 * s, -0.15 * s, 0.35 * s, "bush_0")
    return [g]
