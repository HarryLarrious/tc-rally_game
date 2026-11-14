#!/usr/bin/env python3
"""Procedural engine sound: the rally car's 2.0 turbo inline-4 and the
hypercar's 4.0 twin-turbo V8.

    python3 pack/src/engine_sound.py                       # built-in combustion pulse
    python3 pack/src/engine_sound.py --pulse bang.wav      # your own pulse
    python3 pack/src/engine_sound.py --preview sweep.wav   # also render a rev sweep to listen to

Minecraft cannot synthesize or re-pitch a sound while it plays, so the
engine is a granular loop: one short clip of whole 4-cylinder firing cycles,
faded in and out, which the game (tc/sound.tc) plays every tick pitched to
the exact rpm. Consecutive clips overlap, so the pitch follows the rpm in
small steps instead of jumping.

Minecraft clamps pitch to 0.5..2, and idle to the limiter is about 9x, so
the same cycle is baked at three base speeds (crossfaded at 1900 and 4100 rpm):

  pack/assets/rally/sounds/engine/lo.ogg    1300 rpm base, 2 cycles   (900..2100 rpm)
  pack/assets/rally/sounds/engine/mid.ogg   2900 rpm base, 5 cycles   (1700..4300 rpm)
  pack/assets/rally/sounds/engine/hi.ogg    5800 rpm base, 10 cycles  (3900..8000 rpm)
  pack/assets/rally/sounds/engine/pop.ogg   one anti-lag bang for the overrun
  pack/assets/rally/sounds/engine/v8_*.ogg  the same three clips and pop for the V8
  pack/assets/rally/sounds/engine/turbo.ogg the V8's turbo whistle (pitched with boost)
  pack/assets/rally/sounds/engine/bov.ogg   its blow-off valve (boost dumped on a lift)
  pack/assets/rally/sounds.json             engine.<clip> for each

The V8 is a cross-plane engine: four firings per crank revolution (firing
order 1-8-4-3-6-5-7-2), alternating unevenly between the banks (L R R L R L
L R). Each bank has its own exhaust with its own pipe resonance, which gives
the burble; the pulses are bigger and lower than the inline-4's. Its turbo
whistle is a separate clip so it can follow the boost, not the rpm.

How a cycle is built:
  - Combustion: one pulse per firing. An inline-4 fires twice per crank
    revolution (firing order 1-3-4-2). Each cylinder has its own slight
    level, plus a little timing and level jitter. The pulse is the
    "explosion": the built-in one is a short exhaust thump plus a burst of
    noise; --pulse swaps in any WAV.
  - Exhaust: a low-pass and two pipe resonances; crank hum, valvetrain tick
    and turbo whistle on top.

Needs numpy, scipy and ffmpeg (libvorbis).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from scipy import signal

ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS = ROOT / "pack/assets/rally"
SR = 44100
TICK = 0.05                  # the game plays a clip every tick
# Base rpm and whole cycles per clip. Three bases keep every clip within about
# +-45% pitch, so the exhaust resonances do not get dragged up and buzzy.
BASES = {"lo": (1300, 2), "mid": (2900, 5), "hi": (5800, 10)}
CROSS = [1900, 4100]         # rpm where the game crossfades lo -> mid -> hi (+-200)
CYL_LEVEL = [1.0, 0.92, 1.06, 0.96]   # firing order 1-3-4-2, slight imbalance
# V8: firing order 1-8-4-3-6-5-7-2; banks (0 left, 1 right) of each firing,
# per-cylinder level and a small timing wobble (fraction of the interval).
V8_BANK = [0, 1, 1, 0, 1, 0, 0, 1]
V8_LEVEL = [1.0, 0.95, 1.05, 0.93, 1.02, 0.97, 1.06, 0.94]
V8_WOBBLE = [0.0, 0.035, -0.03, 0.0, 0.03, -0.035, 0.02, -0.02]


def default_pulse() -> np.ndarray:
    """One combustion as heard at the tailpipe: a decaying low thump with a
    falling pitch, and a short burst of band-passed noise."""
    rng = np.random.default_rng(7)
    n = int(0.045 * SR)
    t = np.arange(n) / SR
    f = 70 * np.exp(-t / 0.03) + 40
    thump = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.012)
    noise = rng.standard_normal(n)
    b, a = signal.butter(2, [200 / (SR / 2), 1400 / (SR / 2)], btype="band")
    burst = signal.lfilter(b, a, noise) * np.exp(-t / 0.003)
    p = thump + 0.25 * burst
    return p / np.max(np.abs(p))


def load_pulse(path: Path) -> np.ndarray:
    """Any WAV, made mono, resampled to SR and trimmed to 80 ms."""
    with wave.open(str(path)) as w:
        rate, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    dtype = {1: np.uint8, 2: np.int16, 4: np.int32}[width]
    x = np.frombuffer(raw, dtype=dtype).astype(np.float64)
    if width == 1:
        x -= 128
    x = x.reshape(-1, ch).mean(axis=1)
    if rate != SR:
        x = signal.resample_poly(x, SR, rate)
    x = x[: int(0.08 * SR)]
    # Cut leading silence so the firing lands on time.
    start = int(np.argmax(np.abs(x) > 0.05 * np.max(np.abs(x))))
    x = x[start:]
    fade = np.ones(len(x))
    k = min(len(x), int(0.01 * SR))
    fade[-k:] = np.linspace(1, 0, k)
    x = x * fade
    return x / np.max(np.abs(x))


def stretch(p: np.ndarray, factor: float) -> np.ndarray:
    """Slower and lower by `factor` (simple resampling)."""
    n = int(len(p) * factor)
    return np.interp(np.linspace(0, len(p) - 1, n), np.arange(len(p)), p)


def lowpass(x: np.ndarray, hz: float) -> np.ndarray:
    b, a = signal.butter(2, min(hz, SR * 0.45) / (SR / 2))
    return signal.lfilter(b, a, x)


def resonance(x: np.ndarray, hz: float, q: float) -> np.ndarray:
    b, a = signal.iirpeak(hz / (SR / 2), q)
    return signal.lfilter(b, a, x)


def render_v8(rpm: float, on: bool, pulse: np.ndarray, seed: int, seconds: float = 1.0) -> np.ndarray:
    """The twin-turbo V8: cross-plane firing into two banks, each with its
    own exhaust resonance. No turbo whistle (that is its own clip)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    pad = int(0.15 * SR)
    banks = [np.zeros(n + 2 * pad), np.zeros(n + 2 * pad)]
    period = SR / (rpm / 15.0)           # 8 cylinders, 4-stroke: 4 firings per rev
    load = 1.0 if on else 0.3
    big = stretch(pulse, 1.45)           # bigger cylinders: a lower, longer thump
    pop = stretch(pulse, 2.0)
    t = -pad * 0.5
    k = 0
    while t < n + pad:
        i = k % 8
        pos = int(pad + t + (V8_WOBBLE[i] + rng.normal(0, 0.004)) * period)
        amp = load * V8_LEVEL[i] * (1 + rng.normal(0, 0.05))
        out = banks[V8_BANK[i]]
        if 0 <= pos < len(out):
            seg = big[: len(out) - pos]
            out[pos:pos + len(seg)] += amp * seg
            if not on and rpm >= 3000 and rng.random() < 0.015 + rpm / 500000:
                seg = pop[: len(out) - pos]
                out[pos:pos + len(seg)] += rng.uniform(0.8, 1.4) * seg
        t += period
        k += 1
    cut = (380 + rpm * 0.10) if on else (300 + rpm * 0.045)
    left = lowpass(banks[0], cut)
    right = lowpass(banks[1], cut)
    ex = (left + 0.55 * resonance(left, 68, 3) + 0.2 * resonance(left, 190, 5)
          + right + 0.55 * resonance(right, 84, 3) + 0.2 * resonance(right, 230, 5))
    time = np.arange(len(ex)) / SR
    crank = rpm / 60.0
    mech = 0.03 * np.sin(2 * np.pi * crank * 4 * time) + 0.015 * np.sin(2 * np.pi * crank * 8 * time)
    tick = lowpass(rng.standard_normal(len(ex)), 2500) * 0.003 * (0.5 + rpm / 8000)
    mix = signal.lfilter(*signal.butter(2, 25 / (SR / 2), btype="high"), ex + mech + tick)
    return mix[pad:pad + n]


