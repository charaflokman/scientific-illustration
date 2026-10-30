#!/usr/bin/env python3
"""Synthesise an original soundtrack for a video: a calm music bed plus sound effects placed on the cuts.
Everything is generated from maths (no samples, no downloads), so there is no licence to worry about.

  python make_audio.py events.json out.wav

events.json: {"seconds": 37.2, "bpm": 96, "events": [{"t": 3.1, "kind": "whoosh"}, {"t": 8.0, "kind": "ticks", "dur": 1.4},
              {"t": 20, "kind": "pop"}, {"t": 0.1, "kind": "hit"}, {"t": 30, "kind": "riser", "dur": 1.5}]}
render_video.py writes this file itself from the scene timings, so it is rarely called by hand.
"""
import json
import sys
import wave

import numpy as np

SR = 44100
RNG = np.random.default_rng(7)


def env(n, a=.005, r=.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(r, 1e-4))


def lowpass(x, cutoff):
    # one-pole low-pass; cutoff may be an array (for sweeps)
    c = np.broadcast_to(np.asarray(cutoff, float), x.shape)
    a = np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def add(buf, sig, t):
    i = int(t * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[:j - i]


def kick():
    n = int(.35 * SR)
    t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .002, .12) * .9


def hat():
    n = int(.06 * SR)
    x = RNG.standard_normal(n)
    return (x - lowpass(x, 6000)) * env(n, .001, .015) * .18


def note(freq, dur, kind="pad"):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == "pad":  # detuned saws through a soft low-pass, slow attack
        s = sum(2 * ((t * freq * d) % 1) - 1 for d in (1, 1.004, .996))
        s = lowpass(s / 3, 1400)
        e = np.minimum(1, t / .6) * np.minimum(1, (dur - t) / .5)
        return s * e * .12
    s = np.sin(2 * np.pi * freq * t) + .3 * np.sin(4 * np.pi * freq * t)  # pluck
    return s * env(n, .003, .18) * .16


def whoosh(dur=.55):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    x = RNG.standard_normal(n)
    y = lowpass(x, 300 + 5000 * np.sin(np.pi * t) ** 2)
    return y * np.sin(np.pi * t) ** 1.5 * .5


def pop():
    n = int(.12 * SR)
    t = np.arange(n) / SR
    f = 900 * np.exp(-t * 25) + 300
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .001, .03) * .35


def tick():
    n = int(.03 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2400 * t) * env(n, .0005, .006) * .25


def hit():
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(40 + 60 * np.exp(-t * 12)) / SR) * env(n, .002, .5)
    air = lowpass(RNG.standard_normal(n), 2500) * env(n, .002, .25) * .6
    return (boom + air) * .55


def riser(dur=1.5):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    x = lowpass(RNG.standard_normal(n), 200 + 7000 * t ** 2)
    tone = np.sin(2 * np.pi * np.cumsum(200 + 600 * t ** 2) / SR) * .15
    return (x * .4 + tone) * t ** 2


def music(seconds, bpm):
    buf = np.zeros(int((seconds + 2) * SR))
    beat = 60 / bpm
    # Am - F - C - G, one bar each, looping
    chords = [[220, 261.6, 329.6], [174.6, 220, 261.6], [196, 261.6, 329.6], [196, 246.9, 293.7]]
    arp = [[440, 523.3, 659.3, 523.3], [349.2, 440, 523.3, 440], [392, 523.3, 659.3, 523.3], [392, 493.9, 587.3, 493.9]]
    bars = int(seconds / (4 * beat)) + 1
    for b in range(bars):
        t0 = b * 4 * beat
        for f in chords[b % 4]:
            add(buf, note(f, 4 * beat + .4), t0)
        add(buf, note(chords[b % 4][0] / 2, 4 * beat, "pad") * 1.6, t0)  # bass
        for k in range(8):
            if b >= 1:
                add(buf, note(arp[b % 4][k % 4], .4, "pluck"), t0 + k * beat / 2)
            if b >= 2:
                add(buf, hat(), t0 + k * beat / 2 + beat / 4)
        if b >= 2:
            for k in range(4):
                add(buf, kick(), t0 + k * beat)
    return buf


def main():
    ev = json.load(open(sys.argv[1], encoding="utf-8"))
    secs = ev["seconds"]
    buf = music(secs, ev.get("bpm", 96)) * .55
    # dynamics: start quiet and build toward the end; optional short break (drums out) before the call to action
    buf *= np.linspace(.7, 1.0, len(buf)) ** 1.5
    if ev.get("break_at"):
        i0, i1 = int((ev["break_at"] - .6) * SR), int(ev["break_at"] * SR)
        buf[i0:i1] *= np.linspace(1, .15, i1 - i0)
    fx = np.zeros_like(buf)
    for e in ev.get("events", []):
        k = e["kind"]
        if k == "whoosh":
            add(fx, whoosh(), max(0, e["t"] - .25))
        elif k == "pop":
            add(fx, pop(), e["t"])
        elif k == "hit":
            add(fx, hit() * e.get("gain", 1), e["t"])
        elif k == "riser":
            add(fx, riser(e.get("dur", 1.5)), max(0, e["t"] - e.get("dur", 1.5)))
        elif k == "ticks":
            for i, tt in enumerate(np.arange(0, e.get("dur", 1.2), .06)):
                add(fx, tick() * (1 - i * .01), e["t"] + tt)
    mix = buf + fx
    n = int(secs * SR)
    mix = mix[:n]
    fade = int(1.5 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = np.tanh(mix / (np.abs(mix).max() + 1e-9) * 1.4) * .85  # gentle saturation as a limiter
    stereo = np.stack([mix, np.roll(mix, 120)], 1)  # tiny delay on one side for width
    with wave.open(sys.argv[2], "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((stereo * 32767).astype("<i2").tobytes())
    print("wrote", sys.argv[2], f"{secs:.1f}s")


if __name__ == "__main__":
    main()
