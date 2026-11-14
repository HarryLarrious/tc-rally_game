"""The muscle car: a third look for the rally car (car_parts.py).

A late-sixties American fastback coupe in the game's blocky style. It keeps
the rally car's part list, chassis, suspension, gearbox, radiator, fuel cell
and drive shafts, so physics and damage work the same; the game drives only
its rear wheels. The body: coke-bottle sides (front fenders and rear
haunches stand out past the doors) with a crease along the flanks, a long
flat hood with a raised center and twin scoops, a full-width black grille
with round lamps at its ends, a hardtop with no door pillar, a tunnel-back
roof (sail panels run from the roof down to the tail, with the rear window
sunk between them), a short deck with a ducktail lip, a recessed tail panel
with four lamps, thin chrome bumpers, an accent-colored stripe around the
tail and slotted chrome wheels on tall tires. Under the hood: a big-block
V8 with a round air cleaner and dual exhausts out the rear corners.

muscle_body() returns {part id: (car-frame elements, pivot)}; car_parts.py
swaps them into a copy of its parts. Written for the left side (+X) and
mirrored for the right.
"""

from __future__ import annotations

import math
from dataclasses import replace

from car_super import cage as super_cage
from car_parts import AXLE_F, AXLE_R, arch, beam, box, mirror_x, plate, prism


def both(left: list) -> list:
    return left + mirror_x(left)


# Side profile: belt line (top of the fenders, doors and quarters).
BELT = 0.92


def fender(s: int) -> list:
    """Front fender: stands out past the door (coke bottle), carries the
    outer half of the grille with two round lamps, and a side marker."""
    e = [
        box((0.84, 0.40, 0.80), (0.90, BELT, 0.86), "paint"),                     # behind the arch
        box((0.84, 0.78, 0.86), (0.90, BELT, 1.68), "paint"),                     # over the arch
        box((0.84, 0.40, 1.68), (0.90, BELT, 2.06), "paint"),                     # ahead of the arch
        box((0.60, BELT - 0.03, 0.86), (0.90, BELT + 0.01, 2.06), "paint"),       # top
        box((0.90, 0.74, 0.86), (0.915, 0.77, 2.02), "paint"),                    # flank crease
        # Grille end: chrome surround, black mesh and two round lamps.
        box((0.84, 0.46, 2.06), (0.89, 0.89, 2.11), "chrome"),
        box((0.42, 0.48, 2.06), (0.84, 0.86, 2.075), "grille", faces=("south",)),
        box((0.60, 0.86, 2.06), (0.89, 0.89, 2.10), "chrome"),                    # top bar
        box((0.90, 0.60, 1.88), (0.905, 0.68, 1.98), "foglight", faces=("east",), dent=False),  # side marker
        box((0.47, 0.36, 0.86), (0.49, 0.86, 1.66), "plastic"),                   # arch liner
    ]
    for x in (0.54, 0.73):
        e += prism((x, 0.67, 2.08), "z", 0.085, 0.02, 12, "chrome")                # bezel
        e += prism((x, 0.67, 2.09), "z", 0.068, 0.02, 12, "headlight", dent=False)
    e += arch(AXLE_F, 1, 0.86, 0.915, "paint", r_in=0.41, r_out=0.46)
    return e if s > 0 else mirror_x(e)


