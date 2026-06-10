# fixture known-good: pomost v2 (długość, klepki, balustrada, polery)
CONTRACT_VERSION = 2


def _box(g, x0, x1, y0, y1, z0, z1, mat):
    b = len(g["vertices"])
    g["vertices"] += [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
                      (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
    for q in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
              (1, 2, 6, 5), (3, 0, 4, 7)):
        g["faces"].append((mat, tuple(b + i for i in q)))


def build(length=14.0, width=2.0):
    g = {"name": "pier", "vertices": [], "faces": [], "colors": {
        "plank_0": (0.55, 0.40, 0.25), "plank_1": (0.50, 0.36, 0.22),
        "pile": (0.35, 0.25, 0.15), "rail_post": (0.45, 0.32, 0.20),
        "rail_top": (0.40, 0.28, 0.18), "bollard": (0.30, 0.22, 0.14)}}
    n = 35
    step = length / n
    for i in range(n):  # osobne klepki
        x0 = i * step
        _box(g, x0 + 0.02, x0 + step - 0.02, 0.60, 0.70,
             -width / 2, width / 2, "plank_%d" % (i % 2))
    for k in range(9):  # 9 par pali
        x = 0.5 + k * (length - 1.0) / 8
        for s in (-1, 1):
            _box(g, x - 0.12, x + 0.12, -1.0, 0.60,
                 s * (width / 2 - 0.15) - 0.12, s * (width / 2 - 0.15) + 0.12, "pile")
    for k in range(5):  # słupki balustrady po obu stronach
        x = 0.8 + k * (length - 1.6) / 4
        for s in (-1, 1):
            _box(g, x - 0.06, x + 0.06, 0.70, 1.60,
                 s * width / 2 - 0.06, s * width / 2 + 0.06, "rail_post")
    for s in (-1, 1):  # poręcze
        _box(g, 0.6, length - 0.6, 1.55, 1.65,
             s * width / 2 - 0.05, s * width / 2 + 0.05, "rail_top")
    for s in (-1, 1):  # polery cumownicze na końcu
        _box(g, length - 0.5, length - 0.2, 0.70, 1.10,
             s * (width / 2 - 0.3) - 0.15, s * (width / 2 - 0.3) + 0.15, "bollard")
    return [g]
