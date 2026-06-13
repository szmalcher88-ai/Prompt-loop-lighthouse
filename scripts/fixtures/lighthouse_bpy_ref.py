# -*- coding: utf-8 -*-
"""Referencyjny builder latarni w bpy (M3) — WZORZEC nowego kontraktu części.
„Fixture jako spec": pętla tworzy parts/lighthouse_bpy.py na podstawie tego pliku.

build(seed=0) tworzy w bieżącej scenie bpy obiekty nazwane jak wymagane grupy
(base/tower/gallery/lantern/roof/door), z modyfikatorami (bevel + subdivision)
i materiałami proceduralnymi (kamień, naprzemienne pasy biel/czerwień na wieży,
szkło laterny, metal). NIE eksportuje — eksport robi scripts/bpy_build.py.

Forma odpowiada scripts/check_lighthouse.py (pionowa kolejność części, drzwi
w dolnej wieży, dach najwyżej, wieża zwęża się ku górze). Determinizm: brak
losowości; seed zarezerwowany (kontrakt), wynik niezależny od seeda.

Budujemy w Blenderze Z-up (wysokość = Z); eksporter (up_axis='Y') zamienia na
OBJ Y-up, którego oczekuje checker.
"""

import bpy


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


def build(seed=0, taper=True, height_scale=1.0):
    s = height_scale
    stone = _mat("stone", (0.46, 0.43, 0.39))
    white = _mat("stripe_white", (0.92, 0.92, 0.90))
    red = _mat("stripe_red", (0.78, 0.12, 0.10))
    glass = _mat("glass", (0.55, 0.75, 0.85), rough=0.1)
    metal = _mat("metal", (0.30, 0.32, 0.34), rough=0.4)

    # --- base: skalisty cokół (cylinder) ---
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=3.0, depth=2.0 * s,
                                        location=(0, 0, 1.0 * s))
    base = _rename("base")
    base.data.materials.append(stone)
    _bevel(base, width=0.12)
    _subsurf(base, 1)

    # --- tower: zwężający się stożek w pasy (biel/czerwień naprzemiennie) ---
    r_bottom, r_top = 2.4, (1.4 if taper else 2.4)
    t_depth = 16.0 * s
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=r_bottom, radius2=r_top,
                                    depth=t_depth, location=(0, 0, 10.0 * s))
    tower = _rename("tower")
    tower.data.materials.append(white)
    tower.data.materials.append(red)
    stripe_h = t_depth / 6.0
    for poly in tower.data.polygons:
        band = int((poly.center.z + t_depth / 2) / stripe_h)
        poly.material_index = band % 2
    _bevel(tower, width=0.05)
    _subsurf(tower, 1)

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

    # --- roof: stożkowy dach (najwyższy punkt) ---
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=1.6, radius2=0.0,
                                    depth=2.2 * s, location=(0, 0, 22.6 * s))
    roof = _rename("roof")
    roof.data.materials.append(red)
    _bevel(roof, width=0.04)
    _subsurf(roof, 1)

    # --- door: drzwi w dolnej części wieży (front -Y) ---
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, -2.15, 3.2 * s))
    door = _rename("door")
    door.scale = (0.8, 0.35, 1.7 * s)
    door.data.materials.append(metal)
    _bevel(door, width=0.05)

    return [base, tower, gallery, lantern, roof, door]
