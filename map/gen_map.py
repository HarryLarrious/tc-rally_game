#!/usr/bin/env python3
"""Generates the rally map: terrain, water, the stage road and its props.

The map fills the whole 1001 x 1001 build area of the plot (plot x and z
0..1000, ground at y 49, build limit 255). The design is made here, at full
resolution, and sent to the plot as compact data that the plot code
(tc/map.tc) turns into blocks:

  * terrain: one height per 8 blocks (126 x 126 nodes). The plot code
    interpolates them bilinearly with integer math, exactly as
    `column_height` here does, so this script knows every column's height.
  * one letter per 8 x 8 cell for the surface (meadow, forest, rock, snow,
    canyon, lake bed, farm, village ...). The plot code scatters plants,
    trees and boulders by that letter.
  * the stage road: a closed loop sampled every 3 blocks with its height in
    half blocks and its surface. The plot code stamps it block by block.
  * props (hay bales, marker posts, chevrons, signs, spectator stands) and
    structures (start and finish gantries, service park, village houses,
    bridge, lake jetty, cabins).

Writes tc/map_data.tc, map/preview.png and map/map.json (summary).

    python3 map/gen_map.py
"""

import json
import math
import os

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 1001          # map size in blocks
G = 8             # node spacing
NN = 126          # nodes per side (0..125 -> 0..1000)
NC = 125          # cells per side
WL = 46           # water level: water fills up to this y
BASE = 49         # original ground surface y
SNOW = 104        # surface y from which cells are snow
ROAD_W = 7        # stage road width
VERGE = 3         # flat verge each side of the road

X, Z = np.meshgrid(np.arange(S, dtype=float), np.arange(S, dtype=float))


# ---------------------------------------------------------------- noise

def vnoise(scale, seed):
    """Smooth value noise in -1..1 with features about `scale` blocks."""
    rng = np.random.default_rng(seed)
    n = int(S / scale) + 3
    lat = rng.random((n, n)) * 2 - 1
    fx, fz = X / scale, Z / scale
    ix, iz = fx.astype(int), fz.astype(int)
    tx, tz = fx - ix, fz - iz
    sx, sz = tx * tx * (3 - 2 * tx), tz * tz * (3 - 2 * tz)
    a, b = lat[iz, ix], lat[iz, ix + 1]
    c, d = lat[iz + 1, ix], lat[iz + 1, ix + 1]
    return (a * (1 - sx) + b * sx) * (1 - sz) + (c * (1 - sx) + d * sx) * sz


def fbm(scale, seed, octaves=4, gain=0.5):
    tot, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        tot = tot + amp * vnoise(scale / 2 ** o, seed * 31 + o)
        norm += amp
        amp *= gain
    return tot / norm


def gauss(cx, cz, sigma):
    return np.exp(-((X - cx) ** 2 + (Z - cz) ** 2) / (2 * sigma * sigma))


