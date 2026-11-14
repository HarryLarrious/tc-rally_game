"""The hypercar: a second look for the rally car (car_parts.py).

It keeps the rally car's part list, cage layout, suspension, wheels and
drive shafts, so physics and damage work the same. The body panels get new,
angular shapes, and the engine moves behind the seats: a twin-turbo V8
with a transaxle behind it, the fuel cell in the nose and twin center
tail pipes (its own chassis has the firewall behind the seats). Parts keep
their ids (and so their HP, parents and effects); shields follow the new
layout. The body: a low, wide coupe with high front fenders and slim LED
headlights, a low hood with a black air channel, a teardrop canopy with a
steeply raked windshield and flying buttresses, rear haunches with side
intakes, a louvered engine deck, a full-width tail light bar, a carbon
splitter and diffuser, and a big swan-neck wing.

hyper_body() returns {part id: (car-frame elements, pivot)}; car_parts.py
swaps them into a copy of its parts. Written for the left side (+X) and
mirrored for the right.
"""

from __future__ import annotations

from dataclasses import replace

from car_parts import AXLE_F, AXLE_R, arch, beam, box, mirror_x, plate, prism


def both(left: list) -> list:
    return left + mirror_x(left)


def fender(s: int) -> list:
    """Front fender: its crest slopes down from the windshield and breaks
    into a steeper tip carrying the headlight slash. An arch liner hides
    what is behind the wheel."""
    e = [
        box((0.82, 0.40, 0.80), (0.90, 0.88, 0.86), "paint"),                     # behind the arch
        box((0.82, 0.76, 0.86), (0.90, 0.82, 1.66), "paint"),                     # over the arch
        beam((0.66, 0.955, 0.86), (0.66, 0.85, 1.70), 0.48, 0.04, "paint"),       # crest
        beam((0.43, 0.90, 0.98), (0.43, 0.79, 1.70), 0.03, 0.10, "paint"),        # wall down to the hood
        beam((0.68, 0.85, 1.70), (0.68, 0.60, 2.02), 0.44, 0.04, "paint"),        # tip
        beam((0.47, 0.80, 1.70), (0.47, 0.52, 2.06), 0.02, 0.08, "paint"),        # tip's inner edge
        box((0.84, 0.40, 1.66), (0.90, 0.78, 1.80), "paint"),                     # side ahead of the arch
        box((0.84, 0.40, 1.80), (0.90, 0.60, 2.00), "paint"),
        # Headlight: a slim LED slash in a black housing on the tip.
        beam((0.70, 0.79, 1.82), (0.70, 0.70, 1.935), 0.34, 0.02, "plastic"),
        beam((0.70, 0.753, 1.882), (0.70, 0.733, 1.908), 0.30, 0.012, "led", dent=False),
        beam((0.885, 0.95, 0.95), (0.885, 0.86, 1.65), 0.02, 0.015, "led", dent=False),  # LED brow
        box((0.47, 0.36, 0.86), (0.49, 0.88, 1.66), "plastic"),                   # arch liner
    ]
    e += arch(AXLE_F, 1, 0.84, 0.93, "accent")
    return e if s > 0 else mirror_x(e)


def quarter(s: int) -> list:
    e = [
        box((0.84, 0.40, -0.84), (0.92, 0.98, -0.34), "paint"),                   # ahead of the arch
        box((0.84, 0.78, -1.66), (0.92, 1.00, -0.84), "paint"),                   # over the arch
        box((0.84, 0.40, -2.02), (0.92, 1.00, -1.66), "paint"),                   # behind the arch
        box((0.62, 0.96, -2.00), (0.84, 1.00, -0.36), "paint"),                   # haunch top
        plate((0.88, 0.965, -1.18), (0.11, 0.04, 1.64), "paint", (0.0, 0.0, -35.0)),  # bevelled edge
        plate((0.82, 0.70, -2.03), (0.22, 0.30, 0.03), "paint", (0.0, -40.0, 0.0)),   # chamfered tail corner
        box((0.40, 0.55, -2.04), (0.92, 1.00, -2.00), "paint"),                   # rear face
        box((0.50, 0.36, -1.66), (0.52, 0.86, -0.84), "plastic"),                 # arch liner
        # Side intake ahead of the rear wheel: black mesh with a lip.
        box((0.92, 0.50, -0.80), (0.925, 0.84, -0.40), "grille", faces=("east",)),
        beam((0.93, 0.86, -0.38), (0.93, 0.48, -0.82), 0.03, 0.03, "accent"),
        # Tail light: part of the full-width bar, wrapping round the corner.
        box((0.42, 0.86, -2.05), (0.92, 0.90, -2.04), "taillight", faces=("north", "east", "up", "down"), dent=False),
        box((0.92, 0.86, -2.02), (0.925, 0.90, -1.86), "taillight", faces=("east", "up", "down"), dent=False),
    ]
    e += arch(AXLE_R, 1, 0.84, 0.94, "accent")
    return e if s > 0 else mirror_x(e)


