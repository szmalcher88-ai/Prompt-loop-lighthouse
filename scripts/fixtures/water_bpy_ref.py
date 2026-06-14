# -*- coding: utf-8 -*-
"""Część RDZENIA w kontrakcie bpy (M4): tafla morza (migracja water).

Prosta tafla na y=0 — BEZ głębi, fal, materiału zaawansowanego (to przyszły
milestone materiałowy). Jedyne zadanie: nośnik asercji zanurzenia łódki
(dno≈y=0, burty>0). Dlatego tafla MUSI zostać dokładnie na y=0 — ŻADNYCH
modyfikatorów ruszających wierzchołki (bevel/subsurf przesunęłyby je z y=0
i złamały asercję). Reużycie parts/water.py (ta sama geometria).

Pod Blenderem: build(seed=0) tworzy obiekt 'water' na y=0. Bez Blendera: zwraca
grupy w kontrakcie części (check_parts waliduje formę).
"""

import importlib.util
from pathlib import Path

try:
    import bpy
except ImportError:
    bpy = None

CONTRACT_VERSION = 1

_spec = importlib.util.spec_from_file_location(
    "water_obj", Path(__file__).resolve().parent / "water.py")
water_obj = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(water_obj)


def _mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    return m


def _mesh_from_group(group):
    # OBJ(x,y,z) = (bx, bz, -by); chcemy OBJ=(x,y,z) grupy -> Blender (x,-z,y)
    bverts = [(x, -z, y) for (x, y, z) in group["vertices"]]
    bfaces = [tuple(idx) for _m, idx in group["faces"]]
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
    # BEZ modyfikatorów — tafla zostaje dokładnie na y=0
    return obj


def build(seed=0, **params):
    groups = water_obj.build(**params)
    if bpy is not None:
        return [_mesh_from_group(g) for g in groups]
    return groups