def smoothstep(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def polyline(points, step=1.0):
    """Densely sampled points along a polyline."""
    out = []
    for (x0, z0), (x1, z1) in zip(points, points[1:]):
        n = max(1, int(math.hypot(x1 - x0, z1 - z0) / step))
        for k in range(n):
            t = k / n
            out.append((x0 + (x1 - x0) * t, z0 + (z1 - z0) * t))
    out.append(points[-1])
    return np.array(out)


def dist_field(pts):
    tree = cKDTree(pts)
    d, idx = tree.query(np.stack([X.ravel(), Z.ravel()], 1))
    return d.reshape(S, S), idx.reshape(S, S)


# ---------------------------------------------------------------- layout

# Places (plot x, z).
LAKE_C = (318, 676)
LAKE_R = 104
VILLAGE_C = (168, 432)
PARK = (470, 912, 720, 992)          # service park x0 z0 x1 z1
CANYON = (790, 560, 1000, 870)
DARK_FOREST = (420, 330, 75)
RIVER = [(566, -20), (562, 110), (545, 250), (505, 395), (452, 515),
         (398, 598), (355, 640)]
CREEK = [(350, 770), (380, 840), (408, 895), (420, 950), (428, 1030)]

# The stage: a clockwise loop (seen from above, x right, z down). Each
# control point starts a stretch with that surface:
#   a asphalt, g gravel, d dirt, s snow, r rocky gravel
STAGE = [
    (760, 902, "a"),   # 0 flying finish, start line a little further
    (640, 902, "a"),
    (548, 900, "g"),
    (470, 892, "g"),
    (410, 882, "g"),   # water splash (creek)
    (338, 856, "d"),   # 5 lakeside
    (246, 826, "d"),
    (172, 770, "d"),
    (132, 672, "g"),
    (128, 566, "a"),   # village
    (150, 470, "a"),   # 10
    (166, 392, "a"),
    (150, 322, "g"),   # forest twisties
    (96, 262, "g"),
    (84, 182, "g"),
    (130, 104, "g"),   # 15
    (214, 76, "g"),
    (272, 128, "g"),
    (324, 196, "g"),   # crest jump
    (398, 156, "g"),
    (468, 124, "g"),   # 20
    (530, 116, "g"),   # bridge over the river
    (604, 118, "g"),
    (660, 162, "d"),   # down into the middle woods
    (656, 246, "d"),
    (606, 318, "d"),   # 25
    (624, 412, "d"),
    (700, 452, "g"),
    (770, 420, "r"),   # climb
    (790, 352, "r"),
    (744, 300, "r"),   # 30 hairpin
    (770, 246, "r"),
    (846, 236, "s"),   # the pass
    (900, 280, "s"),
    (930, 360, "g"),
    (944, 450, "g"),   # 35 big jump
    (930, 540, "r"),
    (884, 612, "d"),   # canyon
    (852, 684, "d"),
    (830, 760, "d"),
    (812, 836, "g"),   # 40
    (792, 884, "g"),
]
START_S = 120      # start line: blocks along the road from the first point
FINISH_S = 0       # finish line: at the first point (flying finish)
JUMPS = [(944, 450, 2.6, 11), (324, 196, 1.6, 8), (812, 836, 1.8, 9), (624, 412, 1.4, 7)]
SURF = {
    "a": ("gray_concrete", "polished_deepslate_slab", "stone"),
    "g": ("gravel", "tuff_slab", "dirt"),
    "d": ("coarse_dirt", "mud_brick_slab", "dirt"),
    "s": ("snow_block", "smooth_quartz_slab", "stone"),
    "r": ("gravel", "tuff_slab", "stone"),
}


# Surface letters: (surface, sub soil, lake/river bed, fill depth, patch
# blocks, patches per cell, plants ("+" = two blocks tall), plants per cell,
# trees (Generate Tree types), trees per cell, boulders per cell).
# Upper case letters (near the road) get no trees and no boulders.
GRASSES = ["short_grass"] * 6 + ["tall_grass+", "dandelion", "poppy", "cornflower", "oxeye_daisy",
                                  "azure_bluet", "wildflowers", "bush"]
PARAMS = {
    "g": ("grass_block", "dirt", "sand", 5, ["coarse_dirt", "moss_block"], 1.5, GRASSES, 18,
          ["Oak Tree"] * 4 + ["Birch Tree", "Big Oak Tree"], 0.1, 0.03),
    "f": ("grass_block", "dirt", "gravel", 5, ["podzol", "coarse_dirt", "moss_block"], 5,
          ["short_grass"] * 3 + ["fern", "fern", "leaf_litter", "leaf_litter", "bush", "lily_of_the_valley",
                                 "tall_grass+"], 12,
          ["Oak Tree", "Oak Tree", "Birch Tree", "Birch Tree", "Tall Birch Tree", "Big Oak Tree"], 1.1, 0.06),
    "p": ("grass_block", "dirt", "gravel", 6, ["podzol", "podzol", "coarse_dirt"], 10,
          ["fern", "fern", "fern", "short_grass", "short_grass", "large_fern+", "sweet_berries", "leaf_litter"], 8,
          ["Spruce Tree", "Spruce Tree", "Slightly Taller Spruce Tree", "Slightly Taller Spruce Tree",
           "Big Spruce Tree"], 1.4, 0.1),
    "k": ("grass_block", "dirt", "gravel", 5, ["podzol", "moss_block", "coarse_dirt"], 10,
          ["fern", "leaf_litter", "leaf_litter", "brown_mushroom", "red_mushroom", "short_grass"], 7,
          ["Dark Oak Tree"] * 4 + ["Big Oak Tree"], 2.0, 0.05),
    "r": ("stone", "stone", "gravel", 9, ["andesite", "cobblestone", "gravel", "tuff", "coarse_dirt"], 16,
          [], 0, ["Spruce Tree"], 0.08, 0.25),
    "m": ("stone", "stone", "gravel", 9, ["snow_block", "snow_block", "andesite", "gravel"], 22,
          [], 0, ["Spruce Tree"], 0.1, 0.12),
    "n": ("snow_block", "stone", "gravel", 9, ["stone", "packed_ice"], 3, [], 0, [], 0, 0.03),
    "c": ("terracotta", "terracotta", "sand", 12, [], 0, ["dead_bush", "short_dry_grass", "short_dry_grass"], 2,
          [], 0, 0.15),
    "s": ("sand", "sandstone", "sand", 4, ["gravel"], 3, ["short_dry_grass"], 1, [], 0, 0),
    "l": ("sand", "sand", "sand", 3, ["clay", "gravel"], 8, ["seagrass"], 8, [], 0, 0),
    "v": ("grass_block", "dirt", "sand", 4, ["coarse_dirt"], 1,
          ["short_grass", "short_grass", "poppy", "dandelion", "oxeye_daisy"], 5, [], 0, 0),
    "a": ("grass_block", "dirt", "sand", 4, [], 0, ["short_grass"], 2, [], 0, 0),
    "h": ("farmland", "dirt", "sand", 4, [], 0, [], 0, [], 0, 0),
}


def catmull_loop(ctrl, step=1.0):
    """Closed Catmull-Rom spline through the control points, resampled every
    `step` blocks. Returns points and the control index of each point."""
    pts = np.array([(c[0], c[1]) for c in ctrl], float)
    n = len(pts)
    dense, owner = [], []
    for i in range(n):
        p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        seg = np.linalg.norm(p2 - p1)
        m = max(8, int(seg * 4))
        for k in range(m):
            t = k / m
            t2, t3 = t * t, t * t * t
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                       + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            dense.append(q)
            owner.append(i)
    dense.append(dense[0])
    owner.append(owner[0])
    dense = np.array(dense)
    seglen = np.linalg.norm(np.diff(dense, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seglen)])
    total = cum[-1]
    s = np.arange(0, total, step)
    xs = np.interp(s, cum, dense[:, 0])
    zs = np.interp(s, cum, dense[:, 1])
    own = np.array(owner)[np.searchsorted(cum, s, side="right") - 1]
    return np.stack([xs, zs], 1), own, total


