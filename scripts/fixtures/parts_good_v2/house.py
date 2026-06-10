# fixture known-good: dom v2 (okna z ramami, komin, fundament, framuga)
CONTRACT_VERSION = 2


def _box(g, x0, x1, y0, y1, z0, z1, mat):
    b = len(g["vertices"])
    g["vertices"] += [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
                      (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
    for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
              (1, 2, 6, 5), (3, 0, 4, 7)):
        g["faces"].append((mat, tuple(b + i for i in q)))


def build(width=6.0, depth=5.0, wall_h=3.0):
    g = {"name": "house", "vertices": [], "faces": [], "colors": {
        "foundation": (0.45, 0.45, 0.45), "wall_0": (0.85, 0.78, 0.62),
        "wall_1": (0.82, 0.75, 0.59), "roof_0": (0.55, 0.20, 0.15),
        "roof_1": (0.52, 0.18, 0.14), "door": (0.35, 0.22, 0.12),
        "frame": (0.95, 0.95, 0.90), "glass": (0.55, 0.70, 0.85),
        "chimney": (0.50, 0.30, 0.25)}}
    w, d = width / 2, depth / 2
    _box(g, -w, w, 0.0, 0.3, -d, d, "foundation")
    _box(g, -w + 0.1, 0, 0.3, wall_h, -d + 0.1, d - 0.1, "wall_0")
    _box(g, 0, w - 0.1, 0.3, wall_h, -d + 0.1, d - 0.1, "wall_1")
    # dwuspadowy dach: dwie pochyłe płaszczyzny + szczyty
    b = len(g["vertices"])
    ridge = wall_h + 1.4
    g["vertices"] += [(-w, wall_h, -d), (w, wall_h, -d), (w, wall_h, d),
                      (-w, wall_h, d), (-w, ridge, 0.0), (w, ridge, 0.0)]
    g["faces"] += [("roof_0", (b + 0, b + 1, b + 5, b + 4)),
                   ("roof_1", (b + 3, b + 2, b + 5, b + 4)),
                   ("wall_0", (b + 0, b + 3, b + 4)),
                   ("wall_1", (b + 1, b + 2, b + 5))]
    # drzwi z framugą (front z = -d)
    _box(g, -0.7, 0.7, 0.3, 2.3, -d - 0.06, -d + 0.02, "frame")
    _box(g, -0.55, 0.55, 0.3, 2.15, -d - 0.08, -d + 0.01, "door")
    # dwa okna z ramami
    for x in (-w + 1.5, w - 1.5):
        _box(g, x - 0.55, x + 0.55, 1.2, 2.2, -d - 0.05, -d + 0.02, "frame")
        _box(g, x - 0.40, x + 0.40, 1.35, 2.05, -d - 0.07, -d + 0.01, "glass")
    # komin ponad kalenicą
    _box(g, w - 1.6, w - 1.0, ridge - 0.4, ridge + 0.6, -0.3, 0.3, "chimney")
    return [g]
