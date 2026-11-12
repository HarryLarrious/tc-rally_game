#!/usr/bin/env python3
"""Generate the rally car: one resource-pack model per part, plus the part spec.

    python3 pack/src/car_parts.py

Writes:
  pack/assets/rally/models/item/car/<model>.json   cuboid models (intact, and _damaged)
  pack/assets/rally/items/car/<model>.json         item definitions (tints, damage state)
  pack/assets/rally/textures/item/car/<mat>.png    material textures
  car/parts.json                                   the part spec the game code reads
  tools/viewer/car_data.js                         the same data for the 3D viewer

This file is the single source of truth for the car. Geometry is written in
car-frame meters (1 m = 1 block):

  +X left, +Y up, +Z forward. Origin: on the ground, centered between the
  axles. A car entity at yaw 0 faces +Z (south), and its left is +X (east).

Each part has a pivot (car frame). Its model is built around that pivot, so
the game places a part with: translate(pivot) * rotate(rest) * animate.
Models are half scale (MODEL_SCALE): 8 model units = 1 m, so a part may reach
3 m from its pivot inside Minecraft's -16..32 element limit. Each item
definition carries a "transformation" that scales the model back up by 2
about its center and undoes the 180 degree Y turn that item displays apply,
so an item display with an identity matrix shows the part at full size, the
right way round, with its pivot on the entity.

Needs Pillow.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS = ROOT / "pack/assets/rally"
NS = "rally"
MODEL_SCALE = 0.5            # model is half size; display scale = 2
UNITS_PER_M = 16 * MODEL_SCALE

# ---------------------------------------------------------------------------
# Materials. Each is one texture; "tint" names the custom_model_data color
# slot the face takes (0 = paint, 1 = accent). "dmg" is the texture used by the
# damaged variant of a part.
# ---------------------------------------------------------------------------

MATERIALS: dict[str, dict] = {
    "paint":     {"tint": 0, "dmg": "paint_dmg"},
    "accent":    {"tint": 1, "dmg": "accent_dmg"},
    "plastic":   {"dmg": "plastic_dmg"},
    "glass":     {"dmg": "glass_dmg"},
    "rubber":    {"dmg": "rubber_dmg"},
    "sidewall":  {},
    "rim":       {"tint": 1},
    "steel":     {},
    "darksteel": {},
    "alloy":     {},
    "valve":     {},
    "exhaust":   {},
    "spring":    {},
    "caliper":   {},
    "disc":      {},
    "cage":      {},
    "seat":      {},
    "grille":    {},
    "radiator":  {},
    "fuelcell":  {},
    "mudflap":   {"tint": 1},
    "headlight": {"emit": 15},
    "foglight":  {"emit": 15},
    "taillight": {"emit": 10},
}


def _noise(img: Image.Image, amount: int, seed: int) -> None:
    rnd = random.Random(seed)
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            n = rnd.randint(-amount, amount)
            px[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)), a)


def _flat(rgb, size=16, noise=4, seed=1, alpha=255) -> Image.Image:
    img = Image.new("RGBA", (size, size), (*rgb, alpha))
    if noise:
        _noise(img, noise, seed)
    return img


def _scratches(img: Image.Image, seed: int, color, count=7) -> Image.Image:
    img = img.copy()
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    w = img.width
    for _ in range(count):
        x0, y0 = rnd.randint(0, w - 1), rnd.randint(0, w - 1)
        x1, y1 = x0 + rnd.randint(-6, 6), y0 + rnd.randint(-3, 3)
        d.line((x0, y0, x1, y1), fill=color, width=1)
    return img


def make_textures() -> dict[str, Image.Image]:
    t: dict[str, Image.Image] = {}
    # Paint and accent are near white so the tint sets the color.
    t["paint"] = _flat((236, 236, 236), noise=3, seed=2)
    t["paint_dmg"] = _scratches(_flat((222, 222, 222), noise=4, seed=3), 4, (150, 150, 150, 255), 4)
    t["accent"] = _flat((240, 240, 240), noise=2, seed=5)
    t["accent_dmg"] = _scratches(_flat((222, 222, 222), noise=4, seed=6), 7, (150, 150, 150, 255), 4)
    t["plastic"] = _flat((38, 38, 41), noise=4, seed=8)
    t["plastic_dmg"] = _scratches(_flat((44, 44, 46), noise=7, seed=9), 10, (95, 95, 95, 255))

    glass = Image.new("RGBA", (16, 16), (150, 185, 205, 120))
    d = ImageDraw.Draw(glass)
    d.line((2, 13, 9, 2), fill=(225, 240, 250, 150))
    d.line((5, 14, 12, 4), fill=(210, 230, 245, 135))
    t["glass"] = glass
    cracked = Image.new("RGBA", (16, 16), (170, 195, 210, 165))
    d = ImageDraw.Draw(cracked)
    for a in range(0, 360, 40):  # star crack from an impact point
        r = math.radians(a)
        d.line((10, 6, 10 + 9 * math.cos(r), 6 + 9 * math.sin(r)), fill=(240, 245, 250, 230))
    d.ellipse((8, 4, 12, 8), outline=(250, 250, 250, 240))
    t["glass_dmg"] = cracked

    tread = Image.new("RGBA", (16, 16), (30, 30, 32, 255))
    d = ImageDraw.Draw(tread)
    for y in range(0, 16, 4):  # gravel blocks
        off = 2 if (y // 4) % 2 else 0
        for x in range(off, 16, 5):
            d.rectangle((x, y, x + 2, y + 2), fill=(48, 48, 50, 255))
    t["rubber"] = tread
    t["rubber_dmg"] = _scratches(_flat((40, 38, 36), noise=10, seed=11), 12, (90, 86, 80, 255), 12)
    t["sidewall"] = _flat((27, 27, 29), noise=0)
    t["rim"] = _flat((235, 235, 235), noise=0)

    t["steel"] = _flat((150, 153, 158), noise=6, seed=12)
    t["darksteel"] = _flat((62, 64, 68), noise=5, seed=13)
    t["alloy"] = _flat((182, 184, 186), noise=7, seed=14)
    t["valve"] = _flat((170, 30, 32), noise=6, seed=15)
    t["exhaust"] = _flat((105, 84, 70), noise=12, seed=16)
    t["spring"] = _flat((228, 182, 30), noise=5, seed=17)
    t["caliper"] = _flat((214, 40, 32), noise=4, seed=18)
    disc = _flat((128, 128, 132), noise=10, seed=19)
    ImageDraw.Draw(disc).ellipse((5, 5, 10, 10), outline=(90, 90, 94, 255))
    t["disc"] = disc
    t["cage"] = _flat((70, 72, 76), noise=4, seed=20)
    seat = _flat((30, 31, 36), noise=5, seed=21)
    ImageDraw.Draw(seat).line((7, 0, 7, 15), fill=(160, 25, 25, 255), width=2)
    t["seat"] = seat
    grille = Image.new("RGBA", (16, 16), (20, 20, 22, 255))
    d = ImageDraw.Draw(grille)
    for i in range(0, 16, 3):
        d.line((i, 0, i, 15), fill=(62, 62, 66, 255))
        d.line((0, i, 15, i), fill=(62, 62, 66, 255))
    t["grille"] = grille
    rad = Image.new("RGBA", (16, 16), (150, 152, 150, 255))
    d = ImageDraw.Draw(rad)
    for x in range(0, 16, 2):
        d.line((x, 0, x, 15), fill=(95, 98, 96, 255))
    t["radiator"] = rad
    t["fuelcell"] = _flat((236, 120, 20), noise=5, seed=22)
    flap = _flat((236, 236, 236), noise=3, seed=23)
    ImageDraw.Draw(flap).rectangle((0, 12, 15, 15), fill=(30, 30, 30, 255))
    t["mudflap"] = flap

    def lens(rgb, rim):
        img = Image.new("RGBA", (16, 16), (*rim, 255))
        ImageDraw.Draw(img).ellipse((1, 1, 14, 14), fill=(*rgb, 255))
        ImageDraw.Draw(img).ellipse((4, 3, 8, 7), fill=(255, 255, 255, 255))
        return img

    t["headlight"] = lens((250, 246, 225), (200, 200, 200))
    t["foglight"] = lens((255, 220, 90), (60, 60, 60))
    t["taillight"] = _flat((210, 25, 25), noise=6, seed=24)
    return t


# ---------------------------------------------------------------------------
# Geometry. An element is an axis-aligned box in part-local meters with an
# optional Euler XYZ rotation (degrees, Minecraft's rotationZYX order) about a
# local origin.
# ---------------------------------------------------------------------------

FACES = ("north", "south", "east", "west", "up", "down")


@dataclass
class Elem:
    a: tuple            # min corner, local meters
    b: tuple            # max corner
    mat: str
    rot: tuple | None = None       # (x, y, z) degrees
    origin: tuple | None = None    # local meters
    faces: tuple = FACES
    dent: bool = True              # jittered in the damaged variant


@dataclass
class Part:
    id: str
    label: str
    group: str
    parent: str | None
    pivot: tuple                   # car frame meters
    mass: float                    # kg
    hp: int
    on_break: str                  # "detach" or "fail"
    effect: str                    # what breaking it does
    model: str | None = None       # shared model name; defaults to id
    rest: tuple = (0.0, 0.0, 0.0)  # rest rotation, Euler XYZ degrees
    anim: str = "fixed"            # how the game moves it, see ANIMS
    shield: list = field(default_factory=list)  # parts that take hits before it
    links: dict = field(default_factory=dict)   # mount points shared with other parts
    elems: list = field(default_factory=list)
    attach: tuple | None = None    # where it mounts (the pivot it was built around)
    rigid: bool = False            # drawn with the car's own matrix
    damaged: bool = True           # has a damaged model variant


ANIMS = {
    "fixed": "rigid with its parent",
    "spin_x": "rolls about local X (wheels)",
    "steer_y": "turns about local Y (front uprights)",
    "swing_z": "swings about local Z (control arms: suspension travel)",
    "stretch_y": "aimed between two mount points, scaled along local Y (springs)",
    "stretch_x": "aimed between two mount points, scaled along local X (half shafts)",
    "spin_z": "rotates about local Z (steering wheel, drive shaft)",
}


def box(a, b, mat, **kw) -> Elem:
    return Elem(tuple(min(p, q) for p, q in zip(a, b)), tuple(max(p, q) for p, q in zip(a, b)), mat, **kw)


def plate(center, size, mat, rot, **kw) -> Elem:
    """Box of `size` centered on `center`, rotated about its own center."""
    h = [s / 2 for s in size]
    a = tuple(c - s for c, s in zip(center, h))
    b = tuple(c + s for c, s in zip(center, h))
    return Elem(a, b, mat, rot=rot, origin=tuple(center), **kw)


def beam(p, q, w, h, mat, **kw) -> Elem:
    """Box from point p to point q with a w (x) by h (y) cross section."""
    d = [qi - pi for pi, qi in zip(p, q)]
    length = math.sqrt(sum(c * c for c in d))
    mid = tuple((pi + qi) / 2 for pi, qi in zip(p, q))
    yaw = math.degrees(math.atan2(d[0], d[2]))
    pitch = -math.degrees(math.asin(max(-1.0, min(1.0, d[1] / length))))
    return plate(mid, (w, h, length), mat, (round(pitch, 3), round(yaw, 3), 0.0), **kw)


def prism(center, axis, radius, length, sides, mat, faces_end=True, start=0.0, **kw) -> list[Elem]:
    """Regular `sides`-gon prism along a local axis, made of sides/2 rotated boxes.

    Each box is one pair of opposite polygon sides; their union is exactly the
    polygon. End faces overlap, so give them a flat texture.
    """
    apo = radius * math.cos(math.pi / sides)
    side = 2 * apo * math.tan(math.pi / sides)
    out = []
    ax = "xyz".index(axis)
    for k in range(sides // 2):
        ang = start + k * 360.0 / sides
        size = [0.0, 0.0, 0.0]
        size[ax] = length
        # the two in-plane axes: the box's "radial" size is 2*apothem along one, side along the other
        u, v = [i for i in range(3) if i != ax]
        size[u] = side
        size[v] = 2 * apo
        rot = [0.0, 0.0, 0.0]
        rot[ax] = round(ang, 3)
        side_faces = {"x": ("east", "west"), "y": ("up", "down"), "z": ("north", "south")}[axis]
        radial = {0: ("east", "west"), 1: ("up", "down"), 2: ("north", "south")}[v]
        faces = list(radial) + (list(side_faces) if faces_end else [])
        out.append(plate(center, size, mat, tuple(rot), faces=tuple(faces), **kw))
    return out


def helix(base_y, top_y, radius, coils, seg_per_coil, wire, mat) -> list[Elem]:
    pts = []
    n = coils * seg_per_coil
    for i in range(n + 1):
        t = i / n
        a = 2 * math.pi * coils * t
        pts.append((radius * math.cos(a), base_y + (top_y - base_y) * t, radius * math.sin(a)))
    return [beam(pts[i], pts[i + 1], wire, wire, mat) for i in range(n)]


def to_local(elems: list[Elem], pivot) -> list[Elem]:
    """Shift elements written in car-frame meters to part-local meters."""
    out = []
    for e in elems:
        sh = lambda p: tuple(pi - qi for pi, qi in zip(p, pivot))
        out.append(Elem(sh(e.a), sh(e.b), e.mat, e.rot, sh(e.origin) if e.origin else None, e.faces, e.dent))
    return out


def mirror_x(elems: list[Elem]) -> list[Elem]:
    """Mirror car-frame elements left to right (x -> -x)."""
    out = []
    for e in elems:
        a = (-e.b[0], e.a[1], e.a[2])
        b = (-e.a[0], e.b[1], e.b[2])
        rot = (e.rot[0], -e.rot[1], -e.rot[2]) if e.rot else None
        origin = (-e.origin[0], e.origin[1], e.origin[2]) if e.origin else None
        faces = tuple({"east": "west", "west": "east"}.get(f, f) for f in e.faces)
        out.append(Elem(a, b, e.mat, rot, origin, faces, e.dent))
    return out


def center_of(elems: list[Elem]) -> tuple:
    lo = [min(e.a[i] for e in elems) for i in range(3)]
    hi = [max(e.b[i] for e in elems) for i in range(3)]
    return tuple(round((l + h) / 2, 3) for l, h in zip(lo, hi))


# ---------------------------------------------------------------------------
# Car dimensions (meters).
# ---------------------------------------------------------------------------

WHEELBASE = 2.50
AXLE_F = WHEELBASE / 2
AXLE_R = -WHEELBASE / 2
TRACK_X = 0.77           # wheel center offset from centerline
WHEEL_R = 0.32
WHEEL_W = 0.22
HUB_Y = WHEEL_R
ARM_IN_X = 0.30          # control arm inboard pivot
ARM_Y = 0.24
ARM_OUT = (0.64, 0.20)   # ball joint (x, y)
STRUT_TOP = (0.56, 0.82)
SPRING_BOT_ON_ARM = 0.22  # along the arm from its pivot
DIFF_OUT_X = 0.13

PARTS: list[Part] = []


def add(p: Part, car_elems: list[Elem] | None = None, local_elems: list[Elem] | None = None, pivot=None):
    if car_elems is not None:
        if pivot is None:
            pivot = center_of(car_elems)
        p.pivot = tuple(round(c, 3) for c in pivot)
        p.elems = to_local(car_elems, p.pivot)
    else:
        p.elems = local_elems
    PARTS.append(p)
    return p


# ---------------------------------------------------------------- chassis
def chassis():
    e = [
        box((-0.72, 0.28, -1.20), (0.72, 0.34, 0.95), "darksteel", dent=False),            # floor
        box((-0.15, 0.34, -1.00), (0.15, 0.60, 0.92), "darksteel", dent=False),            # tunnel
        box((-0.72, 0.34, 0.92), (0.72, 0.95, 0.97), "darksteel", dent=False),             # firewall
        box((-0.72, 0.45, -1.88), (0.72, 0.50, -1.20), "darksteel", dent=False),           # boot floor
        box((-0.72, 0.34, -1.22), (0.72, 0.62, -1.18), "darksteel", dent=False),           # rear bulkhead
    ]
    for s in (1, -1):
        def X(a, b):
            return (min(s * a, s * b), max(s * a, s * b))
        x0, x1 = X(0.72, 0.85)
        e.append(box((x0, 0.28, -0.88), (x1, 0.50, 0.88), "darksteel", dent=False))      # sill
        x0, x1 = X(0.35, 0.45)
        e.append(box((x0, 0.35, 0.95), (x1, 0.55, 1.90), "steel", dent=False))           # front rail
        x0, x1 = X(0.40, 0.50)
        e.append(box((x0, 0.38, -1.88), (x1, 0.55, -1.20), "steel", dent=False))         # rear rail
        x0, x1 = X(0.50, 0.62)
        for z0, z1 in ((1.15, 1.35), (-1.35, -1.15)):
            e.append(box((x0, 0.50, z0), (x1, 0.86, z1), "darksteel", dent=False))       # strut tower
        x0, x1 = X(0.45, 0.62)
        e.append(box((x0, 0.50, 1.10), (x1, 0.56, 1.40), "darksteel", dent=False))       # tower brace foot
    e.append(box((-0.45, 0.50, 1.84), (0.45, 0.56, 1.90), "steel", dent=False))          # front crossmember
    add(Part("chassis", "Chassis (floor pan, rails, towers)", "structure", None, (0, 0, 0), 330, 400, "fail",
             "Bent chassis: alignment pull and weaker crash absorption; at 0 the car is wrecked",
             damaged=False), e)


# ---------------------------------------------------------------- body shell
def shell():
    e = [box((-0.70, 1.36, -1.10), (0.70, 1.41, 0.35), "paint")]                        # roof
    e.append(box((-0.70, 0.92, 0.86), (0.70, 0.97, 1.02), "plastic"))                    # cowl
    e.append(box((-0.30, 1.41, -0.40), (0.30, 1.45, -0.05), "plastic"))                  # roof vent
    for s in (1, -1):
        e.append(beam((s * 0.72, 0.95, 0.92), (s * 0.69, 1.37, 0.35), 0.06, 0.06, "paint"))     # A pillar
        e.append(box((min(s * 0.76, s * 0.81), 0.95, -0.34), (max(s * 0.76, s * 0.81), 1.37, -0.26), "paint"))  # B pillar
        e.append(beam((s * 0.70, 1.37, -1.10), (s * 0.80, 1.00, -1.92), 0.07, 0.06, "paint"))  # C pillar
        e.append(box((min(s * 0.76, s * 0.79), 0.96, -1.05), (max(s * 0.76, s * 0.79), 1.33, -0.34), "glass"))  # quarter glass
        e.append(box((min(s * 0.70, s * 0.79), 1.33, -1.10), (max(s * 0.70, s * 0.79), 1.38, 0.35), "paint"))  # roof rail
    add(Part("shell", "Body shell (roof, pillars)", "structure", "chassis", (0, 0, 0), 60, 220, "fail",
             "Crushed roof in a rollover: cosmetic, and the cage takes over"), e)


def cage():
    t = 0.045
    e = []
    for s in (1, -1):
        x = s * 0.62
        e.append(beam((x, 0.34, -0.36), (x, 1.30, -0.36), t, t, "cage"))                # main hoop leg
        e.append(beam((x, 0.38, 0.80), (x, 0.95, 0.80), t, t, "cage"))                  # front hoop leg
        e.append(beam((x, 0.95, 0.80), (s * 0.60, 1.30, 0.30), t, t, "cage"))           # A pillar bar
        e.append(beam((s * 0.60, 1.30, 0.30), (x, 1.30, -0.36), t, t, "cage"))          # roof bar
        e.append(beam((x, 1.30, -0.36), (s * 0.55, 0.50, -1.15), t, t, "cage"))         # rear stay
        e.append(beam((x, 0.45, 0.78), (x, 0.90, -0.34), t, t, "cage"))                 # door bar X
        e.append(beam((x, 0.90, 0.78), (x, 0.45, -0.34), t, t, "cage"))
        # bucket seat
        sx = s * 0.33
        e.append(box((sx - 0.23, 0.34, -0.25), (sx + 0.23, 0.46, 0.25), "seat"))
        e.append(plate((sx, 0.80, -0.27), (0.46, 0.68, 0.08), "seat", (-10.0, 0.0, 0.0)))
        for b in (-1, 1):
            e.append(plate((sx + b * 0.21, 0.72, -0.20), (0.06, 0.50, 0.16), "seat", (-10.0, 0.0, 0.0)))
    e.append(beam((0.62, 1.30, -0.36), (-0.62, 1.30, -0.36), t, t, "cage"))              # main hoop top
    e.append(beam((0.62, 0.40, -0.36), (-0.62, 1.30, -0.36), t, t, "cage"))              # main hoop diagonal
    e.append(beam((0.62, 1.30, 0.30), (-0.62, 1.30, 0.30), t, t, "cage"))                # windscreen bar
    e.append(box((-0.68, 0.70, 0.62), (0.68, 0.90, 0.88), "plastic"))                    # dashboard
    e.append(box((-0.10, 0.34, 0.20), (0.10, 0.70, 0.62), "plastic"))                    # center console
    e.append(beam((0.0, 0.60, 0.05), (0.0, 0.78, 0.20), 0.025, 0.025, "darksteel"))      # handbrake
    add(Part("cage", "Roll cage, seats, dash", "interior", "chassis", (0, 0, 0), 45, 300, "fail",
             "Protects the crew; at 0 HP the roof crush reaches the driver (car is wrecked)", damaged=False), e)


def steering_wheel():
    # local frame: rim in the X/Y plane, column along -Z (toward the dash is +Z)
    e = []
    n, r = 12, 0.17
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        e.append(beam((r * math.cos(a0), r * math.sin(a0), 0), (r * math.cos(a1), r * math.sin(a1), 0), 0.03, 0.03, "plastic"))
    e.append(box((-0.17, -0.02, -0.015), (0.17, 0.02, 0.015), "darksteel"))               # spokes
    e.append(box((-0.02, -0.17, -0.015), (0.02, 0.0, 0.015), "darksteel"))
    e.append(box((-0.04, -0.04, -0.03), (0.04, 0.04, 0.03), "accent"))                   # hub
    e.append(box((-0.02, -0.02, 0.03), (0.02, 0.02, 0.25), "darksteel"))                 # column
    add(Part("steering_wheel", "Steering wheel", "interior", "cage", (0.33, 0.95, 0.45), 2, 40, "fail",
             "Cosmetic; turns with the front wheels", rest=(22.0, 0.0, 0.0), anim="spin_z", damaged=False),
        local_elems=e)


def glass_parts():
    ws = beam((0.0, 0.95, 0.92), (0.0, 1.365, 0.35), 1.36, 0.02, "glass")
    add(Part("windshield", "Windshield", "glass", "shell", (0, 0, 0), 12, 30, "fail",
             "Cracks, then shatters (stays in the frame as a cracked model)"), [ws])
    rw = beam((0.0, 1.365, -1.12), (0.0, 1.02, -1.88), 1.30, 0.02, "glass")
    add(Part("rear_window", "Rear window", "glass", "hatch", (0, 0, 0), 6, 20, "fail",
             "Cracks, then shatters"), [rw])


def door(side: int):
    s = side
    X = lambda a, b: (min(s * a, s * b), max(s * a, s * b))
    e = []
    x0, x1 = X(0.80, 0.86)
    e.append(box((x0, 0.45, -0.25), (x1, 0.96, 0.90), "paint"))                           # skin
    xi0, xi1 = X(0.76, 0.80)
    e.append(box((xi0, 0.50, -0.20), (xi1, 0.94, 0.85), "plastic"))                       # inner card
    gx0, gx1 = X(0.775, 0.79)
    e.append(box((gx0, 0.97, -0.24), (gx1, 1.32, 0.34), "glass"))                         # side glass
    e.append(beam((s * 0.783, 0.97, 0.80), (s * 0.783, 1.30, 0.38), 0.015, 0.06, "glass"))  # front glass wedge
    fx0, fx1 = X(0.77, 0.80)
    e.append(box((fx0, 1.32, -0.25), (fx1, 1.35, 0.36), "paint"))                         # frame top
    e.append(beam((s * 0.785, 0.96, 0.89), (s * 0.785, 1.34, 0.36), 0.03, 0.04, "paint"))  # frame front
    hx0, hx1 = X(0.86, 0.875)
    e.append(box((hx0, 0.84, -0.18), (hx1, 0.87, -0.06), "plastic"))                     # handle
    name = "door_l" if s > 0 else "door_r"
    add(Part(name, f"Door ({'left' if s > 0 else 'right'})", "body", "shell", (0, 0, 0), 18, 90, "detach",
             "Falls off; the side glass goes with it", shield=[]), e,
        pivot=(s * 0.83, 0.80, 0.86))  # hinge line
    # mirror on the door's front top corner
    m = []
    mx0, mx1 = X(0.86, 0.94)
    m.append(box((mx0, 1.00, 0.74), (mx1, 1.03, 0.78), "plastic"))                       # stalk
    hx0, hx1 = X(0.92, 1.02)
    m.append(box((hx0, 0.99, 0.70), (hx1, 1.10, 0.80), "paint"))                         # housing
    gx0, gx1 = X(0.925, 1.015)
    m.append(box((gx0, 1.0, 0.695), (gx1, 1.09, 0.70), "glass", faces=("north",)))       # mirror glass
    add(Part("mirror_l" if s > 0 else "mirror_r", f"Mirror ({'left' if s > 0 else 'right'})", "body", name,
             (0, 0, 0), 1.5, 15, "detach", "Falls off"), m, pivot=(s * 0.90, 1.02, 0.76))


def arch(zc, s, x0, x1, mat, r_in=0.40, r_out=0.46, segs=7):
    """Wheel-arch flare: a half ring of boxes around (zc, HUB_Y)."""
    e = []
    for k in range(segs):
        a0 = math.pi * k / segs
        a1 = math.pi * (k + 1) / segs
        rm = (r_in + r_out) / 2
        p = (s * (x0 + x1) / 2, HUB_Y + rm * math.sin(a0), zc + rm * math.cos(a0))
        q = (s * (x0 + x1) / 2, HUB_Y + rm * math.sin(a1), zc + rm * math.cos(a1))
        e.append(beam(p, q, x1 - x0, r_out - r_in, mat))
    return e


def fender(side: int):
    s = side
    X = lambda a, b: (min(s * a, s * b), max(s * a, s * b))
    e = []
    x0, x1 = X(0.80, 0.86)
    e.append(box((x0, 0.50, 1.66), (x1, 0.88, 1.96), "paint"))                            # ahead of the arch
    e.append(box((x0, 0.74, 0.84), (x1, 0.88, 1.66), "paint"))                            # over the arch
    e.append(box((x0, 0.50, 0.82), (x1, 0.88, 0.88), "paint"))                            # behind the arch
    tx0, tx1 = X(0.60, 0.86)
    e.append(box((tx0, 0.86, 0.84), (tx1, 0.90, 1.96), "paint"))                          # top
    nx0, nx1 = X(0.44, 0.86)
    e.append(box((nx0, 0.55, 1.94), (nx1, 0.88, 1.97), "paint"))                          # nose face
    lx0, lx1 = X(0.48, 0.80)
    e.append(box((lx0, 0.60, 1.97), (lx1, 0.80, 2.00), "plastic"))                        # lamp housing
    for c in (0.565, 0.715):
        e.append(box((s * c - 0.065, 0.635, 2.00), (s * c + 0.065, 0.765, 2.006), "headlight",
                     faces=("south",), dent=False))
    e += arch(AXLE_F, s, 0.83, 0.92, "accent")
    name = "fender_fl" if s > 0 else "fender_fr"
    add(Part(name, f"Front fender ({'left' if s > 0 else 'right'})", "body", "chassis", (0, 0, 0), 5, 60,
             "detach", "Falls off with its headlight; that side loses its low beam"), e)


def quarter(side: int):
    s = side
    X = lambda a, b: (min(s * a, s * b), max(s * a, s * b))
    e = []
    x0, x1 = X(0.80, 0.86)
    e.append(box((x0, 0.50, -1.94), (x1, 1.00, -1.66), "paint"))                          # behind the arch
    e.append(box((x0, 0.74, -1.66), (x1, 1.00, -0.84), "paint"))                          # over the arch
    e.append(box((x0, 0.50, -0.88), (x1, 1.00, -0.25), "paint"))                          # ahead of the arch
    tx0, tx1 = X(0.68, 0.86)
    e.append(box((tx0, 0.96, -1.92), (tx1, 1.00, -0.34), "paint"))                        # shoulder
    rx0, rx1 = X(0.45, 0.86)
    e.append(box((rx0, 0.55, -1.97), (rx1, 1.00, -1.93), "paint"))                        # rear face
    lx0, lx1 = X(0.52, 0.82)
    e.append(box((lx0, 0.76, -1.985), (lx1, 0.93, -1.97), "taillight", faces=("north", "east", "west", "up", "down"),
                 dent=False))
    e += arch(AXLE_R, s, 0.83, 0.93, "accent")
    name = "quarter_rl" if s > 0 else "quarter_rr"
    add(Part(name, f"Rear quarter panel ({'left' if s > 0 else 'right'})", "body", "chassis", (0, 0, 0), 9, 80,
             "detach", "Falls off with its tail light"), e)


def mudflap(side: int, front: bool):
    s = side
    z = 0.80 if front else -1.70
    x0, x1 = (0.66, 0.88) if s > 0 else (-0.88, -0.66)
    e = [box((x0, 0.10, z - 0.01), (x1, 0.50, z + 0.01), "mudflap")]
    tag = ("f" if front else "r") + ("l" if s > 0 else "r")
    add(Part(f"mudflap_{tag}", f"Mud flap ({tag.upper()})", "body", ("fender_f" if front else "quarter_r") + tag[1],
             (0, 0, 0), 1, 10, "detach", "Torn off"), e, pivot=((x0 + x1) / 2, 0.50, z))


def hood():
    e = [plate((0.0, 0.89, 1.48), (1.24, 0.04, 0.98), "paint", (7.8, 0.0, 0.0))]
    e.append(plate((0.0, 0.935, 1.30), (0.40, 0.05, 0.30), "plastic", (7.8, 0.0, 0.0)))   # scoop
    e.append(plate((0.0, 0.937, 1.448), (0.36, 0.044, 0.01), "grille", (7.8, 0.0, 0.0), faces=("south",)))
    add(Part("hood", "Hood", "body", "chassis", (0, 0, 0), 10, 70, "detach",
             "Flies off; the engine is exposed and takes hits directly"), e, pivot=(0.0, 0.95, 1.02))


def lightpod():
    e = [box((-0.52, 0.86, 1.86), (0.52, 0.90, 1.92), "plastic")]
    for x in (-0.40, -0.14, 0.14, 0.40):
        e += prism((x, 0.95, 1.95), "z", 0.08, 0.10, 12, "plastic")
        e.append(box((x - 0.06, 0.89, 2.00), (x + 0.06, 1.01, 2.003), "foglight", faces=("south",), dent=False))
    add(Part("lightpod", "Light pod (4 lamps)", "body", "hood", (0, 0, 0), 8, 30, "detach",
             "Falls off: no long-range lights for night stages"), e)


def bumpers():
    f = [box((-0.86, 0.30, 1.90), (0.86, 0.55, 2.05), "paint"),
         box((-0.80, 0.26, 1.86), (0.80, 0.30, 2.09), "plastic"),                        # splitter
         box((-0.42, 0.55, 1.93), (0.42, 0.80, 1.98), "grille"),                         # upper grille
         box((-0.40, 0.35, 2.05), (0.40, 0.50, 2.055), "grille", faces=("south",))]      # lower intake
    for s in (1, -1):
        f.append(box((s * 0.62 - 0.07, 0.39, 2.05), (s * 0.62 + 0.07, 0.49, 2.06), "foglight",
                     faces=("south", "east", "west", "up", "down"), dent=False))
    f.append(box((0.30, 0.30, 2.05), (0.36, 0.36, 2.12), "accent"))                     # tow eye
    add(Part("bumper_f", "Front bumper", "body", "chassis", (0, 0, 0), 7, 70, "detach",
             "Absorbs front hits first; once gone the radiator takes them"), f)

    r = [box((-0.86, 0.30, -2.02), (0.86, 0.55, -1.92), "paint"),
         box((-0.70, 0.26, -1.98), (0.70, 0.30, -1.90), "plastic"),                      # diffuser
         box((-0.26, 0.42, -2.03), (0.26, 0.53, -2.02), "plastic", faces=("north",))]    # plate
    r.append(box((-0.36, 0.31, -2.08), (-0.30, 0.37, -2.02), "accent"))                 # tow eye
    add(Part("bumper_r", "Rear bumper", "body", "chassis", (0, 0, 0), 6, 60, "detach",
             "Absorbs rear hits first; once gone the fuel cell and exhaust take them"), r)


def hatch():
    e = []
    for s in (1, -1):
        e.append(beam((s * 0.67, 1.375, -1.10), (s * 0.67, 1.01, -1.90), 0.06, 0.03, "paint"))   # side rails
    e.append(box((-0.67, 1.35, -1.13), (0.67, 1.39, -1.08), "paint"))                   # top rail
    e.append(box((-0.45, 0.55, -1.98), (0.45, 1.02, -1.93), "paint"))                   # tailgate
    e.append(box((-0.06, 0.70, -1.985), (0.06, 0.74, -1.98), "plastic", faces=("north",)))  # handle
    add(Part("hatch", "Rear hatch", "body", "chassis", (0, 0, 0), 9, 70, "detach",
             "Falls off with the rear window and wing"), e, pivot=(0.0, 1.38, -1.10))


def wing():
    e = [plate((0.0, 1.16, -1.94), (1.60, 0.03, 0.30), "accent", (-6.0, 0.0, 0.0))]
    for s in (1, -1):
        e.append(box((s * 0.80 - 0.012, 1.08, -2.10), (s * 0.80 + 0.012, 1.24, -1.80), "plastic"))  # endplates
        e.append(beam((s * 0.40, 1.00, -1.90), (s * 0.40, 1.15, -1.93), 0.03, 0.06, "plastic"))   # stands
    add(Part("wing", "Rear wing", "body", "hatch", (0, 0, 0), 6, 40, "detach",
             "Falls off: less rear downforce, the tail gets loose at speed"), e)


# ---------------------------------------------------------------- powertrain
def engine():
    e = [box((-0.20, 0.40, 1.20), (0.20, 0.75, 1.76), "alloy", dent=False),               # block
         box((-0.17, 0.75, 1.24), (0.17, 0.83, 1.72), "valve", dent=False),               # cam cover
         box((-0.16, 0.33, 1.40), (0.16, 0.40, 1.72), "darksteel", dent=False),           # oil pan
         box((0.20, 0.58, 1.26), (0.32, 0.76, 1.68), "alloy", dent=False),                # intake plenum
         box((-0.30, 0.50, 1.28), (-0.20, 0.68, 1.66), "exhaust", dent=False)]            # exhaust manifold
    e += prism((-0.34, 0.66, 1.42), "x", 0.085, 0.10, 12, "steel", dent=False)            # turbo
    e += prism((0.0, 0.52, 1.785), "z", 0.085, 0.05, 12, "darksteel", dent=False)         # crank pulley
    e += prism((0.12, 0.66, 1.775), "z", 0.05, 0.05, 10, "steel", dent=False)             # alternator
    add(Part("engine", "Engine (2.0 turbo inline-4)", "powertrain", "chassis", (0, 0, 0), 145, 160, "fail",
             "Power drops with HP; at 0 it seizes. Overheats if the radiator leaks",
             shield=["hood", "radiator", "bumper_f"], damaged=False), e)


def gearbox():
    e = [box((-0.18, 0.38, 1.04), (0.18, 0.70, 1.20), "alloy", dent=False),               # bellhousing
         box((-0.12, 0.38, 0.70), (0.12, 0.58, 1.04), "alloy", dent=False),               # case
         box((-0.03, 0.58, 0.80), (0.03, 0.66, 0.86), "darksteel", dent=False)]           # shifter base
    e += prism((0.0, 0.36, 0.67), "z", 0.04, 0.06, 8, "darksteel", dent=False)            # output flange
    add(Part("gearbox", "Gearbox (6-speed sequential)", "powertrain", "engine", (0, 0, 0), 60, 140, "fail",
             "Damage drops gears: at low HP it jumps out of the top gears; at 0 no drive",
             shield=["chassis"], damaged=False), e)


def driveshaft():
    z0, z1 = 0.64, -1.10
    local = prism((0, 0, 0), "z", 0.035, z0 - z1, 8, "steel", dent=False)
    for z in ((z0 - z1) / 2 - 0.03, -(z0 - z1) / 2 + 0.03):
        local += prism((0, 0, z), "z", 0.055, 0.06, 8, "darksteel", dent=False)          # u-joints
    add(Part("driveshaft", "Center drive shaft", "powertrain", "chassis", (0.0, 0.36, (z0 + z1) / 2), 12, 70,
             "detach", "Snaps (bottoming out): the rear axle loses drive, the car is front-drive",
             shield=["chassis"], damaged=False,
             links={"front": [0, 0.36, z0], "rear": [0, 0.36, z1]}), local_elems=local)


def diff(front: bool):
    z = AXLE_F if front else AXLE_R
    d = 1 if front else -1
    e = [box((-0.12, 0.21, z - 0.10), (0.12, 0.41, z + 0.10), "alloy", dent=False)]
    e += prism((0.0, 0.31, z - d * 0.12), "z", 0.11, 0.05, 12, "darksteel", dent=False)  # cover
    for s in (1, -1):
        e += prism((s * 0.125, 0.31, z), "x", 0.045, 0.03, 8, "darksteel", dent=False)    # output flanges
    name = "diff_f" if front else "diff_r"
    add(Part(name, f"{'Front' if front else 'Rear'} differential", "powertrain", "chassis", (0, 0, 0),
             25 if front else 30, 110, "fail",
             f"Breaks: the {'front' if front else 'rear'} axle loses drive",
             shield=["chassis"], damaged=False,
             links={"out_l": [DIFF_OUT_X, 0.31, z], "out_r": [-DIFF_OUT_X, 0.31, z]}), e)


def radiator():
    e = [box((-0.40, 0.38, 1.82), (0.40, 0.74, 1.86), "radiator", dent=False),
         box((-0.43, 0.36, 1.81), (-0.40, 0.76, 1.87), "darksteel", dent=False),
         box((0.40, 0.36, 1.81), (0.43, 0.76, 1.87), "darksteel", dent=False)]
    e.append(beam((0.22, 0.72, 1.82), (0.10, 0.80, 1.72), 0.05, 0.05, "plastic", dent=False))  # top hose
    add(Part("radiator", "Radiator", "powertrain", "chassis", (0, 0, 0), 8, 40, "fail",
             "Leaks: the engine heats up; overheated, it loses HP over time",
             shield=["bumper_f"], damaged=False), e)


def fuel_tank():
    e = [box((-0.40, 0.50, -1.80), (0.40, 0.76, -1.38), "fuelcell", dent=False),
         box((-0.42, 0.50, -1.82), (0.42, 0.53, -1.36), "darksteel", dent=False),
         box((0.18, 0.76, -1.55), (0.28, 0.80, -1.45), "darksteel", dent=False)]
    add(Part("fuel_tank", "Fuel cell", "powertrain", "chassis", (0, 0, 0), 50, 80, "fail",
             "Leaks fuel; at 0 it catches fire", shield=["bumper_r", "hatch"], damaged=False), e)


def exhaust():
    pts = [(-0.30, 0.55, 1.36), (-0.27, 0.40, 1.22), (-0.22, 0.25, 1.00), (-0.22, 0.25, -1.44)]
    e = [beam(pts[i], pts[i + 1], 0.07, 0.07, "exhaust", dent=False) for i in range(len(pts) - 1)]
    e.append(box((-0.45, 0.20, -1.80), (-0.15, 0.36, -1.44), "exhaust", dent=False))     # silencer
    e += prism((-0.40, 0.29, -1.92), "z", 0.05, 0.24, 10, "steel", dent=False)            # tail pipe
    add(Part("exhaust", "Exhaust and silencer", "powertrain", "chassis", (0, 0, 0), 18, 50, "detach",
             "Torn off: louder, a little less power", shield=["bumper_r"], damaged=False), e)


# ---------------------------------------------------------------- corners
def wheel_model():
    """Local frame: hub center, outer face toward +X (left side of the car)."""
    e = []
    e += prism((0, 0, 0), "x", WHEEL_R, WHEEL_W, 16, "rubber", faces_end=False)            # tread
    e += prism((0, 0, 0), "x", WHEEL_R - 0.004, WHEEL_W + 0.01, 16, "sidewall", faces_end=True, start=11.25)
    e += prism((0.112, 0, 0), "x", 0.215, 0.012, 16, "rim", faces_end=True)               # rim face
    e += prism((-0.112, 0, 0), "x", 0.215, 0.012, 16, "darksteel", faces_end=True)        # inner rim
    for k in range(6):                                                                     # spokes
        a = 2 * math.pi * k / 6
        p = (0.122, 0.04 * math.sin(a), 0.04 * math.cos(a))
        q = (0.122, 0.19 * math.sin(a), 0.19 * math.cos(a))
        e.append(beam(p, q, 0.01, 0.045, "plastic"))
    e += prism((0.125, 0, 0), "x", 0.05, 0.02, 8, "accent")                               # center cap
    return e


def corner(side: int, front: bool):
    s = side
    z = AXLE_F if front else AXLE_R
    tag = ("f" if front else "r") + ("l" if s > 0 else "r")
    yaw = 0.0 if s > 0 else 180.0
    hub = (s * TRACK_X, HUB_Y, z)
    side_name = "left" if s > 0 else "right"
    end = "front" if front else "rear"

    # Control arm: pivot at the inboard mount; swings about local Z.
    arm_piv = (s * ARM_IN_X, ARM_Y, z)
    bj = (ARM_OUT[0] - ARM_IN_X, ARM_OUT[1] - ARM_Y, 0.0)                                 # ball joint, local
    spring_bot = (SPRING_BOT_ON_ARM, (ARM_OUT[1] - ARM_Y) * SPRING_BOT_ON_ARM / (ARM_OUT[0] - ARM_IN_X), 0.0)
    add(Part(f"arm_{tag}", f"Control arm ({end} {side_name})", "suspension", "chassis", arm_piv, 5, 60, "detach",
             "Bends (toe and camber pull to one side); broken, the wheel and upright come off",
             model="arm", rest=(0.0, yaw, 0.0), anim="swing_z", shield=["chassis"],
             links={"ball_joint": list(bj), "spring_mount": [round(c, 4) for c in spring_bot]}),
        local_elems=None)

    # Upright: knuckle, hub, brake disc and caliper; steers if front.
    add(Part(f"upright_{tag}", f"Upright and brake ({end} {side_name})", "suspension", f"arm_{tag}", hub, 12, 70,
             "detach", "Brake fades with damage; broken, the wheel comes off",
             model="upright", rest=(0.0, yaw, 0.0), anim="steer_y" if front else "fixed", shield=[f"wheel_{tag}"],
             links={"halfshaft": [-0.14, 0.0, 0.0]}), local_elems=None)

    # Coilover: from the arm to the strut tower, scaled along local Y.
    bot_world = (s * (ARM_IN_X + spring_bot[0]), ARM_Y + spring_bot[1], z)
    top_world = (s * STRUT_TOP[0], STRUT_TOP[1], z)
    dx, dy = top_world[0] - bot_world[0], top_world[1] - bot_world[1]
    tilt = -math.degrees(math.atan2(dx, dy))
    add(Part(f"spring_{tag}", f"Coilover spring and damper ({end} {side_name})", "suspension", "chassis",
             bot_world, 6, 50, "fail", "Weakens: that corner sags and bounces; broken, it bottoms out",
             model="spring", rest=(0.0, 0.0, round(tilt, 3)), anim="stretch_y", shield=[f"wheel_{tag}"],
             links={"bottom": [round(c, 4) for c in bot_world], "top": [round(c, 4) for c in top_world],
                    "rest_length": round(math.hypot(dx, dy), 4)}), local_elems=None)

    # Half shaft: diff output to the hub, scaled along local X.
    hs_in = (s * DIFF_OUT_X + s * 0.015, 0.31, z)
    hs_out = (s * (TRACK_X - 0.14), HUB_Y, z)
    add(Part(f"halfshaft_{tag}", f"Half shaft ({end} {side_name})", "powertrain", f"diff_{'f' if front else 'r'}",
             hs_in, 6, 45, "fail", "Snaps: this wheel gets no drive",
             model="halfshaft", rest=(0.0, yaw, 0.0), anim="stretch_x", shield=["chassis"],
             links={"inner": [round(c, 4) for c in hs_in], "outer": [round(c, 4) for c in hs_out],
                    "rest_length": round(abs(hs_out[0] - hs_in[0]), 4)}), local_elems=None)

    add(Part(f"wheel_{tag}", f"Wheel and tire ({end} {side_name})", "wheel", f"upright_{tag}", hub, 18, 60,
             "detach", "Punctures: less grip and a lower ride; broken, it comes off and rolls away",
             model="wheel", rest=(0.0, yaw, 0.0), anim="spin_x"), local_elems=None)


def arm_model():
    bx, by = ARM_OUT[0] - ARM_IN_X, ARM_OUT[1] - ARM_Y
    e = [beam((0, 0, 0.18), (bx, by, 0), 0.035, 0.035, "darksteel"),
         beam((0, 0, -0.18), (bx, by, 0), 0.035, 0.035, "darksteel"),
         beam((0, 0, 0.20), (0, 0, -0.20), 0.04, 0.04, "steel")]                          # pivot axle
    e += prism((bx, by, 0), "y", 0.03, 0.04, 8, "steel")                                  # ball joint
    sb = SPRING_BOT_ON_ARM
    e.append(box((sb - 0.03, by * sb / bx - 0.03, -0.03), (sb + 0.03, by * sb / bx + 0.01, 0.03), "steel"))
    return e


def upright_model():
    e = []
    e += prism((-0.048, 0, 0), "x", 0.15, 0.025, 14, "disc", dent=False)                  # brake disc
    e.append(box((-0.075, 0.08, 0.04), (-0.02, 0.16, 0.13), "caliper", dent=False))       # caliper
    e.append(box((-0.15, -0.14, -0.045), (-0.085, 0.17, 0.045), "darksteel"))             # knuckle
    e += prism((-0.06, 0, 0), "x", 0.055, 0.05, 8, "steel", dent=False)                   # hub
    e.append(box((-0.16, 0.02, 0.045), (-0.10, 0.06, 0.16), "darksteel"))                 # steering arm
    return e


def spring_model(rest_len):
    e = []
    e += prism((0, 0.18, 0), "y", 0.035, 0.34, 8, "darksteel", dent=False)                # damper body
    e += prism((0, 0.47, 0), "y", 0.014, 0.26, 6, "steel", dent=False)                    # shaft
    e += prism((0, 0.04, 0), "y", 0.075, 0.015, 10, "steel", dent=False)                  # lower seat
    e += prism((0, rest_len - 0.03, 0), "y", 0.075, 0.015, 10, "steel", dent=False)       # top seat
    e += helix(0.05, rest_len - 0.04, 0.06, 6, 8, 0.018, "spring")
    for el in e:
        el.dent = False
    return e


def halfshaft_model(length):
    e = []
    e += prism((length / 2, 0, 0), "x", 0.02, length - 0.12, 8, "steel", dent=False)     # shaft
    e += prism((0.04, 0, 0), "x", 0.045, 0.08, 8, "plastic", dent=False)                  # inner CV boot
    e += prism((length - 0.04, 0, 0), "x", 0.045, 0.08, 8, "plastic", dent=False)         # outer CV boot
    return e


# ---------------------------------------------------------------------------
# Build everything.
# ---------------------------------------------------------------------------

def build_parts():
    chassis(); shell(); cage(); steering_wheel(); glass_parts()
    door(1); door(-1); fender(1); fender(-1); quarter(1); quarter(-1)
    for s in (1, -1):
        for f in (True, False):
            mudflap(s, f)
    hood(); lightpod(); bumpers(); hatch(); wing()
    engine(); gearbox(); radiator(); driveshaft(); diff(True); diff(False); fuel_tank(); exhaust()
    for f in (True, False):
        for s in (1, -1):
            corner(s, f)


def shared_models() -> dict[str, list[Elem]]:
    spring = next(p for p in PARTS if p.model == "spring")
    hs = next(p for p in PARTS if p.model == "halfshaft")
    return {
        "wheel": wheel_model(),
        "arm": arm_model(),
        "upright": upright_model(),
        "spring": spring_model(spring.links["rest_length"]),
        "halfshaft": halfshaft_model(hs.links["rest_length"]),
    }


def u(v: float) -> float:
    return round(8 + v * UNITS_PER_M, 4)


def elem_json(e: Elem, dent_rng: random.Random | None) -> dict:
    a, b = list(e.a), list(e.b)
    rot = list(e.rot) if e.rot else [0.0, 0.0, 0.0]
    origin = list(e.origin) if e.origin else [(ai + bi) / 2 for ai, bi in zip(a, b)]
    mat = e.mat
    if dent_rng is not None:
        mat = MATERIALS[mat].get("dmg", mat)
        if e.dent:
            rot = [r + dent_rng.uniform(-5, 5) for r in rot]
            shift = [dent_rng.uniform(-0.012, 0.012) for _ in range(3)]
            a = [ai + si for ai, si in zip(a, shift)]
            b = [bi + si for bi, si in zip(b, shift)]
            origin = [oi + si for oi, si in zip(origin, shift)]
    out = {"from": [u(c) for c in a], "to": [u(c) for c in b]}
    for c in out["from"] + out["to"]:
        if c < -16 or c > 32:
            raise ValueError(f"element outside the model limit: {out}")
    if any(abs(r) > 1e-6 for r in rot):
        out["rotation"] = {"origin": [u(c) for c in origin], "x": round(rot[0], 3), "y": round(rot[1], 3),
                           "z": round(rot[2], 3)}
    meta = MATERIALS[e.mat]
    faces = {}
    for f in e.faces:
        face = {"uv": [0, 0, 16, 16], "texture": f"#{mat}"}
        if "tint" in meta:
            face["tintindex"] = meta["tint"]
        faces[f] = face
    out["faces"] = faces
    if meta.get("emit"):
        out["light_emission"] = meta["emit"]
    return out


def model_json(elems: list[Elem], damaged: bool, seed: int) -> dict:
    rng = random.Random(seed) if damaged else None
    els = [elem_json(e, rng) for e in elems]
    mats = sorted({f["texture"][1:] for el in els for f in el["faces"].values()})
    tex = {m: f"{NS}:item/car/{m}" for m in mats}
    tex["particle"] = tex[mats[0]]
    return {"textures": tex, "elements": els}


TINTS = [
    {"type": "minecraft:custom_model_data", "index": 0, "default": 0xD8D8D8},   # paint
    {"type": "minecraft:custom_model_data", "index": 1, "default": 0x1E5AA8},   # accent
]


# Item display rendering in 26.3 is: entity * matrix * rotateY(180) * translate(-0.5) * this.
# This undoes the 180 degree turn and scales the half-size model back up about
# its center: p -> rotateY(180)(S * p) + t, with t chosen so the model center
# (0.5, 0.5, 0.5) lands on the display's origin.
S = 1 / MODEL_SCALE
UPSCALE = {"translation": [0.5 + 0.5 * S, 0.5 - 0.5 * S, 0.5 + 0.5 * S], "left_rotation": [0, 1, 0, 0],
           "scale": [S] * 3, "right_rotation": [0, 0, 0, 1]}


def item_json(name: str, has_damaged: bool) -> dict:
    base = {"type": "minecraft:model", "model": f"{NS}:item/car/{name}", "transformation": UPSCALE, "tints": TINTS}
    if not has_damaged:
        return {"model": base}
    dmg = {"type": "minecraft:model", "model": f"{NS}:item/car/{name}_damaged", "transformation": UPSCALE,
           "tints": TINTS}
    return {"model": {"type": "minecraft:select", "property": "minecraft:custom_model_data", "index": 0,
                      "cases": [{"when": "damaged", "model": dmg}], "fallback": base}}


def hitbox(elems: list[Elem]) -> list:
    """Local AABB (meters) around every element corner after its rotation."""
    pts = []
    for e in elems:
        corners = [(x, y, z) for x in (e.a[0], e.b[0]) for y in (e.a[1], e.b[1]) for z in (e.a[2], e.b[2])]
        if e.rot:
            rx, ry, rz = (math.radians(r) for r in e.rot)
            o = e.origin

            def R(p):
                x, y, z = (p[i] - o[i] for i in range(3))
                y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
                x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
                x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
                return (x + o[0], y + o[1], z + o[2])
            corners = [R(c) for c in corners]
        pts += corners
    lo = [round(min(p[i] for p in pts), 3) for i in range(3)]
    hi = [round(max(p[i] for p in pts), 3) for i in range(3)]
    return [lo, hi]


def write_parts_table(spec: dict) -> None:
    lines = ["# Car parts", "",
             "Generated by `pack/src/car_parts.py` from the same data as the models. Do not edit.", "",
             f"{len(spec['parts'])} parts, {spec['total_mass']} kg in total.", "",
             "| Part | Group | Parent | Model | Mass (kg) | HP | Breaks | Moves | Shielded by | Effect |",
             "| --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- |"]
    for p in spec["parts"]:
        lines.append(f"| `{p['id']}` | {p['group']} | {p['parent'] or '-'} | `{p['model']}` | {p['mass']:g} | "
                     f"{p['hp']} | {'off' if p['on_break'] == 'detach' else 'in place'} | {p['anim']} | "
                     f"{', '.join(p['shield']) or '-'} | {p['effect']} |")
    (ROOT / "car/PARTS.md").write_text("\n".join(lines) + "\n")


def rest_matrix(pivot, rest) -> list[float]:
    """Row-major 4x4: translate(pivot) * Rz * Ry * Rx (Minecraft's rotationZYX)."""
    rx, ry, rz = (math.radians(a) for a in rest)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    Ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    Rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
    mul = lambda A, B: [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    R = mul(Rz, mul(Ry, Rx))
    out = []
    for i in range(3):
        out += [R[i][0], R[i][1], R[i][2], pivot[i]]
    out += [0, 0, 0, 1]
    return out


def tc_num(v: float) -> str:
    v = round(v, 3)
    if v == 0:
        return "0"
    return f"{v:g}"


def write_tc_data(spec: dict) -> None:
    """tc/car_data.tc: the part list and the suspension geometry for the game code."""
    kinds = {"wheel": "wheel", "upright": "upright", "arm": "arm", "spring": "spring", "halfshaft": "halfshaft",
             "steering_wheel": "steer"}
    rows = []
    for p in spec["parts"]:
        kind = "rigid" if p["rigid"] else kinds[p["model"]]
        rows.append(f'        "{p["id"]} {p["item_model"]} {kind} {corner_of(p["id"])}"')
    parts = {p["id"]: p for p in spec["parts"]}
    arm, spring, shaft = parts["arm_fl"], parts["spring_fl"], parts["halfshaft_fl"]
    sw = parts["steering_wheel"]
    geom = {
        "gWheelR": WHEEL_R, "gTrackX": TRACK_X, "gAxleF": AXLE_F, "gAxleR": AXLE_R, "gHubRestY": HUB_Y,
        "gArmX": ARM_IN_X, "gArmY": ARM_Y, "gArmLen": ARM_OUT[0] - ARM_IN_X,
        "gSpringMountX": arm["links"]["spring_mount"][0], "gSpringMountY": arm["links"]["spring_mount"][1],
        "gStrutX": STRUT_TOP[0], "gStrutY": STRUT_TOP[1], "gSpringRest": spring["links"]["rest_length"],
        "gShaftInX": shaft["links"]["inner"][0], "gShaftInY": shaft["links"]["inner"][1],
        "gHubInset": 0.14, "gShaftRest": shaft["links"]["rest_length"],
        "gSteerX": sw["pivot"][0], "gSteerY": sw["pivot"][1], "gSteerZ": sw["pivot"][2], "gSteerTilt": sw["rest"][0],
        "gMass": spec["total_mass"],
    }
    gl = "\n".join(f"    global {k} = {tc_num(v)};" for k, v in geom.items())
    decl = "\n".join(f"declare global {k}: num;" for k in geom)
    text = (
        "// Generated by pack/src/car_parts.py from car/parts.json. Do not edit.\n\n"
        "/** The car's parts in spawn order, each \"id itemModel kind corner\". Kind\n"
        " * \"rigid\" parts are built around the car origin and share the car's matrix;\n"
        " * the others are moved one by one (render.tc). Corner: 1 front left, 2 front\n"
        " * right, 3 rear left, 4 rear right, 0 none. */\n"
        "function carPartData(): list {\n    return [\n"
        + ",\n".join(rows) + "\n    ];\n}\n\n"
        f"/** Number of parts in a car. */\nfunction carPartCount(): num {{\n    return {len(rows)};\n}}\n\n"
        "/** Suspension and drawing geometry (car frame, meters) and the total mass. */\n"
        + decl + "\n\n/** Sets the geometry globals. */\nfunction loadCarGeom {\n" + gl + "\n}\n"
    )
    (ROOT / "tc").mkdir(exist_ok=True)
    (ROOT / "tc/car_data.tc").write_text(text)


def make_rigid() -> None:
    """Rebuild every part that never moves relative to the body around the car
    origin, so all of them share one display matrix (the car's) while driving.
    Their mount point stays in `attach`."""
    by_id = {p.id: p for p in PARTS}

    def fixed_chain(p: Part) -> bool:
        while p is not None:
            if p.anim != "fixed":
                return False
            p = by_id.get(p.parent) if p.parent else None
        return True

    for p in PARTS:
        p.attach = p.pivot
        if p.model is None and fixed_chain(p):
            p.elems = to_local(p.elems, tuple(-c for c in p.pivot))
            p.pivot = (0.0, 0.0, 0.0)
            p.rigid = True


def corner_of(pid: str) -> int:
    return {"_fl": 1, "_fr": 2, "_rl": 3, "_rr": 4}.get(pid[-3:], 0)


def main():
    build_parts()
    shared = shared_models()
    for p in PARTS:
        if p.elems is None:
            p.elems = shared[p.model]
    make_rigid()

    models: dict[str, tuple[list[Elem], bool]] = {}
    for p in PARTS:
        name = p.model or p.id
        if name not in models:
            models[name] = (p.elems, p.damaged)

    mdir = ASSETS / "models/item/car"
    idir = ASSETS / "items/car"
    tdir = ASSETS / "textures/item/car"
    for d in (mdir, idir, tdir):
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("*"):
            old.unlink()

    used_tex: set[str] = set()
    model_data = {}
    for i, (name, (elems, dmg)) in enumerate(sorted(models.items())):
        m = model_json(elems, False, 0)
        (mdir / f"{name}.json").write_text(json.dumps(m, indent=1) + "\n")
        used_tex |= set(m["textures"].values())
        model_data[name] = m
        if dmg:
            md = model_json(elems, True, 1000 + i)
            (mdir / f"{name}_damaged.json").write_text(json.dumps(md, indent=1) + "\n")
            used_tex |= set(md["textures"].values())
            model_data[name + "_damaged"] = md
        (idir / f"{name}.json").write_text(json.dumps(item_json(name, dmg), indent=1) + "\n")

    textures = make_textures()
    tex_b64 = {}
    import base64
    import io
    for name, img in textures.items():
        if f"{NS}:item/car/{name}" not in used_tex:
            continue
        img.save(tdir / f"{name}.png", optimize=True)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        tex_b64[name] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    missing = {t.split("/")[-1] for t in used_tex} - set(tex_b64)
    if missing:
        raise SystemExit(f"textures missing: {missing}")

    ids = {p.id for p in PARTS}
    spec_parts = []
    for p in PARTS:
        if p.parent and p.parent not in ids:
            raise SystemExit(f"{p.id}: unknown parent {p.parent}")
        for s in p.shield:
            if s not in ids:
                raise SystemExit(f"{p.id}: unknown shield {s}")
        spec_parts.append({
            "id": p.id, "label": p.label, "group": p.group, "parent": p.parent,
            "model": p.model or p.id, "item_model": f"{NS}:car/{p.model or p.id}",
            "pivot": [round(c, 4) for c in p.pivot], "rest": list(p.rest), "anim": p.anim,
            "rigid": p.rigid, "attach": [round(c, 4) for c in p.attach],
            "mass": p.mass, "hp": p.hp, "on_break": p.on_break, "effect": p.effect,
            "shield": p.shield, "damaged_model": p.damaged, "hitbox": hitbox(p.elems), "links": p.links,
        })

    spec = {
        "frame": "+X left, +Y up, +Z forward; meters; origin on the ground between the axles",
        "model_scale": MODEL_SCALE,
        "placement": "item display at the car origin; matrix = car * translate(pivot) * rotate_xyz(rest) * anim. "
                     "The pack scales the half-size models back to 1:1, so no extra scale is needed.",
        "anims": ANIMS,
        "tints": {"0": "paint (body color)", "1": "accent (arches, wing, rims, mud flaps)"},
        "damage_state": "custom_model_data string 0 = \"damaged\" swaps to the _damaged model",
        "dimensions": {"wheelbase": WHEELBASE, "track": 2 * TRACK_X, "wheel_radius": WHEEL_R,
                       "wheel_width": WHEEL_W, "length": 4.17, "width": 1.86, "height": 1.45},
        "total_mass": round(sum(p.mass for p in PARTS), 1),
        "parts": spec_parts,
    }
    (ROOT / "car").mkdir(exist_ok=True)
    (ROOT / "car/parts.json").write_text(json.dumps(spec, indent=1) + "\n")

    write_parts_table(spec)
    write_tc_data(spec)

    viewer = ROOT / "tools/viewer"
    viewer.mkdir(parents=True, exist_ok=True)
    (viewer / "car_data.js").write_text(
        "// Generated by pack/src/car_parts.py. Do not edit.\nwindow.CAR = "
        + json.dumps({"spec": spec, "models": model_data, "textures": tex_b64}) + ";\n")

    print(f"{len(PARTS)} parts, {len(models)} models, {len(tex_b64)} textures, "
          f"total mass {spec['total_mass']} kg")


if __name__ == "__main__":
    main()
