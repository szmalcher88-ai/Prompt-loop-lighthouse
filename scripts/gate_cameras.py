#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wspólne źródło prawdy o kamerach bramy (stdlib-only).

Używają go DWA skrypty, żeby się nie rozjechały:
  * scripts/render_blender.py — ustawia realne kamery Blendera wg tych spec;
  * scripts/check_scene.py    — asercja v4 "kapliczka/mostek w kadrze głównym"
    (test frustum w przestrzeni OBJ, bez pikseli).

Przestrzeń: OBJ, Y-up, jednostki ~metry (kanoniczna przestrzeń sceny projektu).
render_blender mapuje pozycje na Z-up Blendera spójnie (obj (x,y,z) -> (x,-z,y)).
"""

import math

# name, elewacja [deg], azymut [deg] (0 = +X, 90 = +Z), współczynnik dystansu,
# pole widzenia [deg], frakcja wysokości celu (gdzie celuje kamera w pionie).
CAMERAS = [
    {"name": "main",    "elev": 32.0, "azim": -50.0, "dist": 1.45, "fov": 46.0, "target_h": 0.42},
    {"name": "profile", "elev": 6.0,  "azim": 180.0, "dist": 1.70, "fov": 40.0, "target_h": 0.35},
    {"name": "bay",     "elev": 16.0, "azim": 90.0,  "dist": 1.15, "fov": 50.0, "target_h": 0.20},
]


def _norm(v):
    n = math.sqrt(sum(c * c for c in v)) or 1e-9
    return [c / n for c in v]


def bounds_metrics(verts):
    """(center, radius_xz, height) z listy (x,y,z)."""
    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]; zs = [v[2] for v in verts]
    center = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)
    radius_xz = max(max(xs) - min(xs), max(zs) - min(zs)) / 2
    height = max(ys) - min(ys)
    return center, radius_xz, height


def camera_position(center, radius_xz, height, spec):
    el = math.radians(spec["elev"]); az = math.radians(spec["azim"])
    dist = spec["dist"] * (2 * radius_xz) + 0.5 * height
    return (
        center[0] + dist * math.cos(el) * math.cos(az),
        center[1] + dist * math.sin(el),
        center[2] + dist * math.cos(el) * math.sin(az),
    )


def camera_target(center, height, spec):
    return (center[0], center[1] + spec["target_h"] * height, center[2])


def in_frustum(point, center, radius_xz, height, spec, margin=1.0):
    """Czy punkt leży w stożku widzenia kamery (przybliżenie frustum: kąt od osi
    patrzenia < fov/2 * margin i punkt przed kamerą)."""
    pos = camera_position(center, radius_xz, height, spec)
    tgt = camera_target(center, height, spec)
    axis = _norm([tgt[i] - pos[i] for i in range(3)])
    v = [point[i] - pos[i] for i in range(3)]
    vn = _norm(v)
    cosang = sum(vn[i] * axis[i] for i in range(3))
    if cosang <= 0:
        return False
    ang = math.degrees(math.acos(max(-1.0, min(1.0, cosang))))
    return ang <= spec["fov"] / 2 * margin


def camera_facing(point, center, radius_xz, height, spec):
    """Czy punkt leży po STRONIE kamery względem środka wyspy (nie schowany za
    centralnym masywem w ujęciu 3/4). Frustum z daleka obejmuje całą wyspę, więc
    sama przynależność do stożka to za mało — to jest realny warunek widoczności."""
    pos = camera_position(center, radius_xz, height, spec)
    to_cam = (pos[0] - center[0], pos[2] - center[2])
    to_pt = (point[0] - center[0], point[2] - center[2])
    return to_cam[0] * to_pt[0] + to_cam[1] * to_pt[1] > 0


def main_spec():
    return CAMERAS[0]
