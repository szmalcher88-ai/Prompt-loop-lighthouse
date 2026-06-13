#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helpery geometryczne na AABB (stdlib-only) — wspólne dla asercji relacji
przestrzennych (check_scene v5, LESSON-004) i przyszłych rund.

AABB reprezentujemy jako krotkę (xmin, xmax, ymin, ymax, zmin, zmax).
Wszystkie progi tolerancji są argumentami — żadnych ukrytych „blisko".
"""


def aabb(points):
    """AABB z iterowalnych (x, y, z)."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def _overlap(lo_a, hi_a, lo_b, hi_b):
    """Długość przecięcia dwóch przedziałów 1D (0, gdy rozłączne)."""
    return max(0.0, min(hi_a, hi_b) - max(lo_a, lo_b))


def overlap_extents(a, b):
    """(ox, oy, oz) — długości przenikania AABB na każdej osi (0 = brak)."""
    return (
        _overlap(a[0], a[1], b[0], b[1]),
        _overlap(a[2], a[3], b[2], b[3]),
        _overlap(a[4], a[5], b[4], b[5]),
    )


def penetrates(a, b, tol):
    """Czy bryły A i B przenikają OBJĘTOŚCIOWO: przecięcie na KAŻDEJ z 3 osi
    większe niż tol. Stykanie się ścianami (przecięcie ~0 na jednej osi) nie
    jest przenikaniem — tol odsiewa szum i lekkie dotknięcia."""
    ox, oy, oz = overlap_extents(a, b)
    return ox > tol and oy > tol and oz > tol


def distance_xz(a, b):
    """Najmniejsza odległość między AABB w rzucie XZ (0, gdy się nachodzą)."""
    dx = max(0.0, max(a[0] - b[1], b[0] - a[1]))
    dz = max(0.0, max(a[4] - b[5], b[4] - a[5]))
    return (dx * dx + dz * dz) ** 0.5


def rests_on(box, h, tol):
    """Czy dno AABB (ymin) spoczywa na poziomie h w tolerancji tol."""
    return abs(box[2] - h) <= tol


def long_axis(box):
    """Oś dłuższa w poziomie: 'x' lub 'z'."""
    return "x" if (box[1] - box[0]) >= (box[5] - box[4]) else "z"


def axis_ends_xz(box):
    """Dwa końce AABB wzdłuż dłuższej osi poziomej, jako (x, z) w środku
    pozostałych osi — do próbkowania terenu pod końcami schodów/mostka."""
    cx = (box[0] + box[1]) / 2
    cz = (box[4] + box[5]) / 2
    if long_axis(box) == "x":
        return (box[0], cz), (box[1], cz)
    return (cx, box[4]), (cx, box[5])
