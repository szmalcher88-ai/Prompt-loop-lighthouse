# Generator fixture scen v5 (relacje przestrzenne: styk schodów/łódki/mostka).
# Bazuje na scenie v4 (gen_scene_v4) i POPRAWIA styki; warianty known-bad
# perturbują jeden element. Commitowane sa .obj; generator dla powtarzalnosci.
import importlib.util
import math
from pathlib import Path

FX = Path(__file__).resolve().parent


def _load(p):
    spec = importlib.util.spec_from_file_location(p.stem, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


v4 = _load(FX / "gen_scene_v4.py")
G3 = FX / "parts_good_v3"
wall = _load(G3 / "wall.py")
bridge = _load(G3 / "bridge.py")


def terrain_sampler(groups):
    g = next(x for x in groups if x["name"].startswith("terrain"))
    xs = sorted({round(v[0], 3) for v in g["vertices"]})
    zs = sorted({round(v[2], 3) for v in g["vertices"]})
    x0, dx = xs[0], xs[1] - xs[0]
    z0, dz = zs[0], zs[1] - zs[0]
    nx, nz = len(xs), len(zs)
    grid = {}
    for v in g["vertices"]:
        i = round((v[0] - x0) / dx)
        j = round((v[2] - z0) / dz)
        grid[(i, j)] = v[1]

    def ny(x, z):
        i = min(nx - 1, max(0, round((x - x0) / dx)))
        j = min(nz - 1, max(0, round((z - z0) / dz)))
        return grid.get((i, j), 0.0)
    return ny


def box_of(g):
    vs = g["vertices"]
    return (min(v[0] for v in vs), max(v[0] for v in vs),
            min(v[1] for v in vs), max(v[1] for v in vs),
            min(v[2] for v in vs), max(v[2] for v in vs))


def tr(groups, dx, dy, dz, rename=None):
    out = []
    for g in groups:
        out.append({"name": rename or g["name"],
                    "vertices": [(x + dx, y + dy, z + dz) for (x, y, z) in g["vertices"]],
                    "faces": g["faces"], "colors": g["colors"]})
    return out


def build_scene(mode="good"):
    G = [g for g in v4.build_scene("good")
         if not (g["name"].startswith("stair") or g["name"].startswith("bridge"))]
    ny = terrain_sampler(G)
    houses = [box_of(g) for g in G if g["name"].startswith("house")]
    chapel = next(g for g in G if g["name"].startswith("chapel"))
    chb = box_of(chapel)

    # --- schody łączące dwa poziomy zbocza, przy osi +Z (zbocze wzdłuż z),
    # z dala od domów. Wysokość = przyrost terenu między końcami footprintu. ---
    SX = 9.0                            # przy +Z, ale odsunięte od grona C(-4,22)
    z_hi, z_lo = 14.0, 19.0             # bliżej centrum = wyżej; dalej = niżej
    h_lo = ny(SX, z_lo)
    h_hi = ny(SX, z_hi)
    rise = max(1.0, h_hi - h_lo)
    base = wall.build(length=4.0, height=rise, steps=8)   # stopnie rosną wzdłuż +z
    bz = box_of(base[0])
    # ustaw footprint na z∈[z_hi, z_lo] i odbij w z, by szczyt był przy z_hi (wyżej)
    for g in base:
        g["vertices"] = [(x + SX - (bz[0] + bz[1]) / 2,
                          y,
                          (z_hi + z_lo) - (z - bz[4] + z_hi)) for (x, y, z) in g["vertices"]]
    base = [{"name": g["name"], "vertices": [(x, y + h_lo, z) for (x, y, z) in g["vertices"]],
             "faces": g["faces"], "colors": g["colors"]} for g in base]
    if mode == "stair_penetrate":
        hx = (houses[0][0] + houses[0][1]) / 2
        hz = (houses[0][4] + houses[0][5]) / 2
        G += tr(base, hx - SX, ny(hx, hz) - h_lo, hz - (z_hi + z_lo) / 2, rename="stair_1")
    elif mode == "stair_short":
        G += tr(base, 0.0, -2.2, 0.0, rename="stair_1")    # opuszczone: szczyt nie sięga góry
    else:
        G += tr(base, 0.0, 0.0, 0.0, rename="stair_1")

    G += tr(wall.build(length=6.0), 34.0, ny(34.0, 6.0), 6.0, rename="wall_3")  # pusty +X

    # --- mostek do kapliczki: przyczółki podążają za gruntem, dochodzi do progu ---
    chx = (chb[0] + chb[1]) / 2
    chz = (chb[4] + chb[5]) / 2
    span = 11.0
    bx0 = chb[0] - span + 0.6           # od strony wioski do progu kapliczki
    br = bridge.build(length=span)
    bbx = box_of(br[0])

    def drape(groups, dx, dz, lift, gap=False, floatup=0.0):
        out = []
        for g in groups:
            vs = []
            for (x, y, z) in g["vertices"]:
                wx, wz = x + dx, z + dz
                follow = 0.0 if gap else (ny(wx, wz) - ny(bx0, chz))
                vs.append((wx, (y - bbx[2]) + ny(bx0, chz) + lift + follow + floatup, wz))
            out.append({"name": "bridge_1", "vertices": vs, "faces": g["faces"],
                        "colors": g["colors"]})
        return out

    if mode == "bridge_float":
        G += drape(br, bx0, chz, 0.9, floatup=3.0)          # przyczółki w powietrzu
    elif mode == "path_gap":
        G += drape([{**g, "vertices": [(x - 9.0, y, z) for (x, y, z) in g["vertices"]]}
                    for g in br], bx0, chz, 0.9)            # urwany przed kapliczką
    else:
        G += drape(br, bx0, chz, 0.9)                       # dno ~0.9 nad gruntem, śledzi teren

    # --- łódka pływająca zatopiona (dno pod wodą; dla kadłuba ~0.8 m wysokości
    # „burty pod wodą" zawsze implikuje dno < -0.4, więc to jeden tryb porażki) ---
    if mode == "boat_sunk":
        for g in G:
            if g["name"] == "boat_1":
                g["vertices"] = [(x, y - 0.8, z) for (x, y, z) in g["vertices"]]
    return G


if __name__ == "__main__":
    modes = [("good", "scene_good_v5"), ("stair_penetrate", "scene_bad_v5_stair_pen"),
             ("stair_short", "scene_bad_v5_stair_short"), ("boat_sunk", "scene_bad_v5_boat_sunk"),
             ("path_gap", "scene_bad_v5_path_gap"), ("bridge_float", "scene_bad_v5_bridge_float")]
    for mode, stem in modes:
        v4.write_obj(FX / (stem + ".obj"), build_scene(mode), stem + ".mtl")
    print("scene v5 fixtures written")
