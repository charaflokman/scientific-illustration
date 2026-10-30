"""Built-in line-art icons for research schematics (original drawings, CC0).

Every icon is drawn inside a 100 x 100 box and returned as an SVG fragment.
`render_figure.py` scales the box to the requested size. Parts that should take
the element's colour carry class="rv-paint" so the editor can recolour them.

Call signature for every icon: fn(c) -> str, where c is an IconCtx.
"""
import math
import random


class IconCtx:
    def __init__(self, fill="#56B4E9", accent="#E69F00", stroke="#333333",
                 sw=1.6, params=None, seed=1):
        self.fill = fill          # main colour (matrix, liquid, body)
        self.accent = accent      # secondary colour (filler, particles)
        self.stroke = stroke
        self.sw = sw              # stroke width in icon units (100-unit box)
        self.p = params or {}
        self.rng = random.Random(seed)
        self.H = 100.0            # drawing height in units (stretchable icons only)


def _s(c, extra=""):
    return f'stroke="{c.stroke}" stroke-width="{c.sw:.2f}" stroke-linejoin="round" stroke-linecap="round" {extra}'


def _light(hex_color, f=0.65):
    """Mix a colour with white (f=1 -> white)."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (round(v + (255 - v) * f) for v in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def _dark(hex_color, f=0.35):
    """Mix a colour with black (f=1 -> black)."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r, g, b = (round(int(h[i:i + 2], 16) * (1 - f)) for i in (0, 2, 4))
    return f"#{r:02X}{g:02X}{b:02X}"


def _gid(kind, col):
    return f"rvg-{kind}-{col.lstrip('#').lower()}"


def _radial(col):
    """Shaded-sphere gradient (light upper-left, dark rim). Same colour -> same id, so repeats are harmless."""
    i = _gid("r", col)
    return (f'<defs><radialGradient id="{i}" cx="0.35" cy="0.3" r="0.75">'
            f'<stop offset="0" stop-color="{_light(col, 0.75)}"/><stop offset="0.45" stop-color="{col}"/>'
            f'<stop offset="1" stop-color="{_dark(col, 0.35)}"/></radialGradient></defs>'), f"url(#{i})"


def _linear(col, vertical=True):
    i = _gid("lv" if vertical else "lh", col)
    x2, y2 = ("0", "1") if vertical else ("1", "0")
    return (f'<defs><linearGradient id="{i}" x1="0" y1="0" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" stop-color="{_light(col, 0.55)}"/><stop offset="0.5" stop-color="{col}"/>'
            f'<stop offset="1" stop-color="{_dark(col, 0.25)}"/></linearGradient></defs>'), f"url(#{i})"


def _ball(c, x, y, r, col=None, cls="rv-accent"):
    """A shaded sphere with a soft specular highlight: the basic BioRender-style particle."""
    col = col or c.accent
    d, u = _radial(col)
    return (f'{d}<circle class="{cls}" cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="{u}" data-base="{col}" '
            f'stroke="{_dark(col, 0.45)}" stroke-width="{max(0.25, r * 0.08):.2f}"/>'
            f'<ellipse cx="{x - r * 0.35:.2f}" cy="{y - r * 0.4:.2f}" rx="{r * 0.32:.2f}" ry="{r * 0.2:.2f}" '
            f'fill="#FFFFFF" opacity="0.55" transform="rotate(-35 {x - r * 0.35:.2f} {y - r * 0.4:.2f})"/>')


def _rod(c, x, y, r, ang, col=None):
    col = col or c.accent
    d, u = _linear(col)
    L, w = r * 3.6, r * 0.8
    return (f'{d}<g transform="rotate({ang:.0f} {x:.2f} {y:.2f})"><rect class="rv-accent" x="{x - L / 2:.2f}" y="{y - w / 2:.2f}" '
            f'width="{L:.2f}" height="{w:.2f}" rx="{w / 2:.2f}" fill="{u}" data-base="{col}" stroke="{_dark(col, 0.45)}" '
            f'stroke-width="{max(0.2, w * 0.1):.2f}"/><rect x="{x - L / 2 + w * 0.4:.2f}" y="{y - w * 0.32:.2f}" width="{L - w * 0.8:.2f}" '
            f'height="{w * 0.18:.2f}" rx="{w * 0.09:.2f}" fill="#FFF" opacity="0.5"/></g>')