def sweep_bandpass(x: np.ndarray, fc: np.ndarray, q: float) -> np.ndarray:
    """Band-pass with a center that moves sample by sample (a state-variable
    filter), so a sweep stays smooth instead of stepping."""
    out = np.zeros_like(x)
    low = band = 0.0
    damp = 1.0 / q
    for n in range(len(x)):
        f = 2 * np.sin(np.pi * min(fc[n], SR * 0.2) / SR)
        high = x[n] - low - damp * band
        band += f * high
        low += f * band
        out[n] = band
    return out


def turbo_sound() -> np.ndarray:
    """The turbo, 0.4 s: soft rushing air (noise around 1.4 kHz, the top
    rolled off) with only a faint whistle, windowed so the copies played
    every tick blend into a steady rush (the game pitches it with the
    boost)."""
    rng = np.random.default_rng(31)
    n = int(0.4 * SR)
    time = np.arange(n) / SR
    air = signal.lfilter(*signal.butter(2, [800 / (SR / 2), 2200 / (SR / 2)], btype="band"), rng.standard_normal(n))
    air = lowpass(air, 2600)
    f = 1700 * (1 + 0.01 * np.sin(2 * np.pi * 23 * time))
    whistle = np.sin(2 * np.pi * np.cumsum(f) / SR)
    x = (air / np.max(np.abs(air)) + 0.1 * whistle) * np.hanning(n)
    return x / np.max(np.abs(x))


