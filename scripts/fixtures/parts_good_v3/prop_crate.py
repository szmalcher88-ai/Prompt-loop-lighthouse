# fixture known-good: skrzynia (prostopadłościan z listwami)
CONTRACT_VERSION = 3


def _box(g, x0, x1, y0, y1, z0, z1, mat):
    b = len(g["vertices"])
    g["vertices"] += [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
                      (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
    for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
              (1, 2, 6, 5), (3, 0, 4, 7)):
        g["faces"].append((mat, tuple(b + i for i in q)))


def build(size=0.8):
    s = size / 2
    g = {"name": "prop_crate", "vertices": [], "faces": [], "colors": {
        "crate_wood": (0.55, 0.42, 0.26), "slat": (0.40, 0.30, 0.18)}}
    _box(g, -s, s, 0.0, size, -s, s, "crate_wood")
    for k in (-1, 1):    # listwy po krawędziach
        _box(g, k * s - 0.03, k * s + 0.03, 0.0, size, -s - 0.02, -s + 0.02, "slat")
        _box(g, k * s - 0.03, k * s + 0.03, 0.0, size, s - 0.02, s + 0.02, "slat")
    return [g]
