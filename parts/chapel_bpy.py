# -*- coding: utf-8 -*-
"""Część RDZENIA w kontrakcie bpy (M4): kapliczka na turni (migracja chapel).

Bryła z dwuspadowym dachem i sygnaturką/krzyżem (najwyższy punkt), mniejsza od
domów; sylwetka turni. Mostek (OBJ, drobiazg) nadal do niej dochodzi — asercja
ciągłości v5 w poprzek bpy↔OBJ (blok A4). Reużycie parts/chapel.py. Pod
Blenderem: jeden obiekt 'chapel' + mały bevel + materiały (kamień/dach/krzyż);
BEZ subsurf. Interfejs build(**params) jak chapel.py (check_chapel działa).
"""

import importlib.util
from pathlib import Path

try:
    import bpy
except ImportError:
    bpy = None

CONTRACT_VERSION = 3

_spec = importlib.util.spec_from_file_location(
    "chapel_obj", Path(__file__).resolve().parent / "chapel.py")
chapel_obj = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chapel_obj)


def _mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    return m


def _mesh_from_group(group, bevel=0.025):
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
    if bevel:
        b = obj.modifiers.new(name="Bevel", type="BEVEL")
        b.width = bevel
        b.segments = 1
        b.limit_method = "ANGLE"
    return obj


def build(seed=0, **params):
    groups = chapel_obj.build(seed=seed, **params)
    if bpy is not None:
        return [_mesh_from_group(g) for g in groups]
    return groups
