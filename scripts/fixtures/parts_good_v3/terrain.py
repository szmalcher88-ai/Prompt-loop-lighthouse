# fixture known-good: teren v3 — tarasowa WYSPA z klifami, zatoczką i turnią
import math

CONTRACT_VERSION = 3

A, B = 40.0, 30.0          # półosie wyspy
TURNIA = (30.0, -6.0)      # turnia pod kapliczkę (rozłączna przez przełęcz)


def height(x, z):
    r = math.hypot(x / A, z / B)
    ang = math.degrees(math.atan2(-z, x))      # zatoczka od -Z (ang ~ +90)
    if r >= 1.0:
        h = -1.8
    elif r >= 0.95:
        h = -0.8
    elif 55.0 <= ang <= 125.0 and 0.55 <= r < 0.95:
        h = 0.3                                # plaża zatoczki
    elif r >= 0.75:
        h = 0.5
    elif r >= 0.55:
        h = 2.5                                # taras dolny
    elif r >= 0.35:
        h = 5.5                                # taras środkowy
    else:
        h = 9.0                                # plateau latarni
    d = math.hypot(x - TURNIA[0], z - TURNIA[1])
    if d < 6.0:
        h = max(h, 6.5 * (1.0 - d / 6.0) + 0.5)
    return h


def build(nx=51, nz=41):
    xs = [-50.0 + 100.0 * i / (nx - 1) for i in range(nx)]
    zs = [-40.0 + 80.0 * j / (nz - 1) for j in range(nz)]
    g = {"name": "terrain", "vertices": [], "faces": [], "colors": {
        "rock_face": (0.48, 0.45, 0.40), "grass": (0.35, 0.50, 0.28),
        "sand": (0.80, 0.72, 0.50), "seabed": (0.22, 0.30, 0.36)}}
    for x in xs:
        for z in zs:
            g["vertices"].append((x, height(x, z), z))
    for i in range(nx - 1):
        for j in range(nz - 1):
            a = i * nz + j
            quad = (a, a + nz, a + nz + 1, a + 1)
            cx = (xs[i] + xs[i + 1]) / 2
            cz = (zs[j] + zs[j + 1]) / 2
            h = height(cx, cz)
            ang = math.degrees(math.atan2(-cz, cx))
            r = math.hypot(cx / A, cz / B)
            if h < 0:
                mat = "seabed"
            elif 58.0 <= ang <= 122.0 and 0.63 <= r <= 0.88 and h <= 1.2:
                mat = "sand"   # pas plaży odsunięty od granic stref (wierzchołki w [-0.1, 1.2])
            elif h >= 4.0:
                mat = "rock_face"
            else:
                mat = "grass"
            g["faces"].append((mat, quad))
    return [g]