def door(s: int) -> list:
    e = [
        box((0.82, 0.42, -0.30), (0.88, 0.86, 0.84), "paint"),                    # skin
        box((0.84, 0.30, -0.30), (0.90, 0.42, 0.80), "carbon"),                   # side skirt
        box((0.78, 0.48, -0.25), (0.82, 0.84, 0.80), "plastic"),                  # inner card
        # Side glass leaning in to the canopy, stepping down toward the front
        # with the raked windshield.
        plate((0.72, 1.10, 0.05), (0.02, 0.44, 0.64), "glass", (0.0, 0.0, 25.0)),
        plate((0.63, 1.31, 0.05), (0.03, 0.03, 0.64), "plastic", (0.0, 0.0, 25.0)),  # top frame
        plate((0.745, 1.04, 0.50), (0.02, 0.32, 0.26), "glass", (0.0, 0.0, 25.0)),
        plate((0.68, 1.19, 0.50), (0.03, 0.03, 0.26), "plastic", (0.0, 0.0, 25.0)),
        plate((0.765, 0.98, 0.72), (0.02, 0.20, 0.18), "glass", (0.0, 0.0, 25.0)),
        box((0.88, 0.70, 0.10), (0.885, 0.73, 0.24), "plastic"),                  # handle
        beam((0.888, 0.46, 0.78), (0.888, 0.66, -0.28), 0.02, 0.05, "carbon"),     # side blade
    ]
    return e if s > 0 else mirror_x(e)


def mirror(s: int) -> list:
    e = [
        beam((0.80, 0.92, 0.72), (0.92, 0.98, 0.66), 0.02, 0.02, "plastic"),       # stalk
        box((0.90, 0.95, 0.58), (1.00, 1.03, 0.72), "paint"),                     # housing
        box((0.905, 0.955, 0.575), (0.995, 1.025, 0.58), "glass", faces=("north",)),
    ]
    return e if s > 0 else mirror_x(e)


def shell() -> list:
    left = [
        beam((0.78, 0.90, 0.98), (0.52, 1.36, 0.30), 0.05, 0.05, "plastic"),      # A pillar
        beam((0.52, 1.36, 0.30), (0.52, 1.36, -0.70), 0.05, 0.05, "plastic"),     # roof rail
        beam((0.52, 1.36, -0.70), (0.66, 1.00, -1.10), 0.05, 0.05, "plastic"),    # canopy back
        beam((0.58, 1.30, -0.62), (0.84, 1.00, -1.75), 0.08, 0.05, "paint"),      # flying buttress
        plate((0.70, 1.12, -0.52), (0.02, 0.40, 0.40), "glass", (0.0, 0.0, 25.0)),  # quarter glass
    ]
    e = both(left)
    e.append(box((-0.52, 1.34, -0.70), (0.52, 1.38, 0.30), "paint"))             # roof
    e.append(box((-0.14, 1.38, -0.60), (0.14, 1.42, -0.10), "plastic"))           # roof scoop
    e.append(box((-0.10, 1.39, 0.00), (0.10, 1.40, 0.28), "accent"))              # roof stripe
    e.append(box((-0.70, 0.86, 0.92), (0.70, 0.90, 1.00), "plastic"))             # cowl
    return e


def windshield() -> list:
    # Steeply raked, narrowing toward the roof: four strips.
    lo, hi = (0.90, 1.00), (1.365, 0.30)
    out = []
    for k in range(4):
        t0, t1 = k / 4, (k + 1) / 4
        p = (0.0, lo[0] + (hi[0] - lo[0]) * t0, lo[1] + (hi[1] - lo[1]) * t0)
        q = (0.0, lo[0] + (hi[0] - lo[0]) * t1, lo[1] + (hi[1] - lo[1]) * t1)
        half = 0.75 - 0.25 * (t0 + t1) / 2
        out.append(beam(p, q, 2 * half, 0.02, "glass"))
    return out


