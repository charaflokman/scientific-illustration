#!/usr/bin/env python3
"""Draw a scientific scene natively in pixel art (game style) from a JSON spec. Nothing is converted from a photo:
every object is placed on a small pixel grid with hand-pixel-art rules, so details stay crisp and readable.

  python pixel_scene.py scene.json out.png            # default 6x upscale
  python pixel_scene.py scene.json out.png --scale 8

Pixel-art rules applied (why it looks hand-made, not filtered):
  - small canvas (e.g. 240x150 px) shown with nearest-neighbour upscale, so every pixel is a crisp square;
  - each colour becomes a 5-step ramp with hue shifting (shadows lean blue/purple, highlights lean yellow);
  - light from the top-left; one dark, hue-shifted outline per object; one bright highlight pixel on spheres;
  - isometric 2:1 lines (pixel-perfect stairs) for slabs; no anti-aliasing, no dithering noise;
  - labels in game dialog boxes with a pixel font (Silkscreen / Press Start 2P, SIL OFL, cached on first use).

Spec:
{"canvas":[240,150], "background":["#1B2B44","#24395A"],   # two flat bands (sky style) or one colour
 "title":"WOUND DRESSING",
 "objects":[
   {"type":"slab","pos":[120,96],"size":[70,44,8],"color":"#E9DFC9","pattern":"mesh"},      # iso box: x-len, y-len, height
   {"type":"spheres","on":"<slab id>","face":"top|front|side","count":8,"r":3,"color":"#C9CED6","seed":2},
   {"type":"fibers","on":"<slab id>","count":6,"len":12,"color":"#D7A55A","seed":4},
   {"type":"brush","on":"<slab id>","spacing":4,"stem":3,"color":"#2E8B6E","head":"#4FC3F7"},
   {"type":"label","text":"SILANE LAYER","at":[200,30],"to":[150,52],"color":"#3FA98A"}]}
Every slab needs an "id" when other objects sit on it.
"""
import argparse
import colorsys
import json
import os
import random
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CACHE = Path(os.environ.get("RV_CACHE", Path.home() / ".cache" / "scientific-illustration"))
FONTS = {"Silkscreen-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/silkscreen/Silkscreen-Regular.ttf",
         "PressStart2P-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/pressstart2p/PressStart2P-Regular.ttf"}


def font(name="Silkscreen-Regular.ttf", size=8):
    p = CACHE / "fonts" / name
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(urllib.request.urlopen(FONTS[name], timeout=60).read())
    return ImageFont.truetype(str(p), size)


