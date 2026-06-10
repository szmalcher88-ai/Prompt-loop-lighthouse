# fixture known-good: sosna (pień + warstwowa, zwężająca się korona)
CONTRACT_VERSION = 2


def _box(g, x0, x1, y0, y1, z0, z1, mat):
    b = len(g["vertices"])
    g["vertices"] += [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
                      (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
    for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
              (1, 2, 6, 5), (3, 0, 4, 7)):
        g["faces"].append((mat, tuple(b + i for i in q)))


def build(height=5.0):
    g = {"name": "tree", "vertices": [], "faces": [], "colors": {
        "trunk": (0.40, 0.28, 0.16), "leaves_0": (0.12, 0.35, 0.18),
        "leaves_1": (0.10, 0.32, 0.16)}}
    _box(g, -0.15, 0.15, 0.0, 1.5, -0.15, 0.15, "trunk")
    layers = [(1.5, 2.9, 1.5), (2.7, 3.9, 1.0), (3.7, height, 0.45)]
    for i, (y0, y1, r) in enumerate(layers):
        _box(g, -r, r, y0, y1, -r, r, "leaves_%d" % (i % 2))
    return [g]
