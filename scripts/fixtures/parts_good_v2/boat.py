# fixture known-good: łódź wiosłowa (zanurzone dno, burty nad wodą, 2 ławki)
CONTRACT_VERSION = 2


def _box(g, x0, x1, y0, y1, z0, z1, mat):
    b = len(g["vertices"])
    g["vertices"] += [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
                      (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
    for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
              (1, 2, 6, 5), (3, 0, 4, 7)):
        g["faces"].append((mat, tuple(b + i for i in q)))


def build(length=3.6, width=1.4):
    g = {"name": "boat", "vertices": [], "faces": [], "colors": {
        "hull_0": (0.40, 0.26, 0.16), "hull_1": (0.37, 0.24, 0.15),
        "seat": (0.62, 0.46, 0.30)}}
    L, W = length / 2, width / 2
    _box(g, -L, L, -0.25, 0.0, -W, W, "hull_0")              # dno (zanurzone)
    _box(g, -L, L, 0.0, 0.55, -W, -W + 0.12, "hull_1")        # burta
    _box(g, -L, L, 0.0, 0.55, W - 0.12, W, "hull_1")          # burta
    _box(g, -L, -L + 0.12, 0.0, 0.55, -W, W, "hull_0")        # rufa
    _box(g, L - 0.12, L, 0.0, 0.55, -W, W, "hull_0")          # dziób
    _box(g, -L / 2 - 0.15, -L / 2 + 0.15, 0.30, 0.38, -W + 0.1, W - 0.1, "seat")
    _box(g, L / 2 - 0.15, L / 2 + 0.15, 0.30, 0.38, -W + 0.1, W - 0.1, "seat")
    return [g]
