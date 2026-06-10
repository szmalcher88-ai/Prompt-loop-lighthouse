#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Weryfikator całej sceny (out/town.obj) — sygnał prawdy pętli.

Kontrakt warunkowy: jeśli scene.py nie istnieje -> exit 0 (zielony baseline).
Normalnie: uruchamia `python scene.py`, potem waliduje out/town.obj + town.mtl.
Tryb testowy: python scripts/check_scene.py <ścieżka.obj> — bez uruchamiania
scene.py, walidacja wskazanego pliku (dla scripts/test_checkers.py).

Asercje geometryczne całości (geometria zamiast pikseli — deterministyczna):
  * latarnia (grupy lighthouse*) jest najwyższym elementem sceny,
  * woda (grupy water*) to tafla na y=0,
  * budynki (grupy house*) posadowione na terenie: min-Y budynku ~ wysokość
    najbliższego wierzchołka terenu (bez lewitacji i zakopania, tol. 0.6 m)
    i nie w wodzie (teren pod budynkiem >= 0),
  * brak kolizji: AABB XZ budynków i latarni rozłączne (tol. 0.2 m),
  * budżety sceny z budgets.json, materiały podpięte (mtllib, >=5 newmtl).
"""

import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENE = ROOT / "scene.py"
BUDGETS = ROOT / "budgets.json"

errors = []


def err(msg):
    errors.append(msg)


def parse_obj(path):
    verts, groups, mtllib, usemtl_all = [], {}, None, set()
    current = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if not parts:
            continue
        tag = parts[0]
        if tag == "v":
            verts.append(tuple(float(c) for c in parts[1:4]))
        elif tag in ("o", "g"):
            current = parts[1] if len(parts) > 1 else ""
            groups.setdefault(current, {"verts": set(), "faces": 0})
        elif tag == "mtllib":
            mtllib = parts[1] if len(parts) > 1 else ""
        elif tag == "usemtl":
            usemtl_all.add(parts[1] if len(parts) > 1 else "")
        elif tag == "f":
            idxs = []
            ok = True
            for tok in parts[1:]:
                i = int(tok.split("/")[0])
                i = i - 1 if i > 0 else len(verts) + i
                if not (0 <= i < len(verts)):
                    err("face wskazuje nieistniejący wierzchołek: %r" % raw)
                    ok = False
                    break
                idxs.append(i)
            if ok and len(idxs) >= 3:
                if current is None:
                    err("face poza grupą `o`: %r" % raw)
                else:
                    groups[current]["faces"] += 1
                    groups[current]["verts"].update(idxs)
    return verts, groups, mtllib, usemtl_all


def main():
    if len(sys.argv) > 1:
        obj = Path(sys.argv[1])
        if not obj.exists():
            print("FAIL: %s nie istnieje" % obj)
            return 1
    else:
        if not SCENE.exists():
            print("OK: scene.py jeszcze nie istnieje (zielony baseline).")
            return 0
        obj = ROOT / "out" / "town.obj"
        if obj.exists():
            obj.unlink()
        proc = subprocess.run([sys.executable, str(SCENE)], cwd=str(ROOT),
                              capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            print("FAIL: `python scene.py` zakończył się kodem %d\n%s%s"
                  % (proc.returncode, proc.stdout, proc.stderr))
            return 1
        if not obj.exists():
            print("FAIL: scene.py nie utworzył out/town.obj")
            return 1

    verts, groups, mtllib, usemtl_all = parse_obj(obj)

    def members(prefix):
        return {n: g for n, g in groups.items() if n.startswith(prefix)}

    terrain = members("terrain")
    water = members("water")
    lighthouse = members("lighthouse")
    houses = members("house")
    pier = members("pier")

    if not terrain:
        err("brak grup terrain*")
    if not water:
        err("brak grup water*")
    if not lighthouse:
        err("brak grup lighthouse*")
    if len(houses) < 5:
        err("za mało domów: %d grup house* (wymagane >= 5)" % len(houses))
    if not pier:
        err("brak grup pier*")
    if errors:
        return report()

    def verts_of(group_map):
        return [verts[i] for g in group_map.values() for i in g["verts"]]

    # latarnia najwyższa
    global_max = max(v[1] for v in verts)
    lh_max = max(v[1] for v in verts_of(lighthouse))
    if global_max - lh_max > 1e-6:
        err("latarnia nie jest najwyższym elementem sceny (%.2f < %.2f)"
            % (lh_max, global_max))

    # woda = tafla na y=0
    bad_water = [v for v in verts_of(water) if abs(v[1]) > 1e-3]
    if bad_water:
        err("woda nie leży na y=0 (%d wierzchołków, np. %r)"
            % (len(bad_water), bad_water[0]))

    # posadowienie budynków na terenie
    tverts = verts_of(terrain)

    def nearest_terrain_y(x, z):
        return min(tverts, key=lambda v: (v[0] - x) ** 2 + (v[2] - z) ** 2)[1]

    boxes = {}
    for name, g in sorted(houses.items()):
        hv = [verts[i] for i in g["verts"]]
        min_y = min(v[1] for v in hv)
        cx = sum(v[0] for v in hv) / len(hv)
        cz = sum(v[2] for v in hv) / len(hv)
        ty = nearest_terrain_y(cx, cz)
        if abs(min_y - ty) > 0.6:
            err("%s: lewitacja/zakopanie — min-Y %.2f vs teren %.2f (tol. 0.6)"
                % (name, min_y, ty))
        if ty < -1e-6:
            err("%s: stoi w wodzie (teren pod budynkiem %.2f < 0)" % (name, ty))
        boxes[name] = (min(v[0] for v in hv), max(v[0] for v in hv),
                       min(v[2] for v in hv), max(v[2] for v in hv))

    lhv = verts_of(lighthouse)
    boxes["lighthouse"] = (min(v[0] for v in lhv), max(v[0] for v in lhv),
                           min(v[2] for v in lhv), max(v[2] for v in lhv))

    # kolizje AABB w XZ (tol. 0.2 m)
    TOL = 0.2
    names = sorted(boxes)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ax0, ax1, az0, az1 = boxes[a]
            bx0, bx1, bz0, bz1 = boxes[b]
            ox = min(ax1, bx1) - max(ax0, bx0)
            oz = min(az1, bz1) - max(az0, bz0)
            if ox > TOL and oz > TOL:
                err("kolizja AABB w XZ: %s nachodzi na %s (%.2f x %.2f m)"
                    % (a, b, ox, oz))

    # budżety sceny
    budget = json.loads(BUDGETS.read_text(encoding="utf-8"))["scene"]
    total_faces = sum(g["faces"] for g in groups.values())
    if len(verts) > budget["max_vertices"]:
        err("budżet wierzchołków sceny przekroczony (%d > %d)"
            % (len(verts), budget["max_vertices"]))
    if total_faces > budget["max_faces"]:
        err("budżet ścianek sceny przekroczony (%d > %d)"
            % (total_faces, budget["max_faces"]))

    # materiały
    if not mtllib:
        err("OBJ nie podpina materiałów (brak mtllib)")
    else:
        mtl = obj.parent / mtllib
        if not mtl.exists():
            err("plik MTL %s nie istnieje obok OBJ" % mtllib)
        else:
            newmtls = {l.split()[1] for l in mtl.read_text(encoding="utf-8").splitlines()
                       if l.startswith("newmtl") and len(l.split()) > 1}
            if len(newmtls) < 5:
                err("za mało materiałów w MTL (%d < 5 newmtl)" % len(newmtls))
            missing = usemtl_all - newmtls
            if missing:
                err("usemtl bez definicji w MTL: %s" % ", ".join(sorted(missing)))
    if not usemtl_all:
        err("OBJ nie używa materiałów (brak usemtl)")

    return report()


def report():
    if errors:
        print("FAIL — check_scene (%d problemów):" % len(errors))
        for e in errors:
            print("  - " + e)
        return 1
    print("OK: scena przechodzi wszystkie kontrole.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
