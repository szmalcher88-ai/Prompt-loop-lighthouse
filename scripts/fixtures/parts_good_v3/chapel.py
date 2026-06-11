# fixture known-good: kapliczka (dwuspadowy dach + sygnaturka z krzyżem)
CONTRACT_VERSION = 3


def _box(g, x0, x1, y0, y1, z0, z1, mat):
    b = len(g["vertices"])
    g["vertices"] += [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
                      (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
    for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
              (1, 2, 6, 5), (3, 0, 4, 7)):
        g["faces"].append((mat, tuple(b + i for i in q)))


def build(width=3.0, depth=4.0):
    g = {"name": "chapel", "vertices": [], "faces": [], "colors": {
        "stone_0": (0.62, 0.58, 0.52), "stone_1": (0.58, 0.54, 0.48),
        "roof_0": (0.35, 0.30, 0.32), "door": (0.35, 0.22, 0.12),
        "cross": (0.25, 0.18, 0.10)}}
    w, d = width / 2, depth / 2
    _box(g, -w, 0, 0.0, 2.4, -d, d, "stone_0")
    _box(g, 0, w, 0.0, 2.4, -d, d, "stone_1")
    b = len(g["vertices"])
    g["vertices"] += [(-w, 2.4, -d), (w, 2.4, -d), (w, 2.4, d), (-w, 2.4, d),
                      (-w, 3.6, 0.0), (w, 3.6, 0.0)]
    g["faces"] += [("roof_0", (b, b + 1, b + 5, b + 4)),
                   ("roof_0", (b + 3, b + 2, b + 5, b + 4)),
                   ("stone_0", (b, b + 3, b + 4)),
                   ("stone_1", (b + 1, b + 2, b + 5))]
    _box(g, -0.4, 0.4, 0.0, 1.6, -d - 0.05, -d + 0.02, "door")
    _box(g, -0.06, 0.06, 3.6, 4.5, -0.06, 0.06, "cross")   # sygnaturka
    _box(g, -0.30, 0.30, 4.1, 4.25, -0.06, 0.06, "cross")  # ramię krzyża
    return [g]
