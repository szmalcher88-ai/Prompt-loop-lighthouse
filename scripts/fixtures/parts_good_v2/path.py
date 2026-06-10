# fixture known-good: ścieżka (pas segmentów, płaska, >= 10 m)
CONTRACT_VERSION = 2


def build(length=14.0, width=1.2, segments=8):
    g = {"name": "path", "vertices": [], "faces": [], "colors": {
        "path_0": (0.62, 0.58, 0.50), "path_1": (0.58, 0.54, 0.47)}}
    step = length / segments
    for i in range(segments):
        x0, x1 = i * step, (i + 1) * step
        b = len(g["vertices"])
        g["vertices"] += [(x0, 0.1, -width / 2), (x1, 0.1, -width / 2),
                          (x1, 0.1, width / 2), (x0, 0.1, width / 2)]
        g["faces"].append(("path_%d" % (i % 2), (b, b + 1, b + 2, b + 3)))
    return [g]
