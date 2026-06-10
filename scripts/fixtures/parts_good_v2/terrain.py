# fixture known-good: teren v2 (pas wybrzeża, łukowy brzeg, plaża, klif)
import math

CONTRACT_VERSION = 2


def shore_z(x, half_x=42.0):
    return 16.0 + 6.0 * math.sin((x + half_x) / (2 * half_x) * math.pi)


def height(x, z):
    zs = shore_z(x)
    if z >= zs:                       # morze
        return -1.2
    if z >= zs - 4.0:                 # plaża (pas 4 m)
        return 0.5 * (zs - z) / 4.0
    h = 1.1                           # poziom miasteczka
    d = math.hypot(x + 24.0, z + 18.0)
    if d < 10.0:                      # klif pod latarnię
        h += 3.4 * (1.0 - d / 10.0)
    return h


def build(nx=43, nz=33):
    xs = [-42.0 + 84.0 * i / (nx - 1) for i in range(nx)]
    zs = [-34.0 + 64.0 * j / (nz - 1) for j in range(nz)]
    g = {"name": "terrain", "vertices": [], "faces": [], "colors": {
        "grass": (0.35, 0.50, 0.28), "sand": (0.80, 0.72, 0.50),
        "seabed": (0.25, 0.35, 0.40)}}
    for x in xs:
        for z in zs:
            g["vertices"].append((x, height(x, z), z))
    for i in range(nx - 1):
        for j in range(nz - 1):
            a = i * nz + j
            quad = (a, a + nz, a + nz + 1, a + 1)
            cx = (xs[i] + xs[i + 1]) / 2
            cz = (zs[j] + zs[j + 1]) / 2
            zsh = shore_z(cx)
            if cz >= zsh:
                mat = "seabed"
            elif zsh - 4.5 <= cz <= zsh - 1.5:
                mat = "sand"   # pas plaży odsunięty od linii wody o >= 1 komórkę
            else:
                mat = "grass"
            g["faces"].append((mat, quad))
    return [g]
