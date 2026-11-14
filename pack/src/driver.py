#!/usr/bin/env python3
"""The driver model: the player's own skin, sitting in the car.

Every body part is an item display holding the driver's player head. The
core shader in pack/assets/minecraft/shaders/core/entity.* draws a head as
another part (torso, arm, leg) when the display's brightness override marks
it (sky 0, block = part id), so a part is just a head scaled to the part's
size.

Writes:
  pack/assets/rally/items/driver/unit.json   the head as a 1 x 1 x 1 box at the origin
  pack/assets/rally/items/driver/<part>.json torso and legs, posed in the car frame
  pack/assets/rally/items/empty.json         an item that draws nothing (held while driving)
  tc/driver_data.tc                          the pose for the game code

Frames: the car frame is +X left, +Y up, +Z forward, meters, around the car
origin (same as car_parts.py). A part's own frame is the player's: left, up,
forward. Minecraft draws the head with its face to -Z and the player's left
to -X in an item display's local space (after the display's own 180 degree
turn), so a part with axes (a_left, a_up, a_fwd), size (sx, sy, sz) and
center c is the display matrix [-a_left*sx | a_up*sy | -a_fwd*sz | c] applied
to the unit head.

Torso and legs never move in the car frame, so their pose is baked into their
item model and their displays share the car's rotation matrix with the rigid
car parts. Head and arms move (look, steering, gear shifts) and are posed by
tc/driver.tc every tick on top of unit.json.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ITEMS = ROOT / "pack/assets/rally/items"

# One skin pixel in meters. A Minecraft player sits 20 px tall from the seat
# to the top of the head; 0.04 fits that under the roof (1.36) from the
# cushion (0.46).
PX = 0.04
HIP = (0.33, 0.52, -0.10)        # driver's hip joint center (left seat)
LEAN = 8.0                       # torso leans back (degrees), like the seat back
LEG_DROP = 10.0                  # legs point forward and this much down
LEG_SPLAY = 4.0                  # and this much outward

# Hands on the rim: angle in the rim plane from the car's left (+X) toward
# the rim's top, before the wheel turns.
GRIP_LEFT = 15.0
GRIP_RIGHT = 165.0
RIM = 0.17
# The right hand's targets: gear knob and handbrake top (car frame).
KNOB = (0.02, 0.87, 0.32)
HANDBRAKE = (0.0, 0.79, 0.20)

PART_IDS = {"head": 1, "torso": 2, "arm_r": 3, "arm_l": 4, "leg_r": 5, "leg_l": 6,
            "arm_r_slim": 7, "arm_l_slim": 8}


# ---------------------------------------------------------------- math

def add(a, b): return tuple(x + y for x, y in zip(a, b))
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def mul(a, k): return tuple(x * k for x in a)
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a): return mul(a, 1 / math.sqrt(dot(a, a)))


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def translate(t):
    return [[1, 0, 0, t[0]], [0, 1, 0, t[1]], [0, 0, 1, t[2]], [0, 0, 0, 1]]


def diag(x, y, z):
    return [[x, 0, 0, 0], [0, y, 0, 0], [0, 0, z, 0], [0, 0, 0, 1]]


def columns(cx, cy, cz, t):
    return [[cx[0], cy[0], cz[0], t[0]], [cx[1], cy[1], cz[1], t[1]], [cx[2], cy[2], cz[2], t[2]], [0, 0, 0, 1]]


def swing(d):
    """Axes (left, up, forward) of a limb hanging along d: the standing frame
    turned by the smallest rotation that takes straight down to d."""
    d = norm(d)
    a = (0.0, -1.0, 0.0)
    k = cross(a, d)
    c = dot(a, d)
    f = (0.0, 0.0, 1.0)
    kf = cross(k, f)
    fwd = norm(add(add(f, kf), mul(cross(k, kf), 1 / (1 + c))))
    up = mul(d, -1)
    return cross(up, fwd), up, fwd


# ---------------------------------------------------------------- pose

def pose():
    r = math.radians(LEAN)
    up_t = (0.0, math.cos(r), -math.sin(r))
    fwd_t = (0.0, math.sin(r), math.cos(r))
    left = (1.0, 0.0, 0.0)
    neck = add(HIP, mul(up_t, 12 * PX))
    parts = {
        "torso": (left, up_t, fwd_t, (8, 12, 4), add(HIP, mul(up_t, 6 * PX))),
    }
    for name, s in (("leg_l", 1), ("leg_r", -1)):
        piv = add(HIP, mul(left, s * 2 * PX))
        dr, sp = math.radians(LEG_DROP), math.radians(LEG_SPLAY)
        d = (s * math.sin(sp), -math.sin(dr), math.cos(dr) * math.cos(sp))
        l, u, f = swing(d)
        parts[name] = (l, u, f, (4, 12, 4), add(piv, mul(norm(d), 6 * PX)))
    shoulder_l = add(sub(neck, mul(up_t, 2 * PX)), mul(left, 6 * PX))
    shoulder_r = add(sub(neck, mul(up_t, 2 * PX)), mul(left, -6 * PX))
    return parts, neck, up_t, shoulder_l, shoulder_r


# The unit head: skull model space (pixels / 16, y down, face to -Z, the
# player's left to +X) to a 1 x 1 x 1 box centered at the origin with the
# face to -Z and the player's left to -X, as seen after the item renderer's
# -0.5 shift and the display's 180 degree turn about Y.
#   skull -> diag(-2, -2, 2) -> +(0, -0.5, 0)   = Q (wanted local)
#   local = Ry180 * T(-0.5) * X * skull  =>  X = T(0.5) * Ry180 * Q
RY180 = diag(-1, 1, -1)
Q = matmul(translate((0, -0.5, 0)), diag(-2, -2, 2))


def item_transform(placement):
    """Item model transformation X so the display shows the unit head moved
    by `placement` (a 4x4 in the display's local space)."""
    return matmul(matmul(translate((0.5, 0.5, 0.5)), RY180), matmul(placement, Q))


def placement(l, u, f, size, center):
    sx, sy, sz = (n * PX for n in size)
    return columns(mul(l, -sx), mul(u, sy), mul(f, -sz), center)


def head_item(matrix):
    flat = [round(matrix[i][j], 6) + 0.0 for i in range(4) for j in range(4)]
    return {"model": {"type": "minecraft:special", "base": "minecraft:item/template_skull",
                      "model": {"type": "minecraft:player_head"}, "transformation": flat}}


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + "\n")