def rear_window() -> list:
    # From the roof's rear edge down to the engine deck, along the canopy
    # pillars (top forward, bottom back).
    return [beam((0.0, 1.345, -0.71), (0.0, 1.0, -1.06), 1.08, 0.02, "glass")]


def hood() -> list:
    """Slopes down about 13 degrees from the windshield to the nose, with a
    black air channel and a vent."""
    return [
        beam((0.0, 0.925, 0.98), (0.0, 0.735, 1.80), 0.84, 0.03, "paint"),
        beam((0.0, 0.925, 1.067), (0.0, 0.773, 1.723), 0.26, 0.015, "plastic"),       # air channel
        beam((0.0, 0.877, 1.272), (0.0, 0.839, 1.436), 0.20, 0.016, "grille", faces=("up",)),
    ]


def lightpod() -> list:
    # Long-range LED pods in the intakes under the fender tips, and canards.
    left = [
        box((0.56, 0.44, 2.083), (0.66, 0.48, 2.092), "foglight", faces=("south",), dent=False),
        plate((0.86, 0.36, 2.10), (0.12, 0.015, 0.10), "accent", (0.0, -20.0, -12.0)),
    ]
    return both(left)


def bumper_f() -> list:
    """The nose carries on the hood's line down to a low nose, with a black
    scoop stripe. Under each fender tip a dark intake face, under the nose a
    dark mouth, and a carbon splitter below."""
    left = [
        beam((0.68, 0.60, 2.02), (0.68, 0.30, 2.13), 0.44, 0.03, "plastic"),          # intake face
        beam((0.68, 0.57, 2.044), (0.68, 0.34, 2.128), 0.36, 0.01, "grille", faces=("up",)),
    ]
    for x in (0.30, 0.62):
        left.append(box((x - 0.01, 0.28, 2.00), (x + 0.01, 0.34, 2.22), "carbon"))     # splitter fins
    e = both(left)
    e += [
        beam((0.0, 0.735, 1.80), (0.0, 0.40, 2.14), 0.92, 0.03, "paint"),             # nose
        beam((0.0, 0.732, 1.831), (0.0, 0.431, 2.137), 0.26, 0.015, "plastic"),       # scoop stripe
        box((-0.46, 0.28, 2.04), (0.46, 0.40, 2.15), "plastic"),                      # mouth
        box((-0.42, 0.30, 2.15), (0.42, 0.38, 2.155), "grille", faces=("south",)),
        box((-0.90, 0.24, 1.90), (0.90, 0.28, 2.22), "carbon"),                       # splitter
        box((-0.30, 0.28, 2.15), (0.30, 0.30, 2.22), "accent"),                       # center blade
    ]
    return e


def radiator() -> list:
    """The rally car's radiator, lower, to fit under the sloping nose."""
    return [box((-0.40, 0.38, 1.82), (0.40, 0.64, 1.86), "radiator", dent=False),
            box((-0.43, 0.36, 1.81), (-0.40, 0.66, 1.87), "darksteel", dent=False),
            box((0.40, 0.36, 1.81), (0.43, 0.66, 1.87), "darksteel", dent=False),
            beam((0.22, 0.62, 1.82), (0.10, 0.66, 1.72), 0.05, 0.05, "plastic", dent=False)]


def wheel() -> list:
    """A cleaner, closed wheel (local frame: hub center, outer face +X):
    tire, sidewall discs lined up with the tread, a flat dark backing that
    hides the brake and hub, five wide spokes in the accent color and a hex
    center lock."""
    def ends(elems):
        return [replace(el, faces=tuple(f for f in el.faces if f in ("east", "west"))) for el in elems]
    e = prism((0, 0, 0), "x", 0.32, 0.24, 16, "rubber", faces_end=False)
    e += ends(prism((0, 0, 0), "x", 0.316, 0.246, 16, "sidewall"))
    e += ends(prism((0.10, 0, 0), "x", 0.25, 0.012, 16, "sidewall"))
    for k in range(5):
        a = 2 * 3.141592653589793 * k / 5
        import math
        p = (0.118, 0.045 * math.sin(a), 0.045 * math.cos(a))
        q = (0.118, 0.235 * math.sin(a), 0.235 * math.cos(a))
        e.append(beam(p, q, 0.02, 0.065, "rim"))
    for k in range(16):                                                    # rim lip
        a0, a1 = 2 * math.pi * k / 16, 2 * math.pi * (k + 1) / 16
        r = 0.243
        e.append(beam((0.116, r * math.sin(a0), r * math.cos(a0)), (0.116, r * math.sin(a1), r * math.cos(a1)),
                      0.016, 0.022, "rim"))
    e += prism((0.124, 0, 0), "x", 0.06, 0.02, 6, "rim")
    e += prism((0.135, 0, 0), "x", 0.028, 0.012, 6, "darksteel")
    return e


