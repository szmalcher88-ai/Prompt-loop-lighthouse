#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render-test sceny — deterministyczne rendery PNG + skromne kontrole pikselowe.

Semantyka geometrii jest w check_scene; tu sprawdzamy tylko, że scena
w ogóle się renderuje i materiały weszły, oraz produkujemy podgląd dla
człowieka (out/renders/*.png — materiał na bramę milestone'u).

Kontrakt warunkowy: scene.py nie istnieje -> exit 0 (zielony baseline).
Tryb testowy: python scripts/render_test.py <ścieżka.obj> [katalog_wyjściowy]

Kontrole twarde:
  * trzy STAŁE kamery (panorama od morza / izometryczna / profil sylwetki),
    stała rozdzielczość 800x600 @ dpi 100,
  * obraz niepusty: > 0.5% pikseli różnych od tła,
  * materiały weszły: >= 10 unikalnych kolorów na renderze,
  * determinizm: dwa rendery tej samej kamery dają IDENTYCZNE bajty PNG.

matplotlib (Agg) jest dozwolony WYŁĄCZNIE w narzędziach weryfikacji.
"""

import io
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCENE = ROOT / "scene.py"

CAMERAS = [
    ("panorama", 8, -90),   # od strony morza
    ("iso", 30, 45),        # izometryczny
    ("profile", 0, 0),      # profil sylwetki
]
FIGSIZE, DPI = (8, 6), 100
BACKGROUND = (1.0, 1.0, 1.0)


def parse(obj_path):
    """OBJ + MTL -> (lista trójkątów, lista kolorów RGB per trójkąt)."""
    verts, tris, cols = [], [], []
    colors = {}
    current_rgb = (0.6, 0.6, 0.6)
    mtl_colors = {}
    for raw in obj_path.read_text(encoding="utf-8").splitlines():
        p = raw.split()
        if not p:
            continue
        if p[0] == "mtllib":
            mtl = obj_path.parent / p[1]
            if mtl.exists():
                name = None
                for line in mtl.read_text(encoding="utf-8").splitlines():
                    q = line.split()
                    if not q:
                        continue
                    if q[0] == "newmtl":
                        name = q[1]
                    elif q[0] == "Kd" and name:
                        mtl_colors[name] = tuple(float(c) for c in q[1:4])
        elif p[0] == "v":
            verts.append(tuple(float(c) for c in p[1:4]))
        elif p[0] == "usemtl":
            current_rgb = mtl_colors.get(p[1], current_rgb)
        elif p[0] == "f":
            idxs = []
            for tok in p[1:]:
                i = int(tok.split("/")[0])
                idxs.append(i - 1 if i > 0 else len(verts) + i)
            for a, b in zip(idxs[1:], idxs[2:]):  # fan
                tris.append((verts[idxs[0]], verts[a], verts[b]))
                cols.append(current_rgb)
    return tris, cols


def render_bytes(tris, cols, elev, azim):
    fig = plt.figure(figsize=FIGSIZE, dpi=DPI)
    ax = fig.add_subplot(projection="3d")
    fig.patch.set_facecolor(BACKGROUND)
    ax.set_facecolor(BACKGROUND)
    if tris:
        # Y-up -> matplotlib z-up: (x, y, z) -> (x, z, y)
        polys = [[(x, z, y) for (x, y, z) in t] for t in tris]
        # deterministyczne cieniowanie Lamberta (stałe źródło światła)
        light = np.array([0.5, -0.3, 0.8])
        light = light / np.linalg.norm(light)
        shaded = []
        for t, c in zip(polys, cols):
            a, b, d = (np.array(p) for p in t[:3])
            n = np.cross(b - a, d - a)
            ln = np.linalg.norm(n)
            k = 0.55 + 0.45 * abs(float(np.dot(n / ln, light))) if ln > 0 else 0.55
            shaded.append(tuple(min(1.0, ch * k) for ch in c))
        pc = Poly3DCollection(polys, facecolors=shaded, edgecolors="none")
        ax.add_collection3d(pc)
        pts = np.array([v for t in tris for v in t])
        x0, y0, z0 = pts.min(axis=0)
        x1, y1, z1 = pts.max(axis=0)
        ax.set_xlim(x0, x1)
        ax.set_ylim(z0, z1)
        ax.set_zlim(y0, y1)
        ax.set_box_aspect((max(x1 - x0, 1e-9), max(z1 - z0, 1e-9), max(y1 - y0, 1e-9)))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, facecolor=BACKGROUND,
                metadata={"Software": ""})
    plt.close(fig)
    return buf.getvalue()


def pixel_checks(name, png_bytes, errors):
    img = plt.imread(io.BytesIO(png_bytes))  # float 0..1, HxWx4
    rgb = (img[:, :, :3] * 255).astype(np.uint8)
    bg = np.array([round(c * 255) for c in BACKGROUND], dtype=np.uint8)
    non_bg = np.any(rgb != bg, axis=2).mean()
    if non_bg < 0.005:
        errors.append("%s: render pusty (%.2f%% pikseli nie-tła < 0.5%%)"
                      % (name, non_bg * 100))
    uniq = len(np.unique(rgb.reshape(-1, 3), axis=0))
    if uniq < 10:
        errors.append("%s: za mało kolorów (%d < 10) — materiały nie weszły?"
                      % (name, uniq))


def main():
    if len(sys.argv) > 1:
        obj = Path(sys.argv[1])
        out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else obj.parent / "renders"
        if not obj.exists():
            print("FAIL: %s nie istnieje" % obj)
            return 1
    else:
        if not SCENE.exists():
            print("OK: scene.py jeszcze nie istnieje (zielony baseline).")
            return 0
        obj = ROOT / "out" / "town.obj"
        out_dir = ROOT / "out" / "renders"
        if not obj.exists():
            print("FAIL: brak out/town.obj (uruchom scene.py / check_scene)")
            return 1

    tris, cols = parse(obj)
    errors = []
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, (name, elev, azim) in enumerate(CAMERAS):
        png = render_bytes(tris, cols, elev, azim)
        if i == 0:  # test determinizmu na pierwszej kamerze
            png2 = render_bytes(tris, cols, elev, azim)
            if png != png2:
                errors.append("NIEDETERMINIZM: dwa rendery kamery %r różnią się bajtami" % name)
        pixel_checks(name, png, errors)
        (out_dir / (name + ".png")).write_bytes(png)

    if errors:
        print("FAIL — render_test (%d problemów):" % len(errors))
        for e in errors:
            print("  - " + e)
        return 1
    print("OK: %d renderów deterministycznych w %s." % (len(CAMERAS), out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
