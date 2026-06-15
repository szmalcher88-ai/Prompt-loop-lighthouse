# -*- coding: utf-8 -*-
"""Część w kontrakcie bpy: drewniany pomost na palach — pilot domknięcia
hybrydy na bpy (pierwszy drobiazg przeniesiony z ręcznego OBJ na ścieżkę bpy).

Nośnik styku v5 (scripts/check_scene): pomost styka się z plażą zatoczki i sięga
>= 8 m w morze; jest też nośnikiem rekwizytów (barrel/crate). Reużywa
parts/pier.py (deck/piles/rail/bollards). Pod Blenderem: cztery obiekty z małym
bevel (zaokrąglone krawędzie drewna) + materiały proceduralne; BEZ subsurf
(rozmyłby klepki i pale). Headless (bpy=None) zwraca grupy stdlib — check_pier
i check_parts działają na tej samej formie. Interfejs build(seed, **params)
jak pier.py.

Pozycję w scenie (dwa współliniowe przęsła, dz wzdłuż Z, oś x=0, woda y=0)
nadaje assembler parts/scene_bpy.py; ta część buduje pojedyncze przęsło
w lokalnych współrzędnych Y-up (z=0 morski koniec .. z=length ladowy).
"""

import importlib.util
from pathlib import Path

try:
    import bpy
except ImportError:
    bpy = None

CONTRACT_VERSION = 3

_spec = importlib.util.spec_from_file_location(
    "pier_obj", Path(__file__).resolve().parent / "pier.py")
pier_obj = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pier_obj)


def _mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    return m


def _mesh_from_group(group, bevel=0.02):
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
    groups = pier_obj.build(seed=seed, **params)
    if bpy is not None:
        return [_mesh_from_group(g) for g in groups]
    return groups