# Shared models the hypercar swaps for its own (model name -> local elements).
MODELS = {"wheel": wheel()}


def bumper_r() -> list:
    e = [
        box((-0.88, 0.30, -2.08), (0.88, 0.55, -1.98), "paint"),
        box((-0.80, 0.24, -2.12), (0.80, 0.30, -1.80), "carbon"),                    # diffuser
        box((-0.36, 0.27, -2.085), (0.36, 0.41, -2.08), "plastic", faces=("north",)),  # exhaust surround
    ]
    for s in (1, -1):
        e.append(plate((s * 0.80, 0.42, -2.06), (0.20, 0.20, 0.03), "paint", (0.0, -s * 40.0, 0.0)))  # chamfered corners
    for x in (-0.62, -0.42, 0.42, 0.62):
        e.append(box((x - 0.01, 0.24, -2.14), (x + 0.01, 0.42, -1.90), "carbon"))     # diffuser fins
    return e


def hatch() -> list:
    e = [box((-0.62, 0.98, -2.00), (0.62, 1.02, -0.95), "paint"),                    # engine deck
         box((-0.40, 0.90, -2.04), (0.40, 1.00, -2.00), "paint"),                    # rear center panel
         box((-0.40, 0.55, -2.03), (0.40, 0.86, -2.00), "plastic"),                  # rear vent
         box((-0.38, 0.58, -2.035), (0.38, 0.84, -2.03), "grille", faces=("north",)),
         box((-0.42, 0.86, -2.05), (0.42, 0.90, -2.04), "taillight", faces=("north", "up", "down"), dent=False)]
    for k in range(5):
        z = -1.15 - k * 0.14
        e.append(box((-0.40, 1.02, z - 0.04), (0.40, 1.03, z + 0.04), "grille", faces=("up",)))  # louvers
    return e


def wing() -> list:
    e = [plate((0.0, 1.34, -1.92), (1.86, 0.035, 0.36), "carbon", (-8.0, 0.0, 0.0)),
         plate((0.0, 1.37, -2.09), (1.80, 0.06, 0.015), "accent", (-8.0, 0.0, 0.0))]   # gurney flap
    for s in (1, -1):
        e.append(box((min(s * 0.92, s * 0.95), 1.20, -2.12), (max(s * 0.92, s * 0.95), 1.46, -1.74), "accent"))
        e.append(beam((s * 0.36, 1.00, -1.75), (s * 0.36, 1.33, -1.90), 0.03, 0.05, "carbon"))  # swan necks
    return e


def mudflap(s: int, front: bool) -> list:
    # Aero vanes behind the front wheels and at the rear bumper corners.
    if front:
        e = [box((0.88, 0.30, 0.66), (0.90, 0.60, 0.80), "accent")]
    else:
        e = [box((0.86, 0.30, -1.82), (0.90, 0.55, -1.70), "accent")]
    return e if s > 0 else mirror_x(e)


