# -*- coding: utf-8 -*-
"""Część RDZENIA w kontrakcie bpy (M4): dom mieszkalny (migracja house).

Trzy archetypy (mur pruski / kamienna chata / dwukondygnacyjny) rozróżnialne
GEOMETRYCZNIE, bevel na bryle (zaokrąglone krawędzie zamiast kanciastych),
materiały per część (ściana/dach/okno/komin/drzwi/fundament). Reużycie
parts/house.py (ta sama forma i asercje v1+v2+v3; check_parts waliduje ścieżkę
stdlib, scripts/test_bpy_parts.py — eksport bpy: 3 archetypy różne + determinizm).

Interfejs build(**params) jak house.py (jeden dom; archetype/width/.../seed),
więc check_house_v3 (wołające build(archetype=a)) działa bez zmian. Pod
Blenderem grupy domu są SCALONE w jeden obiekt 'house...' (scena traktuje dom
jako jedną bryłę: AABB, posadowienie, kolizje). BEZ subsurf (zaokrągliłby dom
w blob i ruszył wysokości); bevel mały, by nie naruszyć asercji.

POSADOWIENIE (uwaga M4): interfejs wysokości terenu ma ziarnistość ~0.35 m we
wnętrzu tarasów (zmierzone), ~3-5 m przy klifach. Tolerancja posadowienia 0.6 m
w check_scene jest adekwatna TYLKO dla domów we wnętrzu tarasów — layout (A4)
musi trzymać domy z dala od krawędzi klifów. To ograniczenie layoutu, nie tolerancji.
"""

import importlib.util
from pathlib import Path

try:
    import bpy
except ImportError:
    bpy = None

CONTRACT_VERSION = 3

_spec = importlib.util.spec_from_file_location(
    "house_obj", Path(__file__).resolve().parent / "house.py")
house_obj = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(house_obj)


def _mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    return m


def _merged_object(groups, name):
    """Scal grupy domu (Y-up) w jeden obiekt bpy (Z-up: (x,-z,y)), materiały
    per ścianka, mały bevel. Indeksy ścianek przesuwane przy scalaniu."""
    verts, faces, fmat = [], [], []
    colors = {}
    for g in groups:
        base = len(verts)
        verts += [(x, -z, y) for (x, y, z) in g["vertices"]]
        for mat_name, idx in g["faces"]:
            faces.append(tuple(base + i for i in idx))
            fmat.append(mat_name)
        colors.update(g["colors"])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    slot = {}
    for mat_name in dict.fromkeys(fmat):
        slot[mat_name] = len(obj.data.materials)
        obj.data.materials.append(_mat(mat_name, colors.get(mat_name, (0.7, 0.7, 0.7))))
    for i, mat_name in enumerate(fmat):
        obj.data.polygons[i].material_index = slot[mat_name]
    bev = obj.modifiers.new(name="Bevel", type="BEVEL")
    bev.width = 0.03
    bev.segments = 1
    bev.limit_method = "ANGLE"
    return obj


def build(seed=0, **params):
    groups = house_obj.build(seed=seed, **params)
    if bpy is not None:
        name = params.get("name", "house_" + params.get("archetype", "timber"))
        return [_merged_object(groups, name)]
    return groups
