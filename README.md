# tc-rally_game

A rally game for DiamondFire, written in
[Terracotta](https://github.com/Owlfroggy/terracotta). The cars are built from
separate parts, so they can be damaged and broken apart.

## Layout

| Path | Contents |
| --- | --- |
| [car/](car/) | Car design: [README](car/README.md), [part list](car/PARTS.md), `parts.json` for the game code |
| [pack/](pack/) | Resource pack (Minecraft 26.3, format 97.1), namespace `rally` |
| [pack/src/car_parts.py](pack/src/car_parts.py) | Generates the car models, textures and part data |
| [pack/src/car_hyper.py](pack/src/car_hyper.py) | The hypercar: its body panels and rear twin-turbo V8 layout (same parts, different shapes) |
| [tc/](tc/) | Terracotta code for the plot (206003, Mega): pack, commands, car spawning; `car_data.tc` is generated |
| [pack/src/engine_sound.py](pack/src/engine_sound.py) | Synthesizes the engine sound loops (inline-4, and the hypercar's V8, turbo whistle and blow-off valve) |
| [pack/src/driver.py](pack/src/driver.py) | Generates the driver model's item models and `tc/driver_data.tc` (its pose) |
| [pack/assets/minecraft/shaders/core/](pack/assets/minecraft/shaders/core/) | Entity core shader: draws player heads as the driver's body parts |
| [tools/build_pack.py](tools/build_pack.py) | Validates, zips and publishes the pack to the `pack-dist` branch |
| [tools/viewer/](tools/viewer/) | 3D viewer for the car models |
| [map/gen_map.py](map/gen_map.py) | Designs the rally map and writes `tc/map_data.tc` and [map/preview.png](map/preview.png) |

## Build the car

```bash
python3 pack/src/car_parts.py
```

Needs Python 3 with Pillow. It rewrites the files under
`pack/assets/rally/`, `car/parts.json`, `car/PARTS.md` and
`tools/viewer/car_data.js`. `python3 pack/src/driver.py` rewrites the driver
model's files (`pack/assets/rally/items/driver/`, `tc/driver_data.tc`).

## Publish the pack

```bash
python3 tools/build_pack.py --publish --push
```

Then put the printed URL in `packUrl()` in `tc/pack.tc` and send the code.
The build also compiles every core shader in the pack with `glslc` (shaderc)
the way the 26.3 client does, once per define set the game uses for it
(`tools/shader_variants.json`), and stops on any error.

## In game

| Command | Effect |
| --- | --- |
| `@menu` | Open the service board (also: right click the Roadbook in hotbar slot 1) |
| `@start [new \| SEED]` | Put a car before the start line of the procedural stage with you in it (the current one; `new` for a random seed, or a seed number); the clock runs from the start line to the finish |
| `@gen [rate N \| lead N \| wipe]` | Stage builder state; work per tick (default 60); road points kept built ahead of drivers (default 110); wipe every cell stages built |
| `@map build [X0 Z0 X1 Z1]` | Build the whole map (or only that plot-space area); `@map terrain\|road\|structs\|props\|decor\|wipe [area]` builds one phase, `@map stop` stops |
| `@tp X Y Z [YAW [PITCH]]` | Teleport in plot space (what the code uses: x and z from the plot corner) |
| `@tpa X Y Z [YAW [PITCH]]` | Teleport to absolute (F3) coordinates; `@origin X Y Z` with your F3 position sets the plot origin first |
| `@tpr DX DY DZ [DYAW [DPITCH]]` | Teleport relative, world axes |
| `@tpf FWD [UP [RIGHT]]` | Teleport relative to where you look |
| `@look YAW [PITCH]`, `@where` | Turn on the spot; show plot and absolute position |
| `@spec`, `@fly`, `@walk` | Spectator, creative flying, adventure |
| `@car [turn]` | Spawn a car 6 blocks ahead, facing your way turned by `turn` degrees (your previous car goes; each player has one) |
| `@drive` | Get in the nearest free car within 8 blocks |
| `@exit` | Get out (same as F) |
| `@flip` | Debug: roll your car (or the nearest) onto its roof |
| `@dkeep` | Debug: getting out leaves the driver model where it sat, to look at it from outside; `@dkeep` again removes those |
| `@tune [name value \| reset]` | Show or set physics tunables: spring, damper, grip, power, brake, steer, lat, smooth, links |
| `@dbg` | Toggle the physics debug readout in the action bar |
| `@damage` | List the damaged parts of your car (or the nearest) |
| `@hit PART AMOUNT` | Damage one part, e.g. `@hit bumper_f 50` (ids in [car/PARTS.md](car/PARTS.md)) |
| `@track build` | Build the rally test track with its start line at your feet, heading your way (about 85 x 70 blocks) |
| `@track clear` | Put grass back over the track's footprint |
| `@fix` | Repair your car (or the nearest): fresh parts, full HP, back on its wheels |
| `@part <id> [turn]` | Spawn one part only, to check its model |
| `@carcheck` | List the newest car's parts that have no display |
| `@clearcars` | Remove every car |
| `@pack` | Send the resource pack again |

## Procedural stages

`@start` (or DRIVE STAGE / NEW STAGE on the service board) drives a stage
made from a seed (`tc/gen.tc`). The same seed always gives the same stage,
so players can race each other's seeds; the best time is kept per seed.
Each seed picks its hill height, how much of the land is flat, and two or
three biome styles: Meadow, Woods, Pines, Alpine (snow and stone, gravel
roads go to snow) and Canyon (red sand and terracotta bands).

Everything comes from a hash of whole numbers and the seed, so any
column's height or biome can be worked out on its own, in any order.
Terrain heights sit on a node every 16 blocks (a smooth 96-block hill
lattice plus roughness) with bilinear columns in between; a 160-block
lattice picks the biome. The road is laid in 3-block steps through
straights, sweepers, tight bends, hairpins and chicanes, 2.1 to 3.2 km
long; it looks 21 and 42 blocks ahead and turns away from the plot edges,
the spawn and road it laid earlier. No step may land within 16 blocks of
earlier road (other than the last 8 points), so it never touches itself;
at a dead end it backs up 25 points and turns the other way (up to 10
times). Snowy roads are smooth quartz, so they stand out from the snow. Its height follows the ground
averaged over 33 blocks and climbs at most half a block per step.

The builder (`tc/gen_build.tc`) works only near the road: the 16 x 16
cells within about two cells of it, in the order the road reaches them.
Planning and the first 150 blocks take about 15 seconds; after that it
keeps the road built 110 points (330 blocks) ahead of the furthest driver,
and the HUD shows BUILDING AHEAD if a car catches up. A cell is filled in
runs of equal height and biome that grow from row to row, so flat ground
costs one fill. Then come trees, plants and boulders, the road's 13-block
shoulders, the 7-block road, marker posts and hay on bends, chevron boards
before tight bends, the start and finish gantries and a hay wall at the
end of the road. Before a new stage is built, every cell an older stage built is wiped back
to plain grass (`Clearing the old stage` on the action bar); the built
cells are kept in saved variables, so this works after a restart too.
A new seed can't start while someone else is on a timed run.

Beyond the cells the plot stays flat grass at y 49. The static Kestrel
Ridge map below is still in the code (`@map build`), but stages and the
static map use the same ground, so build only one of them on a plot.

## The map

The plot (206003, Mega) is a 1001 x 1001 block rally map: plot x and z
0..1000 (absolute x 100000.., z 4000..), ground at y 49, build limit 255.
`map/gen_map.py` designs it (needs numpy, scipy and Pillow):

```bash
python3 map/gen_map.py
```

![map](map/preview.png)

**SS1 Kestrel Ridge**, a 3.4 km loop. From the service park it runs west
along the start straight and through a water splash in the creek, then
round the lake on dirt and north through the village on asphalt. Forest
twisties with a crest jump follow, then a wooden bridge over the river,
the middle woods and a rocky climb with a hairpin. The road crosses a snowy
pass under the north-east mountains, takes the big jump on the descent and
goes through a terracotta canyon. Gravel brings it back to the flying
finish. Hay bales line the bends, with red and white marker posts, chevron
boards at the hairpins, kilometre signs, and spectator stands at the splash,
the jumps and the hairpins.

The plot code (`tc/map.tc`, `tc/map_build.tc`) builds it from compact data:
terrain heights every 8 blocks (interpolated exactly the same way in both
places), one surface letter per 8 x 8 cell (meadow, oak and spruce forest,
dark forest, rock, snow, canyon, lake bed, farm, village), the road every
3 blocks, the props and the structures. It works a few rows or road
stamps per tick and slows down when the plot CPU rises. Trees are
Minecraft's own (Generate Tree). `@map build` takes about 20 minutes on a
Mega plot (the client gets few chunk updates while it runs); run
`@map wipe` first to rebuild over an old build. `@map road` also rebuilds
the structures and props, because the road clears 6 blocks each side.
Players join and respawn at the service park, since the plot spawn is
inside the hills at the map edge.

`tc/stage.tc` times the stage: the clock starts at the start line and
stops at the finish line, with split checkpoints along the road that must
be passed in order. The HUD shows the stage time, and the best time is
saved.

## Driving

W throttle, S brake (reverse once stopped), A/D steer, hold Shift for the
handbrake, F to get out, Q to put the car back on its wheels. The action bar
shows speed, gear (`M3` = third with the manual gearbox), rpm and plot CPU.

The gearbox is set per player in the menu. Auto shifts up as the engine nears
the redline (wheelspin included) and down when it would bog, but not while the
tires spin. Manual shifts only on clicks: left click up, right click down.
Traction control is on by default (TRACTION on the service board, per
player): while a tire is past its grip under power, the power drops by 30%
a tick (down to 25%) and comes back 8% a tick once the tires grip, and the
revs stay with the road speed, so the tires keep their side grip. The HUD
shows TC while it cuts. With it off, spinning or sliding tires rev the
engine into the 7800 rpm limiter, which cuts the power for a tick and drops
the revs; the spinning tires then spend most of their grip along the wheel,
which is what keeps a drift going.

## Driver model

While someone drives, the car shows them sitting in it with their own skin
(`tc/driver.tc`), and the real player is hidden: from the other players with
Set Entity Hidden, from the driver's own third-person view with invisibility,
and the Roadbook in their hand turns into an item that draws nothing. The
model's head looks where the player looks (within what a neck allows), the
hands hold the steering wheel and turn it up to 60 degrees, the right hand
goes to the gear lever on each shift and to the handbrake while it is pulled.
In first person the driver looks out from the model's head and sees their arms
on the wheel; the head is not drawn when the camera is inside it. The seat
entity is moved every tick so the rider's eye (always 1.03 straight above
the seat) lands on the center of the model's head, so the camera stays
inside the car even when it lies on its roof.

Each body part is an item display holding the driver's player head, the only
item Minecraft draws with a player's skin. The pack's entity core shader
(`pack/assets/minecraft/shaders/core/entity.vsh` / `.fsh`) recognizes a part
by its display's brightness override: sky light 0 and block light = part id
(1 head, 2 torso, 3/4 right/left arm, 5/6 right/left leg, 7/8 slim arms). For
those it maps the head's texture net onto that part's net of the skin, so a
head scaled to 4 x 12 x 4 pixels is drawn as an arm, and lights it like the
car (full bright). Torso and legs are posed in their item models
(`pack/src/driver.py`, `rally:driver/torso`, `leg_r`, `leg_l`) and share the
car's rotation matrix; head and arms use `rally:driver/unit` (a 1 x 1 x 1
head) and get their own matrix every tick. The model is about 0.68 of a
player's size, so it fits under the roof. The service board's ARMS choice
(Classic 4 px or Slim 3 px) should match the player's skin.

