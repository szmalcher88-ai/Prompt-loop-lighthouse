# fixture known-good: dom v3 — trzy archetypy o istotnie różnej geometrii
CONTRACT_VERSION = 3


def _box(g, x0, x1, y0, y1, z0, z1, mat):
    b = len(g["vertices"])
    g["vertices"] += [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
                      (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
    for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
              (1, 2, 6, 5), (3, 0, 4, 7)):
        g["faces"].append((mat, tuple(b + i for i in q)))


COLORS = {
    "foundation": (0.45, 0.45, 0.45), "wall_0": (0.85, 0.78, 0.62),
    "wall_1": (0.82, 0.75, 0.59), "stone_0": (0.55, 0.52, 0.48),
    "stone_1": (0.52, 0.49, 0.45), "beam": (0.30, 0.20, 0.12),
    "roof_0": (0.45, 0.30, 0.30), "roof_1": (0.42, 0.28, 0.28),
    "door": (0.35, 0.22, 0.12), "frame": (0.95, 0.95, 0.90),
    "glass": (0.55, 0.70, 0.85), "chimney": (0.50, 0.30, 0.25),
}


def _body(g, w, d, wall_h, wall_mat, ridge_dy):
    _box(g, -w, w, 0.0, 0.3, -d, d, "foundation")
    _box(g, -w + 0.1, 0, 0.3, wall_h, -d + 0.1, d - 0.1, wall_mat + "_0")
    _box(g, 0, w - 0.1, 0.3, wall_h, -d + 0.1, d - 0.1, wall_mat + "_1")
    b = len(g["vertices"])
    ridge = wall_h + ridge_dy
    g["vertices"] += [(-w, wall_h, -d), (w, wall_h, -d), (w, wall_h, d),
                      (-w, wall_h, d), (-w, ridge, 0.0), (w, ridge, 0.0)]
    g["faces"] += [("roof_0", (b, b + 1, b + 5, b + 4)),
                   ("roof_1", (b + 3, b + 2, b + 5, b + 4)),
                   (wall_mat + "_0", (b, b + 3, b + 4)),
                   (wall_mat + "_1", (b + 1, b + 2, b + 5))]
    _box(g, -0.7, 0.7, 0.3, 2.3, -d - 0.06, -d + 0.02, "frame")
    _box(g, -0.55, 0.55, 0.3, 2.15, -d - 0.08, -d + 0.01, "door")
    _box(g, w - 1.5, w - 0.9, ridge - 0.4, ridge + 0.6, -0.3, 0.3, "chimney")
    return ridge


def _window(g, x, y0, y1, d):
    _box(g, x - 0.55, x + 0.55, y0 - 0.15, y1 + 0.15, -d - 0.05, -d + 0.02, "frame")
    _box(g, x - 0.40, x + 0.40, y0, y1, -d - 0.07, -d + 0.01, "glass")


def build(archetype="timber", width=6.0, depth=5.0):
    g = {"name": "house", "vertices": [], "faces": [], "colors": dict(COLORS)}
    w, d = width / 2, depth / 2
    if archetype == "timber":
        _body(g, w, d, 3.2, "wall", 1.4)
        for x in (-w + 0.4, -w / 2, 0.4, w / 2 + 0.4):   # belki muru pruskiego
            _box(g, x - 0.08, x + 0.08, 0.3, 3.2, -d - 0.04, -d + 0.0, "beam")
        _box(g, -w, w, 1.7, 1.86, -d - 0.04, -d + 0.0, "beam")
        _window(g, -w + 1.3, 1.3, 2.1, d)
        _window(g, w - 1.3, 1.3, 2.1, d)
    elif archetype == "stone":
        _body(g, w + 0.3, d + 0.2, 2.6, "stone", 1.2)
        _window(g, -w + 1.2, 1.3, 1.9, d + 0.2)
        _window(g, w - 1.2, 1.3, 1.9, d + 0.2)
    elif archetype == "two_story":
        _body(g, w - 0.4, d - 0.3, 5.3, "wall", 1.5)
        _window(g, -w + 1.3, 1.1, 1.9, d - 0.3)
        _window(g, w - 1.3, 1.1, 1.9, d - 0.3)
        _window(g, -w + 1.3, 3.6, 4.4, d - 0.3)
        _window(g, w - 1.3, 3.6, 4.4, d - 0.3)
    else:
        raise ValueError("nieznany archetyp %r" % archetype)
    return [g]
