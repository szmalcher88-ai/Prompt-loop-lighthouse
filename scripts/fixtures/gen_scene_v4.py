# Generator fixture scen v4 (organiczny obrys, grona domów, kapliczka w kadrze).
# Tryby: good / ring (regularny pierścień) / rect (gładka elipsa) / chapel_out.
# Commitowane sa pliki .obj; generator dla powtarzalnosci (jak gen_scene_v3).
import importlib.util
import math
from pathlib import Path

FX = Path(__file__).resolve().parent
G3 = FX / "parts_good_v3"
G2 = FX / "parts_good_v2"


def load(p):
    spec = importlib.util.spec_from_file_location("fx_" + p.stem + p.parent.name, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


house = load(G3 / "house.py")
wall = load(G3 / "wall.py")
chapel = load(G3 / "chapel.py")
bridge = load(G3 / "bridge.py")
barrel = load(G3 / "prop_barrel.py")
crate = load(G3 / "prop_crate.py")
bush = load(G3 / "bush.py")
pier = load(G2 / "pier.py")
boat = load(G2 / "boat.py")
tree = load(G2 / "tree.py")
rocks = load(G2 / "rocks.py")

CX, CZ = 0.0, 0.0          # środek wyspy
A, B = 42.0, 34.0          # bazowe półosie


def r_organic(theta):
    return 1.0 + 0.13 * math.sin(3 * theta + 0.6) + 0.09 * math.sin(5 * theta + 1.7) \
        + 0.06 * math.sin(7 * theta + 0.2) + 0.04 * math.sin(11 * theta)


def rmax(theta, mode):
    base = A * B / math.hypot(B * math.cos(theta), A * math.sin(theta))  # elipsa
    if mode == "rect":
        return base                      # gładka elipsa (known-bad organiczności)
    return base * r_organic(theta)       # organiczny brzeg


FAR_TURNIA = (-26.0, 18.0)   # chapel_out: poprawna turnia po przeciwnej stronie kamery


TURNIA = (30.0, -16.0)     # wysunięta ku brzegowi (niski dome -> przełęcz)


def height(x, z, mode):
    dx, dz = x - CX, z - CZ
    theta = math.atan2(dz, dx)
    d = math.hypot(dx, dz)
    rr = d / rmax(theta, mode)
    # gładka kopuła z ŁAGODNĄ plażą: ciągła wysokość (brak dwuznaczności
    # posadowienia) + szeroki pas brzegowy, by linia y∈[-0.3,0.3] była gęsto
    # spróbkowana po wszystkich sektorach (test organiczności obrysu).
    if rr >= 1.05:
        h = -2.5
    elif rr >= 0.80:
        h = 0.6 - (rr - 0.80) * 12.4                    # łagodna plaża 0.6 -> -2.5
    else:
        t = (0.80 - rr) / 0.80
        h = 0.6 + 8.4 * (t * t * (3 - 2 * t))           # smoothstep do ~9 w centrum
    # turnia pod kapliczkę: osobny pagórek (przełęcz przez niski dome wokół)
    tx, tz = TURNIA
    dd = math.hypot(x - tx, z - tz)
    if dd < 6.5:
        h = max(h, 6.5 * (1.0 - dd / 6.5) + 0.8)
    if mode == "chapel_out":          # druga, poprawna turnia po dalekiej stronie
        fx, fz = FAR_TURNIA
        df = math.hypot(x - fx, z - fz)
        if df < 6.5:
            h = max(h, 6.5 * (1.0 - df / 6.5) + 0.8)
    return h


def terrain_groups(mode, nx=121, nz=101):
    xs = [-50.0 + 100.0 * i / (nx - 1) for i in range(nx)]
    zs = [-46.0 + 92.0 * j / (nz - 1) for j in range(nz)]
    g = {"name": "terrain", "vertices": [], "faces": [], "colors": {
        "rock_face": (0.48, 0.45, 0.40), "grass": (0.34, 0.49, 0.27),
        "sand": (0.80, 0.72, 0.50), "seabed": (0.22, 0.30, 0.36)}}
    for x in xs:
        for zz in zs:
            g["vertices"].append((x, height(x, zz, mode), zz))
    for i in range(nx - 1):
        for j in range(nz - 1):
            a = i * nz + j
            quad = (a, a + nz, a + nz + 1, a + 1)
            cx = (xs[i] + xs[i + 1]) / 2
            cz = (zs[j] + zs[j + 1]) / 2
            h = height(cx, cz, mode)
            theta = math.atan2(cz - CZ, cx - CX)
            in_cove = (-math.pi / 2 - 0.5) <= theta <= (-math.pi / 2 + 0.5)
            if h < 0:
                mat = "seabed"
            elif in_cove and h <= 1.0:
                mat = "sand"
            elif h >= 4.0:
                mat = "rock_face"
            else:
                mat = "grass"
            g["faces"].append((mat, quad))
    # sampler: wysokość NAJBLIŻSZEGO wierzchołka siatki (to samo, co mierzy
    # check_scene.nearest_terrain_y) -> obiekty stawiane tu mają min-Y == teren.
    x0, dx = xs[0], xs[1] - xs[0]
    z0, dz = zs[0], zs[1] - zs[0]
    vlist = g["vertices"]

    def nearest(x, z):
        i = min(nx - 1, max(0, round((x - x0) / dx)))
        j = min(nz - 1, max(0, round((z - z0) / dz)))
        return vlist[i * nz + j][1]

    return [g], nearest


def tr(groups, dx, dy, dz, rot90=False, rename=None):
    out = []
    for i, gg in enumerate(groups):
        vs = []
        for (x, y, z) in gg["vertices"]:
            if rot90:
                x, z = z, x
            vs.append((x + dx, y + dy, z + dz))
        nm = rename if rename and len(groups) == 1 else \
            ((rename or gg["name"]) + ("" if len(groups) == 1 else "_%d" % (i + 1)))
        out.append({"name": nm, "vertices": vs, "faces": gg["faces"], "colors": gg["colors"]})
    return out


def build_scene(mode="good"):
    G = []
    tgroups, ny = terrain_groups(mode)
    G += tgroups

    G.append({"name": "water", "vertices": [(-50, 0, -46), (50, 0, -46), (50, 0, 46), (-50, 0, 46)],
              "faces": [("sea", (0, 1, 2, 3))], "colors": {"sea": (0.16, 0.28, 0.48)}})

    # latarnia na najwyższym plateau (środek)
    def crossing(name, cx, cz, y0, y1, hw, colors):
        mats = list(colors)
        vs = [(cx - hw, y0, cz), (cx + hw, y0, cz), (cx + hw, y1, cz), (cx - hw, y1, cz),
              (cx, y0, cz - hw), (cx, y0, cz + hw), (cx, y1, cz + hw), (cx, y1, cz - hw)]
        return [{"name": name, "vertices": vs,
                 "faces": [(mats[0], (0, 1, 2, 3)), (mats[-1], (4, 5, 6, 7))], "colors": colors}]
    G += crossing("lighthouse_tower", 0, 0, 8.9, 36.0, 1.5,
                  {"lh_white": (0.92, 0.92, 0.9), "lh_red": (0.75, 0.2, 0.18)})

    # domy: 3 grona-siatki o różnej liczności (4,3,2) i różnym promieniu od
    # wspólnego centroidu (anty-pierścień). Pitch 6.5 m -> AABB rozłączne, ale
    # sąsiad <= 7.5 m (grona się sklejają).
    archs = ["timber", "stone", "two_story"]
    PITCH = 6.5
    if mode == "ring":
        # regularny pierścień: 9 domów równomiernie, ~stały promień od centroidu
        layout = []
        for k in range(9):
            a = math.radians(k * 40.0)
            R = A * B / math.hypot(B * math.cos(a), A * math.sin(a)) * 0.5
            layout.append((R * math.cos(a), R * math.sin(a)))
    else:
        # grono blisko centrum, grono średnie, grono przy brzegu -> duży rozrzut
        # promienia od centroidu domów (CoV >> próg)
        clusters = [
            ((-12.0, 6.0), [(0, 0), (PITCH, 0), (0, PITCH), (PITCH, PITCH)]),   # 4, daleko -X+Z
            ((0.0, -14.0), [(0, 0), (PITCH, 0), (0, PITCH)]),                    # 3, przy turni (-Z)
            ((-4.0, 22.0), [(0, 0), (PITCH, 0)]),                               # 2, daleko +Z
        ]
        layout = []
        for (ax, az), offs in clusters:
            for (ox, oz) in offs:
                layout.append((ax + ox, az + oz))
    for k, (x, z) in enumerate(layout):
        a = archs[k % 3]
        # wymiary zmienne per dom (nie per archetyp) -> żadne dwa identyczne
        w = 4.0 + 0.3 * (k % 4)
        dep = 4.0 + 0.25 * (k % 3)
        grp = house.build(archetype=a, width=w, depth=dep)
        # posadowienie wg terenu pod CENTROIDEM domu (to sprawdza check_scene;
        # centroid ≠ punkt bazowy przez dach/komin) -> min-Y == teren
        vs = [v for g in grp for v in g["vertices"]]
        lcx = sum(v[0] for v in vs) / len(vs)
        lcz = sum(v[2] for v in vs) / len(vs)
        G += tr(grp, x, ny(x + lcx, z + lcz), z, rename="house_%d_%s" % (k + 1, a))

    for k, (x, z) in enumerate([(-22.0, -4.0), (16.0, 2.0)]):
        G += tr(wall.build(), x, ny(x, z), z, rename="wall_%d" % (k + 1))
    sx, sz = -10.0, 12.0
    G += tr(wall.build(), sx, ny(sx, sz), sz, rename="stair_1")

    # kapliczka na turni (30,-16) + mostek wzdłuż X (z=-14) łączący turnię z
    # gronem B (0,-14). chapel_out: kapliczka+mostek wyrzucone poza kadr główny.
    if mode != "chapel_out":
        tx, tz = TURNIA
        G += tr(chapel.build(), tx, ny(tx, tz), tz, rename="chapel_1")
        # mostek: środek x=20, z=-15, rozpięty x∈[16,24] (bridge.build wzdłuż X)
        G += tr(bridge.build(length=8.0), 16.0, ny(20.0, -15.0) + 2.2, -15.0,
                rename="bridge_1")
        wx, wz = 10.0, -10.0
    else:
        # poprawna turnia, ale po PRZECIWNEJ stronie kamery głównej (known-bad v4c)
        tx, tz = FAR_TURNIA
        G += tr(chapel.build(), tx, ny(tx, tz), tz, rename="chapel_1")
        G += tr(bridge.build(length=8.0), tx - 9.0, ny(tx - 5.0, tz) + 2.2, tz,
                rename="bridge_1")
        wx, wz = -16.0, 16.0
    G += tr(wall.build(length=6.0), wx, ny(wx, wz), wz, rename="wall_3")

    # pomosty w zatoczce (-Z): baza w wodzie (z=-46), biegną +Z ku lądowi (-32)
    # -> koniec w wodzie >= 8 m od lądu, początek styka się z brzegiem.
    for k, px in enumerate((-6.0, 6.0)):
        G += tr(pier.build(), px, 0, -46.0, rot90=True, rename="pier_%d" % (k + 1))
    # rekwizyty na pomoście (deck ~0.6) — w XZ <= 5 m od pomostu
    for k in range(4):
        x = -6.0 + (k % 2) * 1.4
        z = -42.0 + (k // 2) * 3.0
        G += tr(barrel.build(), x, 0.65, z, rename="barrel_%d" % (k + 1))
    for k in range(3):
        x = 6.0 + (k % 2) * 1.4
        z = -42.0 + (k // 2) * 3.0
        G += tr(crate.build(), x, 0.65, z, rename="crate_%d" % (k + 1))

    # krzewy przy gronach
    bush_anchor = layout[:8]
    for k, (x, z) in enumerate(bush_anchor):
        G += tr(bush.build(scale=0.8 + 0.06 * k), x + 2.2, ny(x + 2.2, z + 1.0), z + 1.0,
                rename="bush_%d" % (k + 1))

    G += tr(boat.build(), -3.0, 0, -40.0, rename="boat_1")          # cumuje przy pomoście
    G += tr(boat.build(length=4.0), 30.0, 0, 28.0, rename="boat_2")  # otwarta woda
    G += tr(boat.build(length=3.2), 1.0, ny(1.0, -27.5) + 0.3, -27.5, rename="boat_3")  # plaża

    for k in range(6):
        ang = math.radians(20 + 16 * k)
        rr = rmax(ang, "rect" if mode == "rect" else "good") * 0.6
        x, z = CX + rr * math.cos(ang), CZ + rr * math.sin(ang)
        G += tr(tree.build(height=4.0 + 0.35 * k), x, ny(x, z), z, rename="tree_%d" % (k + 1))

    rgs = rocks.build(count=10, seed=5)
    for k, rg in enumerate(rgs):
        ang = math.radians(36 * k)
        rr = rmax(ang, "rect" if mode == "rect" else "good") * 1.08
        x, z = CX + rr * math.cos(ang), CZ + rr * math.sin(ang)
        y = -0.5 if k < 8 else ny(x, z)
        G += tr([rg], x, y, z, rename="rock_%d" % (k + 1))

    # ścieżka pomost -> latarnia
    ax, az = -6.0, -28.0
    bxp, bzp = 0.0, -2.0
    pv, pf = [], []
    n = 16
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        x0, z0 = ax + (bxp - ax) * t0, az + (bzp - az) * t0
        x1, z1 = ax + (bxp - ax) * t1, az + (bzp - az) * t1
        ux, uz = (bzp - az), -(bxp - ax)
        ul = math.hypot(ux, uz)
        ux, uz = ux / ul * 0.5, uz / ul * 0.5
        b = len(pv)
        pv += [(x0 - ux, ny(x0 - ux, z0 - uz) + 0.1, z0 - uz),
               (x0 + ux, ny(x0 + ux, z0 + uz) + 0.1, z0 + uz),
               (x1 + ux, ny(x1 + ux, z1 + uz) + 0.1, z1 + uz),
               (x1 - ux, ny(x1 - ux, z1 - uz) + 0.1, z1 - uz)]
        pf.append(("path_%d" % (i % 2), (b, b + 1, b + 2, b + 3)))
    G.append({"name": "path_1", "vertices": pv, "faces": pf,
              "colors": {"path_0": (0.62, 0.58, 0.50), "path_1": (0.58, 0.54, 0.47)}})
    return G


def write_obj(path, groups, mtlname):
    mats = {}
    lines = ["mtllib %s" % mtlname]
    off = 1
    for g in groups:
        ns = {}
        for m, rgb in g["colors"].items():
            nm = "%s_%s" % (g["name"], m)
            ns[m] = nm
            mats[nm] = rgb
        lines.append("o " + g["name"])
        for v in g["vertices"]:
            lines.append("v %.4f %.4f %.4f" % v)
        cur = None
        for m, idxs in g["faces"]:
            if ns[m] != cur:
                cur = ns[m]
                lines.append("usemtl " + cur)
            lines.append("f " + " ".join(str(off + i) for i in idxs))
        off += len(g["vertices"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    mtl = []
    for nm, rgb in mats.items():
        mtl += ["newmtl " + nm, "Kd %.3f %.3f %.3f" % rgb, ""]
    (path.parent / mtlname).write_text("\n".join(mtl), encoding="utf-8")


if __name__ == "__main__":
    for mode, stem in (("good", "scene_good_v4"), ("ring", "scene_bad_v4_ring"),
                       ("rect", "scene_bad_v4_rect"), ("chapel_out", "scene_bad_v4_chapel")):
        write_obj(FX / (stem + ".obj"), build_scene(mode), stem + ".mtl")
    print("scene v4 fixtures written")