def cage() -> list:
    """The rally car's cage, seats and dash, with the hoops lowered and
    narrowed to fit under the canopy."""
    t = 0.045
    e = []
    for s in (1, -1):
        x = s * 0.62
        xr = s * 0.55
        e.append(beam((x, 0.34, -0.36), (xr, 1.26, -0.36), t, t, "cage"))           # main hoop leg
        e.append(beam((x, 0.38, 0.80), (x, 0.92, 0.80), t, t, "cage"))              # front hoop leg
        e.append(beam((x, 0.92, 0.80), (xr, 1.26, 0.30), t, t, "cage"))             # A pillar bar
        e.append(beam((xr, 1.26, 0.30), (xr, 1.26, -0.36), t, t, "cage"))           # roof bar
        e.append(beam((xr, 1.26, -0.36), (s * 0.55, 0.50, -1.15), t, t, "cage"))    # rear stay
        e.append(beam((x, 0.45, 0.78), (x, 0.88, -0.34), t, t, "cage"))             # door bar X
        e.append(beam((x, 0.88, 0.78), (x, 0.45, -0.34), t, t, "cage"))
        sx = s * 0.33
        e.append(box((sx - 0.23, 0.34, -0.25), (sx + 0.23, 0.46, 0.25), "seat"))
        e.append(plate((sx, 0.80, -0.27), (0.46, 0.68, 0.08), "seat", (-10.0, 0.0, 0.0)))
        for b in (-1, 1):
            e.append(plate((sx + b * 0.21, 0.72, -0.20), (0.06, 0.50, 0.16), "seat", (-10.0, 0.0, 0.0)))
    e.append(beam((0.55, 1.26, -0.36), (-0.55, 1.26, -0.36), t, t, "cage"))             # main hoop top
    e.append(beam((0.62, 0.40, -0.36), (-0.55, 1.26, -0.36), t, t, "cage"))             # main hoop diagonal
    e.append(beam((0.55, 1.26, 0.30), (-0.55, 1.26, 0.30), t, t, "cage"))               # windscreen bar
    e.append(box((-0.68, 0.70, 0.62), (0.68, 0.90, 0.88), "plastic"))                   # dashboard
    e.append(box((-0.10, 0.34, 0.20), (0.10, 0.70, 0.62), "plastic"))                   # center console
    e.append(beam((0.0, 0.60, 0.05), (0.0, 0.78, 0.20), 0.025, 0.025, "darksteel"))     # handbrake
    e.append(beam((0.0, 0.70, 0.40), (0.02, 0.85, 0.32), 0.022, 0.022, "darksteel"))    # gear lever
    e.append(box((-0.015, 0.84, 0.29), (0.055, 0.89, 0.35), "accent"))                  # gear knob
    return e


def chassis() -> list:
    """The rally car's floor and front structure; the firewall sits behind
    the seats and the rear is an open engine bay with a low floor."""
    e = [
        box((-0.72, 0.28, -1.20), (0.72, 0.34, 0.95), "darksteel", dent=False),            # floor
        box((-0.15, 0.34, -0.40), (0.15, 0.60, 0.92), "darksteel", dent=False),            # tunnel
        box((-0.72, 0.34, 0.92), (0.72, 0.95, 0.97), "darksteel", dent=False),             # front bulkhead
        box((-0.72, 0.34, -0.46), (0.72, 0.95, -0.42), "darksteel", dent=False),           # firewall
        box((-0.72, 0.26, -1.95), (0.72, 0.30, -1.20), "darksteel", dent=False),           # engine bay floor
    ]
    for s in (1, -1):
        def X(a, b):
            return (min(s * a, s * b), max(s * a, s * b))
        x0, x1 = X(0.72, 0.85)
        e.append(box((x0, 0.28, -0.88), (x1, 0.50, 0.88), "darksteel", dent=False))      # sill
        x0, x1 = X(0.35, 0.45)
        e.append(box((x0, 0.35, 0.95), (x1, 0.55, 1.90), "steel", dent=False))           # front rail
        x0, x1 = X(0.50, 0.60)
        e.append(box((x0, 0.30, -1.92), (x1, 0.44, -0.46), "steel", dent=False))         # rear subframe rail
        x0, x1 = X(0.50, 0.62)
        for z0, z1 in ((1.15, 1.35), (-1.35, -1.15)):
            e.append(box((x0, 0.50, z0), (x1, 0.86, z1), "darksteel", dent=False))       # strut tower
        x0, x1 = X(0.45, 0.62)
        e.append(box((x0, 0.50, 1.10), (x1, 0.56, 1.40), "darksteel", dent=False))       # tower brace foot
    e.append(box((-0.45, 0.50, 1.84), (0.45, 0.56, 1.90), "steel", dent=False))          # front crossmember
    return e


