#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Niezależny weryfikator modelu 3D latarni morskiej (sygnał prawdy pętli).

Kontrakt:
  * Jeśli lighthouse.py nie istnieje -> exit 0 (zielony baseline przed startem).
  * Jeśli istnieje: `python lighthouse.py` musi zapisać out/lighthouse.obj
    (Y-up, jednostki ~metry) z grupami `o`: base, tower, gallery, lantern,
    roof, door i przejść wszystkie asercje geometryczne poniżej.
  * Sekcja materiałów: jeśli generator tworzy out/lighthouse.mtl, OBJ musi
    go podpinać (mtllib), używać >=3 materiałów (usemtl), a grupa tower
    >=2 naprzemiennych materiałów (pasy latarni).

Ten plik jest chroniony (protected_paths) — agent ma go czytać, nie zmieniać.
"""

import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATOR = ROOT / "lighthouse.py"
OBJ = ROOT / "out" / "lighthouse.obj"
MTL = ROOT / "out" / "lighthouse.mtl"

REQUIRED_GROUPS = ["base", "tower", "gallery", "lantern", "roof", "door"]

errors = []


def err(msg):
    errors.append(msg)


def main():
    if not GENERATOR.exists():
        print("OK: lighthouse.py jeszcze nie istnieje (zielony baseline).")
        return 0

    if OBJ.exists():
        OBJ.unlink()
    if MTL.exists():
        MTL.unlink()

    proc = subprocess.run(
        [sys.executable, str(GENERATOR)], cwd=str(ROOT),
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        print("FAIL: `python lighthouse.py` zakończył się kodem %d\n%s%s"
              % (proc.returncode, proc.stdout, proc.stderr))
        return 1
    if not OBJ.exists():
        print("FAIL: generator nie utworzył out/lighthouse.obj")
        return 1

    verts = []            # lista (x, y, z)
    groups = {}           # nazwa -> {"faces": int, "verts": set(idx), "usemtl": set()}
    current = None
    current_mtl = None
    mtllib = None
    usemtl_all = set()

    for raw in OBJ.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if not parts:
            continue
        tag = parts[0]
        if tag == "v":
            verts.append(tuple(float(c) for c in parts[1:4]))
        elif tag in ("o", "g"):
            current = parts[1] if len(parts) > 1 else ""
            groups.setdefault(current, {"faces": 0, "verts": set(), "usemtl": set()})
        elif tag == "mtllib":
            mtllib = parts[1] if len(parts) > 1 else ""
        elif tag == "usemtl":
            current_mtl = parts[1] if len(parts) > 1 else ""
            usemtl_all.add(current_mtl)
            if current is not None:
                groups[current]["usemtl"].add(current_mtl)
        elif tag == "f":
            idxs = []
            for tok in parts[1:]:
                i = int(tok.split("/")[0])
                idxs.append(i - 1 if i > 0 else len(verts) + i)
            if len(idxs) < 3:
                err("face z mniej niż 3 wierzchołkami: %r" % raw)
                continue
            for i in idxs:
                if not (0 <= i < len(verts)):
                    err("face wskazuje nieistniejący wierzchołek: %r" % raw)
                    break
            else:
                if current is None:
                    err("face poza jakąkolwiek grupą `o`: %r" % raw)
                else:
                    groups[current]["faces"] += 1
                    groups[current]["verts"].update(idxs)

    # --- struktura ---
    for name in REQUIRED_GROUPS:
        if name not in groups:
            err("brak wymaganej grupy `o %s`" % name)
        elif groups[name]["faces"] < 4:
            err("grupa %s ma za mało ścianek (%d < 4)" % (name, groups[name]["faces"]))
    if len(verts) < 150:
        err("za mało wierzchołków łącznie (%d < 150) — model zbyt uproszczony" % len(verts))
    total_faces = sum(g["faces"] for g in groups.values())
    if total_faces < 150:
        err("za mało ścianek łącznie (%d < 150)" % total_faces)
    if errors:
        return report()

    def ys(name):
        return [verts[i][1] for i in groups[name]["verts"]]

    def centroid_y(name):
        v = ys(name)
        return sum(v) / len(v)

    # --- wymiary i orientacja (Y-up) ---
    all_y = [v[1] for v in verts]
    height = max(all_y) - min(all_y)
    if not (4.0 <= height <= 200.0):
        err("całkowita wysokość %.2f poza zakresem [4, 200] (Y-up, metry)" % height)

    order = ["base", "tower", "gallery", "lantern", "roof"]
    cys = {n: centroid_y(n) for n in order + ["door"]}
    for low, high in zip(order, order[1:]):
        if not cys[low] < cys[high]:
            err("centroid %s (%.2f) powinien leżeć niżej niż %s (%.2f)"
                % (low, cys[low], high, cys[high]))
    if cys["door"] >= cys["tower"]:
        err("door powinny być w dolnej części wieży (centroid door < centroid tower)")
    if min(ys("base")) - min(all_y) > 1e-6 + 0.2 * height:
        err("base nie sięga dołu modelu")
    if max(all_y) - max(ys("roof")) > 1e-6:
        err("najwyższy punkt modelu powinien należeć do roof")

    # --- zwężanie wieży ---
    tys = ys("tower")
    t_lo, t_hi = min(tys), max(tys)
    if t_hi - t_lo < 0.4 * height:
        err("tower zbyt niska (%.2f) względem całości (%.2f)" % (t_hi - t_lo, height))

    def radius_at(frac_lo, frac_hi):
        rs = [math.hypot(verts[i][0], verts[i][2])
              for i in groups["tower"]["verts"]
              if frac_lo <= (verts[i][1] - t_lo) / max(t_hi - t_lo, 1e-9) <= frac_hi]
        return max(rs) if rs else 0.0

    r_bottom, r_top = radius_at(0.0, 0.25), radius_at(0.75, 1.0)
    if not r_top < r_bottom * 0.95:
        err("tower nie zwęża się ku górze (r_dol=%.3f, r_gora=%.3f)" % (r_bottom, r_top))

    # --- materiały (wymagane dopiero, gdy generator tworzy MTL) ---
    if MTL.exists():
        if mtllib != MTL.name:
            err("OBJ nie podpina materiałów: oczekiwano `mtllib %s`" % MTL.name)
        if len(usemtl_all) < 3:
            err("za mało materiałów w użyciu (%d < 3 usemtl)" % len(usemtl_all))
        if len(groups["tower"]["usemtl"]) < 2:
            err("tower powinna używać >=2 materiałów (pasy), ma %d"
                % len(groups["tower"]["usemtl"]))
        mtl_text = MTL.read_text(encoding="utf-8")
        newmtls = [l.split()[1] for l in mtl_text.splitlines()
                   if l.startswith("newmtl") and len(l.split()) > 1]
        if len(set(newmtls)) < 3:
            err("lighthouse.mtl definiuje za mało materiałów (%d < 3 newmtl)" % len(set(newmtls)))
        if "Kd " not in mtl_text:
            err("lighthouse.mtl nie definiuje kolorów (brak linii Kd)")
        missing = usemtl_all - set(newmtls)
        if missing:
            err("usemtl bez definicji w MTL: %s" % ", ".join(sorted(missing)))

    return report()


def report():
    if errors:
        print("FAIL — weryfikacja modelu latarni (%d problemów):" % len(errors))
        for e in errors:
            print("  - " + e)
        return 1
    print("OK: out/lighthouse.obj przechodzi wszystkie kontrole.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
