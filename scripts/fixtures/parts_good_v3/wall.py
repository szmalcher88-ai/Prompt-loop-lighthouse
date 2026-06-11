# fixture known-good: mur oporowy + schody między tarasami
CONTRACT_VERSION = 3


def _box(g, x0, x1, y0, y1, z0, z1, mat):
    b = len(g["vertices"])
    g["vertices"] += [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
                      (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
    for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
              (1, 2, 6, 5), (3, 0, 4, 7)):
        g["faces"].append((mat, tuple(b + i for i in q)))


def build(length=10.0, height=1.6, steps=8):
    g = {"name": "wall", "vertices": [], "faces": [], "colors": {
        "wall_stone_0": (0.50, 0.47, 0.43), "wall_stone_1": (0.47, 0.44, 0.40),
        "step": (0.58, 0.55, 0.50)}}
    seg = length / 4
    for k in range(4):   # segmenty muru wzdłuż krawędzi tarasu
        _box(g, k * seg + 0.05, (k + 1) * seg - 0.05, 0.0, height,
             -0.3, 0.0, "wall_stone_%d" % (k % 2))
    rise = (height + 0.4) / steps
    for s in range(steps):   # kamienne schody w dół skarpy
        _box(g, length / 2 - 1.0, length / 2 + 1.0,
             s * rise, (s + 1) * rise,
             0.4 + s * 0.45, 0.4 + (s + 1) * 0.45, "step")
    return [g]
