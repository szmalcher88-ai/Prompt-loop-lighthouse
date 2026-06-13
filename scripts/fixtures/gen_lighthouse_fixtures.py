# -*- coding: utf-8 -*-
"""Generator fixture known-bad dla check_lighthouse (bpy). Post-processuje
known-good (scripts/fixtures/lighthouse_good.obj, wyeksportowany z
lighthouse_bpy_ref.py przez bpy_build) w warianty łamiące pojedyncze asercje:
  * lighthouse_bad_notaper.obj — wieża cylindryczna (brak zwężenia ku górze),
  * lighthouse_bad_short.obj   — cała latarnia spłaszczona (wysokość < 4 m).
Bad warianty NIE mają MTL (mtllib usunięty) — test sprawdza GEOMETRIĘ.
"""

import math
from pathlib import Path

FX = Path(__file__).resolve().parent
GOOD = FX / "lighthouse_good.obj"


def parse(path):
    verts, faces_groups, current = [], [], None
    lines = path.read_text(encoding="utf-8").splitlines()
    tower_idx = set()
    for raw in lines:
        p = raw.split()
        if not p:
            continue
        if p[0] == "v":
            verts.append([float(c) for c in p[1:4]])
        elif p[0] in ("o", "g"):
            current = p[1] if len(p) > 1 else ""
        elif p[0] == "f" and current == "tower":
            for tok in p[1:]:
                i = int(tok.split("/")[0])
                tower_idx.add(i - 1 if i > 0 else len(verts) + i)
    return verts, tower_idx, lines


def write(path, lines, verts):
    out = []
    vi = 0
    for raw in lines:
        if raw.startswith("mtllib"):
            continue                      # bad bez MTL -> test geometrii
        if raw.startswith("v "):
            x, y, z = verts[vi]
            out.append("v %.6f %.6f %.6f" % (x, y, z))
            vi += 1
        else:
            out.append(raw)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    verts, tower_idx, lines = parse(GOOD)

    # --- bad_notaper: ujednolić promień wieży = promień dna (cylinder) ---
    v1 = [list(v) for v in verts]
    tys = [v1[i][1] for i in tower_idx]
    t_lo, t_hi = min(tys), max(tys)
    r_bottom = max(math.hypot(v1[i][0], v1[i][2]) for i in tower_idx
                   if (v1[i][1] - t_lo) / (t_hi - t_lo) <= 0.25)
    for i in tower_idx:
        r = math.hypot(v1[i][0], v1[i][2])
        if r > 1e-6:
            v1[i][0] *= r_bottom / r
            v1[i][2] *= r_bottom / r
    write(FX / "lighthouse_bad_notaper.obj", lines, v1)

    # --- bad_short: spłaszcz całość (wysokość < 4 m) ---
    v2 = [[v[0], v[1] * 0.12, v[2]] for v in verts]
    write(FX / "lighthouse_bad_short.obj", lines, v2)

    # --- bad_uniform: wieża jednolita (wszystkie pasy -> jeden materiał) ---
    # zachowuje MTL (by dojść do asercji pasów); kolaps usemtl w bloku `o tower`.
    mtl_src = GOOD.with_suffix(".mtl")
    uobj = FX / "lighthouse_bad_uniform.obj"
    (FX / "lighthouse_bad_uniform.mtl").write_text(mtl_src.read_text(encoding="utf-8"),
                                                   encoding="utf-8")
    cur = None
    out = []
    for raw in lines:
        p = raw.split()
        if p and p[0] in ("o", "g"):
            cur = p[1] if len(p) > 1 else ""
        if raw.startswith("mtllib"):
            out.append("mtllib lighthouse_bad_uniform.mtl")
        elif cur == "tower" and raw.startswith("usemtl"):
            out.append("usemtl stripe_white")        # cała wieża jednym materiałem
        else:
            out.append(raw)
    uobj.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("fixtures bad: notaper + short + uniform")


if __name__ == "__main__":
    main()
