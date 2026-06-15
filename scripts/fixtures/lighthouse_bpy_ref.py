# -*- coding: utf-8 -*-
"""Builder latarni w kontrakcie bpy (M3-migracja).

Pod Blenderem (`scripts/bpy_build.py`): build(seed=0) tworzy w bieżącej scenie
bpy obiekty nazwane jak wymagane grupy (base/tower/gallery/lantern/roof/door),
z modyfikatorami (bevel + subdivision) i materiałami proceduralnymi (kamień,
naprzemienne pasy biel/czerwień na wieży, szkło laterny, metal). Część NIE
eksportuje — eksport robi scripts/bpy_build.py. Wzorzec ścieżki bpy:
scripts/fixtures/lighthouse_bpy_ref.py.

Bez Blendera (czysty Python, np. scripts/check_parts.py): bpy nie jest dostępne,
więc build() zwraca opisową listę grup w starym kontrakcie części
(parts/README.md) — ten sam kształt i te same materiały, wystarczająco wierne,
by przejść wspólne asercje. Prawdą ścieżki bpy pozostaje scripts/check_lighthouse.py.

Forma odpowiada scripts/check_lighthouse.py (pionowa kolejność części, drzwi
w dolnej wieży, dach najwyżej, wieża zwęża się ku górze). Determinizm: brak
losowości; seed zarezerwowany (kontrakt), wynik niezależny od seeda.

Budujemy w Blenderze Z-up (wysokość = Z); eksporter (up_axis='Y') zamienia na
OBJ Y-up. Ścieżka stdlib zwraca geometrię od razu w Y-up (kontrakt części).
"""

import math

try:
    import bpy
except ImportError:  # czysty Python (check_parts) — brak Blendera
    bpy = None

# Wspólna paleta materiałów (RGB 0..1) dla obu ścieżek.
_STONE = (0.46, 0.43, 0.39)
_WHITE = (0.92, 0.92, 0.90)
_RED = (0.78, 0.12, 0.10)
_GLASS = (0.55, 0.75, 0.85)
_METAL = (0.30, 0.32, 0.34)
_ROOF = (0.15, 0.14, 0.15)   # ciemny dach laterny (jak w referencji — nie czerwony)


# --------------------------------------------------------------------------- #
# Ścieżka bpy (pod Blenderem) — wzorzec: scripts/fixtures/lighthouse_bpy_ref.py
# --------------------------------------------------------------------------- #

def _mat(name, rgb, rough=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)   # źródło Kd w eksporcie OBJ/MTL
    return m


def _rename(name):
    o = bpy.context.active_object
    o.name = name
    o.data.name = name
    return o


def _bevel(obj, width=0.06, segments=2):
    m = obj.modifiers.new(name="Bevel", type="BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"


def _subsurf(obj, levels=1):
    m = obj.modifiers.new(name="Subdiv", type="SUBSURF")
    m.levels = levels
    m.render_levels = levels


def _bpy_tower(white, red, taper, s):
    """Wieża jako stos pierścieni (Blender Z-up): pasy = naprzemienny materiał
    co 2 pierścienie -> realne poziome pasy biel/czerwień (po subsurf gładkie)."""
    z0, z1 = 2.0 * s, 18.0 * s
    r0, r1 = 2.4, (1.4 if taper else 2.4)
    rings, seg = 12, 32
    verts, faces, fmat = [], [], []
    for k in range(rings + 1):
        t = k / rings
        r, z = r0 + (r1 - r0) * t, z0 + (z1 - z0) * t
        verts += [(r * math.cos(2 * math.pi * j / seg),
                   r * math.sin(2 * math.pi * j / seg), z) for j in range(seg)]
    for k in range(rings):
        m = (k // 2) % 2                       # 2 pierścienie na pas
        lo, hi = k * seg, (k + 1) * seg
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((lo + j, lo + j2, hi + j2, hi + j))
            fmat.append(m)
    cb = len(verts); verts.append((0.0, 0.0, z0))
    ct = len(verts); verts.append((0.0, 0.0, z1))
    top = rings * seg
    for j in range(seg):
        j2 = (j + 1) % seg
        faces.append((cb, j2, j)); fmat.append(0)
        faces.append((ct, top + j, top + j2)); fmat.append((rings - 1) // 2 % 2)
    mesh = bpy.data.meshes.new("tower")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("tower", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(white)
    obj.data.materials.append(red)
    for i, poly in enumerate(obj.data.polygons):
        poly.material_index = fmat[i]
    _bevel(obj, width=0.05)
    _subsurf(obj, 1)
    return obj


def _build_bpy(taper, s):
    stone = _mat("stone", _STONE)
    white = _mat("stripe_white", _WHITE)
    red = _mat("stripe_red", _RED)
    glass = _mat("glass", _GLASS, rough=0.1)
    metal = _mat("metal", _METAL, rough=0.4)
    roof_dark = _mat("roof_dark", _ROOF, rough=0.5)

    # --- base: skalisty cokół (cylinder) ---
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=3.0, depth=2.0 * s,
                                        location=(0, 0, 1.0 * s))
    base = _rename("base")
    base.data.materials.append(stone)
    _bevel(base, width=0.12)
    _subsurf(base, 1)

    # --- tower: zwężający się walec w POZIOME PASY biel/czerwień ---
    # Pierścienie (loop cuts w pionie) zamiast jednej ścianki na całą wysokość —
    # inaczej banding po wysokości środka ścianki daje jednolitą wieżę (dług M3).
    tower = _bpy_tower(white, red, taper, s)

    # --- gallery: szersza galeryjka pod laterną ---
    bpy.ops.mesh.primitive_cylinder_add(vertices=28, radius=2.0, depth=0.6 * s,
                                        location=(0, 0, 18.3 * s))
    gallery = _rename("gallery")
    gallery.data.materials.append(metal)
    _bevel(gallery, width=0.05)

    # --- lantern: przeszklona laterna ---
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=1.3, depth=2.4 * s,
                                        location=(0, 0, 19.9 * s))
    lantern = _rename("lantern")
    lantern.data.materials.append(glass)
    _bevel(lantern, width=0.04)

    # --- roof: NISKI ciemny dach laterny z drobnym okapem (jak referencja) ---
    # radius1=1.5 (okap 0.2 nad laterną r=1.3); depth 1.4 (niski, nie szpikulec);
    # location 21.7*s -> baza Z=21.0 ~ góra laterny 21.1 (siada), czubek 22.4
    # (najwyższy). subsurf zaokrągla w kopułkowaty stożek.
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=1.5, radius2=0.0,
                                    depth=1.4 * s, location=(0, 0, 21.7 * s))
    roof = _rename("roof")
    roof.data.materials.append(roof_dark)
    _bevel(roof, width=0.04)
    _subsurf(roof, 1)

    # --- door: smukły, cienki, wpuszczony panel przy progu wieży (front -Y) ---
    # scale 0.55x0.18x1.4 (wys/szer=2.5, cienki panel), location z=2.85*s ->
    # dół drzwi 2.15 ~ spód wieży 2.0; y=-2.30 wpuszcza panel w ścianę; bevel 0.02.
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, -2.30, 2.85 * s))
    door = _rename("door")
    door.scale = (0.55, 0.18, 1.4 * s)
    door.data.materials.append(metal)
    _bevel(door, width=0.02)

    return [base, tower, gallery, lantern, roof, door]


