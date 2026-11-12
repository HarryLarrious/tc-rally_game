# Car design

The rally car is a two-door hatchback with four-wheel drive and a front engine.
It is built from 52 separate parts. Each part is its own resource-pack model on
its own item display, so any part can take damage, fail, or break off.

- [PARTS.md](PARTS.md): every part with its parent, mass, HP and what breaking
  it does (generated).
- [parts.json](parts.json): the same data for the game code: pivots, rest
  rotations, hitboxes, mount points (generated).
- [../pack/src/car_parts.py](../pack/src/car_parts.py): the source of truth.
  It holds the geometry and the part data, and writes the models, item
  definitions, textures, both files above and the viewer data.
- [../tools/viewer/](../tools/viewer/): a 3D viewer for the generated models.

## Size and frame

| | |
| --- | --- |
| Length × width × height | 4.17 × 1.86 × 1.45 m (blocks) |
| Wheelbase, track | 2.50 m, 1.54 m |
| Wheels | 0.32 m radius, 0.22 m wide |
| Mass | 1108 kg (sum of the parts) |

Car frame: **+X left, +Y up, +Z forward**, in meters (1 m = 1 block). The
origin is on the ground, centered between the axles. This matches a Minecraft
entity at yaw 0, which faces +Z (south) and has +X (east) on its left.

## How a part is placed

Every part has a **pivot** (a point in the car frame) and a **rest rotation**
(Euler XYZ degrees, the same order Minecraft uses). Its model is built around
the pivot. The game puts each display at the car's position and sets its
matrix to:

```
car rotation * translate(pivot) * rotate(rest) * animation
```

The models are authored at half size, so that a part can reach 3 m from its
pivot inside Minecraft's -16..32 element limit. Each item definition scales
the model back up with a `transformation`, so the game code uses 1:1 meters
and no extra scale. The same `transformation` also undoes the 180° Y turn
that Minecraft applies to every item display, so the matrix above is all the
game needs.

DiamondFire spawns item displays without the yaw of the spawn location, so a
car's heading goes into the matrix too (`turnMatrix` in `tc/car.tc`).

Parts that move use one of these animations (the `anim` field):

| Anim | Parts | Motion |
| --- | --- | --- |
| `fixed` | body, engine, diffs, rear uprights | Rigid with the car |
| `spin_x` | wheels | Roll about the axle |
| `steer_y` | front uprights | Steer |
| `swing_z` | control arms | Swing up and down with the suspension |
| `stretch_y` | springs | Aim from the arm mount to the strut top, scale along the length |
| `stretch_x` | half shafts | Aim from the diff to the hub, scale along the length |
| `spin_z` | drive shaft, steering wheel | Spin about their own axis |

The mount points that tie moving parts together (ball joint, spring mounts,
diff outputs, hub) are in each part's `links` in `parts.json`.

## Parts

52 parts in seven groups. [PARTS.md](PARTS.md) has the full list.

| Group | Parts |
| --- | --- |
| Structure | chassis (floor, sills, rails, strut towers, firewall), shell (roof, pillars, quarter glass) |
| Interior | roll cage with seats and dash, steering wheel |
| Glass | windshield, rear window |
| Body | 2 doors, 2 mirrors, 2 front fenders (with headlights), 2 rear quarters (with tail lights), 4 mud flaps, hood, light pod, 2 bumpers, hatch, rear wing |
| Powertrain | engine, gearbox, radiator, center drive shaft, front and rear diffs, 4 half shafts, fuel cell, exhaust |
| Suspension | per corner: control arm, upright with brake disc and caliper, coilover (spring and damper) |
| Wheels | 4 wheels (tire and rim) |

The four corners share five models (`wheel`, `upright`, `arm`, `spring`,
`halfshaft`). The right side uses the same models turned 180° about Y.

## Hierarchy

Each part has one parent. When a part breaks off, everything it carries goes
with it:

```
chassis
├── shell ── windshield, door_l ── mirror_l, door_r ── mirror_r
├── cage ── steering_wheel
├── hood ── lightpod
├── hatch ── rear_window, wing
├── bumper_f, bumper_r
├── fender_fl ── mudflap_fl   (and fender_fr, quarter_rl, quarter_rr likewise)
├── engine ── gearbox
├── radiator, fuel_tank, exhaust, driveshaft
├── diff_f ── halfshaft_fl, halfshaft_fr
├── diff_r ── halfshaft_rl, halfshaft_rr
├── spring_fl, spring_fr, spring_rl, spring_rr
└── arm_fl ── upright_fl ── wheel_fl    (one chain per corner)
```

## Damage model (simple)

This is the plan for the damage step. The data it needs is already in
`parts.json`.

1. **HP per part.** A hit (a collision or a hard landing) has a point, a
   direction and an energy. The parts whose `hitbox` the hit reaches take the
   damage.
2. **Shields.** A part's `shield` list names the parts that must go first. The
   bumper takes front hits before the radiator; the radiator and hood before
   the engine; the chassis takes ground strikes before the diffs and shafts.
3. **Two ways to break.** `detach` parts (body panels, wheels, arms, uprights,
   exhaust, drive shaft) come off and become loose debris with their children.
   `fail` parts (engine, gearbox, diffs, springs, half shafts, glass, chassis)
   stay on the car and stop working.
4. **Damaged look.** Body panels, glass and wheels have a `_damaged` model:
   dented panels, scratched paint, cracked glass, a torn tire. Setting custom
   model data string 0 to `damaged` switches to it. Mechanical parts show
   damage through smoke, sound and handling.
5. **Effects.** Each part's `effect` says what failing does: less engine
   power, lost gears, an axle without drive, a sagging corner, a brake that
   fades, a wheel that comes off.

## Pack

- Namespace `rally`. Item definitions are at `rally:car/<model>` (use as the
  `item_model` component on the display's item).
- Tint 0 is the body paint and tint 1 the accent color (wheel arches, wing,
  rims, mud flaps). Set them with custom model data colors 0 and 1.
- Head, fog and pod lamps glow (`light_emission`).
- The target client is Minecraft 26.3, resource pack format 97.1.

## Entity budget

One car is 52 item displays plus a seat entity. Most parts only follow the
car body, but each needs a matrix update when the car moves. Ideas for when
this costs too much:

- Parts hidden under the body (drive shaft, half shafts, diffs, gearbox) can
  stay unspawned until the body around them is gone.
- Parts that never come off (chassis, shell, cage) could merge into one model.

## Tested in game

Spawned on plot 163352 (Minecraft 26.3, 2026-11-12): all 52 parts load and
sit where the viewer shows them; glass is translucent, the lamps glow, and
the paint and accent tints work. The damaged models have not been shown in
game yet.
