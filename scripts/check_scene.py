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
            groups.setdefault(current, {"verts": set(), "faces": 0, "mats": set()})
        elif tag == "mtllib":
            mtllib = parts[1] if len(parts) > 1 else ""
        elif tag == "usemtl":
            m = parts[1] if len(parts) > 1 else ""
            usemtl_all.add(m)
            if current is not None:
                groups[current]["mats"].add(m)
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


def scene_version():
    """SCENE_VERSION z scene.py (deklaracja wersji kontraktu sceny)."""
    import re
    m = re.search(r"^SCENE_VERSION\s*=\s*(\d+)", SCENE.read_text(encoding="utf-8"),
                  re.MULTILINE)
    return int(m.group(1)) if m else 1


def main():
    if len(sys.argv) > 1:
        obj = Path(sys.argv[1])
        version = int(sys.argv[2]) if len(sys.argv) > 2 else 1
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
        version = scene_version()
        floor = json.loads((ROOT / "scripts" / "versions_floor.json")
                           .read_text(encoding="utf-8"))["scene"]
        if version < floor:
            print("FAIL: SCENE_VERSION=%d poniżej podłogi %d "
                  "(scripts/versions_floor.json; LESSON-003 — wersji nie wolno obniżać)"
                  % (version, floor))
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

    # ----- zaostrzenia v2 (aktywne od SCENE_VERSION >= 2) -----
    if version >= 2:
        def center_xz(group_map):
            vs = verts_of(group_map)
            return (sum(v[0] for v in vs) / len(vs), sum(v[2] for v in vs) / len(vs))

        def dist_xz(a, b):
            return math.hypot(a[0] - b[0], a[1] - b[1])

        boats = members("boat")
        trees = members("tree")
        rocks = members("rock")
        paths = members("path")
        if len(boats) < 2:
            err("v2: za mało łodzi (%d grup boat* < 2)" % len(boats))
        else:
            pc = center_xz(pier)
            dists = [dist_xz(center_xz({n: g}), pc) for n, g in boats.items()]
            if min(dists) > 6:
                err("v2: żadna łódź nie cumuje przy pomoście (najbliższa %.1f m > 6)" % min(dists))
            if max(dists) < 10:
                err("v2: brak łodzi na otwartej wodzie (najdalsza %.1f m < 10 od pomostu)" % max(dists))
        if len(trees) < 6:
            err("v2: za mało drzew (%d grup tree* < 6)" % len(trees))
        if len(rocks) < 10:
            err("v2: za mało głazów (%d grup rock* < 10)" % len(rocks))
        if not paths:
            err("v2: brak ścieżki (grupy path*)")
        else:
            pv = verts_of(paths)
            d_pier = min(dist_xz((a[0], a[2]), (b[0], b[2]))
                         for a in pv for b in verts_of(pier))
            d_lh = min(dist_xz((a[0], a[2]), (b[0], b[2]))
                       for a in pv for b in lhv)
            if d_pier > 5:
                err("v2: ścieżka nie dochodzi do rejonu pomostu (%.1f m > 5)" % d_pier)
            if d_lh > 5:
                err("v2: ścieżka nie dochodzi do rejonu latarni (%.1f m > 5)" % d_lh)
            for i, v in enumerate(pv):
                if abs(v[1] - nearest_terrain_y(v[0], v[2])) > 0.5:
                    err("v2: ścieżka lewituje/zakopana względem terenu (np. %r)" % (v,))
                    break

        # domy parami różne (anty-kopiuj-wklej): wymiary AABB albo materiały
        sigs = {}
        for hname, g in sorted(houses.items()):
            hv = [verts[i] for i in g["verts"]]
            dims = tuple(round(max(c[a] for c in hv) - min(c[a] for c in hv), 1)
                         for a in (0, 1, 2))
            mats = frozenset(m.split("_")[-1] for m in g["mats"])
            sigs[hname] = (dims, mats)
        names_h = sorted(sigs)
        for i, a in enumerate(names_h):
            for b in names_h[i + 1:]:
                if sigs[a][0] == sigs[b][0] and sigs[a][1] == sigs[b][1]:
                    err("v2: %s i %s są identyczne (wymiary %s i te same materiały)"
                        % (a, b, sigs[a][0]))

        # pomost: styk z plażą i zasięg w morze
        land = [v for v in tverts if v[1] > 0.05]
        if land:
            pverts = verts_of(pier)
            d_land = [min(math.hypot(p[0] - t[0], p[2] - t[2]) for t in land)
                      for p in pverts]
            if min(d_land) > 2.0:
                err("v2: pomost nie styka się z lądem/plażą (najbliżej %.1f m > 2)" % min(d_land))
            if max(d_land) < 8.0:
                err("v2: pomost nie sięga >= 8 m w morze (max odległość od lądu %.1f m)" % max(d_land))
        else:
            err("v2: teren nie ma lądu (brak wierzchołków y > 0.05)")

    # ----- zaostrzenia v3 (aktywne od SCENE_VERSION >= 3): wyspa wg ART_DIRECTION -----
    if version >= 3:
        def gcent(group_map_or_name):
            gm = group_map_or_name if isinstance(group_map_or_name, dict) else {0: group_map_or_name}
            vs = verts_of(gm)
            return (sum(v[0] for v in vs) / len(vs), sum(v[2] for v in vs) / len(vs))

        def d2(a, b):
            return math.hypot(a[0] - b[0], a[1] - b[1])

        chapel = members("chapel")
        bridge = members("bridge")
        walls = members("wall")
        stairs = members("stair")
        barrels = members("barrel") or members("prop_barrel")
        crates = members("crate") or members("prop_crate")
        bushes = members("bush")

        # latarnia na najwyższym plateau
        lc = gcent(lighthouse)
        if nearest_terrain_y(*lc) < max(v[1] for v in tverts) - 1.0:
            err("v3: latarnia nie stoi na najwyższym plateau (teren pod nią %.1f, max %.1f)"
                % (nearest_terrain_y(*lc), max(v[1] for v in tverts)))

        # >= 9 domów, ciasno, >= 3 archetypy, nazwy house_<k>_<archetyp>
        if len(houses) < 9:
            err("v3: za mało domów (%d < 9)" % len(houses))
        cents = {n: gcent({n: g}) for n, g in houses.items()}
        for n, c in cents.items():
            others = [d2(c, c2) for n2, c2 in cents.items() if n2 != n]
            if others and min(others) > 12:
                err("v3: %s bez sąsiada w promieniu 12 m (najbliższy %.1f m)" % (n, min(others)))
        suffixes = {"two_story" if n.endswith("two_story") else n.split("_")[-1]
                    for n in houses}
        missing_arch = {"timber", "stone", "two_story"} - suffixes
        if missing_arch:
            err("v3: brak archetypów w nazwach grup domów (house_<k>_<archetyp>): %s"
                % ", ".join(sorted(missing_arch)))
        for n, g in sorted(houses.items()):
            arch = "two_story" if n.endswith("two_story") else n.split("_")[-1]
            mats_join = " ".join(g["mats"])
            hv = [verts[i] for i in g["verts"]]
            height = max(v[1] for v in hv) - min(v[1] for v in hv)
            if arch == "timber" and "beam" not in mats_join and "timber" not in mats_join:
                err("v3: %s bez belek muru pruskiego (materiał 'beam*'/'timber*')" % n)
            if arch == "stone" and "stone" not in mats_join:
                err("v3: %s bez kamienia (materiał 'stone*')" % n)
            if arch == "two_story" and height < 5.0:
                err("v3: %s za niski jak na dwukondygnacyjny (%.1f < 5 m)" % (n, height))

        # kapliczka na turni rozłącznej z masywem, połączonej mostkiem
        if not chapel:
            err("v3: brak kapliczki (grupy chapel*)")
        if not bridge:
            err("v3: brak mostka linowego (grupy bridge*)")
        if chapel and houses:
            cc = gcent(chapel)
            ch_ground = nearest_terrain_y(*cc)
            if ch_ground < 3.0:
                err("v3: turnia kapliczki za niska (teren %.1f < 3 m)" % ch_ground)
            dists = {n: d2(cc, c) for n, c in cents.items()}
            nearest_house = min(dists, key=dists.get) if dists else None
            if nearest_house and dists[nearest_house] < 6.0:
                err("v3: kapliczka za blisko zabudowy (%.1f m < 6 — ma stać na osobnej turni)"
                    % dists[nearest_house])
            if nearest_house:
                hc = cents[nearest_house]
                hy = nearest_terrain_y(*hc)
                saddle = min(nearest_terrain_y(cc[0] + (hc[0] - cc[0]) * t / 20.0,
                                               cc[1] + (hc[1] - cc[1]) * t / 20.0)
                             for t in range(21))
                if saddle > min(ch_ground, hy) - 1.5:
                    err("v3: turnia nie jest rozłączna z masywem (brak przełęczy: siodło %.1f "
                        "vs końce %.1f/%.1f, wymagane >= 1.5 m niżej)" % (saddle, ch_ground, hy))
        if chapel and bridge:
            bv = [(v[0], v[2]) for v in verts_of(bridge)]
            cv = [(v[0], v[2]) for v in verts_of(chapel)]
            d_ch = min(d2(a, b) for a in bv for b in cv)
            if d_ch > 5.0:
                err("v3: mostek nie dochodzi do turni kapliczki (%.1f m > 5)" % d_ch)
            vil = [(verts[i][0], verts[i][2]) for g in houses.values() for i in g["verts"]] + \
                  [(verts[i][0], verts[i][2]) for g in walls.values() for i in g["verts"]]
            if vil:
                d_vil = min(d2(a, b) for a in bv for b in vil)
                if d_vil > 6.0:
                    err("v3: mostek nie dochodzi do poziomu wioski (%.1f m > 6)" % d_vil)

        # mur oporowy i schody
        if len(walls) < 2:
            err("v3: za mało segmentów muru oporowego (%d grup wall* < 2)" % len(walls))
        if not stairs:
            err("v3: brak schodów między tarasami (grupy stair*)")

        # pomosty i rekwizyty
        pier_groups = members("pier")
        if len(pier_groups) < 2:
            err("v3: za mało segmentów pomostów (%d grup pier* < 2)" % len(pier_groups))
        pier_xz = [(v[0], v[2]) for v in verts_of(pier)]
        quay = [(v[0], v[2]) for v in tverts if 0.0 <= v[1] <= 1.0]
        if len(barrels) < 4:
            err("v3: za mało beczek (%d grup barrel* < 4)" % len(barrels))
        if len(crates) < 3:
            err("v3: za mało skrzyń (%d grup crate* < 3)" % len(crates))
        for n, g in sorted({**barrels, **crates}.items()):
            c = gcent({n: g})
            d_pier = min((d2(c, p) for p in pier_xz), default=1e9)
            d_quay = min((d2(c, q) for q in quay), default=1e9)
            if d_pier > 5.0 and d_quay > 3.0:
                err("v3: %s nie stoi na pomoście ani nabrzeżu (pomost %.1f m, nabrzeże %.1f m)"
                    % (n, d_pier, d_quay))

        # krzewy między zabudową
        if len(bushes) < 8:
            err("v3: za mało krzewów (%d grup bush* < 8)" % len(bushes))
        for n, g in sorted(bushes.items()):
            c = gcent({n: g})
            if cents and min(d2(c, hc) for hc in cents.values()) > 10:
                err("v3: %s rośnie z dala od zabudowy (> 10 m od najbliższego domu)" % n)

        # zatoczka: łódka na piasku (nie w wodzie)
        beach_boats = [n for n, g in boats.items()
                       if nearest_terrain_y(*gcent({n: g})) > 0.05]
        if not beach_boats:
            err("v3: brak łódki na plaży zatoczki (boat* nad lądem; w wodzie to nie plaża)")

        # pierścień skał w wodzie poza obrysem wyspy
        wet_rocks = [n for n, g in rocks.items()
                     if nearest_terrain_y(*gcent({n: g})) < -0.2]
        if len(wet_rocks) < 8:
            err("v3: za mało głazów w wodzie wokół wyspy (%d < 8)" % len(wet_rocks))

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