# --------------------------------------------------------------------------- #
# Ścieżka stdlib (bez Blendera) — opis tej samej formy w kontrakcie części.
# Y-up; te same proporcje co ścieżka bpy (wysokość Z latarni -> oś Y).
# --------------------------------------------------------------------------- #

def _ring(r, y, seg):
    return [(r * math.cos(2 * math.pi * j / seg), y, r * math.sin(2 * math.pi * j / seg))
            for j in range(seg)]


def _frustum(name, r0, r1, y0, y1, rings, seg, mats, colors):
    """Frustum (cylinder/stożek ścięty) z wieloma pasmami materiałów."""
    verts = []
    for k in range(rings + 1):
        t = k / rings
        verts += _ring(r0 + (r1 - r0) * t, y0 + (y1 - y0) * t, seg)
    faces = []
    for k in range(rings):
        mat = mats[k % len(mats)]
        lo, hi = k * seg, (k + 1) * seg
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((mat, (lo + j, lo + j2, hi + j2, hi + j)))
    cb = len(verts); verts.append((0.0, y0, 0.0))
    ct = len(verts); verts.append((0.0, y1, 0.0))
    top = rings * seg
    for j in range(seg):
        j2 = (j + 1) % seg
        faces.append((mats[0], (cb, j2, j)))
        faces.append((mats[(rings - 1) % len(mats)], (ct, top + j, top + j2)))
    return {"name": name, "vertices": verts, "faces": faces, "colors": colors}


def _cone(name, r0, y0, y1, seg, mat, colors):
    verts = _ring(r0, y0, seg)
    apex = len(verts); verts.append((0.0, y1, 0.0))
    cb = len(verts); verts.append((0.0, y0, 0.0))
    faces = []
    for j in range(seg):
        j2 = (j + 1) % seg
        faces.append((mat, (j, j2, apex)))
        faces.append((mat, (cb, j2, j)))
    return {"name": name, "vertices": verts, "faces": faces, "colors": colors}


def _box(name, cx, cy, cz, sx, sy, sz, mat, colors):
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    verts = [(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
             (cx + hx, cy - hy, cz + hz), (cx - hx, cy - hy, cz + hz),
             (cx - hx, cy + hy, cz - hz), (cx + hx, cy + hy, cz - hz),
             (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)]
    faces = [(mat, q) for q in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
                                (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0))]
    return {"name": name, "vertices": verts, "faces": faces, "colors": colors}


def _build_stdlib(taper, s):
    r_top = 1.4 if taper else 2.4
    base = _frustum("base", 3.0, 3.0, 0.0, 2.0 * s, 1, 24,
                    ["stone"], {"stone": _STONE})
    tower = _frustum("tower", 2.4, r_top, 2.0 * s, 18.0 * s, 6, 32,
                     ["stripe_white", "stripe_red"],
                     {"stripe_white": _WHITE, "stripe_red": _RED})
    gallery = _frustum("gallery", 2.0, 2.0, 18.0 * s, 18.6 * s, 1, 28,
                       ["metal"], {"metal": _METAL})
    lantern = _frustum("lantern", 1.3, 1.3, 18.7 * s, 21.1 * s, 1, 20,
                       ["glass"], {"glass": _GLASS})
    roof = _cone("roof", 1.5, 21.0 * s, 22.4 * s, 24, "roof_dark",
                 {"roof_dark": _ROOF})
    door = _box("door", 0.0, 2.85 * s, -2.30, 0.55, 1.4 * s, 0.18, "metal",
                {"metal": _METAL})
    return [base, tower, gallery, lantern, roof, door]


def build(seed=0, taper=True, height_scale=1.0):
    """Pod Blenderem: tworzy obiekty bpy (zwraca ich listę). Bez Blendera:
    zwraca listę grup w kontrakcie części. Seed zarezerwowany (brak losowości)."""
    if bpy is not None:
        return _build_bpy(taper, height_scale)
    return _build_stdlib(taper, height_scale)
