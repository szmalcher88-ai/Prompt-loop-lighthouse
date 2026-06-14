# -*- coding: utf-8 -*-
"""Część RDZENIA w kontrakcie bpy (M4): WYSPA tarasowa (migracja terrain).

KLUCZOWE: terrain jest fundamentem geometrycznym — checker czyta z jego
wyeksportowanej geometrii WYSOKOŚĆ terenu w danym XZ (nearest_terrain_y), a od
tego wiszą wszystkie asercje posadowienia/styku kolejnych części. Dlatego
terrain_bpy MUSI raportować te same wysokości co terrain OBJ. Osiągamy to
reużyciem tej samej parametrycznej funkcji wysokości (parts/terrain.py) i
budową siatki przez from_pydata BEZ modyfikatorów zniekształcających wysokości
(żadnego subsurf/bevel na wierzchołkach siatki — inaczej tarasy by się rozmyły
i interfejs wysokości pękłby dwa bloki dalej, przy domach).

Forma, materiały i asercje v3/v4 = jak parts/terrain.py (check_parts dla ścieżki
stdlib, scripts/test_terrain_bpy.py dla ścieżki bpy + dowód interfejsu wysokości).

Pod Blenderem: build(seed=0) tworzy obiekt 'terrain' (Blender Z-up; eksport
up_axis='Y' odtwarza OBJ Y-up identyczny z terrain OBJ). Bez Blendera: zwraca
grupy w kontrakcie części (ta sama geometria), by check_parts walidował formę.
"""

import importlib.util
import math  # noqa: F401  (re-eksport spójności; funkcje w parts/terrain.py)
from pathlib import Path

try:
    import bpy
except ImportError:
    bpy = None

CONTRACT_VERSION = 4

# reużycie sprawdzonej geometrii terenu OBJ (ta sama height(), rmax(), build())
_spec = importlib.util.spec_from_file_location(
    "terrain_obj", Path(__file__).resolve().parent / "terrain.py")
terrain_obj = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(terrain_obj)

height = terrain_obj.height          # interfejs wysokości — TEN SAM co terrain OBJ
rmax = terrain_obj.rmax


def _mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    return m


def _mesh_from_group(group):
    """Tworzy obiekt bpy z grupy kontraktu części (Y-up) -> Blender Z-up tak,
    by eksport up_axis='Y' odtworzył dokładnie geometrię Y-up grupy.
    Bez modyfikatorów: wierzchołki siatki = wysokości parametryczne (interfejs)."""
    # OBJ(x,y,z) z eksportu = (bx, bz, -by); chcemy OBJ = (x, h, z) -> Blender (x,-z,h)
    bverts = [(x, -z, y) for (x, y, z) in group["vertices"]]
    bfaces = [tuple(idx) for _mat_name, idx in group["faces"]]
    mesh = bpy.data.meshes.new(group["name"])
    mesh.from_pydata(bverts, [], bfaces)
    mesh.update()
    obj = bpy.data.objects.new(group["name"], mesh)
    bpy.context.collection.objects.link(obj)
    slot = {}
    for mat_name, rgb in group["colors"].items():
        slot[mat_name] = len(obj.data.materials)
        obj.data.materials.append(_mat(mat_name, rgb))
    for i, (mat_name, _idx) in enumerate(group["faces"]):
        obj.data.polygons[i].material_index = slot[mat_name]
    return obj


def build(seed=0, **params):
    groups = terrain_obj.build(**params)
    if bpy is not None:
        return [_mesh_from_group(g) for g in groups]
    return groups