def hx(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def ramp(base):
    """5 tones: outline, shadow, base, light, highlight; hue shifts toward blue in shade, toward yellow in light."""
    r, g, b = (v / 255 for v in hx(base))
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    def tone(dl, dh, ds):
        hh = (h + dh) % 1
        return tuple(round(v * 255) for v in colorsys.hls_to_rgb(hh, min(.97, max(.04, l + dl)), min(1, max(0, s + ds))))
    toward = lambda target, amt: ((target - h + .5) % 1 - .5) * amt  # signed hue step toward a target hue
    return [tone(-.42, toward(.70, .35), .10), tone(-.16, toward(.66, .18), .06), hx(base),
            tone(.12, toward(.15, .10), -.02), tone(.24, toward(.15, .18), -.06)]


class Scene:
    def __init__(self, spec):
        self.W, self.H = spec.get("canvas", [240, 150])
        self.im = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
        self.d.fontmode = "1"  # no anti-aliasing on text
        self.slabs = {}
        bg = spec.get("background", "#1B2B44")
        bands = bg if isinstance(bg, list) else [bg]
        for i, c in enumerate(bands):
            y0 = self.H * i // len(bands)
            self.d.rectangle([0, y0, self.W, self.H * (i + 1) // len(bands)], fill=hx(c))
        self.rng = random.Random(spec.get("seed", 1))
        star = random.Random(99)
        for _ in range(spec.get("stars", 0)):  # twinkling background pixels, a few as tiny crosses
            x, y = star.randrange(self.W), star.randrange(self.H)
            c = star.choice([(255, 255, 255), (170, 200, 255), (255, 236, 140)])
            self.d.point((x, y), fill=c)
            if star.random() < .15:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    self.d.point((x + dx, y + dy), fill=tuple(v // 2 for v in c))

    # isometric 2:1 projection: x runs down-right, y runs down-left, z up
    def iso(self, ox, oy, x, y, z):
        return (round(ox + (x - y)), round(oy + (x + y) / 2 - z))

    def slab(self, o):
        ox, oy = o["pos"]
        lx, ly, h = o["size"]
        R = ramp(o["color"])
        P = lambda x, y, z: self.iso(ox, oy, x - lx / 2, y - ly / 2, z)
        top = [P(0, 0, h), P(lx, 0, h), P(lx, ly, h), P(0, ly, h)]
        right = [P(lx, 0, h), P(lx, ly, h), P(lx, ly, 0), P(lx, 0, 0)]
        left = [P(0, ly, h), P(lx, ly, h), P(lx, ly, 0), P(0, ly, 0)]
        if o.get("shadow"):  # soft drop shadow offset below the slab, one darker flat tone
            sh = [(x, y + h + 4) for x, y in [P(0, 0, 0), P(lx, 0, 0), P(lx, ly, 0), P(0, ly, 0)]]
            self.d.polygon(sh, fill=tuple(max(0, v - 14) for v in self.im.getpixel((self.W - 1, self.H - 1))[:3]))
        self.d.polygon(left, fill=R[2])
        self.d.polygon(right, fill=R[1])
        self.d.polygon(top, fill=R[3])
        if o.get("pattern") == "mesh":  # woven fibres of a porous substrate, drawn on all faces
            for t in range(4, int(lx), 6):
                self.d.line([P(t, 0, h), P(t, ly, h)], fill=R[2])
                self.d.line([P(t, ly, h), P(t, ly, 0)], fill=R[1])
            for t in range(4, int(ly), 6):
                self.d.line([P(0, t, h), P(lx, t, h)], fill=R[2])
                self.d.line([P(lx, t, h), P(lx, t, 0)], fill=R[0])
        if o.get("pattern") == "glass":  # translucent look: soft inner band + reflection stripes
            self.d.line([P(lx * .15, ly, h * .7), P(lx * .45, ly, h * .7)], fill=R[4])
            self.d.line([P(lx, ly * .2, h * .75), P(lx, ly * .35, h * .75)], fill=R[3])
        # highlight on the front top edges, outline on the silhouette
        self.d.line([P(0, ly, h), P(lx, ly, h), P(lx, 0, h)], fill=R[4])
        self.d.line([P(lx, ly, h), P(lx, ly, 0)], fill=R[3])
        self.d.line(top[:2] + [top[1]], fill=R[0])
        self.d.line([P(0, 0, h), P(0, ly, h), P(0, ly, 0), P(lx, ly, 0), P(lx, 0, 0), P(lx, 0, h), P(0, 0, h)], fill=R[0])
        self.slabs[o.get("id", "")] = (o, P)

    def points_on(self, o, n):
        so, P = self.slabs[o["on"]]
        lx, ly, h = so["size"]
        face = o.get("face", "top")
        m = o.get("margin", 4)
        for _ in range(n):
            if face == "top":
                yield P(self.rng.uniform(m, lx - m), self.rng.uniform(m, ly - m), h)
            elif face == "front":
                yield P(self.rng.uniform(m, lx - m), ly, self.rng.uniform(2, max(2, h - 2)))
            else:
                yield P(lx, self.rng.uniform(m, ly - m), self.rng.uniform(2, max(2, h - 2)))

    def sphere(self, cx, cy, r, R):
        for y in range(-r, r + 1):
            for x in range(-r, r + 1):
                dd = x * x + y * y
                if dd > r * r + r * .8:
                    continue
                edge = dd > (r - .9) ** 2 + r * .8
                lit = (-x - y) / (r * 1.6)  # light from the top-left
                k = 0 if edge else (1 if lit < -.35 else 2 if lit < .25 else 3)
                self.d.point((cx + x, cy + y), fill=R[k])
        hl = max(1, r // 2)
        self.d.point((cx - hl, cy - hl), fill=R[4])
        if r >= 4:
            self.d.point((cx - hl + 1, cy - hl), fill=R[4])

    def spheres(self, o):
        R = ramp(o["color"])
        pts = sorted(self.points_on(o, o.get("count", 8)), key=lambda p: p[1])
        for x, y in pts:
            r = o.get("r", 3)
            self.sphere(x, y - r + 1, r, R)
            if o.get("sparkle") and self.rng.random() < .35:  # small 4-point glint on shiny (metal) particles
                sx, sy = x + r, y - 2 * r
                for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                    self.d.point((sx + dx, sy + dy), fill=(255, 255, 255) if (dx, dy) == (0, 0) else R[4])

    def fibers(self, o):
        R = ramp(o["color"])
        for x, y in self.points_on(o, o.get("count", 6)):
            a = self.rng.choice([(1, .5), (1, -.5), (-1, .5), (2, .5), (2, -.5)])
            L = o.get("len", 12) / 2
            p0 = (round(x - a[0] * L / 2), round(y - a[1] * L / 2))
            p1 = (round(x + a[0] * L / 2), round(y + a[1] * L / 2))
            self.d.line([(p0[0], p0[1] + 1), (p1[0], p1[1] + 1)], fill=R[0])
            self.d.line([p0, p1], fill=R[3])

    def brush(self, o):
        so, P = self.slabs[o["on"]]
        lx, ly, h = so["size"]
        R, Hd = ramp(o["color"]), ramp(o.get("head", o["color"]))
        sp, stem = o.get("spacing", 4), o.get("stem", 3)
        pts = [P(x + (y % (2 * sp)) / 2, y, h) for y in range(2, int(ly) - 1, sp) for x in range(2, int(lx) - 2, sp)]
        for x, y in sorted(pts, key=lambda p: p[1]):
            self.d.line([(x, y), (x, y - stem + 1)], fill=R[1])
            self.d.point((x, y - stem + 1), fill=R[2])
            self.d.point((x, y - stem), fill=Hd[3])
            self.d.point((x - 1, y - stem), fill=Hd[1])

    def label(self, o):
        R = ramp(o.get("color", "#FFFFFF"))
        f = font(o.get("font", "Silkscreen-Regular.ttf"), o.get("size", 8))
        x, y = o["at"]
        tw, th = f.getbbox(o["text"])[2:]
        box = [x - 3, y - 3, x + tw + 3, y + th + 2]
        if o.get("to"):  # pixel leader line with a dot at the target
            tx, ty = o["to"]
            sx = box[0] if tx < x else box[2] if tx > box[2] else (box[0] + box[2]) // 2
            sy = (box[1] + box[3]) // 2
            self.d.line([(sx, sy), (tx, ty)], fill=(255, 255, 255))
            self.d.rectangle([tx - 1, ty - 1, tx + 1, ty + 1], fill=R[3], outline=(255, 255, 255))
        self.d.rectangle([box[0] + 1, box[1] + 1, box[2] + 1, box[3] + 1], fill=(10, 14, 26))   # drop shadow
        self.d.rectangle(box, fill=(18, 24, 42), outline=(255, 255, 255))                    # dialog box
        self.d.line([box[0] + 1, box[3] - 1, box[2] - 1, box[3] - 1], fill=R[1])               # colour strip
        self.d.text((x, y), o["text"], font=f, fill=R[4] if o.get("color") else (255, 255, 255))

    def title(self, text):
        f = font("PressStart2P-Regular.ttf", 8)
        tw = f.getbbox(text)[2]
        x = (self.W - tw) // 2
        self.d.text((x + 1, 7), text, font=f, fill=(10, 14, 26))
        self.d.text((x, 6), text, font=f, fill=(255, 236, 140))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("out", nargs="?")
    ap.add_argument("-o", dest="out_opt", help="output PNG (same as the positional out)")
    ap.add_argument("--scale", type=int, default=6)
    a = ap.parse_args()
    a.out = a.out or a.out_opt
    if not a.out:
        ap.error("give the output PNG path")
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    s = Scene(spec)
    labels = []
    for o in spec["objects"]:
        if o["type"] == "label":
            labels.append(o)
        else:
            getattr(s, o["type"])(o)
    for o in labels:  # labels always on top
        s.label(o)
    if spec.get("title"):
        s.title(spec["title"])
    s.im.resize((s.W * a.scale, s.H * a.scale), Image.NEAREST).save(a.out, optimize=True)
    print("wrote", a.out, s.W * a.scale, "x", s.H * a.scale)


if __name__ == "__main__":
    main()