# ---------------------------------------------------------------- terrain

def build_terrain():
    H = 50.3 + 2.6 * fbm(220, 1) + 1.2 * fbm(70, 2, 3)
    # Wooded hills north and west of the middle.
    hills = 20 * gauss(300, 230, 170) + 12 * gauss(560, 430, 120) + 8 * gauss(80, 140, 120)
    H += hills * (0.55 + 0.45 * fbm(140, 3))
    # Mountains in the north-east: ridged noise on broad peaks.
    ridge = 1 - np.abs(fbm(150, 4, 5))
    mount = 78 * gauss(930, 110, 95) + 40 * gauss(770, 20, 75) + 34 * gauss(990, 300, 70) + 22 * gauss(830, 160, 60)
    H += mount * (0.55 + 0.6 * ridge)
    # Canyon plateau in the east, the road cuts through it.
    cx0, cz0, cx1, cz1 = CANYON
    inside = np.minimum.reduce([X - cx0, cz1 - Z, Z - cz0]) + 45 * fbm(70, 12, 3)
    plateau = smoothstep(0, 18, inside)
    H += plateau * (24 + 6 * fbm(60, 5, 3))
    # Higher ground at the map edge.
    edge = np.minimum.reduce([X, Z, S - 1 - X, S - 1 - Z])
    H += 15 * smoothstep(80, 0, edge) * (0.65 + 0.35 * fbm(90, 6))
    # Flat village and service park.
    vd = np.hypot(X - VILLAGE_C[0], Z - VILLAGE_C[1])
    w = smoothstep(125, 85, vd)
    H = H * (1 - w) + 51.2 * w
    px0, pz0, px1, pz1 = PARK
    pd = np.maximum.reduce([px0 - X, X - px1, pz0 - Z, Z - pz1, np.zeros_like(X)])
    w = smoothstep(30, 0, pd)
    H = H * (1 - w) + 50 * w
    # The lake, its river and the creek that leaves it.
    ang = np.arctan2(Z - LAKE_C[1], X - LAKE_C[0])
    rr = LAKE_R * (1 + 0.13 * np.sin(3 * ang + 0.7) + 0.08 * np.sin(5 * ang + 2.1))
    ld = np.hypot(X - LAKE_C[0], Z - LAKE_C[1]) - rr          # <0 inside
    lake_bed = WL - np.clip(-ld * 0.22 + 1.5, 1.5, 9)
    H = np.where(ld < 0, np.minimum(H, lake_bed), H)
    shore = WL + 1 + np.clip(ld, 0, None) * 0.18
    H = np.where((ld >= 0) & (ld < 40), np.minimum(H, shore), H)
    water = ld < 0
    rd, _ = dist_field(polyline(RIVER))
    H = np.where(rd < 11, np.minimum(H, 41.5 + (rd / 11) ** 2 * 4), H)
    H = np.where((rd >= 11) & (rd < 46), np.minimum(H, WL + 1 + (rd - 11) * 0.45), H)
    water |= rd < 10.5
    cd, _ = dist_field(polyline(CREEK))
    H = np.where(cd < 9, np.minimum(H, 43.5 + (cd / 9) ** 2 * 2.5), H)
    H = np.where((cd >= 9) & (cd < 30), np.minimum(H, WL + 1 + (cd - 9) * 0.3), H)
    water |= cd < 8.5
    H = np.where(water, np.minimum(H, WL - 0.6), np.maximum(H, WL + 0.6))
    return H, water, ld, rd, cd, mount, plateau