Without the pack the parts show as plain heads. A real player head standing
in sky light 0 with block light 1 to 8 (deep indoors) would also be redrawn,
which is the cost of marking parts by brightness.

## Menu

`tc/menu.tc` draws the service board: like the dueling game's menus, the
player sits on a seat while it is open and the screen is made of text
displays, but here they form a flat board in the world (no shader), so the
crosshair is the cursor. Panels are text displays holding one space with a
colored background, scaled to size; buttons light up yellow under the
crosshair. Left click picks, right click or Shift closes. The board holds
the gearbox choice, the driver model's arm width, the stage record with a
start button, and spawn car.

The garage is a second panel hinged to the board's right edge, turned 40
degrees toward the player (each panel has its own frame, and a click hits
whichever panel the crosshair is on). It holds the car model (the rally
hatchback or the hypercar, see [car/README.md](car/README.md)), primary and
secondary colors (8 swatches each, with a livery preview), and rows for
decals and parts to come. The model and colors are used by every car the
player spawns.

Player data is kept by UUID, since names can change: gearbox, arm width
and colors per player, and stage records hold the driver's UUID. A saved
UUID-to-name table (updated on join and at the finish) shows the latest
name.
Only the player who opened it sees it.

The physics (`tc/physics.tc`) is one rigid body per car, stepped once per
tick: spring-damper suspension per wheel, tires capped by a friction
circle that depends on the surface block, a torque curve with a six-speed
gearbox and 40/60 four-wheel drive, and probe points that push the body out
of blocks. The ground is smoothed (`tc/ground.tc`): each block column's
surface height is averaged over the 10 x 10 columns around it (`@tune smooth
N` sets the half-width), so a one-block step or a slab is a ramp about 10
blocks long. Wheels and body probes both ride on that
surface. A block with a solid block above it, or a column more than about one
block above the car, is a wall. All rigid parts share one display matrix (`tc/render.tc`), so a
driven car costs about 5% plot CPU.

