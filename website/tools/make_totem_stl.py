"""Generates public/models/totem.stl: the floor-standing signage totem in the hero.

Written as a script rather than checked in as an opaque binary so the shape can be tweaked by
changing a number here and re-running it. Units are millimetres, matching a real 55 inch
portrait totem, and the Vue component scales the whole thing down to fit its scene.

    python3 tools/make_totem_stl.py

The screen itself is NOT in this mesh. It is a separate plane in the scene carrying the
canvas texture, sitting a hair in front of the panel's face, because STL has no UVs to map a
texture onto.
"""

import math
import pathlib
import struct

# --- The totem, in millimetres -------------------------------------------------------------
PANEL_W, PANEL_H, PANEL_D = 620.0, 1780.0, 58.0
BASE_W, BASE_H, BASE_D = 700.0, 62.0, 430.0
WHEEL_R, WHEEL_W = 48.0, 34.0
BASE_Y = 2 * WHEEL_R          # the base sits on top of the wheels
PANEL_Y = BASE_Y + BASE_H     # and the panel rises out of the base

Tri = tuple[tuple[float, float, float], ...]


def box(cx: float, cy: float, cz: float, w: float, h: float, d: float) -> list[Tri]:
    """Twelve triangles for an axis-aligned box centred on (cx, cy, cz)."""
    x0, x1 = cx - w / 2, cx + w / 2
    y0, y1 = cy - h / 2, cy + h / 2
    z0, z1 = cz - d / 2, cz + d / 2
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [(0, 2, 1), (0, 3, 2),   # back
             (4, 5, 6), (4, 6, 7),   # front
             (0, 4, 7), (0, 7, 3),   # left
             (1, 2, 6), (1, 6, 5),   # right
             (3, 7, 6), (3, 6, 2),   # top
             (0, 1, 5), (0, 5, 4)]   # bottom
    return [(v[a], v[b], v[c]) for a, b, c in faces]


def cylinder_x(cx: float, cy: float, cz: float, r: float, length: float, seg: int = 24) -> list[Tri]:
    """A cylinder lying along X: the wheels."""
    x0, x1 = cx - length / 2, cx + length / 2
    ring = [(cy + r * math.cos(2 * math.pi * i / seg), cz + r * math.sin(2 * math.pi * i / seg))
            for i in range(seg)]
    tris: list[Tri] = []
    for i in range(seg):
        y0, z0 = ring[i]
        y1, z1 = ring[(i + 1) % seg]
        tris += [((x0, y0, z0), (x1, y0, z0), (x1, y1, z1)),
                 ((x0, y0, z0), (x1, y1, z1), (x0, y1, z1)),
                 ((x0, cy, cz), (x0, y1, z1), (x0, y0, z0)),      # near cap
                 ((x1, cy, cz), (x1, y0, z0), (x1, y1, z1))]      # far cap
    return tris


def build() -> list[Tri]:
    tris: list[Tri] = []
    tris += box(0, PANEL_Y + PANEL_H / 2, 0, PANEL_W, PANEL_H, PANEL_D)
    tris += box(0, BASE_Y + BASE_H / 2, 0, BASE_W, BASE_H, BASE_D)
    # A shallow plinth under the base, as the reference has.
    tris += box(0, BASE_Y - 18, 0, BASE_W - 90, 36, BASE_D - 70)
    for sx in (-1, 1):
        for sz in (-1, 1):
            tris += cylinder_x(sx * (BASE_W / 2 - 60), WHEEL_R, sz * (BASE_D / 2 - 70), WHEEL_R, WHEEL_W)
    return tris


def normal(t: Tri) -> tuple[float, float, float]:
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / length, ny / length, nz / length


def write_binary_stl(path: pathlib.Path, tris: list[Tri]) -> None:
    with path.open('wb') as f:
        f.write(b'Paskall signage totem'.ljust(80, b'\0'))
        f.write(struct.pack('<I', len(tris)))
        for t in tris:
            f.write(struct.pack('<3f', *normal(t)))
            for v in t:
                f.write(struct.pack('<3f', *v))
            f.write(struct.pack('<H', 0))


if __name__ == '__main__':
    out = pathlib.Path(__file__).resolve().parent.parent / 'public' / 'models' / 'totem.stl'
    out.parent.mkdir(parents=True, exist_ok=True)
    tris = build()
    write_binary_stl(out, tris)
    print(f'{out.relative_to(out.parents[2])}: {len(tris)} triangles, {out.stat().st_size / 1024:.0f} KB')
    print(f'screen face sits at z = {PANEL_D / 2:.1f}, panel spans y {PANEL_Y:.0f} to {PANEL_Y + PANEL_H:.0f}')