def fmt(x: float) -> str:
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def main() -> None:
    parts, neck, up_t, sh_l, sh_r = pose()
    write_json(ITEMS / "driver/unit.json", head_item(item_transform(diag(1, 1, 1))))
    for name, (l, u, f, size, c) in parts.items():
        write_json(ITEMS / f"driver/{name}.json", head_item(item_transform(placement(l, u, f, size, c))))
    write_json(ITEMS / "empty.json", {"model": {"type": "minecraft:empty"}})

    def v(name, p):
        return f"    global {name} = vec({fmt(p[0])}, {fmt(p[1])}, {fmt(p[2])});\n"

    tc = (
        "// Generated by pack/src/driver.py: do not edit.\n"
        "// The driver model's pose in the car frame (+X left, +Y up, +Z forward, m).\n\n"
        "/** One skin pixel (m); the neck, the torso's up axis, the shoulder pivots,\n"
        " * the hands' rim angles and rim radius, the gear knob and handbrake. */\n"
        "declare global dPx: num;\n"
        "declare global dNeck: vec;\n"
        "declare global dTorsoUp: vec;\n"
        "declare global dShoulderL: vec;\n"
        "declare global dShoulderR: vec;\n"
        "declare global dGripL: num;\n"
        "declare global dGripR: num;\n"
        "declare global dRim: num;\n"
        "declare global dKnob: vec;\n"
        "declare global dHandbrake: vec;\n\n"
        "function loadDriverPose {\n"
        f"    global dPx = {fmt(PX)};\n"
        + v("dNeck", neck) + v("dTorsoUp", up_t) + v("dShoulderL", sh_l) + v("dShoulderR", sh_r)
        + f"    global dGripL = {fmt(GRIP_LEFT)};\n"
        f"    global dGripR = {fmt(GRIP_RIGHT)};\n"
        f"    global dRim = {fmt(RIM)};\n"
        + v("dKnob", KNOB) + v("dHandbrake", HANDBRAKE)
        + "}\n\n"
        "/** Item model and part id (the shader's mark) of each rigid part. */\n"
        "function driverRigidParts(): list {\n"
        f"    return [\"rally:driver/torso {PART_IDS['torso']}\", \"rally:driver/leg_r {PART_IDS['leg_r']}\", "
        f"\"rally:driver/leg_l {PART_IDS['leg_l']}\"];\n"
        "}\n"
    )
    (ROOT / "tc/driver_data.tc").write_text(tc)
    print(f"driver: {len(parts)} posed parts, unit head, tc/driver_data.tc")


if __name__ == "__main__":
    main()