def road_profile(H, path, own, rd, cd, plateau):
    """Height of the road (in half blocks of the surface block) per point."""
    n = len(path)
    xi = np.clip(np.round(path[:, 0]).astype(int), 0, S - 1)
    zi = np.clip(np.round(path[:, 1]).astype(int), 0, S - 1)
    h = H[zi, xi].copy()
    # Through the canyon the road keeps low, between the walls.
    h = np.where(np.isin(own, CANYON_OWN), h - 27 * plateau[zi, xi], h)
    # Smooth along the loop.
    k = 41
    pad = np.concatenate([h[-k:], h, h[:k]])
    h = np.convolve(pad, np.ones(k) / k, mode="same")[k:-k]
    rdp, cdp = rd[zi, xi], cd[zi, xi]
    forced = np.full(n, np.nan)
    bridge = rdp < 17
    ford = cdp < 12
    forced[bridge] = WL + 5        # bridge deck block at y 51
    forced[ford] = WL - 0.5        # 45 + a waterlogged slab
    flat = np.zeros(n, bool)
    sx = path[:, 0]
    park = (path[:, 1] > 880) & (sx > 520) & (sx < 790)
    forced[park] = 50
    h = np.maximum(h, WL + 1.5)
    g = 0.13
    fixed = ~np.isnan(forced)
    h = np.where(fixed, forced, h)
    for _ in range(40):
        for i in range(n):
            if not fixed[i]:
                h[i] = min(max(h[i], h[i - 1] - g), h[i - 1] + g)
        for i in range(n - 1, -1, -1):
            if not fixed[i]:
                j = (i + 1) % n
                h[i] = min(max(h[i], h[j] - g), h[j] + g)
    h = np.where(np.isnan(forced), h, forced)
    # Jumps: a short crest.
    for jx, jz, amp, half in JUMPS:
        i0 = int(np.argmin(np.hypot(path[:, 0] - jx, path[:, 1] - jz)))
        for d in range(-half, half + 1):
            i = (i0 + d) % n
            h[i] += amp * 0.5 * (1 + math.cos(math.pi * d / half))
    r2 = np.round(h * 2).astype(int)
    return r2, bridge, ford