def quarter(s: int) -> list:
    """Rear quarter: the rear haunch stands out furthest, with a hip that
    rises over the wheel. The tail end holds the outer half of the recessed
    tail panel with two lamps; the accent stripe wraps round behind the
    wheel."""
    e = [
        box((0.85, 0.40, -0.86), (0.92, BELT, -0.30), "paint"),                   # ahead of the arch
        box((0.85, 0.78, -1.68), (0.92, BELT, -0.86), "paint"),                   # over the arch
        box((0.85, 0.40, -2.04), (0.92, BELT, -1.68), "paint"),                   # behind the arch
        box((0.66, BELT - 0.02, -2.04), (0.92, BELT + 0.04, -0.30), "paint"),     # shoulder
        beam((0.885, BELT + 0.04, -0.40), (0.885, BELT + 0.07, -1.05), 0.07, 0.04, "paint"),  # hip
        box((0.85, BELT + 0.04, -2.04), (0.92, BELT + 0.07, -1.05), "paint"),
        box((0.92, 0.74, -0.30), (0.935, 0.77, -1.95), "paint"),                  # flank crease
        # Tail: paint frame round a recessed black panel with two lamps.
        box((0.84, 0.50, -2.07), (0.92, BELT + 0.07, -2.04), "paint"),
        box((0.40, 0.88, -2.07), (0.84, BELT + 0.07, -2.04), "paint"),
        box((0.40, 0.54, -2.05), (0.84, 0.88, -2.04), "plastic", faces=("north",)),
        box((0.46, 0.64, -2.055), (0.62, 0.82, -2.05), "taillight", faces=("north", "east", "west", "up", "down"),
            dent=False),
        box((0.66, 0.64, -2.055), (0.82, 0.82, -2.05), "taillight", faces=("north", "east", "west", "up", "down"),
            dent=False),
        box((0.92, 0.60, -2.02), (0.925, 0.68, -1.92), "taillight", faces=("east",), dent=False),  # side marker
        # Accent stripe round the tail: down the side and over the shoulder.
        box((0.935, 0.42, -1.86), (0.94, BELT + 0.06, -1.76), "accent", faces=("east",)),
        box((0.66, BELT + 0.071, -1.86), (0.92, BELT + 0.075, -1.76), "accent", faces=("up",)),
        box((0.50, 0.36, -1.66), (0.52, 0.86, -0.84), "plastic"),                 # arch liner
    ]
    e += arch(AXLE_R, 1, 0.88, 0.935, "paint", r_in=0.41, r_out=0.46)
    if s < 0:
        return mirror_x(e)
    # Pop-open fuel cap on the left haunch.
    e += prism((0.925, 0.85, -1.26), "x", 0.055, 0.012, 10, "chrome")
    return e


def door(s: int) -> list:
    """Hardtop door: no pillar, frameless glass leaning in, stepping down
    toward the front with the windshield's rake."""
    lean = (0.0, 0.0, 12.0)
    e = [
        box((0.83, 0.40, -0.32), (0.88, BELT, 0.80), "paint"),                    # skin
        box((0.79, 0.48, -0.27), (0.83, 0.88, 0.76), "plastic"),                  # inner card
        box((0.88, 0.74, -0.30), (0.895, 0.77, 0.78), "paint"),                   # flank crease
        box((0.88, 0.40, -0.32), (0.89, 0.43, 0.80), "chrome"),                   # rocker trim
        box((0.83, BELT, -0.32), (0.88, BELT + 0.015, 0.80), "chrome"),           # belt trim
        plate((0.80, 1.105, 0.05), (0.02, 0.37, 0.70), "glass", lean),
        plate((0.81, 1.035, 0.51), (0.02, 0.23, 0.22), "glass", lean),
        plate((0.815, 0.975, 0.72), (0.02, 0.11, 0.20), "glass", lean),
        box((0.88, 0.80, -0.22), (0.89, 0.83, -0.08), "chrome"),                  # handle
    ]
    return e if s > 0 else mirror_x(e)


def mirror(s: int) -> list:
    """Chrome bullet mirror on the door's front corner."""
    e = [
        beam((0.86, 0.93, 0.70), (0.93, 0.97, 0.68), 0.02, 0.02, "chrome"),       # stalk
        box((0.90, 0.94, 0.60), (0.98, 1.01, 0.72), "chrome"),                    # housing
        box((0.905, 0.945, 0.595), (0.975, 1.005, 0.60), "glass", faces=("north",)),
    ]
    return e if s > 0 else mirror_x(e)


