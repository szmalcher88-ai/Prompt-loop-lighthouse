#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Weryfikator latarni — PRZEPIĘTY na bpy (M3-migracja).

Tryby:
  * brak parts/lighthouse_bpy.py            -> exit 0 (zielony baseline).
  * python check_lighthouse.py <obj>        -> waliduj wskazany OBJ (fixtury),
                                               bez budowania, bez determinizmu.
  * python check_lighthouse.py (bez args)   -> zbuduj latarnię w bpy
      (blender --background --python scripts/bpy_build.py), eksport do
      out/lighthouse.obj Z ZAAPLIKOWANYMI modyfikatorami, TEST DETERMINIZMU
      (dwa eksporty = identyczny OBJ — bramka wyjścia M3) + asercje geometryczne.

Asercje formy zachowane z czasów ręcznego OBJ (proporcje, części, zwężanie,
materiały) — bevel/subdivision zmieniają LICZBĘ wierzchołków, nie kształt;
progi liczbowe pozostają sensowne (subsurf tylko dodaje geometrię).

Ten plik jest chroniony (protected_paths) — agent ma go czytać, nie zmieniać.
"""

import glob
import hashlib
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILDER = ROOT / "parts" / "lighthouse_bpy.py"
BPY_BUILD = ROOT / "scripts" / "bpy_build.py"
OBJ = ROOT / "out" / "lighthouse.obj"

REQUIRED_GROUPS = ["base", "tower", "gallery", "lantern", "roof", "door"]

errors = []


def err(msg):
    errors.append(msg)


def locate_blender():
    env = os.environ.get("BLENDER_BIN")
    if env and Path(env).exists():
        return env
    on_path = shutil.which("blender")
    if on_path:
        return on_path
    for pat in (r"C:\Program Files\Blender Foundation\*\blender.exe",
                r"C:\Program Files (x86)\Blender Foundation\*\blender.exe"):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def run_build(blender, out_obj):
    p = subprocess.run([blender, "--background", "--python", str(BPY_BUILD), "--",
                        str(BUILDER), str(out_obj)],
                       capture_output=True, text=True, timeout=300)
    out = (p.stdout or "") + (p.stderr or "")
    ok = any(line.startswith("OK:") for line in out.splitlines())
    return ok, out


def validate_obj(obj_path):
    """Asercje geometryczne (+ materiały, gdy obok jest .mtl). Zwraca exit code."""
    mtl_path = obj_path.with_suffix(".mtl")
    verts = []
    groups = {}
    current = None
    current_mtl = None
    mtllib = None
    usemtl_all = set()
    tower_faces = []          # (center_y, material) — do asercji pasów
    for raw in obj_path.read_text(encoding="utf-8").splitlines():
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
            if all(0 <= i < len(verts) for i in idxs):
                if current is None:
                    err("face poza grupą `o`: %r" % raw)
                else:
                    groups[current]["faces"] += 1
                    groups[current]["verts"].update(idxs)
                    if current == "tower":
                        cy = sum(verts[i][1] for i in idxs) / len(idxs)
                        tower_faces.append((cy, current_mtl))
            else:
                err("face wskazuje nieistniejący wierzchołek: %r" % raw)

    for name in REQUIRED_GROUPS:
        if name not in groups:
            err("brak wymaganej grupy `o %s`" % name)
        elif groups[name]["faces"] < 4:
            err("grupa %s ma za mało ścianek (%d < 4)" % (name, groups[name]["faces"]))
    if len(verts) < 150:
        err("za mało wierzchołków łącznie (%d < 150)" % len(verts))
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

    all_y = [v[1] for v in verts]
    height = max(all_y) - min(all_y)
    if not (4.0 <= height <= 200.0):
        err("całkowita wysokość %.2f poza zakresem [4, 200]" % height)

    order = ["base", "tower", "gallery", "lantern", "roof"]
    cys = {n: centroid_y(n) for n in order + ["door"]}
    for low, high in zip(order, order[1:]):
        if not cys[low] < cys[high]:
            err("centroid %s (%.2f) powinien leżeć niżej niż %s (%.2f)"
                % (low, cys[low], high, cys[high]))
    if cys["door"] >= cys["tower"]:
        err("door powinny być w dolnej części wieży")
    if min(ys("base")) - min(all_y) > 1e-6 + 0.2 * height:
        err("base nie sięga dołu modelu")
    if max(all_y) - max(ys("roof")) > 1e-6:
        err("najwyższy punkt modelu powinien należeć do roof")

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

    if mtl_path.exists():
        if mtllib != mtl_path.name:
            err("OBJ nie podpina materiałów: oczekiwano `mtllib %s`, jest %r"
                % (mtl_path.name, mtllib))
        if len(usemtl_all) < 3:
            err("za mało materiałów w użyciu (%d < 3 usemtl)" % len(usemtl_all))
        if len(groups["tower"]["usemtl"]) < 2:
            err("tower powinna używać >=2 materiałów (pasy), ma %d"
                % len(groups["tower"]["usemtl"]))
        # Asercja PASÓW (spłata długu M3: '>=2 materiały' przechodziło trywialnie
        # czapkami vs boki, bez realnych poziomych pasów). Binujemy ścianki wieży
        # po wysokości, bierzemy dominujący materiał per bin i liczymy naprzemienne
        # zmiany między biel/czerwień. Jednolita wieża => 0 zmian => FAIL.
        stripe_mats = {m for m in usemtl_all if "white" in m or "red" in m or "stripe" in m}
        band_faces = [(cy, m) for cy, m in tower_faces if m in stripe_mats]
        if len(band_faces) < 12:
            err("za mało ścianek pasowych na wieży (%d) — brak materiałów pasów?"
                % len(band_faces))
        else:
            ys = [cy for cy, _ in band_faces]
            y_lo, y_hi = min(ys), max(ys)
            nbins = 12
            bins = [{} for _ in range(nbins)]
            for cy, m in band_faces:
                b = min(nbins - 1, int((cy - y_lo) / max(y_hi - y_lo, 1e-9) * nbins))
                bins[b][m] = bins[b].get(m, 0) + 1
            dom = [max(b, key=b.get) for b in bins if b]
            alternations = sum(1 for a, c in zip(dom, dom[1:]) if a != c)
            if alternations < 4:
                err("wieża nie ma naprzemiennych poziomych pasów biel/czerwień "
                    "(%d zmian materiału po wysokości < 4 — wieża niemal jednolita)"
                    % alternations)
        mtl_text = mtl_path.read_text(encoding="utf-8")
        newmtls = {l.split()[1] for l in mtl_text.splitlines()
                   if l.startswith("newmtl") and len(l.split()) > 1}
        if len(newmtls) < 3:
            err("MTL definiuje za mało materiałów (%d < 3 newmtl)" % len(newmtls))
        if "Kd " not in mtl_text:
            err("MTL nie definiuje kolorów (brak linii Kd)")
        missing = usemtl_all - newmtls
        if missing:
            err("usemtl bez definicji w MTL: %s" % ", ".join(sorted(missing)))

    return report()


def report():
    if errors:
        print("FAIL — weryfikacja latarni (%d problemów):" % len(errors))
        for e in errors:
            print("  - " + e)
        return 1
    print("OK: latarnia przechodzi wszystkie kontrole.")
    return 0


def _digest(obj_path):
    """Hash geometrii+materiałów OBJ. Pomijamy linie komentarzy `#` (wersja
    Blendera) i `mtllib` (referencja do NAZWY pliku MTL, nie do treści modelu)
    — istotny jest kształt i materiały, nie nazwa pliku wyjściowego."""
    h = hashlib.sha256()
    for path in (obj_path, obj_path.with_suffix(".mtl")):
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.startswith("#") and not line.startswith("mtllib"):
                    h.update(line.encode("utf-8"))
                    h.update(b"\n")
    return h.hexdigest()


def main():
    # tryb fixtury: waliduj wskazany OBJ
    if len(sys.argv) > 1:
        obj = Path(sys.argv[1])
        if not obj.exists():
            print("FAIL: %s nie istnieje" % obj)
            return 1
        return validate_obj(obj)

    if not BUILDER.exists():
        print("OK: parts/lighthouse_bpy.py jeszcze nie istnieje (zielony baseline).")
        return 0

    blender = locate_blender()
    if not blender:
        print("FAIL: nie znaleziono Blendera (ustaw BLENDER_BIN albo dodaj do PATH)")
        return 1

    # TEST DETERMINIZMU (bramka wyjścia M3): dwa build+export do TEJ SAMEJ
    # ścieżki -> identyczny OBJ (porównanie hasha treści, bez nazwy pliku MTL).
    ok1, out1 = run_build(blender, OBJ)
    if not ok1:
        print("FAIL: bpy_build #1 nie powiódł się\n%s" % out1[-800:])
        return 1
    digest1 = _digest(OBJ)

    ok2, out2 = run_build(blender, OBJ)   # nadpisuje — ta sama ścieżka, ten sam mtllib
    if not ok2:
        print("FAIL: bpy_build #2 (determinizm) nie powiódł się\n%s" % out2[-800:])
        return 1
    digest2 = _digest(OBJ)
    if digest1 != digest2:
        print("FAIL: NIEDETERMINIZM eksportu — dwa build+export dają różny OBJ "
              "(%s != %s). Znajdź źródło losowości (seed!) przed uznaniem migracji."
              % (digest1[:12], digest2[:12]))
        return 1

    print("OK: determinizm eksportu potwierdzony (hash %s)" % digest1[:12])
    return validate_obj(OBJ)


if __name__ == "__main__":
    sys.exit(main())