def bov_sound() -> np.ndarray:
    """Blow-off valve, 0.5 s: a burst of air whose pitch falls smoothly from
    2.8 kHz to 600 Hz, with a soft compressor flutter in its tail."""
    rng = np.random.default_rng(32)
    n = int(0.5 * SR)
    time = np.arange(n) / SR
    noise = rng.standard_normal(n)
    fc = 600 + 2200 * np.exp(-time / 0.12)
    x = sweep_bandpass(noise, fc, 1.4)
    x = x + 0.25 * lowpass(noise, 900)
    env = np.minimum(1, time / 0.008) * np.exp(-time / 0.17)
    flutter = 1 - 0.3 * np.clip((time - 0.12) / 0.05, 0, 1) * (0.5 + 0.5 * np.sin(2 * np.pi * 22 * time))
    x = lowpass(x * env * flutter, 5000)
    return x / np.max(np.abs(x))


def render(rpm: float, on: bool, pulse: np.ndarray, seed: int, seconds: float = 1.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    pad = int(0.15 * SR)                 # room for pulse tails and filter warm-up
    out = np.zeros(n + 2 * pad)
    fire_hz = rpm / 30.0                 # 4 cylinders, 4-stroke: 2 firings per rev
    period = SR / fire_hz
    load = 1.0 if on else 0.32
    pop = stretch(pulse, 1.6)
    t = -pad * 0.5
    k = rng.integers(4)
    while t < n + pad:
        pos = int(pad + t + rng.normal(0, 0.004) * period)
        amp = load * CYL_LEVEL[k % 4] * (1 + rng.normal(0, 0.04))
        if 0 <= pos < len(out):
            seg = pulse[: len(out) - pos]
            out[pos:pos + len(seg)] += amp * seg
            # Overrun: anti-lag pops and bangs.
            if not on and rpm >= 3500 and rng.random() < 0.02 + rpm / 400000:
                seg = pop[: len(out) - pos]
                out[pos:pos + len(seg)] += rng.uniform(0.8, 1.5) * seg
        t += period
        k += 1

    # Exhaust: opens with rpm and load; two pipe resonances.
    cut = (500 + rpm * 0.12) if on else (350 + rpm * 0.05)
    ex = lowpass(out, cut)
    ex = ex + 0.5 * resonance(ex, 85, 3) + 0.2 * resonance(ex, 240, 5)

    time = np.arange(len(out)) / SR
    crank = rpm / 60.0
    mech = 0.04 * np.sin(2 * np.pi * crank * 2 * time) + 0.02 * np.sin(2 * np.pi * crank * 4 * time)
    tick = lowpass(rng.standard_normal(len(out)), 3000) * 0.004 * (0.5 + rpm / 8000)
    mix = ex + mech + tick
    if on and rpm > 2500:
        spool = (rpm - 2500) / 5500
        whistle = np.sin(2 * np.pi * (2200 + rpm * 0.55) * time) * 0.012 * spool
        hiss = signal.lfilter(*signal.butter(2, 3000 / (SR / 2), btype="high"), rng.standard_normal(len(out)))
        mix = mix + whistle + hiss * 0.006 * spool
    # Remove DC and rumble below hearing (it only eats headroom).
    mix = signal.lfilter(*signal.butter(2, 30 / (SR / 2), btype="high"), mix)
    return mix[pad:pad + n]


def write_wav(path: Path, x: np.ndarray) -> None:
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def to_ogg(wav: Path, ogg: Path, quality: int = 3) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-c:a", "libvorbis",
                    "-q:a", str(quality), str(ogg)], check=True)


def grain(pulse: np.ndarray, rpm: int, cycles: int, seed: int, v8: bool = False) -> np.ndarray:
    """`cycles` whole engine cycles (two crank revolutions each) at `rpm`, cut
    from a steady stretch and Hann-windowed so overlapping copies blend."""
    x = render_v8(rpm, True, pulse, seed, seconds=1.0) if v8 else render(rpm, True, pulse, seed, seconds=1.0)
    cycle = int(round(SR * 120.0 / rpm))           # 2 crank revolutions
    start = int(0.4 * SR)
    g = x[start:start + cycles * cycle]
    return g * np.hanning(len(g))