def shell() -> list:
    """Roof, A pillars and the tunnel back: sail panels from the roof's
    rear corners down to the tail, with the rear window sunk between them."""
    p = (0.76, 1.335, -0.58)
    q = (0.82, BELT + 0.07, -1.98)
    d = [b - a for a, b in zip(p, q)]
    n = math.hypot(d[1], d[2])
    down = (0.0, d[2] / n, -d[1] / n)          # perpendicular to the line, down and forward
    off = 0.15
    pp = tuple(a + off * b for a, b in zip(p, down))
    qq = tuple(a + off * b for a, b in zip(q, down))
    left = [
        beam((0.80, BELT, 0.95), (0.74, 1.345, 0.30), 0.05, 0.05, "paint"),       # A pillar
        beam(pp, qq, 0.10, 2 * off, "paint"),                                      # sail panel
        plate((0.80, 1.10, -0.44), (0.02, 0.32, 0.22), "glass", (0.0, 0.0, 12.0)),  # quarter glass
        beam((0.79, BELT + 0.01, -0.30), (0.75, 1.32, -0.33), 0.03, 0.03, "chrome"),  # its front edge
    ]
    e = both(left)
    e.append(box((-0.76, 1.32, -0.60), (0.76, 1.36, 0.30), "paint"))              # roof
    e.append(box((-0.80, BELT - 0.02, 0.92), (0.80, BELT + 0.02, 1.00), "plastic"))  # cowl
    return e


def windshield() -> list:
    lo, hi = (BELT + 0.01, 0.95), (1.335, 0.30)
    return [beam((0.0, *lo), (0.0, *hi), 1.54, 0.02, "glass")]


def rear_window() -> list:
    # Sunk between the sail panels: from the roof's rear edge down to the deck.
    return [beam((0.0, 1.33, -0.60), (0.0, BELT + 0.05, -0.98), 1.40, 0.02, "glass")]


def hood() -> list:
    """Long and flat, with a raised center and twin scoops."""
    e = [
        box((-0.60, BELT - 0.03, 0.98), (0.60, BELT + 0.01, 2.06), "paint"),
        box((-0.30, BELT + 0.01, 1.04), (0.30, BELT + 0.04, 1.98), "paint"),     # raised center
    ]
    for x in (-0.15, 0.15):
        e.append(box((x - 0.10, BELT + 0.04, 1.42), (x + 0.10, BELT + 0.075, 1.72), "paint"))   # scoop
        e.append(box((x - 0.08, BELT + 0.045, 1.72), (x + 0.08, BELT + 0.07, 1.725), "grille", faces=("south",)))
        e.append(box((x - 0.02, BELT + 0.075, 1.44), (x + 0.02, BELT + 0.078, 1.70), "accent", faces=("up",)))
    for x in (-0.48, 0.48):
        e += prism((x, BELT + 0.012, 1.98), "y", 0.025, 0.01, 8, "chrome")       # hood pins
    return e


def lightpod() -> list:
    # Round driving lamps in the valance under the front bumper.
    left = prism((0.62, 0.33, 2.08), "z", 0.055, 0.04, 12, "chrome")
    left.append(box((0.585, 0.295, 2.10), (0.655, 0.365, 2.102), "foglight", faces=("south",), dent=False))
    return both(left)


def bumper_f() -> list:
    """Thin chrome bumper wrapping the corners, the center of the grille with
    a chrome divider, and the valance below."""
    left = [box((0.84, 0.40, 1.94), (0.91, 0.48, 2.10), "chrome")]                # wrap
    e = both(left)
    e += [
        box((-0.89, 0.40, 2.08), (0.89, 0.48, 2.15), "chrome"),                   # bumper
        box((-0.42, 0.48, 2.065), (0.42, 0.86, 2.075), "grille", faces=("south",)),
        box((-0.60, 0.86, 2.06), (0.60, 0.89, 2.10), "chrome"),                   # top bar
        box((-0.025, 0.48, 2.06), (0.025, 0.86, 2.10), "chrome"),                 # divider
        box((-0.84, 0.26, 1.98), (0.84, 0.40, 2.08), "paint"),                    # valance
        box((-0.40, 0.29, 2.08), (0.40, 0.36, 2.085), "grille", faces=("south",)),
    ]
    return e


