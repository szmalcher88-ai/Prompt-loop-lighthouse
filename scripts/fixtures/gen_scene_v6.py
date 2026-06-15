# -*- coding: utf-8 -*-
"""Fixtury v6 (check_scene: posadowienie muru na długości + odstęp drzew od domów).
known-good = aktualna NAPRAWIONA scena (scene.assemble); known-bad pochodne:
  - wall:  mur uniesiony +4 m -> wisi nad terenem,
  - tree:  tree_1 przesunięty na grono domów -> nachodzi na dom.
Uruchom: python scripts/fixtures/gen_scene_v6.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FX = ROOT / "scripts" / "fixtures"
sys.path.insert(0, str(ROOT))
import scene  # noqa: E402


def write_good():
    g = scene.assemble()
    mats = scene.collect_materials(g)
    scene.write_mtl(FX / "scene_good_v6.mtl", mats)
    scene.write_obj(FX / "scene_good_v6.obj", g, "scene_good_v6.mtl")


def _read(src):
    return (FX / src).read_text(encoding="utf-8").splitlines()


def _write(dst, src, lines):
    (FX / dst).write_text("\n".join(lines) + "\n", encoding="utf-8")
    mtl = (FX / src).with_suffix(".mtl")
    if mtl.exists():
        (FX / dst).with_suffix(".mtl").write_text(
            mtl.read_text(encoding="utf-8").replace(src[:-4], dst[:-4]), encoding="utf-8")


def _vidx_of(lines, match):
    """Globalne (1-based) indeksy wierzchołków używanych przez grupy spełniające
    match(name). scene.write_obj zapisuje v GLOBALNIE, grupy wskazują je w f."""
    cur, target = None, set()
    for raw in lines:
        p = raw.split()
        if p and p[0] in ("o", "g"):
            cur = p[1]
        elif p and p[0] == "f" and cur and match(cur):
            for tok in p[1:]:
                target.add(int(tok.split("/")[0]))
    return target


def perturb(src, dst, match, fn):
    lines = _read(src)
    target = _vidx_of(lines, match)
    out, vi = [], 0
    for raw in lines:
        p = raw.split()
        if p and p[0] == "v":
            vi += 1
            if vi in target:
                x, y, z = fn(float(p[1]), float(p[2]), float(p[3]))
                out.append("v %.4f %.4f %.4f" % (x, y, z))
                continue
        out.append(raw)
    _write(dst, src, out)


def tree1_centroid(src):
    lines = _read(src)
    idx = _vidx_of(lines, lambda n: n == "tree_1")
    xs, zs, vi = [], [], 0
    for raw in lines:
        p = raw.split()
        if p and p[0] == "v":
            vi += 1
            if vi in idx:
                xs.append(float(p[1]))
                zs.append(float(p[3]))
    return (sum(xs) / len(xs), sum(zs) / len(zs))


def main():
    write_good()
    perturb("scene_good_v6.obj", "scene_bad_v6_wall.obj",
            lambda n: n.startswith("wall_"),
            lambda x, y, z: (x, y + 4.0, z))     # mur w powietrzu
    cx, cz = tree1_centroid("scene_good_v6.obj")
    dx, dz = 3.5 - cx, 18.0 - cz                 # przesuń tree_1 na grono domów (house_9 ~3.5,18)
    perturb("scene_good_v6.obj", "scene_bad_v6_tree.obj",
            lambda n: n == "tree_1",
            lambda x, y, z: (x + dx, y, z + dz))
    print("OK: fixtury v6 (good + bad_wall + bad_tree)")


if __name__ == "__main__":
    main()
