#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Weryfikator części modelu (parts/*.py) — sygnał prawdy pętli.

Kontrakt (parts/README.md): build(**params) -> list grup
  {"name": str, "vertices": [(x,y,z)...], "faces": [(material, (i0,i1,...))...],
   "colors": {material: (r,g,b)}}

Kontrakt warunkowy: część, której nie ma, nie jest sprawdzana;
brak katalogu parts/ lub pusty katalog = zielony baseline.

Asercje wspólne: struktura, niepuste, poprawne indeksy, brak NaN/inf,
deterministyczność (dwa build() identyczne), budżet z budgets.json.
Asercje specyficzne per typ części — sekcje poniżej (terrain/water/
lighthouse/house/pier). Moduł o innej nazwie dostaje tylko wspólne.

Użycie: python scripts/check_parts.py [katalog_parts]   # argv do testów
"""

import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
PARTS_DIR = Path(_args[0]) if _args else ROOT / "parts"
BUDGETS = ROOT / "budgets.json"
# Podłoga wersji (LESSON-003) to ratchet REALNEGO repo: egzekwujemy ją na biegu
# domyślnym (bez argumentów) zawsze; na jawnym katalogu fixture'a tylko z flagą
# --floor (inaczej fixture'y starszych kontraktów testują asercje, nie ratchet).
ENFORCE_FLOOR = (not _args) or ("--floor" in sys.argv[1:])

errors = []


def err(part, msg):
    errors.append("[%s] %s" % (part, msg))


def load_module(path):
    spec = importlib.util.spec_from_file_location("part_" + path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def all_vertices(groups):
    return [v for g in groups for v in g["vertices"]]


def faces_with_material(groups, predicate):
    """Wierzchołki ścianek, których materiał spełnia predykat."""
    out = []
    for g in groups:
        for mat, idxs in g["faces"]:
            if predicate(mat):
                out.extend(g["vertices"][i] for i in idxs)
    return out


def centroid_y(verts):
    return sum(v[1] for v in verts) / len(verts)


def check_common(name, groups, budget):
    if not isinstance(groups, list) or not groups:
        err(name, "build() musi zwrócić niepustą listę grup")
        return False
    total_v = total_f = 0
    for g in groups:
        for key in ("name", "vertices", "faces", "colors"):
            if key not in g:
                err(name, "grupa bez klucza %r" % key)
                return False
        if not g["vertices"] or not g["faces"]:
            err(name, "grupa %s: puste vertices/faces" % g["name"])
            return False
        for v in g["vertices"]:
            if len(v) != 3 or any(not math.isfinite(c) for c in v):
                err(name, "grupa %s: zły wierzchołek %r" % (g["name"], v))
                return False
        n = len(g["vertices"])
        for mat, idxs in g["faces"]:
            if len(idxs) < 3:
                err(name, "grupa %s: ścianka < 3 indeksów" % g["name"])
                return False
            if any(not (0 <= i < n) for i in idxs):
                err(name, "grupa %s: indeks poza zakresem" % g["name"])
                return False
            if mat not in g["colors"]:
                err(name, "grupa %s: materiał %r bez koloru w colors" % (g["name"], mat))
                return False
        for mat, rgb in g["colors"].items():
            if len(rgb) != 3 or any(not (0.0 <= c <= 1.0) for c in rgb):
                err(name, "kolor %r poza [0,1]" % mat)
                return False
        total_v += n
        total_f += len(g["faces"])
    if total_v > budget["max_vertices"]:
        err(name, "budżet wierzchołków przekroczony (%d > %d)" % (total_v, budget["max_vertices"]))
    if total_f > budget["max_faces"]:
        err(name, "budżet ścianek przekroczony (%d > %d)" % (total_f, budget["max_faces"]))
    return True


def extent(verts, axis):
    vals = [v[axis] for v in verts]
    return max(vals) - min(vals)


def check_terrain(name, groups):
    verts = all_vertices(groups)
    if extent(verts, 0) < 40 or extent(verts, 2) < 40:
        err(name, "teren za mały: wymagany zakres XZ >= 40 m w obu osiach")
    ys = [v[1] for v in verts]
    if min(ys) < -2 or max(ys) > 12:
        err(name, "wysokości terenu poza zakresem [-2, 12] (jest %.2f..%.2f)" % (min(ys), max(ys)))
    if max(ys) - min(ys) < 1.0:
        err(name, "brak wzniesienia: max-min wysokości < 1 m")


def check_water(name, groups):
    verts = all_vertices(groups)
    bad = [v for v in verts if abs(v[1]) > 1e-6]
    if bad:
        err(name, "woda nie jest taflą na y=0 (%d wierzchołków poza, np. %r)" % (len(bad), bad[0]))
    if extent(verts, 0) < 20 or extent(verts, 2) < 20:
        err(name, "tafla za mała: wymagany zakres XZ >= 20 m")


def check_lighthouse(name, groups):
    verts = all_vertices(groups)
    ys = [v[1] for v in verts]
    height = max(ys) - min(ys)
    if not (10 <= height <= 200):
        err(name, "wysokość latarni %.2f poza zakresem [10, 200]" % height)
    tower = [g for g in groups if "tower" in g["name"]]
    if not tower:
        err(name, "brak grupy zawierającej 'tower'")
        return
    tverts = all_vertices(tower)
    t_lo = min(v[1] for v in tverts)
    t_hi = max(v[1] for v in tverts)

    def radius(frac_lo, frac_hi):
        xs = [v for v in tverts if frac_lo <= (v[1] - t_lo) / max(t_hi - t_lo, 1e-9) <= frac_hi]
        cx = sum(v[0] for v in tverts) / len(tverts)
        cz = sum(v[2] for v in tverts) / len(tverts)
        return max((math.hypot(v[0] - cx, v[2] - cz) for v in xs), default=0.0)

    if not radius(0.75, 1.0) < radius(0.0, 0.25) * 0.95:
        err(name, "wieża nie zwęża się ku górze")


def check_house(name, groups):
    verts = all_vertices(groups)
    ys = [v[1] for v in verts]
    height = max(ys) - min(ys)
    if not (2 <= height <= 15):
        err(name, "wysokość domu %.2f poza zakresem [2, 15]" % height)
    roof = faces_with_material(groups, lambda m: "roof" in m or "dach" in m)
    door = faces_with_material(groups, lambda m: "door" in m or "drzwi" in m)
    walls = faces_with_material(groups, lambda m: not any(
        k in m for k in ("roof", "dach", "door", "drzwi")))
    if not roof:
        err(name, "brak ścianek z materiałem dachu (nazwa zawierająca 'roof')")
    if not door:
        err(name, "brak ścianek z materiałem drzwi (nazwa zawierająca 'door')")
    if roof and walls and centroid_y(roof) <= centroid_y(walls):
        err(name, "dach nie jest powyżej ścian (centroidy: dach %.2f, ściany %.2f)"
            % (centroid_y(roof), centroid_y(walls)))
    if door and min(v[1] for v in door) - min(ys) > 0.5:
        err(name, "drzwi nie sięgają podłoża domu (luka > 0.5 m)")


def check_pier(name, groups):
    verts = all_vertices(groups)
    below = [v for v in verts if v[1] < -0.2]
    above = [v for v in verts if v[1] > 0.0]
    if not below:
        err(name, "pale nie sięgają poniżej wody (brak wierzchołków y < -0.2)")
    if len(above) < 0.5 * len(verts):
        err(name, "większość pomostu powinna być nad wodą y=0")


# ---------------------------------------------------------------------------
# Sekcje v2 (aktywne od CONTRACT_VERSION >= 2) + nowe typy części.
# Wzorzec wersjonowanego kontraktu: parts/README.md.
# ---------------------------------------------------------------------------

def xz_clusters(verts, cell=0.5):
    """Liczba odrębnych kolumn w XZ (kratownica o boku cell)."""
    return len({(round(v[0] / cell), round(v[2] / cell)) for v in verts})


def mat_faces(groups, *needles):
    """Lista ścianek (listy wierzchołków), których materiał zawiera podciąg."""
    out = []
    for g in groups:
        for mat, idxs in g["faces"]:
            if any(n in mat for n in needles):
                out.append([g["vertices"][i] for i in idxs])
    return out


def check_pier_v2(name, groups):
    verts = all_vertices(groups)
    if max(extent(verts, 0), extent(verts, 2)) < 12:
        err(name, "v2: pomost za krótki (oś długa < 12 m)")
    piles = [v for v in verts if v[1] < -0.2]
    if xz_clusters(piles) < 16:
        err(name, "v2: za mało pali (< 16 kolumn = 8 par; jest %d)" % xz_clusters(piles))
    planks = mat_faces(groups, "plank", "deck")
    if len(planks) < 30:
        err(name, "v2: za mało klepek (%d ścianek 'plank'/'deck' < 30 — deski mają być osobne)" % len(planks))
    rails = mat_faces(groups, "rail")
    if len(rails) < 8:
        err(name, "v2: brak balustrady (>= 8 ścianek z materiałem 'rail*': słupki + poręcz)")
    elif planks:
        deck_top = max(v[1] for f in planks for v in f)
        rail_top = max(v[1] for f in rails for v in f)
        if rail_top < deck_top + 0.7:
            err(name, "v2: poręcz za nisko (%.2f < deska %.2f + 0.7)" % (rail_top, deck_top))
    bollards = [v for f in mat_faces(groups, "bollard") for v in f]
    if xz_clusters(bollards, cell=1.0) < 2:
        err(name, "v2: za mało polerów cumowniczych (materiał 'bollard*', >= 2 odrębne)")


def check_terrain_v2(name, groups):
    verts = all_vertices(groups)
    if extent(verts, 0) < 80 or extent(verts, 2) < 60:
        err(name, "v2: pas wybrzeża za mały (wymagane >= 80 m w X i >= 60 m w Z)")
    land = [v for v in verts if v[1] > 0.05]
    if len(land) < 0.6 * len(verts):
        err(name, "v2: ląd to mniej niż 60%% wierzchołków — to wyspa, nie pas wybrzeża")
    sand = mat_faces(groups, "sand", "beach")
    if len(sand) < 20:
        err(name, "v2: brak pasa plaży (>= 20 ścianek 'sand*'/'beach*')")
    else:
        sverts = [v for f in sand for v in f]
        if not all(-0.1 <= v[1] <= 1.2 for v in sverts):
            err(name, "v2: plaża poza zakresem wysokości [-0.1, 1.2]")
    shore = [v for v in verts if 0.0 <= v[1] <= 0.15]
    if len(shore) >= 3:
        xs = [v[0] for v in shore]
        zs = [v[2] for v in shore]
        if extent(shore, 0) >= extent(shore, 2):
            a, b = min(range(len(shore)), key=lambda i: xs[i]), max(range(len(shore)), key=lambda i: xs[i])
        else:
            a, b = min(range(len(shore)), key=lambda i: zs[i]), max(range(len(shore)), key=lambda i: zs[i])
        ax, az, bx, bz = xs[a], zs[a], xs[b], zs[b]
        ln = math.hypot(bx - ax, bz - az) or 1e-9
        dev = max(abs((bx - ax) * (az - z) - (ax - x) * (bz - az)) / ln
                  for x, z in zip(xs, zs))
        if dev < 3.0:
            err(name, "v2: linia brzegowa zbyt prosta (max odchylenie od cięciwy %.1f m < 3)" % dev)
    else:
        err(name, "v2: nie można wyznaczyć linii brzegowej (brak wierzchołków przy y~0)")
    ys = sorted(v[1] for v in land) if land else [0]
    town_level = ys[len(ys) // 2]
    if max(v[1] for v in verts) < town_level + 2.0:
        err(name, "v2: brak klifu/wyniesienia pod latarnię (>= 2 m nad poziom miasteczka %.2f)" % town_level)


def check_house_v2(name, groups):
    win = mat_faces(groups, "glass", "window")
    if len(win) < 2:
        err(name, "v2: za mało okien (%d ścianek 'glass*'/'window*' < 2)" % len(win))
    if len(mat_faces(groups, "frame")) < 4:
        err(name, "v2: brak ram okiennych/framugi drzwi (>= 4 ścianki 'frame*')")
    roof = mat_faces(groups, "roof", "dach")
    chimney = mat_faces(groups, "chimney")
    if not chimney:
        err(name, "v2: brak komina (materiał 'chimney*')")
    elif roof:
        if max(v[1] for f in chimney for v in f) < max(v[1] for f in roof for v in f) + 0.2:
            err(name, "v2: komin nie wystaje ponad kalenicę (>= 0.2 m)")
    found = mat_faces(groups, "foundation", "plinth")
    verts = all_vertices(groups)
    if not found:
        err(name, "v2: brak cokołu/fundamentu (materiał 'foundation*'/'plinth*')")
    elif min(v[1] for f in found for v in f) - min(v[1] for v in verts) > 1e-6:
        err(name, "v2: fundament nie sięga podstawy domu")


def check_boat(name, groups):
    verts = all_vertices(groups)
    if min(v[1] for v in verts) >= -0.05:
        err(name, "dno łodzi powinno być zanurzone (min-Y < -0.05)")
    if max(v[1] for v in verts) <= 0.3:
        err(name, "burty powinny wystawać nad wodę (max-Y > 0.3)")
    seats = mat_faces(groups, "seat", "bench")
    cents = {(round(sum(v[0] for v in f) / len(f), 1), round(sum(v[2] for v in f) / len(f), 1))
             for f in seats}
    if len(cents) < 2:
        err(name, "za mało ławek (>= 2 ścianki 'seat*'/'bench*' w różnych miejscach)")


def check_tree(name, groups):
    verts = all_vertices(groups)
    h = extent(verts, 1)
    if not (3 <= h <= 8):
        err(name, "wysokość sosny %.2f poza zakresem [3, 8]" % h)
    trunk = [v for f in mat_faces(groups, "trunk", "bark") for v in f]
    crown = [v for f in mat_faces(groups, "leaves", "crown", "needle") for v in f]
    if not trunk:
        err(name, "brak pnia (materiał 'trunk*'/'bark*')")
    if not crown:
        err(name, "brak korony (materiał 'leaves*'/'crown*'/'needle*')")
    if trunk and crown:
        if centroid_y(crown) <= centroid_y(trunk):
            err(name, "korona nie jest powyżej pnia")
        c_lo = min(v[1] for v in crown)
        c_hi = max(v[1] for v in crown)
        cx = sum(v[0] for v in crown) / len(crown)
        cz = sum(v[2] for v in crown) / len(crown)

        def rad(f0, f1):
            sel = [v for v in crown if f0 <= (v[1] - c_lo) / max(c_hi - c_lo, 1e-9) <= f1]
            return max((math.hypot(v[0] - cx, v[2] - cz) for v in sel), default=0.0)

        if not rad(0.7, 1.0) < rad(0.0, 0.3) * 0.8:
            err(name, "korona nie jest stożkowa/warstwowa (góra ma być węższa od dołu)")


def check_rocks(name, groups):
    for g in groups:
        vs = g["vertices"]
        for ax, label in ((0, "X"), (1, "Y"), (2, "Z")):
            vals = [v[ax] for v in vs]
            if max(vals) - min(vals) < 0.1:
                err(name, "głaz %s płaski w osi %s — to nie bryła" % (g["name"], label))
        if len(vs) < 8:
            err(name, "głaz %s zbyt prosty (< 8 wierzchołków)" % g["name"])
        used = {i for _, idxs in g["faces"] for i in idxs}
        if used != set(range(len(vs))):
            err(name, "głaz %s: wierzchołki nieużyte w ściankach (bryła nie jest zamknięta)" % g["name"])


def check_path(name, groups):
    verts = all_vertices(groups)
    if max(extent(verts, 0), extent(verts, 2)) < 10:
        err(name, "ścieżka za krótka (< 10 m)")
    if extent(verts, 1) > 4:
        err(name, "ścieżka skacze w pionie (> 4 m różnicy wysokości)")


# ---------------------------------------------------------------------------
# Sekcje v3 (aktywne od CONTRACT_VERSION >= 3) — milestone 2 "Forma":
# wyspa wg referencji (ART_DIRECTION.md). terrain v3 ZASTĘPUJE v2 (wyspa
# unieważnia pas wybrzeża — decyzja architekta); house v3 DODAJE archetypy
# ponad v2; nowe typy: wall/chapel/bridge/prop_barrel/prop_crate/bush.
# ---------------------------------------------------------------------------

def _xz_buckets(verts, cell):
    buckets = {}
    for v in verts:
        buckets.setdefault((int(v[0] // cell), int(v[2] // cell)), []).append(v)
    return buckets


def check_terrain_v3(name, groups):
    verts = all_vertices(groups)
    if extent(verts, 0) < 80 or extent(verts, 2) < 60:
        err(name, "v3: wyspa za mała (wymagane >= 80 m w X i >= 60 m w Z)")
    ys = [v[1] for v in verts]
    if min(ys) < -3 or max(ys) > 20:
        err(name, "v3: wysokości poza zakresem [-3, 20] (jest %.2f..%.2f)" % (min(ys), max(ys)))
    # wyspa: cały obrys siatki pod wodą
    x0 = min(v[0] for v in verts); x1 = max(v[0] for v in verts)
    z0 = min(v[2] for v in verts); z1 = max(v[2] for v in verts)
    border = [v for v in verts if v[0] - x0 < 1.0 or x1 - v[0] < 1.0
              or v[2] - z0 < 1.0 or z1 - v[2] < 1.0]
    wet = [v for v in border if v[1] < 0]
    if len(wet) < len(border):
        err(name, "v3: to nie wyspa — %d wierzchołków obrysu siatki nad wodą"
            % (len(border) - len(wet)))
    land = [v for v in verts if v[1] > 0.05]
    if not (0.20 * len(verts) <= len(land) <= 0.75 * len(verts)):
        err(name, "v3: udział lądu %.0f%% poza zakresem 20-75%% (wyspa w wodzie)"
            % (100 * len(land) / max(len(verts), 1)))
    # >= 3 poziomy tarasowe: pasma wysokości skupiające >= 5% lądu, rozdzielone >= 1 m
    hist = {}
    for v in land:
        hist[round(v[1] * 2) / 2] = hist.get(round(v[1] * 2) / 2, 0) + 1
    bands = sorted(h for h, c in hist.items() if c >= 0.05 * len(land))
    plateaus = []
    for h in bands:
        if not plateaus or h - plateaus[-1] >= 1.0:
            plateaus.append(h)
    if len(plateaus) < 3:
        err(name, "v3: za mało poziomów tarasowych (%d < 3; pasma: %s)"
            % (len(plateaus), plateaus))
    # klify: >= 8 miejsc z uskokiem >= 2.5 m na dystansie <= 3 m
    cliff_sites = set()
    for key, vs in _xz_buckets(verts, 3.0).items():
        lo = min(v[1] for v in vs)
        hi = max(v[1] for v in vs)
        if hi - lo >= 2.5:
            cliff_sites.add(key)
    if len(cliff_sites) < 8:
        err(name, "v3: za mało klifów (%d miejsc z uskokiem >= 2.5 m < 8)" % len(cliff_sites))
    # zatoczka z plażą: piasek wcięty w głąb obrysu lądu
    sand = [v for f in mat_faces(groups, "sand", "beach") for v in f]
    if len(mat_faces(groups, "sand", "beach")) < 10:
        err(name, "v3: brak plaży w zatoczce (>= 10 ścianek 'sand*'/'beach*')")
    elif land:
        cx = sum(v[0] for v in land) / len(land)
        cz = sum(v[2] for v in land) / len(land)
        shore = [v for v in verts if 0.0 <= v[1] <= 0.2]
        if shore:
            import statistics
            r_shore = statistics.mean(math.hypot(v[0] - cx, v[2] - cz) for v in shore)
            r_sand = statistics.mean(math.hypot(v[0] - cx, v[2] - cz) for v in sand)
            if r_sand > r_shore - 2.0:
                err(name, "v3: plaża nie tworzy zatoczki (wcięcie %.1f m < 2 m w głąb obrysu)"
                    % (r_shore - r_sand))
        if not all(-0.1 <= v[1] <= 1.2 for v in sand):
            err(name, "v3: plaża poza zakresem wysokości [-0.1, 1.2]")


HOUSE_ARCHETYPES = ("timber", "stone", "two_story")


def _glass_levels(groups):
    """Pasma wysokości okien: grupy wierzchołków szyb rozdzielone > 1.2 m."""
    ys = sorted({round(v[1], 1) for f in mat_faces(groups, "glass", "window") for v in f})
    bands = 0
    prev = None
    for y in ys:
        if prev is None or y - prev > 1.2:
            bands += 1
        prev = y
    return list(range(bands))


def check_house_v3(name, mod):
    builds = {}
    for a in HOUSE_ARCHETYPES:
        try:
            builds[a] = mod.build(archetype=a)
        except TypeError as e:
            err(name, "v3: build(archetype=%r) nieobsługiwane: %r" % (a, e))
            return
        except Exception as e:
            err(name, "v3: build(archetype=%r) rzucił wyjątek: %r" % (a, e))
            return
    for a, groups in builds.items():
        sub = "%s[%s]" % (name, a)
        check_house(sub, groups)       # asercje v1 obowiązują każdy archetyp
        check_house_v2(sub, groups)    # i v2 (okna/komin/fundament/framuga)
    g = builds["timber"]
    if len(mat_faces(g, "beam", "timber")) < 6:
        err(name, "v3[timber]: mur pruski wymaga >= 6 ścianek belek 'beam*'/'timber*' na elewacji")
    g = builds["stone"]
    verts = all_vertices(g)
    if extent(verts, 1) > 4.5:
        err(name, "v3[stone]: chata kamienna za wysoka (%.1f > 4.5 m — 1 kondygnacja)" % extent(verts, 1))
    if len(mat_faces(g, "stone")) < 6:
        err(name, "v3[stone]: chata kamienna wymaga >= 6 ścianek 'stone*' (pełny cokół/mur)")
    if len(_glass_levels(g)) > 1:
        err(name, "v3[stone]: chata kamienna ma mieć 1 poziom okien")
    g = builds["two_story"]
    verts = all_vertices(g)
    if extent(verts, 1) < 5.0:
        err(name, "v3[two_story]: dom dwukondygnacyjny za niski (%.1f < 5 m)" % extent(verts, 1))
    if len(_glass_levels(g)) < 2:
        err(name, "v3[two_story]: wymagane >= 2 poziomy okien (są: %s)" % _glass_levels(g))
    sigs = {a: (len(all_vertices(g)), tuple(round(extent(all_vertices(g), ax), 1) for ax in (0, 1, 2)))
            for a, g in builds.items()}
    for i, a in enumerate(HOUSE_ARCHETYPES):
        for b in HOUSE_ARCHETYPES[i + 1:]:
            if sigs[a] == sigs[b]:
                err(name, "v3: archetypy %s i %s geometrycznie nieodróżnialne" % (a, b))


def check_wall(name, groups):
    wall_f = mat_faces(groups, "wall", "stone")
    if len(wall_f) < 8:
        err(name, "mur oporowy: za mało ścianek 'wall*'/'stone*' (%d < 8)" % len(wall_f))
    elif max(v[1] for f in wall_f for v in f) - min(v[1] for f in wall_f for v in f) < 0.5:
        err(name, "mur oporowy za niski (< 0.5 m)")
    steps = mat_faces(groups, "stair", "step")
    levels = sorted({round(sum(v[1] for v in f) / len(f), 1) for f in steps})
    if len(levels) < 6:
        err(name, "schody: za mało stopni (%d poziomów < 6)" % len(levels))
    elif levels[-1] - levels[0] < 1.0:
        err(name, "schody nie pokonują różnicy poziomów (>= 1 m)")


def check_chapel(name, groups):
    verts = all_vertices(groups)
    roof = mat_faces(groups, "roof", "dach")
    if not roof:
        err(name, "kapliczka bez dachu (materiał 'roof*')")
    cross = mat_faces(groups, "cross", "spire", "sygnaturka")
    if not cross:
        err(name, "kapliczka bez sygnaturki/krzyża (materiał 'cross*'/'spire*')")
    else:
        top = max(v[1] for f in cross for v in f)
        if max(v[1] for v in verts) - top > 1e-6:
            err(name, "sygnaturka/krzyż nie jest najwyższym punktem kapliczki")
    if roof:
        others = faces_with_material(groups, lambda m: not any(
            k in m for k in ("roof", "dach", "cross", "spire", "sygnaturka")))
        if others and max(v[1] for f in roof for v in f) < max(v[1] for v in others) - 1e-6:
            err(name, "dach kapliczki nie wieńczy bryły")
    w, h, d = (extent(verts, a) for a in (0, 1, 2))
    if w * d > 25:
        err(name, "kapliczka za duża w planie (%.1f m2 > 25 — ma być mniejsza od domów)" % (w * d))
    if h > 7:
        err(name, "kapliczka za wysoka (%.1f > 7 m)" % h)


def check_bridge(name, groups):
    rope_v = [v for f in mat_faces(groups, "rope", "lina") for v in f]
    if not rope_v:
        err(name, "mostek bez lin nośnych (materiał 'rope*'/'lina*')")
        return
    axis = 0 if extent(rope_v, 0) >= extent(rope_v, 2) else 2
    perp = 2 if axis == 0 else 0
    if max(extent(rope_v, 0), extent(rope_v, 2)) < 4:
        err(name, "mostek za krótki (< 4 m)")
    strands = sorted({round(v[perp], 1) for v in rope_v})
    spread = (strands[-1] - strands[0]) if strands else 0
    if len(strands) < 2 or spread < 0.4:
        err(name, "wymagane >= 2 liny nośne rozstawione >= 0.4 m w poprzek")
    t0 = min(v[axis] for v in rope_v)
    t1 = max(v[axis] for v in rope_v)
    span = max(t1 - t0, 1e-9)
    ends = [v[1] for v in rope_v if (v[axis] - t0) / span < 0.15 or (v[axis] - t0) / span > 0.85]
    mid = [v[1] for v in rope_v if 0.4 <= (v[axis] - t0) / span <= 0.6]
    if not mid or not ends:
        err(name, "liny bez punktów pośrednich — nie da się ocenić zwisu")
    elif min(mid) > min(ends) - 0.2:
        err(name, "liny bez zwisu (środek %.2f, końce %.2f — wymagane >= 0.2 m niżej)"
            % (min(mid), min(ends)))
    if len(mat_faces(groups, "plank", "deck")) < 8:
        err(name, "mostek bez desek (>= 8 ścianek 'plank*'/'deck*')")


def check_prop_barrel(name, groups):
    verts = all_vertices(groups)
    h = extent(verts, 1)
    if not (0.6 <= h <= 1.3):
        err(name, "beczka: wysokość %.2f poza [0.6, 1.3]" % h)
    w, d = extent(verts, 0), extent(verts, 2)
    if max(w, d) > 1.4 * min(w, d):
        err(name, "beczka nie jest obła (przekrój %.2f x %.2f zbyt spłaszczony)" % (w, d))
    if len(verts) < 24:
        err(name, "beczka zbyt kanciasta (< 24 wierzchołków)")
    hoops = mat_faces(groups, "hoop", "band", "obrecz")
    levels = {round(sum(v[1] for v in f) / len(f), 1) for f in hoops}
    if len(levels) < 2:
        err(name, "beczka: wymagane >= 2 obręcze 'hoop*'/'band*' na różnych wysokościach")


def check_prop_crate(name, groups):
    verts = all_vertices(groups)
    for ax, label in ((0, "X"), (1, "Y"), (2, "Z")):
        e = extent(verts, ax)
        if not (0.4 <= e <= 1.3):
            err(name, "skrzynia: wymiar %s = %.2f poza [0.4, 1.3]" % (label, e))
    if len(mat_faces(groups, "slat", "trim", "listwa")) < 4:
        err(name, "skrzynia bez listew (>= 4 ścianki 'slat*'/'trim*')")


def check_bush(name, groups):
    verts = all_vertices(groups)
    h = extent(verts, 1)
    if not (0.5 <= h <= 1.5):
        err(name, "krzew: wysokość %.2f poza [0.5, 1.5]" % h)
    if not (mat_faces(groups, "bush", "leaves", "green")):
        err(name, "krzew bez zieleni (materiał 'bush*'/'leaves*')")
    if len(verts) < 12:
        err(name, "krzew zbyt prosty (< 12 wierzchołków)")
    if len({round(v[1], 1) for v in verts}) < 3:
        err(name, "krzew zbyt regularny (< 3 poziomy wysokości — ma być nieregularna bryła)")


SPECIFIC = {
    "terrain": check_terrain,
    "water": check_water,
    "lighthouse": check_lighthouse,
    "house": check_house,
    "pier": check_pier,
    "boat": check_boat,
    "tree": check_tree,
    "rocks": check_rocks,
    "path": check_path,
    "wall": check_wall,
    "chapel": check_chapel,
    "bridge": check_bridge,
    "prop_barrel": check_prop_barrel,
    "prop_crate": check_prop_crate,
    "bush": check_bush,
}

SPECIFIC_V2 = {
    "terrain": check_terrain_v2,
    "house": check_house_v2,
    "pier": check_pier_v2,
}


def main():
    if not PARTS_DIR.is_dir():
        print("OK: katalog %s nie istnieje (zielony baseline)." % PARTS_DIR.name)
        return 0
    modules = sorted(p for p in PARTS_DIR.glob("*.py") if p.stem != "__init__")
    if not modules:
        print("OK: brak modułów części (zielony baseline).")
        return 0

    budgets = json.loads(BUDGETS.read_text(encoding="utf-8"))["parts"]
    floors = json.loads((ROOT / "scripts" / "versions_floor.json")
                        .read_text(encoding="utf-8"))["parts"]
    for path in modules:
        name = path.stem
        try:
            mod = load_module(path)
        except Exception as e:
            err(name, "import nieudany: %r" % e)
            continue
        if not hasattr(mod, "build"):
            err(name, "brak funkcji build()")
            continue
        version = getattr(mod, "CONTRACT_VERSION", 1)
        floor = floors.get(name)
        if ENFORCE_FLOOR and floor is not None and version < floor:
            err(name, "CONTRACT_VERSION=%d poniżej podłogi %d "
                "(scripts/versions_floor.json; LESSON-003 — wersji nie wolno obniżać)"
                % (version, floor))
            continue
        try:
            groups = mod.build()
            groups2 = mod.build()
        except Exception as e:
            err(name, "build() rzucił wyjątek: %r" % e)
            continue
        if groups != groups2:
            err(name, "build() niedeterministyczny: dwa wywołania różnią się")
            continue
        budget = budgets.get(name, budgets["default"])
        if not check_common(name, groups, budget):
            continue
        # dispatch wersjonowany: terrain v3 (wyspa) ZASTĘPUJE asercje v1/v2
        # pasa wybrzeża (decyzja architekta w ART_DIRECTION.md)
        if name == "terrain" and version >= 3:
            check_terrain_v3(name, groups)
            continue
        if name in SPECIFIC:
            SPECIFIC[name](name, groups)
        if version >= 2 and name in SPECIFIC_V2:
            SPECIFIC_V2[name](name, groups)
        if version >= 3 and name == "house":
            check_house_v3(name, mod)

    if errors:
        print("FAIL — check_parts (%d problemów):" % len(errors))
        for e in errors:
            print("  - " + e)
        return 1
    print("OK: wszystkie części (%s) przechodzą kontrole." % ", ".join(p.stem for p in modules))
    return 0


if __name__ == "__main__":
    sys.exit(main())