def corridor(H, path, r2, bridge, own):
    """Flattens the terrain along the road to the road height."""
    tree = cKDTree(path)
    d, idx = tree.query(np.stack([X.ravel(), Z.ravel()], 1), distance_upper_bound=40)
    d = d.reshape(S, S)
    idx = np.minimum(idx.reshape(S, S), len(path) - 1)
    target = (r2[idx] // 2).astype(float)
    surf = np.array([STAGE[o][2] for o in own])
    # Canyon stretch: steep walls; elsewhere wide grassy shoulders.
    blend = np.where(np.isin(own[idx], CANYON_OWN), 4.0, 16.0)
    inner = ROAD_W / 2 + VERGE + 0.5
    w = np.clip(1 - (d - inner) / blend, 0, 1)
    w = w * w * (3 - 2 * w)
    w = np.where(np.isfinite(d), w, 0)
    w = np.where(bridge[idx], 0, w)
    return H * (1 - w) + target * w, d, idx


CANYON_OWN = [36, 37, 38, 39]


# ---------------------------------------------------------------- DF math

def column_heights(nodes):
    """Surface y of every column, the way the plot code computes it."""
    out = np.zeros((S, S), int)
    for z in range(S):
        j = min(z // G, NN - 2)
        v = z - G * j
        R = (G - v) * nodes[j] + v * nodes[j + 1]          # units 1/8
        for i in range(NC):
            u = np.arange(G)
            num = (G - u) * R[i] + u * R[i + 1]
            out[z, G * i:G * i + G] = (num + 32) // 64
        out[z, 1000] = (8 * R[125] + 32) // 64
    return out


# ---------------------------------------------------------------- props

def snap_rot(dx, dz):
    """Sign rotation (0..15) facing direction (dx, dz)."""
    yaw = math.degrees(math.atan2(-dx, dz))      # MC yaw of that direction
    return int(round(((yaw + 180) % 360) / 22.5)) % 16


def make_props(path, r2, own, bridge, ford, total):
    n = len(path)
    t = np.roll(path, -2, 0) - np.roll(path, 2, 0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    nrm = np.stack([-t[:, 1], t[:, 0]], 1)          # right of travel (x right, z down)
    # Signed curvature from heading change over 10 blocks.
    head = np.unwrap(np.arctan2(t[:, 1], t[:, 0]))
    curv = (np.roll(head, -6) - np.roll(head, 6)) / 12
    props = []

    def at(i, off):
        p = path[i] + nrm[i] * off
        return int(round(p[0])), int(round(p[1]))

    def y_of(i):
        return int(r2[i] // 2) + 1 + (r2[i] % 2)   # first free block above the road

    edge = ROAD_W / 2 + 1.5
    # Hairpins and tight bends: hay bales and a chevron board on the outside.
    i = 0
    while i < n:
        if abs(curv[i]) > 0.035 and not bridge[i] and not ford[i]:
            j = i
            while j < n and abs(curv[j]) > 0.02:
                j += 1
            apex = (i + j) // 2
            side = -1 if curv[apex] > 0 else 1          # outside of the bend
            for k in range(i, j, 2):
                x, z = at(k, side * (edge + 0.5))
                props.append(("hay", x, y_of(k), z, 0, 0))
            x, z = at(apex, side * (edge + 3))
            props.append(("chev", x, y_of(apex), z, 1 if abs(t[apex][0]) > abs(t[apex][1]) else 0,
                          snap_rot(-nrm[apex][0] * side, -nrm[apex][1] * side)))
            i = j + 10
        else:
            i += 1
    # Marker posts every 24 blocks, both sides; kilometre signs.
    for i in range(0, n, 24):
        if bridge[i] or ford[i] or STAGE[own[i]][2] == "a":
            continue
        for side in (-1, 1):
            x, z = at(i, side * (edge + 0.5))
            props.append(("post", x, y_of(i), z, 0, 0))
    for km in range(1, int(total // 1000) + 1):
        i = (START_S + km * 1000) % n
        x, z = at(i, edge + 1.5)
        props.append(("km", x, y_of(i), z, km, snap_rot(-nrm[i][0], -nrm[i][1])))
    return props, nrm, t


def main():
    H, water, ld, rd, cd, mount, plateau = build_terrain()
    path, own, total = catmull_loop(STAGE, 1.0)
    n = len(path)
    r2, bridge, ford = road_profile(H, path, own, rd, cd, plateau)
    H, road_d, road_i = corridor(H, path, r2, bridge, own)
    Hs = ndimage.uniform_filter(H, 3)
    nodes = np.clip(np.round(Hs[::G, ::G]), 30, 200).astype(int)
    assert nodes.shape == (NN, NN)
    Hd = column_heights(nodes)

    # ---- cells
    dark = np.hypot(X - DARK_FOREST[0], Z - DARK_FOREST[1]) < DARK_FOREST[2]
    fnoise = fbm(90, 9, 3)
    vd = np.hypot(X - VILLAGE_C[0], Z - VILLAGE_C[1])
    cells = []
    nslope = np.maximum.reduce([
        np.abs(nodes[1:, 1:] - nodes[:-1, :-1]), np.abs(nodes[1:, :-1] - nodes[:-1, 1:]),
        np.abs(nodes[1:, 1:] - nodes[1:, :-1]), np.abs(nodes[:-1, 1:] - nodes[:-1, :-1]),
        np.abs(nodes[1:, 1:] - nodes[:-1, 1:]), np.abs(nodes[1:, :-1] - nodes[:-1, :-1])])
    px0, pz0, px1, pz1 = PARK
    farms = [(40, 470, 105, 560), (215, 470, 275, 540), (60, 300, 120, 360)]
    for j in range(NC):
        row = []
        for i in range(NC):
            cx, cz = G * i + 4, G * j + 4
            h = Hd[cz, cx]
            near_road = road_d[cz, cx] < 16
            if h < WL:
                c = "l"
            elif px0 - 6 <= cx <= px1 + 6 and pz0 - 6 <= cz <= pz1 + 6:
                c = "a"
            elif any(a <= cx <= b and c0 <= cz <= d for a, c0, b, d in farms) and not near_road:
                c = "h"
            elif vd[cz, cx] < 100:
                c = "v"
            elif CANYON[0] <= cx <= CANYON[2] and CANYON[1] <= cz <= CANYON[3] and plateau[cz, cx] > 0.3:
                c = "c"
            elif h >= SNOW:
                c = "n"
            elif h >= SNOW - 8:
                c = "m"
            elif nslope[j, i] >= 7:
                c = "r"
            elif ld[cz, cx] < 8 and h <= WL + 2:
                c = "s"
            elif dark[cz, cx]:
                c = "k"
            elif mount[cz, cx] > 14 or (cz < 330 and cx > 640):
                c = "p"
            elif fnoise[cz, cx] > -0.05 and (cz < 560 or cx > 520) and not (cz > 860):
                c = "f" if cx < 560 else "p"
            else:
                c = "g"
            if near_road or road_d[cz, cx] < 20:
                c = c.upper()
            row.append(c)
        cells.append(row)

    props, nrm, tang = make_props(path, r2, own, bridge, ford, total)
    structs = make_structs(path, r2, own, nrm, tang, bridge, Hd, road_d)

    write_tc(nodes, cells, path, r2, own, bridge, ford, props, structs)
    render_preview(Hd, cells, path, props, structs)
    summary = {
        "road_length": round(float(total)),
        "start": [round(float(v), 1) for v in path[START_S]],
        "nodes_range": [int(nodes.min()), int(nodes.max())],
        "props": len(props), "structs": len(structs),
    }
    with open(os.path.join(ROOT, "map", "map.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary))


# ---------------------------------------------------------------- structures

def make_structs(path, r2, own, nrm, tang, bridge, Hd, road_d):
    """Gantries, park, village houses, bridge, jetty, cabins, stands."""
    n = len(path)
    out = []

    def ry(i):
        return int(r2[i] // 2)

    def axis_of(i):
        return 0 if abs(tang[i][0]) >= abs(tang[i][1]) else 1   # 0: road runs along x

    # Start and finish gantries (the loop runs west along the finish straight).
    for kind, i in (("finish", FINISH_S), ("start", START_S)):
        p = path[i]
        out.append((kind, int(round(p[0])), ry(i), int(round(p[1])), axis_of(i), 0))
    # Service park south of the start straight.
    px0, pz0, px1, pz1 = PARK
    out.append(("park", px0 + 10, 50, pz0 + 6, px1 - 10, pz1 - 6))
    # Bridge: the bridge points, as one straight span.
    bi = np.where(bridge)[0]
    if len(bi):
        a, b = path[bi[0]], path[bi[-1]]
        out.append(("bridge", int(round(a[0])) - 3, ry(bi[0]), int(round(a[1])), int(round(b[0])) + 3,
                    int(round(b[1]))))
    # Village: houses along the asphalt stretch, set back from the road.
    rng = np.random.default_rng(11)
    vi = [i for i in range(n) if STAGE[own[i]][2] == "a" and path[i][1] < 700]
    taken = []
    for k in range(0, len(vi), 17):
        i = vi[k]
        for side in (-1, 1):
            if rng.random() < 0.2:
                continue
            ax = axis_of(i)
            off = 15 + rng.integers(0, 4)
            c = path[i] + nrm[i] * side * off
            cx, cz = int(round(c[0])), int(round(c[1]))
            w, d = (9, 7) if ax == 0 else (7, 9)
            # Keep clear of the road and other houses.
            xs, zs = range(cx - w // 2 - 2, cx + w // 2 + 3), range(cz - d // 2 - 2, cz + d // 2 + 3)
            if min(road_d[z, x] for x in (xs[0], xs[-1]) for z in (zs[0], zs[-1])) < 9:
                continue
            if any(abs(cx - tx) < 14 and abs(cz - tz) < 14 for tx, tz in taken):
                continue
            taken.append((cx, cz))
            y = int(max(Hd[z, x] for x in xs for z in zs))
            # Door faces the road.
            fx, fz = -nrm[i][0] * side, -nrm[i][1] * side
            face = (0 if fx > 0 else 2) if abs(fx) > abs(fz) else (1 if fz > 0 else 3)   # +x, +z, -x, -z
            style = int(rng.integers(0, 3))
            out.append(("house", cx, y, cz, face, style))
    # Church with a tower in the village square.
    out.append(("church", VILLAGE_C[0] + 46, int(Hd[VILLAGE_C[1] - 4, VILLAGE_C[0] + 46]), VILLAGE_C[1] - 4, 2, 0))
    # Lake jetty and boathouse on the south-east shore.
    jz = LAKE_C[1]
    while Hd[jz, LAKE_C[0] + 30] < WL + 1:
        jz += 1
    out.append(("jetty", LAKE_C[0] + 30, WL, jz + 1, 3, 0))
    # Cabins in the woods.
    for cx, cz in ((372, 262), (190, 160), (560, 250)):
        out.append(("cabin", cx, int(Hd[cz, cx]), cz, 0, 0))
    # Spectator stands at the water splash, the big jump and the hairpins:
    # on dry land beside the road, moved along it until one fits.
    for sx, sz in ((410, 882), (944, 450), (744, 300), (324, 196), (548, 900), (846, 236)):
        i0 = int(np.argmin(np.hypot(path[:, 0] - sx, path[:, 1] - sz)))
        done = False
        for shift in (0, 18, -18, 30, -30, 45, -45):
            i = (i0 + shift) % n
            for side in (-1, 1):
                c = path[i] + nrm[i] * side * 15
                cx, cz = int(round(c[0])), int(round(c[1]))
                foot = Hd[cz - 8:cz + 9, cx - 8:cx + 9]
                if road_d[cz, cx] < 12 or foot.min() <= WL or foot.max() - foot.min() > 4:
                    continue
                fx, fz = -nrm[i][0] * side, -nrm[i][1] * side
                face = (0 if fx > 0 else 2) if abs(fx) > abs(fz) else (1 if fz > 0 else 3)
                out.append(("stand", cx, max(ry(i), int(Hd[cz, cx])), cz, face, 0))
                done = True
                break
            if done:
                break
    return out


# ---------------------------------------------------------------- output

def params_tc():
    """mapParams(): the surface letter table as global dicts."""
    names = ["gMat", "gSub", "gBed", "gDepth", "gSpr", "gSprN", "gPlants", "gPlantN", "gTrees", "gTreeN", "gRockN"]
    out = ["/** Surface letter table (PARAMS in gen_map.py). */", "function mapParams {"]
    for k, name in enumerate(names):
        items = []
        for c, row in PARAMS.items():
            for key in (c, c.upper()):
                v = row[k]
                if key.isupper() and name in ("gTreeN", "gRockN"):
                    v = 0
                items.append(f"{key}: {json.dumps(v)}")
        out.append(f"    global {name} = {{" + ", ".join(items) + "};")
    out.append("}\n")
    return "\n".join(out)


def chunks(items, size):
    for k in range(0, len(items), size):
        yield items[k:k + size]


def write_tc(nodes, cells, path, r2, own, bridge, ford, props, structs):
    L = ["// Generated by map/gen_map.py: do not edit.", ""]
    L.append(f"function mapWaterLevel(): num {{\n    return {WL};\n}}\n")
    L.append(params_tc())
    # Start: 12 blocks before the start line, facing down the road.
    k = START_S - 12
    d = path[k + 4] - path[k]
    yaw = math.degrees(math.atan2(-d[0], d[1]))
    top = r2[k] / 2 + 1
    L.append(f"/** Where @start puts the car: before the start line, facing the stage. */")
    L.append(f"function mapStartLoc(): loc {{\n    return loc({path[k][0]:.1f}, {top:.1f}, {path[k][1]:.1f}, 0, {yaw:.1f});\n}}\n")
    # Checkpoints: the start line, every 350 blocks, the finish line.
    n = len(path)
    cps = [START_S]
    k = START_S + 350
    while k < n - 150:
        cps.append(k)
        k += 350
    cps.append(n - 1)
    rows = ", ".join(f"vec({path[k][0]:.1f}, {r2[k] / 2 + 1:.1f}, {path[k][1]:.1f})" for k in cps)
    L.append("/** Stage checkpoints: the start line first, the finish line last. */")
    L.append(f"function mapCheckpoints(): list {{\n    return [{rows}];\n}}\n")
    hrows = [" ".join(str(v) for v in row) for row in nodes]
    for k, part in enumerate(chunks(hrows, 32)):
        body = ",\n        ".join(json.dumps(r) for r in part)
        L.append(f"/** Terrain node heights, rows {k * 32}..{k * 32 + len(part) - 1}. */")
        L.append(f"function mapH{k}(): list {{\n    return [\n        {body}\n    ];\n}}\n")
    crows = [" ".join(r) for r in cells]
    for k, part in enumerate(chunks(crows, 64)):
        body = ",\n        ".join(json.dumps(r) for r in part)
        L.append(f"/** Surface letters, cell rows {k * 64}..{k * 64 + len(part) - 1}. */")
        L.append(f"function mapC{k}(): list {{\n    return [\n        {body}\n    ];\n}}\n")
    # Road every 3 blocks: "x z r2 s" with s the surface letter, w for the
    # ford and b for the bridge.
    pts = []
    for i in range(0, len(path), 3):
        s = STAGE[own[i]][2]
        if own[i] in CANYON_OWN and s == "d":
            s = "c"          # canyon: dirt verges, cleared high above
        if bridge[i]:
            s = "b"
        elif ford[i]:
            s = "w"
        pts.append(f"{path[i][0]:.1f} {path[i][1]:.1f} {int(r2[i])} {s}")
    rows = [",".join(c) for c in chunks(pts, 40)]
    body = ",\n        ".join(json.dumps(r) for r in rows)
    L.append("/** Stage road, every 3 blocks: x z height-in-half-blocks surface. */")
    L.append(f"function mapRoad(): list {{\n    return [\n        {body}\n    ];\n}}\n")
    rows = [";".join(" ".join(str(v) for v in p) for p in c) for c in chunks(props, 30)]
    for k, part in enumerate(chunks(rows, 20)):
        body = ",\n        ".join(json.dumps(r) for r in part)
        L.append(f"/** Road-side props: kind x y z a b. */")
        L.append(f"function mapProps{k}(): list {{\n    return [\n        {body}\n    ];\n}}\n")
    body = ",\n        ".join(json.dumps(" ".join(str(v) for v in s)) for s in structs)
    L.append("/** Structures: kind x y z a b. */")
    L.append(f"function mapStructs(): list {{\n    return [\n        {body}\n    ];\n}}\n")
    nprops = (len(props) + 599) // 600
    L.append(f"function mapPropParts(): num {{\n    return {nprops};\n}}\n")
    L.append("/** Props strings of part k (0-based). */")
    L.append("function mapPropsPart(k: num): list {\n" +
             "".join(f"    if (k == {k}) {{\n        return mapProps{k}();\n    }}\n" for k in range(nprops)) +
             "    return [];\n}\n")
    with open(os.path.join(ROOT, "tc", "map_data.tc"), "w") as f:
        f.write("\n".join(L))


LABELS = [
    ("Service park", (595, 960)), ("START", (640, 925)), ("FINISH", (760, 925)),
    ("Water splash", (410, 915)), ("Lake", (318, 676)), ("Village", (225, 470)),
    ("Forest twisties", (180, 230)), ("Bridge", (565, 95)), ("Middle woods", (700, 330)),
    ("Hairpin", (720, 290)), ("Snowy pass", (870, 210)), ("Big jump", (895, 450)),
    ("Canyon", (900, 700)), ("Dark forest", (420, 330)), ("Mountains", (900, 80)),
]

COLORS = {
    "g": (110, 160, 70), "f": (60, 120, 50), "p": (40, 95, 55), "k": (30, 70, 35),
    "r": (125, 125, 125), "m": (170, 175, 180), "n": (240, 245, 250), "c": (190, 110, 70),
    "s": (220, 205, 150), "l": (60, 100, 200), "v": (140, 170, 90), "a": (150, 150, 150),
    "h": (200, 180, 90),
}


def render_preview(Hd, cells, path, props, structs):
    img = np.zeros((S, S, 3))
    cl = np.array([[COLORS[c.lower()] for c in row] for row in cells], float)
    img = np.repeat(np.repeat(cl, G, 0), G, 1)[:S, :S]
    if img.shape[0] < S:
        img = np.pad(img, ((0, S - img.shape[0]), (0, S - img.shape[1]), (0, 0)), mode="edge")
    water = Hd < WL
    img[water] = (60, 100, 200)
    # Hillshade.
    gz, gx = np.gradient(Hd.astype(float))
    shade = np.clip(1 + (-gx - gz) * 0.12, 0.55, 1.35)
    img = img * shade[..., None]
    # Contours every 10 blocks.
    cont = (Hd // 10) != (np.roll(Hd, 1, 0) // 10)
    img[cont] *= 0.8
    pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    from PIL import ImageDraw
    d = ImageDraw.Draw(pil)
    d.line([tuple(p) for p in path] + [tuple(path[0])], fill=(250, 240, 200), width=7)
    d.line([tuple(p) for p in path] + [tuple(path[0])], fill=(150, 120, 80), width=3)
    for p in props:
        col = {"hay": (230, 200, 60), "post": (230, 60, 60), "chev": (255, 0, 0), "km": (255, 255, 255)}[p[0]]
        d.point((p[1], p[3]), fill=col)
    for s in structs:
        d.rectangle([s[1] - 4, s[3] - 4, s[1] + 4, s[3] + 4], outline=(255, 0, 255))
    from PIL import ImageFont
    font = ImageFont.load_default(size=18)
    for text, (x, z) in LABELS:
        d.text((x + 1, z + 1), text, fill=(0, 0, 0), font=font, anchor="mm")
        d.text((x, z), text, fill=(255, 255, 255), font=font, anchor="mm")
    pil.save(os.path.join(ROOT, "map", "preview.png"))


if __name__ == "__main__":
    main()