def engine() -> list:
    """Twin-turbo V8, mounted lengthwise behind the seats: a 90 degree V of
    two angled banks with red cam covers, a carbon intake plenum in the V,
    and a turbo on each side fed by its bank's headers."""
    z0, z1 = -1.12, -0.48
    zc, zl = (z0 + z1) / 2, z1 - z0
    left = [
        plate((0.21, 0.64, zc), (0.16, 0.28, zl - 0.04), "alloy", (0.0, 0.0, -45.0), dent=False),     # bank
        plate((0.31, 0.74, zc), (0.13, 0.05, zl - 0.08), "valve", (0.0, 0.0, -45.0), dent=False),     # cam cover
        beam((0.34, 0.56, -0.60), (0.44, 0.52, -0.96), 0.05, 0.05, "exhaust", dent=False),           # headers
        beam((0.34, 0.56, -0.86), (0.44, 0.54, -0.98), 0.05, 0.05, "exhaust", dent=False),
        beam((0.44, 0.70, -1.00), (0.10, 0.76, -1.04), 0.06, 0.06, "darksteel", dent=False),         # charge pipe
    ]
    left += prism((0.44, 0.60, -1.00), "x", 0.085, 0.10, 12, "steel", dent=False)                     # turbo
    left += prism((0.44, 0.60, -1.00), "z", 0.07, 0.12, 10, "exhaust", dent=False)                     # turbine
    e = left + mirror_x(left)
    e += [
        box((-0.22, 0.36, z0), (0.22, 0.56, z1), "alloy", dent=False),                    # block
        box((-0.20, 0.30, z0 + 0.04), (0.20, 0.36, z1 - 0.04), "darksteel", dent=False),  # oil pan
        box((-0.11, 0.62, -1.06), (0.11, 0.76, -0.54), "alloy", dent=False),              # intake plenum
        box((-0.09, 0.76, -1.02), (0.09, 0.79, -0.58), "carbon", dent=False),             # plenum cover
    ]
    e += prism((0.0, 0.46, z0 - 0.02), "z", 0.085, 0.04, 12, "darksteel", dent=False)    # crank pulley
    return e


def gearbox() -> list:
    """Transaxle behind the engine, over the rear diff."""
    e = [box((-0.20, 0.34, -1.22), (0.20, 0.62, -1.12), "alloy", dent=False),            # bellhousing
         box((-0.16, 0.38, -1.72), (0.16, 0.58, -1.22), "alloy", dent=False)]            # case
    e += prism((0.0, 0.48, -1.74), "z", 0.06, 0.04, 8, "darksteel", dent=False)          # end cover
    return e


def fuel_tank() -> list:
    """Fuel cell in the nose, where the rally car has its engine."""
    return [box((-0.40, 0.40, 1.22), (0.40, 0.70, 1.72), "fuelcell", dent=False),
            box((-0.42, 0.38, 1.20), (0.42, 0.41, 1.74), "darksteel", dent=False),
            box((0.18, 0.70, 1.40), (0.28, 0.74, 1.50), "darksteel", dent=False)]


def exhaust() -> list:
    """From the turbos to a silencer and twin center tail pipes."""
    left = [beam((0.44, 0.52, -1.06), (0.30, 0.40, -1.58), 0.07, 0.07, "exhaust", dent=False),
            beam((0.22, 0.36, -1.84), (0.22, 0.34, -1.98), 0.08, 0.08, "exhaust", dent=False)]
    left += prism((0.22, 0.34, -2.02), "z", 0.06, 0.12, 10, "steel", dent=False)          # tail pipe
    e = left + mirror_x(left)
    e.append(box((-0.36, 0.30, -1.86), (0.36, 0.44, -1.58), "exhaust", dent=False))       # silencer
    return e


# Shields that change with the layout (part id -> parts that take hits first).
SHIELDS = {
    "engine": ["hatch", "bumper_r", "chassis"],
    "gearbox": ["bumper_r", "chassis"],
    "fuel_tank": ["bumper_f", "hood"],
    "exhaust": ["bumper_r"],
}
LABELS = {
    "engine": "Engine (4.0 twin-turbo V8, behind the seats)",
    "gearbox": "Transaxle (6-speed sequential)",
    "fuel_tank": "Fuel cell (in the nose)",
}


def hyper_body() -> dict:
    """Part id -> (car-frame elements, pivot or None for the elements' center).
    Hinged parts keep the rally car's pivots."""
    out = {
        "chassis": (chassis(), None), "engine": (engine(), None), "gearbox": (gearbox(), None),
        "fuel_tank": (fuel_tank(), None), "exhaust": (exhaust(), None), "radiator": (radiator(), None),
        "shell": (shell(), None), "cage": (cage(), None), "windshield": (windshield(), None),
        "rear_window": (rear_window(), None), "hood": (hood(), (0.0, 0.95, 1.02)),
        "lightpod": (lightpod(), None), "bumper_f": (bumper_f(), None), "bumper_r": (bumper_r(), None),
        "hatch": (hatch(), (0.0, 1.38, -1.10)), "wing": (wing(), None),
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