def pop_sound(pulse: np.ndarray) -> np.ndarray:
    """One anti-lag bang: the pulse slowed down, darker, with a short tail."""
    p = stretch(pulse, 1.7)
    p = np.concatenate([p, np.zeros(int(0.06 * SR))])
    p = lowpass(p, 1800) + 0.3 * resonance(p, 115, 4)
    return p / np.max(np.abs(p))


def game_pitch(rpm: float):
    """[(name, pitch, volume)] the game plays this tick (mirrors tc/sound.tc)."""
    up1 = min(max((rpm - (CROSS[0] - 200)) / 400, 0), 1)
    up2 = min(max((rpm - (CROSS[1] - 200)) / 400, 0), 1)
    mixes = {"lo": 1 - up1, "mid": up1 * (1 - up2), "hi": up2}
    out = []
    for name, (base, cycles) in BASES.items():
        if mixes[name] <= 0:
            continue
        pitch = min(max(rpm / base, 0.5), 2.0)
        overlap = cycles * 120.0 / base / pitch / TICK   # copies alive at once
        vol = min(1.0, 0.75 / np.sqrt(overlap * 0.375))
        out.append((name, pitch, vol * mixes[name]))
    return out


def preview(sounds: dict, path: Path) -> None:
    """A rev sweep played the way the game does: every clip once per tick."""
    rpms = []
    rpm = 900.0
    for step in range(320):                         # 16 s
        on = step < 200 or 240 <= step < 280
        rpm += (52 if on else -64) * (1 - rpm / 8200) * (1.6 if on else 1)
        rpms.append((min(max(rpm, 900), 7800), on))
    total = int((len(rpms) * TICK + 1.0) * SR)
    out = np.zeros(total)
    rng = np.random.default_rng(3)
    for i, (r, on) in enumerate(rpms):
        start = int(i * TICK * SR)
        for name, pitch, vol in game_pitch(r):
            x = sounds[name]
            x = np.interp(np.arange(0, len(x) - 1, pitch), np.arange(len(x)), x)
            out[start:start + len(x)] += x * vol * (1.0 if on else 0.45)
        if not on and r > 3500 and rng.random() < 0.08:
            x = sounds["pop"]
            out[start:start + len(x)] += x * 0.8
    write_wav(path, out / np.max(np.abs(out)) * 0.9)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pulse", type=Path, help="WAV to use as one combustion (the 'explosion')")
    ap.add_argument("--preview", type=Path, help="also write a rev sweep WAV here")
    args = ap.parse_args()

    pulse = load_pulse(args.pulse) if args.pulse else default_pulse()
    sounds = {name: grain(pulse, base, cycles, seed=base) for name, (base, cycles) in BASES.items()}
    # Same loudness for both bases; the game's volume does the rest.
    for name in sounds:
        sounds[name] = sounds[name] * 0.85 / np.max(np.abs(sounds[name]))
    sounds["pop"] = pop_sound(pulse) * 0.9
    for name, (base, cycles) in BASES.items():
        x = grain(pulse, base, cycles, seed=base + 1, v8=True)
        sounds[f"v8_{name}"] = x * 0.85 / np.max(np.abs(x))
    v8pop = pop_sound(stretch(pulse, 1.3))
    sounds["v8_pop"] = lowpass(v8pop, 1400) / np.max(np.abs(lowpass(v8pop, 1400))) * 0.95
    sounds["turbo"] = turbo_sound() * 0.8
    sounds["bov"] = bov_sound() * 0.85

    out = ASSETS / "sounds/engine"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.ogg"):
        old.unlink()
    with tempfile.TemporaryDirectory() as tmp:
        for name, x in sounds.items():
            wav = Path(tmp) / f"{name}.wav"
            write_wav(wav, x)
            # Noise squashes badly at low Vorbis quality: the air sounds get more bits.
            to_ogg(wav, out / f"{name}.ogg", 7 if name in ("turbo", "bov") else 3)

    sounds_path = ASSETS / "sounds.json"
    table = json.loads(sounds_path.read_text()) if sounds_path.exists() else {}
    table = {k: v for k, v in table.items() if not k.startswith("engine.")}
    for name in sounds:
        table[f"engine.{name}"] = {"sounds": [{"name": f"rally:engine/{name}", "attenuation_distance": 40}]}
    sounds_path.write_text(json.dumps(table, indent=1, sort_keys=True) + "\n")

    if args.preview:
        preview(sounds, args.preview)
    lens = ", ".join(f"{n} {len(x) / SR * 1000:.0f} ms" for n, x in sounds.items())
    print(f"engine clips: {lens}" + (f"; preview {args.preview}" if args.preview else ""))


if __name__ == "__main__":
    main()