def bumper_r() -> list:
    left = [box((0.84, 0.40, -2.12), (0.91, 0.48, -1.96), "chrome"),              # wrap
            box((0.47, 0.26, -2.075), (0.63, 0.36, -2.07), "plastic", faces=("north",))]  # pipe cutout
    e = both(left)
    e += [
        box((-0.89, 0.40, -2.15), (0.89, 0.48, -2.08), "chrome"),                 # bumper
        box((-0.84, 0.26, -2.07), (0.84, 0.40, -1.98), "paint"),                  # valance
    ]
    return e


def hatch() -> list:
    """Short trunk lid: the deck between the sail panels, the middle of the
    tail panel and the accent stripe across."""
    top = BELT + 0.07
    return [
        box((-0.66, top - 0.04, -2.04), (0.66, top, -0.96), "paint"),             # deck
        box((-0.40, 0.88, -2.07), (0.40, top, -2.04), "paint"),                   # tail panel top
        box((-0.40, 0.54, -2.05), (0.40, 0.88, -2.04), "plastic", faces=("north",)),
        box((-0.16, 0.60, -2.055), (0.16, 0.74, -2.05), "chrome", faces=("north",)),  # plate frame
        box((-0.13, 0.62, -2.057), (0.13, 0.72, -2.055), "accent", faces=("north",)),  # plate
        box((-0.66, top, -1.86), (0.66, top + 0.004, -1.76), "accent", faces=("up",)),  # stripe
        box((-0.03, top - 0.02, -2.075), (0.03, top - 0.005, -2.07), "chrome"),   # lock
    ]


def wing() -> list:
    # Ducktail lip at the end of the deck.
    top = BELT + 0.07
    return [plate((0.0, top + 0.02, -2.01), (1.32, 0.035, 0.12), "paint", (-14.0, 0.0, 0.0))]


def mudflap(s: int, front: bool) -> list:
    # Black splash guards inside the arches, behind the wheels.
    if front:
        e = [box((0.80, 0.30, 0.78), (0.86, 0.48, 0.80), "plastic")]
    else:
        e = [box((0.84, 0.30, -1.72), (0.90, 0.48, -1.70), "plastic")]
    return e if s > 0 else mirror_x(e)


def engine() -> list:
    """Big-block V8 up front: a 90 degree V with red valve covers, a round
    chrome air cleaner on top and a header on each side."""
    z0, z1 = 1.14, 1.70
    zc, zl = (z0 + z1) / 2, z1 - z0
    left = [
        plate((0.21, 0.62, zc), (0.16, 0.26, zl - 0.04), "alloy", (0.0, 0.0, -45.0), dent=False),     # bank
        plate((0.30, 0.71, zc), (0.13, 0.05, zl - 0.08), "valve", (0.0, 0.0, -45.0), dent=False),     # valve cover
        beam((0.34, 0.54, 1.62), (0.42, 0.42, 1.30), 0.06, 0.06, "exhaust", dent=False),             # header
    ]
    e = left + mirror_x(left)
    e += [
        box((-0.22, 0.36, z0), (0.22, 0.56, z1), "alloy", dent=False),                    # block
        box((-0.20, 0.30, z0 + 0.04), (0.20, 0.36, z1 - 0.04), "darksteel", dent=False),  # oil pan
        box((-0.12, 0.62, z0 + 0.06), (0.12, 0.74, z1 - 0.06), "alloy", dent=False),      # intake
    ]
    e += prism((0.0, 0.79, 1.42), "y", 0.19, 0.07, 12, "chrome", dent=False)             # air cleaner
    e += prism((0.0, 0.83, 1.42), "y", 0.08, 0.02, 8, "darksteel", dent=False)           # wing nut base
    e += prism((0.0, 0.46, z1 + 0.04), "z", 0.085, 0.04, 12, "darksteel", dent=False)    # crank pulley
    e += prism((0.16, 0.64, z1 + 0.04), "z", 0.05, 0.05, 10, "steel", dent=False)        # alternator
    return e


