#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dowód bloków rdzenia bpy (M4): build solo -> eksport, DETERMINIZM (dwa
buildy = identyczny OBJ) + asercja na WYEKSPORTOWANEJ geometrii (z known-bad,
żeby checker nie był ślepy).

Rozszerzalny per typ: PART_CHECKS[typ] = funkcja(verts_grup) -> (ok, msgs).
Użycie: python scripts/test_bpy_parts.py <typ>   (np. water, house, wall, chapel)
"""

import glob
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def locate_blender():
    env = os.environ.get("BLENDER_BIN")
    if env and Path(env).exists():
        return env
    p = shutil.which("blender")
    if p:
        return p
    for pat in (r"C:\Program Files\Blender Foundation\*\blender.exe",):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def digest(path):
    h = hashlib.sha256()
    for p in (path, path.with_suffix(".mtl")):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line.startswith("#") and not line.startswith("mtllib"):
                    h.update(line.encode("utf-8") + b"\n")
    return h.hexdigest()


def parse_groups(path):
    """OBJ -> {nazwa_grupy: {'verts': [(x,y,z)], 'faces': [(mat,(idx...))]}}
    z indeksami LOKALNYMI per grupa (jak kontrakt części)."""
    gverts, groups, cur, cur_mtl, base = [], {}, None, None, 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        p = raw.split()
        if not p:
            continue
        if p[0] == "v":
            gverts.append((float(p[1]), float(p[2]), float(p[3])))
        elif p[0] in ("o", "g"):
            cur = p[1]
            groups.setdefault(cur, {"verts": [], "faces": [], "_first": len(gverts)})
        elif p[0] == "usemtl":
            cur_mtl = p[1]
        elif p[0] == "f" and cur is not None:
            idx = [int(t.split("/")[0]) - 1 for t in p[1:]]
            groups[cur]["faces"].append((cur_mtl, tuple(idx)))
    # przypisz wierzchołki do grup wg zakresu indeksów (kolejność eksportu)
    for name, g in groups.items():
        used = {i for _m, idx in g["faces"] for i in idx}
        g["verts_global"] = {i: gverts[i] for i in used}
    return groups, gverts


# --------------------------------------------------------------------------- #
# Asercje per typ na wyeksportowanej geometrii
# --------------------------------------------------------------------------- #

def check_water(groups, gverts):
    msgs = []
    wv = [gverts[i] for n, g in groups.items() if n.startswith("water")
          for i in {k for _m, idx in g["faces"] for k in idx}]
    if not wv:
        return False, ["brak grupy water w eksporcie"]
    off = max(abs(v[1]) for v in wv)
    if off > 1e-3:
        msgs.append("tafla nie leży na y=0 (max |y| = %.4f > 0.001)" % off)
    if len(wv) < 9:
        msgs.append("tafla zbyt uboga (%d wierzch.)" % len(wv))
    return (not msgs), msgs


def check_wall(groups, gverts):
    msgs = []
    wall_faces = sum(len(g["faces"]) for n, g in groups.items() if n.startswith("wall"))
    if wall_faces < 8:
        msgs.append("mur: za mało ścianek 'wall*' (%d < 8)" % wall_faces)
    levels = set()
    for n, g in groups.items():
        if n.startswith("stair"):
            for _m, idx in g["faces"]:
                cy = sum(gverts[i][1] for i in idx) / len(idx)
                levels.add(round(cy, 1))
    if len(levels) < 6:
        msgs.append("schody: < 6 poziomów stopni (%d) — schody nie pokonują różnicy" % len(levels))
    return (not msgs), msgs


def check_chapel(groups, gverts):
    msgs = []
    ch = {n: g for n, g in groups.items() if n.startswith("chapel")}
    if not ch:
        return False, ["brak grupy chapel w eksporcie"]
    all_y, cross_y, roof_n = [], [], 0
    for g in ch.values():
        for mat, idx in g["faces"]:
            ys = [gverts[i][1] for i in idx]
            all_y += ys
            if mat and "cross" in mat:
                cross_y += ys
            if mat and "roof" in mat:
                roof_n += 1
    if roof_n < 2:
        msgs.append("kapliczka: brak dachu (roof*, %d ścianek)" % roof_n)
    if not cross_y:
        msgs.append("kapliczka: brak sygnaturki/krzyża (cross*)")
    elif max(cross_y) < max(all_y) - 1e-4:
        msgs.append("kapliczka: krzyż nie jest najwyższym punktem (%.2f < %.2f)"
                    % (max(cross_y), max(all_y)))
    return (not msgs), msgs


PART_CHECKS = {
    "water": check_water,
    "wall": check_wall,
    "chapel": check_chapel,
}

BAD_PERTURB = {
    # known-bad: jak zepsuć eksport, by asercja PADŁA (czerwony dowód)
    "water": lambda verts: [(x, y + 0.5, z) for (x, y, z) in verts],
    "wall": lambda verts: [(x, 0.0, z) for (x, y, z) in verts],   # spłaszcz -> brak poziomów stopni
    # podnieś wierzchołek 0 (ściana) ponad krzyż -> krzyż przestaje być najwyższy
    "chapel": lambda verts: [(v[0], v[1] + 20.0 if i == 0 else v[1], v[2])
                             for i, v in enumerate(verts)],
}


def build_solo(blender, part, params=None, suffix=""):
    builder = ROOT / "parts" / (part + "_bpy.py")
    out = ROOT / "out" / (part + suffix + ".obj")
    args = [blender, "--background", "--python", str(ROOT / "scripts" / "bpy_build.py"),
            "--", str(builder), str(out), "0"]
    for k, v in (params or {}).items():
        args.append("%s=%s" % (k, v))
    p = subprocess.run(args, capture_output=True, text=True, timeout=300)
    o = (p.stdout or "") + (p.stderr or "")
    return any(l.startswith("OK:") for l in o.splitlines()), o, out


def bbox(verts):
    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]; zs = [v[2] for v in verts]
    return (round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2), round(max(zs) - min(zs), 2))


def proof_house(blender):
    """House: 3 archetypy GEOMETRYCZNIE różne + determinizm per archetyp."""
    problems = []
    sigs = {}
    for a in ("timber", "stone", "two_story"):
        ok1, o1, out = build_solo(blender, "house", {"archetype": a}, "_" + a)
        if not ok1:
            return False, ["bpy_build house %s:\n%s" % (a, o1[-400:])]
        d1 = digest(out)
        _, gverts = parse_groups(out)
        ok2, _, _ = build_solo(blender, "house", {"archetype": a}, "_" + a)
        if digest(out) != d1:
            problems.append("NIEDETERMINIZM house[%s]" % a)
        sigs[a] = (len(gverts), bbox(gverts))
    pairs = [("timber", "stone"), ("timber", "two_story"), ("stone", "two_story")]
    for x, y in pairs:
        if sigs[x] == sigs[y]:
            problems.append("archetypy %s i %s geometrycznie nieodróżnialne (%s)"
                            % (x, y, sigs[x]))
    if not problems:
        print("  archetypy (wierzch., bbox): " + "; ".join("%s=%s" % (a, sigs[a]) for a in sigs))
    return (not problems), problems


CUSTOM = {"house": proof_house}


def main(part):
    if part not in PART_CHECKS and part not in CUSTOM:
        print("FAIL: brak asercji dla typu %r (dodaj do PART_CHECKS/CUSTOM)" % part)
        return 1
    if not (ROOT / "parts" / (part + "_bpy.py")).exists():
        print("OK: parts/%s_bpy.py jeszcze nie istnieje (zielony baseline)." % part)
        return 0
    blender = locate_blender()
    if not blender:
        print("FAIL: nie znaleziono Blendera (BLENDER_BIN)")
        return 1

    if part in CUSTOM:
        ok, problems = CUSTOM[part](blender)
        if problems:
            print("FAIL — blok %s (%d problemów):" % (part, len(problems)))
            for p in problems:
                print("  - " + p)
            return 1
        print("OK: %s — 3 archetypy różne, każdy deterministyczny." % part)
        return 0

    ok1, o1, out = build_solo(blender, part)
    if not ok1:
        print("FAIL: bpy_build %s #1:\n%s" % (part, o1[-800:]))
        return 1
    d1 = digest(out)
    groups, gverts = parse_groups(out)

    ok2, o2, _ = build_solo(blender, part)
    if not ok2:
        print("FAIL: bpy_build %s #2:\n%s" % (part, o2[-800:]))
        return 1
    d2 = digest(out)

    problems = []
    if d1 != d2:
        problems.append("NIEDETERMINIZM %s: %s != %s" % (part, d1[:12], d2[:12]))
    good_ok, good_msgs = PART_CHECKS[part](groups, gverts)
    problems += good_msgs

    # known-bad: zaburz eksport i potwierdź, że asercja pada
    if part in BAD_PERTURB:
        bad_gverts = BAD_PERTURB[part](gverts)
        bad_ok, _ = PART_CHECKS[part](groups, bad_gverts)
        if bad_ok:
            problems.append("known-bad %s przeszło asercję (checker ślepy)" % part)

    if problems:
        print("FAIL — blok %s (%d problemów):" % (part, len(problems)))
        for p in problems:
            print("  - " + p)
        return 1
    print("OK: %s deterministyczny (hash %s); asercja na eksporcie zielona, "
          "known-bad odrzucony." % (part, d1[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "water"))