DiamondFire numbers keep 3 decimals, so the physics works per unit mass
(accelerations) and never multiplies by 1 / mass.

## Damage

`tc/damage.tc`. The strongest body hit of a tick above 3 m/s damages the
parts whose hitbox is near the contact point; a part whose shields are also
there and still on is protected (bumper before radiator, hood before engine),
and the chassis takes a share of every hit. Slamming a wheel into its bump
stop damages that spring and arm. Below 60% HP a part shows its damaged
model. At 0 HP a part that comes off breaks away with everything it carries
as tumbling debris; the others fail in place. Effects: engine power, lost top
gears, axles or single wheels without drive, softer springs, punctured tires,
missing wheels, and an engine that overheats without its radiator and smokes
when hurt.

## Engine sound

The engine is a procedural 2.0 turbo inline-4, synthesized offline by
`pack/src/engine_sound.py`: one combustion pulse fired twice per crank
revolution in I4 order (1-3-4-2) with per-cylinder imbalance and jitter,
through an exhaust filter and pipe resonances, with crank hum, valvetrain
tick and turbo whistle. The result is one short clip of whole 4-cylinder
cycles. In game (`tc/sound.tc`) the driven car plays it every tick, pitched
to the exact rpm; the copies overlap, so the pitch follows the rpm smoothly.
Minecraft clamps pitch to 0.5..2, and pitching far also drags the exhaust
tone up, so the same cycle is baked at 1300, 2900 and 5800 rpm and
crossfaded at 1900 and 4100 rpm (no clip is pitched more than about 45%). Off throttle it is quieter, with random
anti-lag pops above 3500 rpm.

To change what each combustion ("explosion") sounds like, give it any WAV:

```bash
python3 pack/src/engine_sound.py --pulse my_bang.wav --preview build/engine_sweep.wav
```

`--preview` also writes a rev sweep to listen to. Then publish the pack.

## View the car

```bash
python3 -m http.server 8765 --directory tools/viewer
```

Then open http://localhost:8765. Drag to orbit. Click a part for its data, and
double-click it to break it off. The controls explode the car, show the
damaged models, ghost the body to show the mechanics, and change the paint and
accent colors.
