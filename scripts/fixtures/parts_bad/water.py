def build(size=15.0):
    s = float(size)
    return [{
        "name": "water",
        "vertices": [(-s, 0.0, -s), (s, 1.0, -s), (s, 0.0, s), (-s, 0.0, s)],
        "faces": [("sea", (0, 1, 2)), ("sea", (0, 2, 3))],
        "colors": {"sea": (0.2, 0.4, 0.8)},
    }]