def exhaust() -> list:
    """Dual exhaust: each header to a pipe under the floor, a silencer each
    and a tail pipe out of the rear valance's corners."""
    pts = [(0.42, 0.42, 1.30), (0.36, 0.24, 1.00), (0.36, 0.22, -1.40)]
    left = [beam(pts[i], pts[i + 1], 0.07, 0.07, "exhaust", dent=False) for i in range(len(pts) - 1)]
    left.append(box((0.27, 0.17, -1.86), (0.45, 0.29, -1.40), "exhaust", dent=False))    # silencer
    left.append(beam((0.40, 0.23, -1.86), (0.55, 0.31, -2.00), 0.06, 0.06, "exhaust", dent=False))
    left += prism((0.55, 0.31, -2.05), "z", 0.045, 0.10, 10, "chrome", dent=False)        # tail pipe
    return both(left)


def wheel() -> list:
    """Slotted chrome wheel on a tall tire (local frame: hub center, outer
    face +X): small rim, wide black sidewall, five dark slots, a trim ring
    and a chrome cap."""
    def ends(elems):
        return [replace(el, faces=tuple(f for f in el.faces if f in ("east", "west"))) for el in elems]
    e = prism((0, 0, 0), "x", 0.32, 0.23, 16, "rubber", faces_end=False)
    e += ends(prism((0, 0, 0), "x", 0.316, 0.236, 16, "sidewall"))
    e += ends(prism((0.125, 0, 0), "x", 0.20, 0.014, 16, "chrome"))                  # rim face
    for k in range(5):
        a = 2 * math.pi * (k + 0.5) / 5
        p = (0.133, 0.085 * math.sin(a), 0.085 * math.cos(a))
        q = (0.133, 0.165 * math.sin(a), 0.165 * math.cos(a))
        e.append(beam(p, q, 0.006, 0.05, "plastic"))                                  # slots
    for k in range(16):                                                               # trim ring
        a0, a1 = 2 * math.pi * k / 16, 2 * math.pi * (k + 1) / 16
        r = 0.2
        e.append(beam((0.136, r * math.sin(a0), r * math.cos(a0)), (0.136, r * math.sin(a1), r * math.cos(a1)),
                      0.012, 0.022, "chrome"))
    e += prism((0.138, 0, 0), "x", 0.055, 0.02, 8, "chrome")                          # cap
    e += prism((0.149, 0, 0), "x", 0.022, 0.006, 8, "accent")                         # cap center
    return e


# Shared models the muscle car swaps for its own (model name -> local elements).
MODELS = {"wheel": wheel()}

SHIELDS = {
    "exhaust": ["bumper_r", "chassis"],
}
LABELS = {
    "engine": "Engine (7.0 big-block V8)",
    "gearbox": "Gearbox (4-speed, rear drive)",
    "exhaust": "Dual exhaust",
}


def muscle_body() -> dict:
    """Part id -> (car-frame elements, pivot or None for the elements' center).
    Hinged parts keep the rally car's pivots."""
    out = {
        "engine": (engine(), None), "exhaust": (exhaust(), None),
        "shell": (shell(), None), "cage": (super_cage(), None), "windshield": (windshield(), None),
        "rear_window": (rear_window(), None), "hood": (hood(), (0.0, 0.95, 1.02)),
        "lightpod": (lightpod(), None), "bumper_f": (bumper_f(), None), "bumper_r": (bumper_r(), None),
        "hatch": (hatch(), (0.0, 1.0, -0.98)), "wing": (wing(), None),
    }
    for s, tag in ((1, "l"), (-1, "r")):
        out[f"door_{tag}"] = (door(s), (s * 0.83, 0.80, 0.86))
        out[f"mirror_{tag}"] = (mirror(s), (s * 0.90, 1.02, 0.76))
        out[f"fender_f{tag}"] = (fender(s), None)
        out[f"quarter_r{tag}"] = (quarter(s), None)
        for front, ft in ((True, "f"), (False, "r")):
            z = 0.80 if front else -1.70
            out[f"mudflap_{ft}{tag}"] = (mudflap(s, front), (s * 0.88, 0.50, z))
    return out