def _particles(c, x0, y0, x1, y1, n, mode="uniform", r=2.2, shape="dot"):
    """Scatter filler particles in a rectangle. mode: uniform | agglomerated."""
    out = []
    pts = []
    if mode == "agglomerated":
        k = max(2, n // 9)
        centres = [(c.rng.uniform(x0 + 6, x1 - 6), c.rng.uniform(y0 + 4, y1 - 4)) for _ in range(k)]
        for i in range(n):
            cx, cy = centres[i % k]
            a = c.rng.uniform(0, 2 * math.pi)
            d = c.rng.uniform(0, r * 2.6)
            pts.append((min(max(cx + d * math.cos(a), x0 + r), x1 - r),
                        min(max(cy + d * math.sin(a), y0 + r), y1 - r)))
    else:
        # jittered grid keeps spacing even (reads as "uniform dispersion")
        cols = max(1, round(math.sqrt(n * (x1 - x0) / max(1e-6, (y1 - y0)))))
        rows = max(1, math.ceil(n / cols))
        dx, dy = (x1 - x0) / cols, (y1 - y0) / rows
        for i in range(n):
            cx = x0 + (i % cols + 0.5) * dx + c.rng.uniform(-dx, dx) * 0.25
            cy = y0 + (i // cols + 0.5) * dy + c.rng.uniform(-dy, dy) * 0.25
            pts.append((cx, cy))
    for (px, py) in sorted(pts, key=lambda q: q[1]):
        out.append(_rod(c, px, py, r, c.rng.uniform(0, 180)) if shape == "rod" else _ball(c, px, py, r))
    return "".join(out)


# ---------------------------------------------------------------- lab vessels
def beaker(c):
    lvl = float(c.p.get("level", 0.55))
    y = 92 - lvl * 70
    liquid = (f'<path class="rv-paint" d="M24,{y:.1f} L76,{y:.1f} L76,86 Q76,92 70,92 L30,92 Q24,92 24,86 Z" '
              f'fill="{_light(c.fill, 0.35)}" stroke="none"/>')
    body = f'<path d="M18,14 L24,18 L24,86 Q24,92 30,92 L70,92 Q76,92 76,86 L76,14" fill="none" {_s(c)}/>'
    ticks = "".join(f'<line x1="66" y1="{t}" x2="74" y2="{t}" {_s(c)}/>' for t in (40, 55, 70))
    parts = ""
    if c.p.get("particles"):
        parts = _particles(c, 28, y + 3, 72, 88, int(c.p["particles"]), c.p.get("dispersion", "uniform"), 1.8,
                           c.p.get("shape", "dot"))
    stir = ""
    if c.p.get("stir_bar"):
        stir = f'<rect x="40" y="85" width="20" height="4" rx="2" fill="#666" stroke="none"/>'
    return liquid + parts + stir + body + ticks


def flask(c):
    lvl = float(c.p.get("level", 0.4))
    y = 92 - lvl * 45
    # conical Erlenmeyer: neck 42..58, shoulder at y=40, base 14..86
    def xw(yy):
        t = (yy - 40) / 52
        return 42 - t * 28, 58 + t * 28
    xl, xr = xw(max(y, 40))
    liquid = (f'<path class="rv-paint" d="M{xl:.1f},{max(y, 40):.1f} L{xr:.1f},{max(y, 40):.1f} L86,88 Q86,92 82,92 '
              f'L18,92 Q14,92 14,88 Z" fill="{_light(c.fill, 0.35)}" stroke="none"/>')
    body = f'<path d="M40,8 L60,8 M42,8 L42,40 L14,88 Q14,92 18,92 L82,92 Q86,92 86,88 L58,40 L58,8" fill="none" {_s(c)}/>'
    return liquid + body


def petri_dish(c):
    """Side/oblique view of a Petri dish, optionally holding a cast film."""
    out = [f'<ellipse cx="50" cy="62" rx="44" ry="14" fill="#FFFFFF" {_s(c)}/>',
           f'<path d="M6,62 L6,72 Q50,96 94,72 L94,62" fill="#F4F4F4" {_s(c)}/>',
           f'<ellipse class="rv-paint" cx="50" cy="63" rx="38" ry="10" fill="{_light(c.fill, 0.35)}" stroke="none"/>']
    if c.p.get("particles"):
        n = int(c.p["particles"])
        for i in range(n):
            a = c.rng.uniform(0, 2 * math.pi)
            rr = math.sqrt(c.rng.uniform(0, 1))
            px, py = 50 + 33 * rr * math.cos(a), 63 + 8 * rr * math.sin(a)
            out.append(f'<circle class="rv-accent" cx="{px:.1f}" cy="{py:.1f}" r="1.5" fill="{c.accent}" stroke="none"/>')
    out.append(f'<ellipse cx="50" cy="62" rx="44" ry="14" fill="none" {_s(c)}/>')
    return "".join(out)


def vial(c):
    lvl = float(c.p.get("level", 0.6))
    y = 92 - lvl * 60
    return (f'<rect class="rv-paint" x="34" y="{y:.1f}" width="32" height="{92 - y - 2:.1f}" fill="{_light(c.fill, 0.35)}" stroke="none"/>'
            f'<rect x="30" y="6" width="40" height="14" rx="2" fill="#888" {_s(c)}/>'
            f'<path d="M34,20 L34,88 Q34,92 38,92 L62,92 Q66,92 66,88 L66,20" fill="none" {_s(c)}/>')


# ---------------------------------------------------------------- equipment
def stir_plate(c):
    """Magnetic stirrer with a beaker on top."""
    inner = IconCtx(c.fill, c.accent, c.stroke, c.sw, dict(c.p, stir_bar=True), seed=c.rng.randint(0, 9999))
    b = beaker(inner)
    return (f'<g transform="translate(15,0) scale(0.7)">{b}</g>'
            f'<rect x="8" y="68" width="84" height="22" rx="4" fill="#E6E6E6" {_s(c)}/>'
            f'<circle cx="26" cy="79" r="5" fill="#FFFFFF" {_s(c)}/><circle cx="74" cy="79" r="5" fill="#FFFFFF" {_s(c)}/>')


def sonicator(c):
    """Probe sonicator dipping into a beaker."""
    inner = IconCtx(c.fill, c.accent, c.stroke, c.sw, dict(c.p, level=0.6), seed=c.rng.randint(0, 9999))
    waves = "".join(f'<path d="M{44 - k * 5},{74 + k * 3} Q50,{80 + k * 4} {56 + k * 5},{74 + k * 3}" fill="none" '
                    f'stroke="{c.stroke}" stroke-width="{c.sw * 0.6:.2f}" opacity="0.7"/>' for k in range(3))
    return (f'<g transform="translate(10,22) scale(0.8)">{beaker(inner)}</g>' + waves +
            f'<rect x="38" y="2" width="24" height="22" rx="3" fill="#D9D9D9" {_s(c)}/>'
            f'<rect x="46" y="24" width="8" height="46" fill="#BDBDBD" {_s(c)}/>')


def oven(c):
    """Drying oven / convection oven with a heat symbol."""
    t = c.p.get("label_inside", "")
    return (f'<rect x="8" y="10" width="84" height="80" rx="5" fill="#F2F2F2" {_s(c)}/>'
            f'<rect x="16" y="20" width="56" height="60" rx="3" fill="#FFFFFF" {_s(c)}/>'
            f'<circle cx="82" cy="30" r="4" fill="#FFFFFF" {_s(c)}/><circle cx="82" cy="46" r="4" fill="#FFFFFF" {_s(c)}/>'
            + "".join(f'<path d="M{26 + k * 14},68 q4,-8 0,-16 q-4,-8 0,-16" fill="none" stroke="#D55E00" '
                      f'stroke-width="{c.sw:.2f}" stroke-linecap="round"/>' for k in range(3))
            + f'<line x1="20" y1="72" x2="68" y2="72" {_s(c)}/>'
            + f'<rect class="rv-paint" x="24" y="66" width="40" height="5" fill="{_light(c.fill, 0.2)}" {_s(c)}/>')


def hot_press(c):
    return (f'<rect x="10" y="6" width="80" height="10" fill="#BDBDBD" {_s(c)}/>'
            f'<line x1="18" y1="16" x2="18" y2="90" {_s(c)}/><line x1="82" y1="16" x2="82" y2="90" {_s(c)}/>'
            f'<rect x="22" y="30" width="56" height="12" fill="#E0E0E0" {_s(c)}/>'
            f'<rect class="rv-paint" x="26" y="44" width="48" height="6" fill="{_light(c.fill, 0.2)}" {_s(c)}/>'
            f'<rect x="22" y="52" width="56" height="12" fill="#E0E0E0" {_s(c)}/>'
            f'<rect x="10" y="84" width="80" height="8" fill="#BDBDBD" {_s(c)}/>'
            f'<path d="M50,18 L50,28 M45,23 L50,28 L55,23" fill="none" stroke="#D55E00" stroke-width="{c.sw:.2f}"/>'
            + "".join(f'<path d="M{30 + k * 14},76 q3,-4 0,-8" fill="none" stroke="#D55E00" stroke-width="{c.sw * 0.8:.2f}"/>'
                      for k in range(4)))


def extruder(c):
    """Twin/single-screw extruder: hopper, barrel with screw, die, strand."""
    flights = "".join(f'<path d="M{24 + k * 8},44 L{28 + k * 8},56" stroke="{c.stroke}" stroke-width="{c.sw:.2f}"/>'
                      for k in range(7))
    heaters = "".join(f'<rect x="{22 + k * 18}" y="34" width="14" height="6" fill="#F4A582" {_s(c)}/>' for k in range(4))
    return (f'<path d="M18,10 L38,10 L32,32 L24,32 Z" class="rv-paint" fill="{_light(c.fill, 0.35)}" {_s(c)}/>'
            f'<rect x="14" y="40" width="74" height="20" rx="2" fill="#EDEDED" {_s(c)}/>' + heaters +
            f'<line x1="18" y1="50" x2="84" y2="50" stroke="{c.stroke}" stroke-width="{c.sw * 1.4:.2f}"/>' + flights +
            f'<path d="M88,44 L94,47 L94,53 L88,56 Z" fill="#BDBDBD" {_s(c)}/>'
            f'<path class="rv-paint" d="M94,50 Q98,62 92,74 Q86,84 96,92" fill="none" stroke="{c.fill}" stroke-width="{c.sw * 2.2:.2f}"/>')


def centrifuge_tube(c):
    lvl = float(c.p.get("level", 0.6))
    return (f'<path class="rv-paint" d="M36,{90 - lvl * 60:.1f} L64,{90 - lvl * 60:.1f} L64,70 L50,94 L36,70 Z" fill="{_light(c.fill, 0.35)}" stroke="none"/>'
            f'<rect x="32" y="4" width="36" height="10" rx="2" fill="#BDBDBD" {_s(c)}/>'
            f'<path d="M36,14 L36,70 L50,94 L64,70 L64,14" fill="none" {_s(c)}/>')


def pipette(c):
    return (f'<rect x="44" y="4" width="12" height="40" rx="4" fill="#D9D9D9" {_s(c)}/>'
            f'<rect x="40" y="0" width="20" height="6" rx="2" fill="#9E9E9E" {_s(c)}/>'
            f'<path d="M46,44 L54,44 L51,92 L49,92 Z" fill="#FFFFFF" {_s(c)}/>'
            f'<circle class="rv-paint" cx="50" cy="96" r="3" fill="{c.fill}" stroke="none"/>')


def syringe(c):
    return (f'<rect x="20" y="40" width="56" height="20" fill="#FFFFFF" {_s(c)}/>'
            f'<rect class="rv-paint" x="40" y="42" width="36" height="16" fill="{_light(c.fill, 0.35)}" stroke="none"/>'
            f'<line x1="4" y1="50" x2="40" y2="50" {_s(c)}/><line x1="4" y1="42" x2="4" y2="58" {_s(c)}/>'
            f'<rect x="38" y="41" width="3" height="18" fill="#666" stroke="none"/>'
            f'<line x1="76" y1="50" x2="96" y2="50" {_s(c)}/><line x1="20" y1="36" x2="20" y2="64" {_s(c)}/>')


def thermometer(c):
    return (f'<rect x="42" y="6" width="16" height="66" rx="8" fill="#FFFFFF" {_s(c)}/>'
            f'<rect x="47" y="30" width="6" height="50" fill="#D55E00" stroke="none"/>'
            f'<circle cx="50" cy="82" r="12" fill="#D55E00" {_s(c)}/>')


def balance(c):
    return (f'<rect x="10" y="66" width="80" height="24" rx="3" fill="#E6E6E6" {_s(c)}/>'
            f'<rect x="22" y="72" width="40" height="12" fill="#FFFFFF" {_s(c)}/>'
            f'<rect x="20" y="58" width="60" height="6" rx="2" fill="#BDBDBD" {_s(c)}/>'
            f'<rect class="rv-paint" x="38" y="40" width="24" height="18" fill="{_light(c.fill, 0.3)}" {_s(c)}/>')


def microscope(c):
    return (f'<path d="M30,90 L80,90" {_s(c)}/><path d="M60,90 L60,40 Q60,20 44,18" fill="none" {_s(c, "")}/>'
            f'<rect x="30" y="6" width="14" height="40" rx="3" transform="rotate(-20 37 26)" fill="#D9D9D9" {_s(c)}/>'
            f'<rect x="28" y="56" width="36" height="5" fill="#BDBDBD" {_s(c)}/>'
            f'<rect x="20" y="84" width="64" height="8" rx="2" fill="#9E9E9E" {_s(c)}/>')


def spectrometer(c):
    """Generic analytical instrument with a spectrum on its screen (FTIR/XRD/UV)."""
    return (f'<rect x="6" y="30" width="88" height="56" rx="5" fill="#EFEFEF" {_s(c)}/>'
            f'<rect x="14" y="38" width="44" height="30" fill="#FFFFFF" {_s(c)}/>'
            f'<path class="rv-paint" d="M16,62 L24,60 L28,46 L31,60 L38,58 L42,50 L45,60 L56,61" fill="none" stroke="{c.fill}" stroke-width="{c.sw:.2f}"/>'
            f'<rect x="64" y="40" width="22" height="8" rx="2" fill="#BDBDBD" {_s(c)}/>'
            f'<circle cx="70" cy="62" r="4" fill="#FFFFFF" {_s(c)}/><circle cx="82" cy="62" r="4" fill="#FFFFFF" {_s(c)}/>')


def tensile_tester(c):
    return (f'<rect x="14" y="6" width="72" height="10" fill="#BDBDBD" {_s(c)}/>'
            f'<line x1="20" y1="16" x2="20" y2="92" {_s(c)}/><line x1="80" y1="16" x2="80" y2="92" {_s(c)}/>'
            f'<rect x="42" y="16" width="16" height="14" fill="#9E9E9E" {_s(c)}/>'
            f'<path class="rv-paint" d="M44,30 L56,30 L56,40 L53,44 L53,64 L56,68 L56,78 L44,78 L44,68 L47,64 L47,44 L44,40 Z" fill="{_light(c.fill, 0.3)}" {_s(c)}/>'
            f'<rect x="42" y="78" width="16" height="10" fill="#9E9E9E" {_s(c)}/>'
            f'<path d="M50,4 L50,-2 M30,22 L30,12 M26,16 L30,12 L34,16" stroke="#D55E00" stroke-width="{c.sw:.2f}" fill="none"/>')


def soil_burial(c):
    stones = "".join(f'<ellipse cx="{c.rng.uniform(12, 88):.1f}" cy="{c.rng.uniform(52, 90):.1f}" rx="2.5" ry="1.6" fill="#8C6D46" stroke="none"/>'
                     for _ in range(14))
    return (f'<rect x="4" y="40" width="92" height="54" fill="#C9A77C" {_s(c)}/>' + stones +
            f'<rect class="rv-paint" x="28" y="64" width="44" height="6" fill="{_light(c.fill, 0.2)}" {_s(c)} stroke-dasharray="4 2"/>'
            f'<path d="M30,40 q4,-14 0,-24 M30,26 q8,-6 12,-2 M70,40 q-3,-10 2,-18 M71,26 q-8,-4 -10,0" fill="none" stroke="#009E73" stroke-width="{c.sw:.2f}"/>')


# ---------------------------------------------------------------- materials
def film(c):
    """Oblique slab of a composite film; params: particles, dispersion, shape(dot|rod), pores."""
    top = f'<path class="rv-paint" d="M8,40 L70,28 L92,46 L30,58 Z" fill="{_light(c.fill, 0.45)}" {_s(c)}/>'
    front = f'<path class="rv-paint" d="M8,40 L30,58 L30,72 L8,54 Z" fill="{_light(c.fill, 0.15)}" {_s(c)}/>'
    side = f'<path class="rv-paint" d="M30,58 L92,46 L92,60 L30,72 Z" fill="{_light(c.fill, 0.3)}" {_s(c)}/>'
    parts = ""
    n = int(c.p.get("particles", 0))
    if n:
        # place in a parallelogram by mapping a unit square onto the top face
        mode = c.p.get("dispersion", "uniform")
        shape = c.p.get("shape", "dot")
        raw = _particles(c, 0, 0, 100, 100, n, mode, 3.0, shape)
        parts = f'<g transform="matrix(0.62,-0.12,0.22,0.18,8,40)">{raw}</g>'
    return top + parts + front + side


def film_cross_section(c):
    """Cross-section of a film with particles (uniform or agglomerated). Stretches to any aspect."""
    n = int(c.p.get("particles", 40))
    mode = c.p.get("dispersion", "uniform")
    shape = c.p.get("shape", "dot")
    H = c.H
    r = float(c.p.get("particle_r", min(3.2, H * 0.06)))
    d, u = _linear(_light(c.fill, 0.45))
    chains = "".join(f'<path d="M3,{y:.1f} q12,-4 24,0 t24,0 t24,0 t24,0" fill="none" stroke="{c.fill}" stroke-opacity="0.25" '
                     f'stroke-width="{c.sw * 0.6:.2f}"/>' for y in [H * k / 7 for k in range(1, 7)])
    return (f'{d}<rect class="rv-paint" x="1" y="1" width="98" height="{H - 2:.2f}" rx="4" fill="{u}" data-base="{c.fill}" '
            f'stroke="{_dark(c.fill, 0.3)}" stroke-width="{c.sw:.2f}"/>' + chains
            + f'<rect x="3" y="2.5" width="94" height="{H * 0.12:.2f}" rx="3" fill="#FFF" opacity="0.35"/>'
            + _particles(c, 5, 5, 95, H - 5, n, mode, r, shape))


def polymer_chain(c):
    """Wavy polymer backbone; params: chains (1-4)."""
    k = int(c.p.get("chains", 2))
    out = []
    for i in range(k):
        y = 20 + i * (60 / max(1, k - 1 if k > 1 else 1)) if k > 1 else 50
        d = f"M4,{y:.1f} " + " ".join(f"Q{12 + j * 16},{y + (10 if j % 2 else -10):.1f} {20 + j * 16},{y:.1f}" for j in range(5))
        out.append(f'<path class="rv-paint" d="{d}" fill="none" stroke="{c.fill}" stroke-width="{c.sw * 2:.2f}" stroke-linecap="round"/>')
    return "".join(out)


def crosslinked_network(c):
    """Two or three chains joined by crosslink bridges (accent colour)."""
    chains = polymer_chain(IconCtx(c.fill, c.accent, c.stroke, c.sw, {"chains": 3}))
    links = "".join(f'<line class="rv-accent" x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{c.accent}" stroke-width="{c.sw * 1.6:.2f}"/>'
                    f'<circle class="rv-accent" cx="{x}" cy="{(y1 + y2) / 2:.1f}" r="3" fill="{c.accent}" stroke="none"/>'
                    for x, y1, y2 in ((20, 20, 50), (52, 20, 50), (36, 50, 80), (68, 50, 80)))
    return chains + links


def nanoparticle(c):
    return _ball(c, 50, 50, 30)


def coated_nanoparticle(c):
    """Particle with a shell of grafted chains (e.g. silane-compatibilised filler)."""
    out = []
    n = int(c.p.get("chains", 18))
    for k in range(n):
        a = k * 2 * math.pi / n
        x1, y1 = 50 + 21 * math.cos(a), 50 + 21 * math.sin(a)
        xm, ym = 50 + 31 * math.cos(a + 0.18), 50 + 31 * math.sin(a + 0.18)
        x2, y2 = 50 + 40 * math.cos(a), 50 + 40 * math.sin(a)
        out.append(f'<path class="rv-paint" d="M{x1:.1f},{y1:.1f} Q{xm:.1f},{ym:.1f} {x2:.1f},{y2:.1f}" fill="none" '
                   f'stroke="{c.fill}" stroke-width="{c.sw * 1.1:.2f}" stroke-linecap="round"/>')
        out.append(_ball(c, x2, y2, 2.8, c.fill, "rv-paint"))
    out.append(f'<circle cx="50" cy="50" r="23.5" fill="none" stroke="{c.fill}" stroke-opacity="0.35" stroke-width="3"/>')
    return "".join(out) + _ball(c, 50, 50, 21)


def agglomerate(c):
    pts = []
    for _ in range(int(c.p.get("particles", 22))):
        a = c.rng.uniform(0, 2 * math.pi)
        d = 30 * math.sqrt(c.rng.uniform(0, 1))
        pts.append((50 + d * math.cos(a), 50 + d * 0.85 * math.sin(a)))
    return "".join(_ball(c, x, y, 9) for x, y in sorted(pts, key=lambda q: q[1]))


def nanocrystal_rods(c):
    """Cellulose nanocrystals / nanofibres as rods."""
    return _particles(c, 10, 10, 90, 90, int(c.p.get("particles", 12)), c.p.get("dispersion", "uniform"), 6, "rod")


def water_drop(c):
    return (f'<path class="rv-paint" d="M50,8 C50,8 18,48 18,64 A32,32 0 0 0 82,64 C82,48 50,8 50,8 Z" fill="{_light(c.fill, 0.25)}" {_s(c)}/>'
            f'<path d="M34,62 A16,16 0 0 0 44,78" fill="none" stroke="#FFFFFF" stroke-width="{c.sw * 1.6:.2f}"/>')


def contact_angle(c):
    th = float(c.p.get("angle", 70))
    # spherical cap: base half-width 30, height from angle
    a = math.radians(th)
    h = 30 * (1 - math.cos(a)) / math.sin(a) if th < 179 else 30
    return (f'<rect x="4" y="70" width="92" height="10" fill="#D9D9D9" {_s(c)}/>'
            f'<path class="rv-paint" d="M20,70 Q50,{70 - 2 * h:.1f} 80,70 Z" fill="{_light(c.fill, 0.3)}" {_s(c)}/>')


def cell(c):
    """Shaded eukaryotic cell; params: kind = round|fibroblast|keratinocyte, state = healthy|damaged."""
    kind = c.p.get("kind", "round")
    d, u = _radial(_light(c.fill, 0.35))
    dn, un = _radial(_dark(c.fill, 0.15))
    if kind == "fibroblast":
        body = "M6,52 C22,40 34,34 50,36 C66,34 80,40 94,48 C80,54 70,62 50,64 C34,66 22,60 6,52 Z"
    elif kind == "keratinocyte":
        body = "M24,22 L62,16 L86,38 L80,74 L46,86 L16,66 Z"
    else:
        body = "M50,14 C74,12 90,30 88,52 C86,74 70,88 48,86 C26,84 12,70 12,50 C12,30 28,16 50,14 Z"
    dmg = c.p.get("state") == "damaged"
    dash = ' stroke-dasharray="4 3"' if dmg else ""
    org = "".join(f'<ellipse cx="{x}" cy="{y}" rx="5" ry="2.6" fill="{_dark(c.accent, 0.1)}" opacity="0.75" transform="rotate({a} {x} {y})"/>'
                  for x, y, a in ((30, 58, 20), (70, 62, -15), (66, 34, 30)))
    out = (f'{d}{dn}<path class="rv-paint" d="{body}" fill="{u}" data-base="{c.fill}" stroke="{_dark(c.fill, 0.35)}" '
           f'stroke-width="{c.sw:.2f}"{dash}/>'
           f'<ellipse cx="50" cy="50" rx="13" ry="11" fill="{un}" stroke="{_dark(c.fill, 0.45)}" stroke-width="{c.sw * 0.6:.2f}"/>'
           f'<circle cx="53" cy="48" r="3.5" fill="{_dark(c.fill, 0.5)}"/>' + org)
    if dmg:
        out += '<path d="M40,20 l6,10 l-5,4 l7,9" fill="none" stroke="#D55E00" stroke-width="2.2" stroke-linecap="round"/>'
    return out


def bacterium(c):
    """Rod-shaped bacterium, shaded, with flagella; params: state = alive|dead."""
    d, u = _linear(_light(c.fill, 0.2))
    fl = "".join(f'<path d="M86,{42 + k * 8} q5,-5 9,0 t9,0" fill="none" stroke="{_dark(c.fill, 0.4)}" stroke-width="{c.sw * 0.6:.2f}"/>' for k in range(3))
    pili = "".join(f'<line x1="{x}" y1="31" x2="{x - 2}" y2="25" stroke="{_dark(c.fill, 0.3)}" stroke-width="0.8"/>'
                   f'<line x1="{x}" y1="69" x2="{x + 2}" y2="75" stroke="{_dark(c.fill, 0.3)}" stroke-width="0.8"/>' for x in range(24, 80, 8))
    body = (f'{d}<rect class="rv-paint" x="12" y="31" width="76" height="38" rx="19" fill="{u}" data-base="{c.fill}" '
            f'stroke="{_dark(c.fill, 0.4)}" stroke-width="{c.sw:.2f}"/>'
            f'<rect x="20" y="35" width="58" height="7" rx="3.5" fill="#FFF" opacity="0.45"/>'
            f'<path d="M30,54 q8,-7 16,0 t16,0" fill="none" stroke="{_dark(c.fill, 0.45)}" stroke-width="{c.sw * 0.7:.2f}"/>')
    out = pili + fl + body
    if c.p.get("state") == "dead":
        out = f'<g opacity="0.45">{out}</g><path d="M28,30 L72,70 M72,30 L28,70" stroke="#D55E00" stroke-width="4" stroke-linecap="round"/>'
    return out


def molecule_generic(c):
    """Ball-and-stick placeholder for 'a small molecule' when no SMILES is given."""
    pts = [(30, 30), (60, 26), (76, 52), (56, 74), (28, 66)]
    bonds = "".join(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" {_s(c)}/>' for a, b in zip(pts, pts[1:] + pts[:1]))
    atoms = "".join(f'<circle class="rv-paint" cx="{x}" cy="{y}" r="7" fill="{c.fill}" {_s(c)}/>' for x, y in pts)
    return bonds + atoms


def arrow_heat(c):
    return "".join(f'<path d="M{24 + k * 22},86 q8,-14 0,-28 q-8,-14 0,-28 q8,-14 0,-22" fill="none" stroke="#D55E00" '
                   f'stroke-width="{c.sw * 1.4:.2f}" stroke-linecap="round"/>' for k in range(3))


def check_mark(c):
    return (f'<circle cx="50" cy="50" r="40" fill="#E6F4EF" stroke="#009E73" stroke-width="{c.sw * 1.5:.2f}"/>'
            f'<path d="M30,52 L45,66 L72,36" fill="none" stroke="#009E73" stroke-width="{c.sw * 3:.2f}" stroke-linecap="round" stroke-linejoin="round"/>')


def cross_mark(c):
    return (f'<circle cx="50" cy="50" r="40" fill="#FBEAE3" stroke="#D55E00" stroke-width="{c.sw * 1.5:.2f}"/>'
            f'<path d="M34,34 L66,66 M66,34 L34,66" fill="none" stroke="#D55E00" stroke-width="{c.sw * 3:.2f}" stroke-linecap="round"/>')


def crack(c):
    """Film cross-section (agglomerated filler by default) with a crack through it."""
    H = c.H
    c.p = dict({"particles": 20, "dispersion": "agglomerated"}, **c.p)
    return film_cross_section(c) + (f'<path d="M50,1 L45,{H * 0.3:.1f} L55,{H * 0.5:.1f} L46,{H * 0.72:.1f} L52,{H * 0.92:.1f}" '
                                    f'fill="none" stroke="#D55E00" stroke-width="{c.sw * 1.6:.2f}"/>')


def plot_curve(c):
    """Tiny generic axes with a curve; params: kind = rise|decay|peak|sigmoid."""
    kind = c.p.get("kind", "rise")
    xs = [i / 20 for i in range(21)]
    if kind == "decay":
        ys = [math.exp(-3 * x) for x in xs]
    elif kind == "peak":
        ys = [math.exp(-((x - 0.3) / 0.12) ** 2) for x in xs]
    elif kind == "sigmoid":
        ys = [1 / (1 + math.exp(-12 * (x - 0.45))) for x in xs]
    else:
        ys = [1 - math.exp(-4 * x) for x in xs]
    d = "M" + " L".join(f"{16 + x * 76:.1f},{84 - y * 66:.1f}" for x, y in zip(xs, ys))
    return (f'<path d="M14,8 L14,86 L94,86" fill="none" {_s(c)}/>'
            f'<path class="rv-paint" d="{d}" fill="none" stroke="{c.fill}" stroke-width="{c.sw * 1.6:.2f}"/>')


def placeholder(c):
    H = c.H
    return (f'<rect x="1" y="1" width="98" height="{H - 2:.2f}" fill="#FAFAFA" stroke="#999" stroke-width="{c.sw:.2f}" stroke-dasharray="5 3"/>'
            f'<path d="M1,1 L99,{H - 1:.2f} M99,1 L1,{H - 1:.2f}" stroke="#DDD" stroke-width="{c.sw * 0.6:.2f}"/>')

def skin_wound(c):
    """Skin cross-section (epidermis / dermis) with a wound bed and dressing; stretches.
    params: dressing (bool), particles, dispersion."""
    H = c.H
    ep, de = "#F2C6A8", "#E8A989"
    d1, u1 = _linear(ep)
    d2, u2 = _linear(de)
    y1, y2 = H * 0.42, H * 0.62
    wound = f"M36,{y1:.1f} Q50,{y2 + H * 0.12:.1f} 64,{y1:.1f} Z"
    out = (d1 + d2 + f'<rect x="1" y="{y1:.1f}" width="98" height="{y2 - y1:.1f}" fill="{u1}" stroke="{_dark(ep, 0.3)}" stroke-width="{c.sw * 0.7:.2f}"/>'
           f'<rect x="1" y="{y2:.1f}" width="98" height="{H - y2 - 1:.1f}" fill="{u2}" stroke="{_dark(de, 0.3)}" stroke-width="{c.sw * 0.7:.2f}"/>'
           + "".join(f'<path d="M{x},{H - 2:.1f} q-3,{-(H - y2) * 0.4:.1f} 1,{-(H - y2) * 0.8:.1f}" fill="none" stroke="#C0392B" '
                     f'stroke-opacity="0.45" stroke-width="1.2"/>' for x in (12, 30, 72, 90))
           + f'<path d="{wound}" fill="#B03A2E" opacity="0.85"/>')
    if c.p.get("dressing", True):
        dd, ud = _linear(_light(c.fill, 0.2))
        out += (dd + f'<rect class="rv-paint" x="6" y="{y1 - H * 0.16:.1f}" width="88" height="{H * 0.14:.1f}" rx="3" fill="{ud}" '
                f'data-base="{c.fill}" stroke="{_dark(c.fill, 0.35)}" stroke-width="{c.sw * 0.8:.2f}" opacity="0.92"/>')
        n = int(c.p.get("particles", 0))
        if n:
            out += _particles(c, 9, y1 - H * 0.145, 91, y1 - H * 0.035, n, c.p.get("dispersion", "uniform"), min(2.2, H * 0.03))
    return out


def drug_release(c):
    """Mini release profile; params: kind = burst|sustained. Illustrative shape, not data."""
    burst = c.p.get("kind", "burst") == "burst"
    xs = [i / 30 for i in range(31)]
    ys = [(0.85 * (1 - math.exp(-14 * x)) + 0.1 * x) if burst else (1 - math.exp(-2.6 * x)) for x in xs]
    d = "M" + " L".join(f"{16 + x * 76:.1f},{84 - y * 66:.1f}" for x, y in zip(xs, ys))
    band = (f'<rect x="16" y="{84 - 0.72 * 66:.1f}" width="76" height="{0.3 * 66:.1f}" fill="#009E73" opacity="0.12"/>'
            f'<line x1="16" y1="{84 - 0.72 * 66:.1f}" x2="92" y2="{84 - 0.72 * 66:.1f}" stroke="#009E73" stroke-dasharray="3 2" stroke-width="0.8"/>')
    fill = f'<path d="{d} L92,84 L16,84 Z" class="rv-paint" fill="{c.fill}" opacity="0.15"/>'
    return (band + fill + f'<path d="M14,8 L14,86 L94,86" fill="none" {_s(c)}/>'
            f'<path class="rv-paint" d="{d}" fill="none" stroke="{c.fill}" stroke-width="{c.sw * 1.8:.2f}" stroke-linecap="round"/>')


def silica_network(c):
    """Polymer chains with a Si-O-Si network (e.g. GPTMS hybrid); params: coupled (bool)."""
    coupled = c.p.get("coupled", True)
    out = []
    nodes = [(22 + 18 * i + (9 if j % 2 else 0), 24 + 17 * j) for j in range(4) for i in range(4)]
    for (x, y) in nodes:
        for (u, v) in nodes:
            if 0 < math.hypot(u - x, v - y) < 21 and (u, v) > (x, y):
                out.append(f'<line x1="{x}" y1="{y}" x2="{u}" y2="{v}" stroke="#7F8C8D" stroke-width="1.4"/>')
    for k in range(3):
        y = 30 + k * 18
        out.append(f'<path class="rv-paint" d="M2,{y + 4} q12,-12 24,0 t24,0 t24,0 t24,0" fill="none" stroke="{c.fill}" '
                   f'stroke-width="{c.sw * 1.7:.2f}" stroke-linecap="round"/>')
    if coupled:
        out += [f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + 8}" stroke="{c.accent}" stroke-width="2.4"/>' for x, y in nodes[1::3]]
    out += [_ball(c, x, y, 3.6, "#95A5A6", "rv-node") for x, y in nodes]
    return "".join(out)


def micrograph(c):
    """SCHEMATIC TEM/SEM field with particles and a scale bar - never present it as a real image."""
    H = c.H
    n = int(c.p.get("particles", 26))
    out = [f'<rect x="1" y="1" width="98" height="{H - 2:.2f}" rx="2" fill="#2B2B2B" stroke="#111" stroke-width="{c.sw:.2f}"/>']
    sub = IconCtx(c.fill, c.p.get("particle_color", "#BDBDBD"), c.stroke, c.sw, None, 3)
    out.append(_particles(sub, 6, 6, 94, H - 14, n, c.p.get("dispersion", "uniform"), min(3, H * 0.05)))
    out.append(f'<rect x="64" y="{H - 9:.1f}" width="26" height="2.4" fill="#FFF"/>')
    return "".join(out)


def drug_molecules(c):
    """Cluster of small drug molecules (hexagons)."""
    out = []
    for _ in range(int(c.p.get("count", 7))):
        x, y = c.rng.uniform(18, 82), c.rng.uniform(18, 82)
        r = 7
        pts = " ".join(f"{x + r * math.cos(a * math.pi / 3):.1f},{y + r * math.sin(a * math.pi / 3):.1f}" for a in range(6))
        out.append(f'<polygon class="rv-accent" points="{pts}" fill="{_light(c.accent, 0.3)}" stroke="{_dark(c.accent, 0.35)}" stroke-width="1.4"/>')
    return "".join(out)


ICONS = {
    "beaker": beaker, "flask": flask, "petri_dish": petri_dish, "vial": vial,
    "stir_plate": stir_plate, "sonicator": sonicator, "oven": oven, "hot_press": hot_press,
    "extruder": extruder, "centrifuge_tube": centrifuge_tube, "pipette": pipette, "syringe": syringe,
    "thermometer": thermometer, "balance": balance, "microscope": microscope, "spectrometer": spectrometer,
    "tensile_tester": tensile_tester, "soil_burial": soil_burial,
    "film": film, "film_cross_section": film_cross_section, "polymer_chain": polymer_chain,
    "crosslinked_network": crosslinked_network, "nanoparticle": nanoparticle,
    "coated_nanoparticle": coated_nanoparticle, "agglomerate": agglomerate, "nanocrystal_rods": nanocrystal_rods,
    "water_drop": water_drop, "contact_angle": contact_angle, "cell": cell, "bacterium": bacterium,
    "molecule_generic": molecule_generic, "heat": arrow_heat, "check": check_mark, "cross": cross_mark,
    "crack": crack, "plot_curve": plot_curve, "placeholder": placeholder,
    "skin_wound": skin_wound, "drug_release": drug_release, "silica_network": silica_network,
    "micrograph": micrograph, "drug_molecules": drug_molecules,
}

# Icons that stretch to the box aspect ratio instead of keeping 1:1.
STRETCH_ICONS = {"film_cross_section", "crack", "placeholder", "skin_wound", "micrograph"}

# Short descriptions, used by `render_figure.py --list-icons`.
ICON_HELP = {
    "beaker": "params: level 0-1, particles N, dispersion uniform|agglomerated, shape dot|rod, stir_bar",
    "film": "oblique composite film; params: particles, dispersion, shape",
    "film_cross_section": "film cross-section; params: particles, dispersion, shape, particle_r",
    "polymer_chain": "params: chains 1-4",
    "plot_curve": "mini readout plot; params: kind rise|decay|peak|sigmoid",
    "contact_angle": "params: angle (deg)",
    "agglomerate": "params: particles",
    "cell": "params: kind round|fibroblast|keratinocyte, state healthy|damaged",
    "bacterium": "params: state alive|dead",
    "skin_wound": "skin + wound bed + dressing; params: dressing, particles, dispersion (stretches)",
    "drug_release": "illustrative release shape; params: kind burst|sustained (therapeutic band)",
    "silica_network": "polymer + Si-O-Si network; params: coupled true|false",
    "micrograph": "SCHEMATIC TEM/SEM field (label it schematic); params: particles, dispersion",
    "drug_molecules": "params: count",
    "placeholder": "dashed box for user-supplied images (SEM, photos)",
}
