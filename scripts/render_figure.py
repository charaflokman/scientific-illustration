#!/usr/bin/env python3
"""Render a figure spec (JSON) into an editable, journal-sized SVG.

The model plans the *meaning* (which elements, labels, conditions, colours) in a
JSON spec; this script owns the *geometry*. Every element becomes an <svg:g>
with a stable id, all text stays as real <text>, and the spec plus any manual
edits are stored inside the SVG (<metadata id="rv-data">), so the SVG alone is a
complete, re-renderable source.

Usage
  python render_figure.py spec.json -o out/figure.svg            # SVG + editor
  python render_figure.py spec.json -o out/figure.svg --keep-edits out/figure.svg
      (re-render after changing the spec, keeping edits saved from the editor)
  python render_figure.py spec.json -o out/figure.svg --overrides edits.json
  python render_figure.py --list-icons

Outputs next to the SVG: <name>.editor.html (open in a browser to drag, retype,
recolour, delete, then save) and a printed report of placeholders and credits.
"""
import argparse
import base64
import copy
import html
import json
import math
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from icons import ICONS, ICON_HELP, STRETCH_ICONS, IconCtx  # noqa: E402

PT = 0.3528  # mm per point

# Okabe & Ito (2008) colour-universal-design palette.
OKABE_ITO = {
    "orange": "#E69F00", "skyblue": "#56B4E9", "green": "#009E73", "yellow": "#F0E442",
    "blue": "#0072B2", "vermillion": "#D55E00", "purple": "#CC79A7", "black": "#000000", "grey": "#999999",
}
DEFAULT_ROLES = {
    "matrix": "#56B4E9", "filler": "#E69F00", "crosslinker": "#009E73", "plasticizer": "#CC79A7",
    "solvent": "#56B4E9", "water": "#56B4E9", "heat": "#D55E00", "good": "#009E73", "bad": "#D55E00",
    "neutral": "#999999", "text": "#222222", "line": "#333333",
}
PLACEHOLDER_RE = re.compile(r"\[\?[^\]]*\]")


def esc(s):
    return html.escape(str(s), quote=True)


def color_of(spec_colors, value, fallback):
    if not value:
        return fallback
    if value.startswith("#") or value.startswith("rgb") or value == "none":
        return value
    return spec_colors.get(value) or OKABE_ITO.get(value) or fallback


# ---------------------------------------------------------------- text helpers
def wrap(text, width_mm, size_mm):
    """Greedy word wrap using an average glyph width of 0.55 em (Arial-like)."""
    lines = []
    for para in str(text).split("\n"):
        # keep each [? ...] placeholder on one line (non-breaking spaces inside it)
        para = PLACEHOLDER_RE.sub(lambda m: m.group(0).replace(" ", " "), para)
        if width_mm is None:
            lines.append(para)
            continue
        maxc = max(4, int(width_mm / (0.55 * size_mm)))
        cur = ""
        for w in para.split(" "):
            if cur and len(cur) + 1 + len(w) > maxc:
                lines.append(cur)
                cur = w
            else:
                cur = f"{cur} {w}" if cur else w
        lines.append(cur)
    return lines


def text_el(tid, x, y, text, size_pt, *, anchor="middle", weight="normal", color="#222222",
            italic=False, width=None, valign="top", font=None):
    size = size_pt * PT
    lines = wrap(text, width, size)
    lh = size * 1.18
    if valign == "middle":
        y0 = y - (len(lines) - 1) * lh / 2 + size * 0.35
    elif valign == "bottom":
        y0 = y - (len(lines) - 1) * lh
    else:
        y0 = y + size * 0.8
    style = ' font-style="italic"' if italic else ""
    fam = f' font-family="{esc(font)}"' if font else ""
    spans = []
    for i, ln in enumerate(lines):
        # colour only the [? ...] part so missing values stand out
        inner = PLACEHOLDER_RE.sub(lambda m: "@@PH@@" + m.group(0) + "@@/PH@@", ln)
        inner = esc(inner).replace("@@PH@@", '<tspan fill="#C0392B" font-weight="bold">').replace("@@/PH@@", "</tspan>")
        spans.append(f'<tspan x="{x:.2f}" y="{y0 + i * lh:.2f}">{inner}</tspan>')
    return (f'<text id="{esc(tid)}" class="rv-text" data-raw="{esc(text)}" data-width="{width or ""}" '
            f'data-valign="{valign}" font-size="{size:.3f}" text-anchor="{anchor}" font-weight="{weight}" '
            f'fill="{color}"{style}{fam}>{"".join(spans)}</text>'), len(lines) * lh


# ---------------------------------------------------------------- arrows
def _clip(cx, cy, bx, by, bw, bh, tx, ty, gap):
    """Point where the ray centre->target leaves the box, pushed out by gap."""
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    sx = (bw / 2) / abs(dx) if dx else math.inf
    sy = (bh / 2) / abs(dy) if dy else math.inf
    s = min(sx, sy)
    L = math.hypot(dx, dy)
    return cx + dx * s + dx / L * gap, cy + dy * s + dy / L * gap


def arrow_geometry(a_box, b_box, curve=0.0, route="straight", gap=1.0):
    """Return (path_d, head_points, label_xy, angle). Boxes are (x, y, w, h) or a point (x, y, 0, 0)."""
    ax, ay, aw, ah = a_box
    bx, by, bw, bh = b_box
    acx, acy, bcx, bcy = ax + aw / 2, ay + ah / 2, bx + bw / 2, by + bh / 2
    if route == "elbow":
        # horizontal first, then vertical
        sx, sy = _clip(acx, acy, ax, ay, aw, ah, bcx, acy, gap) if aw else (acx, acy)
        ex, ey = _clip(bcx, bcy, bx, by, bw, bh, bcx, acy, gap) if bw else (bcx, bcy)
        d = f"M{sx:.2f},{sy:.2f} L{ex:.2f},{sy:.2f} L{ex:.2f},{ey:.2f}"
        ang = math.atan2(ey - sy, 0) if abs(ey - sy) > 1e-6 else (0 if ex > sx else math.pi)
        lx, ly = (sx + ex) / 2, sy
        tip = (ex, ey)
    else:
        sx, sy = _clip(acx, acy, ax, ay, aw, ah, bcx, bcy, gap) if aw else (acx, acy)
        ex, ey = _clip(bcx, bcy, bx, by, bw, bh, acx, acy, gap) if bw else (bcx, bcy)
        L = math.hypot(ex - sx, ey - sy) or 1
        nx, ny = -(ey - sy) / L, (ex - sx) / L
        if curve:
            qx, qy = (sx + ex) / 2 + nx * curve * L, (sy + ey) / 2 + ny * curve * L
            d = f"M{sx:.2f},{sy:.2f} Q{qx:.2f},{qy:.2f} {ex:.2f},{ey:.2f}"
            ang = math.atan2(ey - qy, ex - qx)
            lx, ly = 0.25 * sx + 0.5 * qx + 0.25 * ex, 0.25 * sy + 0.5 * qy + 0.25 * ey
        else:
            d = f"M{sx:.2f},{sy:.2f} L{ex:.2f},{ey:.2f}"
            ang = math.atan2(ey - sy, ex - sx)
            lx, ly = (sx + ex) / 2, (sy + ey) / 2
        tip = (ex, ey)
    return d, tip, (lx, ly), ang


def head(tip, ang, size):
    x, y = tip
    p1 = (x - size * math.cos(ang - 0.42), y - size * math.sin(ang - 0.42))
    p2 = (x - size * math.cos(ang + 0.42), y - size * math.sin(ang + 0.42))
    return f"M{x:.2f},{y:.2f} L{p1[0]:.2f},{p1[1]:.2f} L{p2[0]:.2f},{p2[1]:.2f} Z"


# ---------------------------------------------------------------- external SVG
def embed_svg_file(path, x, y, w, h, prefix):
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"<\?xml[^>]*\?>", "", raw)
    raw = re.sub(r"<!DOCTYPE[^>]*>", "", raw, flags=re.S)
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    raw = re.sub(r"<script.*?</script>", "", raw, flags=re.S | re.I)  # never carry scripts in
    raw = re.sub(r"\son\w+=\"[^\"]*\"", "", raw)
    m = re.search(r"<svg\b([^>]*)>(.*)</svg>", raw, flags=re.S)
    if not m:
        raise ValueError(f"not an SVG: {path}")
    attrs, body = m.group(1), m.group(2)
    # editor metadata (Inkscape, Sodipodi, Affinity/Serif, Illustrator...) uses namespace prefixes declared on the
    # source <svg>; once embedded those declarations are gone and strict XML parsers reject the figure
    body = re.sub(r"<metadata\b.*?</metadata>", "", body, flags=re.S)
    body = re.sub(r"<(?!xlink:)(\w+):[\w.-]+\b[^>]*/>", "", body, flags=re.S)
    body = re.sub(r"<((?!xlink:)\w+:[\w.-]+)\b[^>]*>.*?</\1>", "", body, flags=re.S)
    body = re.sub(r'\s(?!xlink:|xml:)\w+:[\w.-]+\s*=\s*("[^"]*"|\'[^\']*\')', "", body)
    vb = re.search(r'viewBox=["\']([^"\']+)["\']', attrs)
    if vb:
        viewbox = vb.group(1)
    else:
        ww = re.search(r'width="([\d.]+)', attrs)
        hh = re.search(r'height="([\d.]+)', attrs)
        viewbox = f"0 0 {ww.group(1) if ww else 100} {hh.group(1) if hh else 100}"
    ids = set(re.findall(r'\bid="([^"]+)"', body))
    for i in ids:
        body = body.replace(f'id="{i}"', f'id="{prefix}-{i}"').replace(f"url(#{i})", f"url(#{prefix}-{i})") \
                   .replace(f'href="#{i}"', f'href="#{prefix}-{i}"')
    return (f'<svg x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" viewBox="{viewbox}" '
            f'preserveAspectRatio="xMidYMid meet">{body}</svg>')


def molecule_svg(smiles, x, y, w, h):
    try:
        from rdkit import Chem
        from rdkit.Chem.Draw import rdMolDraw2D
    except ImportError:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"RDKit could not parse SMILES: {smiles}")
    d = rdMolDraw2D.MolDraw2DSVG(int(w * 10), int(h * 10))
    o = d.drawOptions()
    o.clearBackground = False
    o.bondLineWidth = 2
    d.DrawMolecule(mol)
    d.FinishDrawing()
    s = d.GetDrawingText()
    s = re.sub(r"<\?xml[^>]*\?>", "", s)
    s = re.sub(r"<rect[^>]*style='opacity:1.0;fill:#FFFFFF[^>]*/>", "", s)
    body = re.search(r"<svg\b[^>]*>(.*)</svg>", s, flags=re.S).group(1)
    return (f'<svg x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" viewBox="0 0 {int(w * 10)} {int(h * 10)}">'
            f'{body}</svg>')


# ---------------------------------------------------------------- renderer
class Renderer:
    def __init__(self, spec, overrides=None, base_dir="."):
        self.spec = spec
        self.ov = overrides or {}
        self.base = Path(base_dir)
        c = spec.get("canvas", {})
        self.W = float(c.get("width_mm", 170))
        self.H = float(c.get("height_mm", 90))
        self.font = c.get("font", "Arial, Helvetica, sans-serif")
        self.fpt = float(c.get("font_pt", 7))
        self.bg = c.get("background", "#FFFFFF")
        self.stroke_mm = float(c.get("stroke_mm", 0.25))
        self.colors = dict(DEFAULT_ROLES)
        self.colors.update(spec.get("colors", {}))
        self.boxes = {}       # id -> (x, y, w, h) after overrides
        self.credits = []
        self.placeholders = []
        self.warnings = []

    # -- overrides ---------------------------------------------------------
    def apply_ov(self, el):
        o = self.ov.get(el.get("id"), {})
        el = dict(el)
        for k in ("color", "accent", "fill", "stroke", "font_pt", "label", "text", "title"):
            if k in o:
                el[k] = o[k]
        return el, o

    def txt_override(self, tid, default):
        o = self.ov.get(tid, {})
        return o.get("text", default), o

    def tx(self, o):
        dx, dy = float(o.get("dx", 0)), float(o.get("dy", 0))
        return f' transform="translate({dx:.2f},{dy:.2f})"' if (dx or dy) else "", dx, dy

    # -- labels ------------------------------------------------------------
    def label(self, tid, text, x, y, size=None, **kw):
        text, o = self.txt_override(tid, text)
        if o.get("hidden"):
            return ""
        size = float(o.get("font_pt", size or self.fpt))
        for ph in PLACEHOLDER_RE.findall(str(text)):
            self.placeholders.append((tid, ph))
        t, _ = text_el(tid, x, y, text, size, **kw)
        tr, _, _ = self.tx(o)
        return f'<g class="rv-label-wrap"{tr}>{t}</g>' if tr else t

    # -- element dispatch ---------------------------------------------------
    def render(self):
        added = [dict(e) for e in self.ov.get("__added__", [])]  # elements created in the editor
        for e in added:
            self.ov.setdefault(e["id"], {}).update({k: e[k] for k in ("dx", "dy") if k in e})
            if "text" in e:
                self.ov.setdefault(e["id"] + ".label", {}).setdefault("text", e["text"])
        els = self.expand(self.spec.get("elements", []) + added)
        # pass 1: compute boxes for all positioned elements (with overrides)
        for el in els:
            if el.get("type") in ("arrow",):
                continue
            if "x" in el and "y" in el:
                o = self.ov.get(el.get("id"), {})
                w = float(el.get("w", 0))
                square = el.get("type") in ("icon", "svgfile", "molecule")   # these default to h = w
                h = float(el.get("h", el.get("w", 0) if square else 0))
                self.boxes[el["id"]] = (float(el["x"]) + float(o.get("dx", 0)),
                                        float(el["y"]) + float(o.get("dy", 0)), w, h)
        out = []
        for el in els:
            fn = getattr(self, "r_" + el.get("type", ""), None)
            if fn is None:
                self.warnings.append(f"unknown element type: {el.get('type')} ({el.get('id')})")
                continue
            el2, o = self.apply_ov(el)
            if o.get("hidden"):
                continue
            out.append(fn(el2, o))
        return self.wrap_svg("".join(out), els)

    def expand(self, els):
        """Give every element an id and expand composite 'flow' elements."""
        out = []
        for i, el in enumerate(els):
            el = dict(el)
            el.setdefault("id", f"{el.get('type', 'el')}{i}")
            if el.get("type") == "flow":
                out.extend(self.expand_flow(el))
            else:
                out.append(el)
        ids = [e["id"] for e in out]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            self.warnings.append(f"duplicate ids: {sorted(dup)}")
        return out

    def expand_flow(self, f):
        steps = f.get("steps", [])
        n = max(1, len(steps))
        x, y, w, h = float(f["x"]), float(f["y"]), float(f["w"]), float(f["h"])
        slot = w / n
        size = float(f.get("icon_size", min(h * 0.62, slot * 0.6)))
        res = []
        for i, s in enumerate(steps):
            sid = s.get("id", f"{f['id']}.s{i}")
            cx = x + slot * (i + 0.5)
            res.append({**{k: v for k, v in s.items() if k != "id"}, "type": s.get("type", "icon"), "id": sid,
                        "x": cx - size / 2, "y": y + float(f.get("icon_top", 0)), "w": size, "h": size,
                        "label_width": s.get("label_width", slot * 0.95)})
        labels = f.get("arrows", [])
        for i in range(n - 1):
            a = steps[i].get("id", f"{f['id']}.s{i}")
            b = steps[i + 1].get("id", f"{f['id']}.s{i + 1}")
            lab = labels[i] if i < len(labels) else ""
            res.append({"type": "arrow", "id": f"{f['id']}.a{i}", "from": a, "to": b, "label": lab,
                        "label_width": slot * 0.8, "color": f.get("arrow_color")})
        return res

    # -- primitives ----------------------------------------------------------
    def r_panel(self, el, o):
        x, y, w, h = (float(el[k]) for k in ("x", "y", "w", "h"))
        tr, _, _ = self.tx(o)
        fill = color_of(self.colors, el.get("fill"), "#FFFFFF")
        stroke = color_of(self.colors, el.get("stroke"), "#BDBDBD")
        dash = ' stroke-dasharray="1.5 1"' if el.get("dashed") else ""
        parts = [f'<rect class="rv-fill" x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{float(el.get("radius", 2)):.2f}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{self.stroke_mm:.2f}"{dash}/>']
        if el.get("title"):
            tb = el.get("title_bar")
            if tb:
                parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{(self.fpt + 1.5) * PT * 1.9:.2f}" '
                             f'rx="{float(el.get("radius", 2)):.2f}" fill="{color_of(self.colors, tb, tb)}" stroke="none"/>')
            parts.append(self.label(el["id"] + ".title", el["title"], x + w / 2, y + 1.2,
                                    size=self.fpt + 1.5, weight="bold", width=w - 12))
        if el.get("letter"):
            parts.append(self.label(el["id"] + ".letter", el["letter"], x + 1.5, y + 1.2,
                                    size=self.fpt + 2, anchor="start", weight="bold"))
        return f'<g id="{esc(el["id"])}" class="rv-el" data-type="panel" data-box="{x} {y} {w} {h}"{tr}>{"".join(parts)}</g>'

    def r_box(self, el, o):
        x, y, w, h = (float(el[k]) for k in ("x", "y", "w", "h"))
        tr, _, _ = self.tx(o)
        fill = color_of(self.colors, el.get("fill") or el.get("color"), "#F2F2F2")
        stroke = color_of(self.colors, el.get("stroke"), "#333333")
        dash = ' stroke-dasharray="1.5 1"' if el.get("dashed") else ""
        body = (f'<rect class="rv-fill" x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{float(el.get("radius", 1.5)):.2f}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{self.stroke_mm:.2f}"{dash}/>')
        if el.get("text"):
            body += self.label(el["id"] + ".label", el["text"], x + w / 2, y + h / 2,
                               size=el.get("font_pt"), width=w - 2, valign="middle",
                               weight=el.get("weight", "normal"),
                               **({"color": color_of(self.colors, el["text_color"], "#222222")} if el.get("text_color") else {}))
        return f'<g id="{esc(el["id"])}" class="rv-el" data-type="box" data-box="{x} {y} {w} {h}"{tr}>{body}</g>'

    def _icon_label(self, el, x, y, w, h):
        if not el.get("label") or el.get("label_pos") == "none":
            return ""
        pos = el.get("label_pos", "below")
        lw = float(el.get("label_width", max(w * 1.6, 18)))
        if pos == "above":
            return self.label(el["id"] + ".label", el["label"], x + w / 2, y - 0.8, width=lw, valign="bottom")
        if pos == "right":
            return self.label(el["id"] + ".label", el["label"], x + w + 1.2, y + h / 2, width=lw, anchor="start", valign="middle")
        if pos == "left":
            return self.label(el["id"] + ".label", el["label"], x - 1.2, y + h / 2, width=lw, anchor="end", valign="middle")
        return self.label(el["id"] + ".label", el["label"], x + w / 2, y + h + 0.8, width=lw)

    def r_icon(self, el, o):
        x, y, w = float(el["x"]), float(el["y"]), float(el["w"])
        h = float(el.get("h", w))
        tr, _, _ = self.tx(o)
        name = el.get("icon", "placeholder")
        fn = ICONS.get(name)
        if fn is None:
            self.warnings.append(f"unknown icon '{name}' on {el['id']}; drew placeholder")
            fn = ICONS["placeholder"]
        stretch = name in STRETCH_ICONS
        s = w / 100 if stretch else min(w, h) / 100
        sw = self.stroke_mm / s
        ctx = IconCtx(fill=color_of(self.colors, el.get("color"), "#56B4E9"),
                      accent=color_of(self.colors, el.get("accent"), "#E69F00"),
                      stroke=color_of(self.colors, el.get("stroke"), "#333333"),
                      sw=sw * float(el.get("stroke_scale", 1.4)), params=el.get("params", {}), seed=el.get("seed", 1))
        if stretch:
            ctx.H = 100 * h / w          # stretchable icons draw into 100 x H units
            ox, oy = x, y
        else:
            ox, oy = x + (w - 100 * s) / 2, y + (h - 100 * s) / 2
        flip = ' scale(-1,1) translate(-100,0)' if el.get("flip") else ""
        art = f'<g class="rv-art" transform="translate({ox:.2f},{oy:.2f}) scale({s:.4f}){flip}">{fn(ctx)}</g>'
        return (f'<g id="{esc(el["id"])}" class="rv-el" data-type="icon" data-icon="{esc(name)}" data-box="{x} {y} {w} {h}"{tr}>'
                f'{art}{self._icon_label(el, x, y, w, h)}</g>')

    def r_svgfile(self, el, o):
        x, y, w = float(el["x"]), float(el["y"]), float(el["w"])
        h = float(el.get("h", w))
        tr, _, _ = self.tx(o)
        p = Path(el["path"])
        if not p.is_absolute():
            p = self.base / p
        art = embed_svg_file(p, x, y, w, h, prefix=re.sub(r"[^\w-]", "_", el["id"]))
        self.credits.append({"id": el["id"], "file": p.name, "license": el.get("license", "UNKNOWN - check"),
                             "author": el.get("author", ""), "source": el.get("source", "")})
        return (f'<g id="{esc(el["id"])}" class="rv-el" data-type="svgfile" data-box="{x} {y} {w} {h}"{tr}>'
                f'{art}{self._icon_label(el, x, y, w, h)}</g>')

    def r_image(self, el, o):
        """Raster image supplied by the user (their own micrograph/photo). Embedded, never altered."""
        x, y, w, h = (float(el[k]) for k in ("x", "y", "w", "h"))
        tr, _, _ = self.tx(o)
        p = Path(el["path"])
        if not p.is_absolute():
            p = self.base / p
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "tif": "image/tiff",
                "webp": "image/webp"}.get(p.suffix.lower().lstrip("."), "image/png")
        data = base64.b64encode(p.read_bytes()).decode()
        if el.get("license"):   # library art (e.g. Servier Medical Art) needs the credits line
            self.credits.append({"id": el["id"], "file": p.name, "license": el["license"], "author": el.get("author", ""),
                                 "source": el.get("source", "")})
        return (f'<g id="{esc(el["id"])}" class="rv-el" data-type="image" data-box="{x} {y} {w} {h}"{tr}>'
                f'<image x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" preserveAspectRatio="xMidYMid meet" '
                f'href="data:{mime};base64,{data}"/>{self._icon_label(el, x, y, w, h)}</g>')

    def r_inset(self, el, o):
        """Circular zoom-in: an image (often a 3D close-up render) clipped to a circle, with a ring, a title above and
        a dashed leader to the spot it magnifies. Keys: cx cy r path, title, color, to [x, y], zoom (image scale)."""
        cx, cy, r = float(el["cx"]), float(el["cy"]), float(el["r"])
        tr, _, _ = self.tx(o)
        col = color_of(self.colors, el.get("color"), "#2B7BB0")
        cid = "clip_" + re.sub(r"[^\w-]", "_", el["id"])
        p = Path(el["path"])
        if not p.is_absolute():
            p = self.base / p
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "svg": "image/svg+xml"}.get(
            p.suffix.lower().lstrip("."), "image/png")
        data = base64.b64encode(p.read_bytes()).decode()
        z = float(el.get("zoom", 1.0))
        s = 2 * r * z
        ox, oy = el.get("offset", [0, 0])
        if el.get("license"):
            self.credits.append({"id": el["id"], "file": p.name, "license": el["license"], "author": el.get("author", ""),
                                 "source": el.get("source", "")})
        parts = [f'<defs><clipPath id="{cid}"><circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}"/></clipPath></defs>']
        if el.get("to"):   # leader from the ring edge to the magnified spot
            tx, ty = el["to"]
            d = math.hypot(tx - cx, ty - cy) or 1
            sx, sy = cx + (tx - cx) / d * r, cy + (ty - cy) / d * r
            parts.append(f'<line x1="{sx:.2f}" y1="{sy:.2f}" x2="{tx:.2f}" y2="{ty:.2f}" stroke="{col}" '
                         f'stroke-width="{self.stroke_mm:.2f}" stroke-dasharray="1.2 0.9"/>'
                         f'<circle cx="{tx:.2f}" cy="{ty:.2f}" r="0.7" fill="{col}"/>')
        parts.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{color_of(self.colors, el.get("fill"), "#FFFFFF")}"/>'
                     f'<image x="{cx - s / 2 + ox:.2f}" y="{cy - s / 2 + oy:.2f}" width="{s:.2f}" height="{s:.2f}" '
                     f'preserveAspectRatio="xMidYMid slice" clip-path="url(#{cid})" href="data:{mime};base64,{data}"/>'
                     f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="none" stroke="{col}" stroke-width="{self.stroke_mm * 3:.2f}"/>')
        if el.get("title"):
            fpt = float(el.get("font_pt", self.fpt))
            for i, line in enumerate(str(el["title"]).split("\n")):
                parts.append(f'<text x="{cx:.2f}" y="{cy - r - 1.6 - (len(str(el["title"]).split(chr(10))) - 1 - i) * fpt * .42:.2f}" '
                             f'text-anchor="middle" font-size="{fpt * PT:.2f}" font-weight="bold" fill="{col}">{esc(line)}</text>')
        return (f'<g id="{esc(el["id"])}" class="rv-el" data-type="inset" data-box="{cx - r} {cy - r} {2 * r} {2 * r}"{tr}>'
                + "".join(parts) + "</g>")

    def r_molecule(self, el, o):
        x, y, w = float(el["x"]), float(el["y"]), float(el["w"])
        h = float(el.get("h", w))
        tr, _, _ = self.tx(o)
        art = molecule_svg(el["smiles"], x, y, w, h)
        if art is None:
            self.warnings.append(f"RDKit not installed: {el['id']} drawn as generic molecule icon")
            ctx = IconCtx(fill=color_of(self.colors, el.get("color"), "#999999"), sw=self.stroke_mm * 140 / w)
            art = f'<g transform="translate({x:.2f},{y:.2f}) scale({w / 100:.4f},{h / 100:.4f})">{ICONS["molecule_generic"](ctx)}</g>'
        return (f'<g id="{esc(el["id"])}" class="rv-el" data-type="molecule" data-smiles="{esc(el["smiles"])}" '
                f'data-box="{x} {y} {w} {h}"{tr}>{art}{self._icon_label(el, x, y, w, h)}</g>')

    def r_text(self, el, o):
        x, y = float(el["x"]), float(el["y"])
        tr, _, _ = self.tx(o)
        t = self.label(el["id"] + ".label", el.get("text", ""), x, y, size=el.get("font_pt"),
                       anchor=el.get("anchor", "start"), weight=el.get("weight", "normal"),
                       color=color_of(self.colors, el.get("color"), "#222222"), italic=el.get("italic", False),
                       width=el.get("w"), valign=el.get("valign", "top"))
        return f'<g id="{esc(el["id"])}" class="rv-el" data-type="text" data-box="{x} {y} 0 0"{tr}>{t}</g>'

    def r_placeholder(self, el, o):
        x, y, w, h = (float(el[k]) for k in ("x", "y", "w", "h"))
        tr, _, _ = self.tx(o)
        txt = el.get("text", "[? image from your data]")
        if not PLACEHOLDER_RE.search(txt):
            txt = f"[? {txt}]"
        ctx = IconCtx(sw=self.stroke_mm * 100 / w)
        ctx.H = 100 * h / w
        art = f'<g transform="translate({x:.2f},{y:.2f}) scale({w / 100:.4f})">{ICONS["placeholder"](ctx)}</g>'
        return (f'<g id="{esc(el["id"])}" class="rv-el" data-type="placeholder" data-box="{x} {y} {w} {h}"{tr}>{art}'
                f'{self.label(el["id"] + ".label", txt, x + w / 2, y + h / 2, width=w - 2, valign="middle")}</g>')

    def r_legend(self, el, o):
        x, y = float(el["x"]), float(el["y"])
        tr, _, _ = self.tx(o)
        size = self.fpt * PT
        gap = float(el.get("gap", size * 1.6))
        horiz = el.get("direction", "vertical") == "horizontal"
        parts, cx, cy = [], x, y
        for i, it in enumerate(el.get("items", [])):
            col = color_of(self.colors, it.get("color"), "#999999")
            shp = it.get("shape", "dot")
            if shp == "line":
                parts.append(f'<line x1="{cx:.2f}" y1="{cy + size / 2:.2f}" x2="{cx + size * 1.6:.2f}" y2="{cy + size / 2:.2f}" '
                             f'stroke="{col}" stroke-width="{self.stroke_mm * 2:.2f}"/>')
                tx0 = cx + size * 2.0
            elif shp == "square":
                parts.append(f'<rect class="rv-fill" x="{cx:.2f}" y="{cy:.2f}" width="{size:.2f}" height="{size:.2f}" fill="{col}" stroke="#333" stroke-width="{self.stroke_mm * 0.6:.2f}"/>')
                tx0 = cx + size * 1.5
            else:
                parts.append(f'<circle class="rv-fill" cx="{cx + size / 2:.2f}" cy="{cy + size / 2:.2f}" r="{size / 2:.2f}" fill="{col}" stroke="#333" stroke-width="{self.stroke_mm * 0.6:.2f}"/>')
                tx0 = cx + size * 1.5
            parts.append(self.label(f"{el['id']}.i{i}", it.get("label", ""), tx0, cy + size / 2, anchor="start", valign="middle"))
            if horiz:
                cx = tx0 + len(it.get("label", "")) * 0.55 * size + size * 2
            else:
                cy += gap
        return f'<g id="{esc(el["id"])}" class="rv-el" data-type="legend" data-box="{x} {y} 0 0"{tr}>{"".join(parts)}</g>'

    def _end_box(self, ref):
        if isinstance(ref, (list, tuple)):
            return (float(ref[0]), float(ref[1]), 0.0, 0.0)
        if ref not in self.boxes:
            raise KeyError(f"arrow endpoint '{ref}' not found")
        return self.boxes[ref]

    def r_arrow(self, el, o):
        a, b = self._end_box(el["from"]), self._end_box(el["to"])
        col = color_of(self.colors, el.get("color"), "#333333")
        sw = float(el.get("width_mm", self.stroke_mm * 1.6))
        d, tip, (lx, ly), ang = arrow_geometry(a, b, float(el.get("curve", 0)), el.get("route", "straight"),
                                               float(el.get("gap", 1.0)))
        dash = ' stroke-dasharray="1.2 0.8"' if el.get("style") == "dashed" else ""
        parts = [f'<path class="rv-line" d="{d}" fill="none" stroke="{col}" stroke-width="{sw:.2f}"{dash}/>',
                 f'<path class="rv-head" d="{head(tip, ang, sw * 4.2)}" fill="{col}" stroke="none"/>']
        if el.get("both"):
            d2, tip2, _, ang2 = arrow_geometry(b, a, -float(el.get("curve", 0)), el.get("route", "straight"),
                                               float(el.get("gap", 1.0)))
            parts.append(f'<path class="rv-head2" d="{head(tip2, ang2, sw * 4.2)}" fill="{col}" stroke="none"/>')
        if el.get("label"):
            side = -1 if el.get("label_side", "above") == "above" else 1
            # place text block above/below the midpoint
            offs = 1.0
            if side < 0:
                parts.append(self.label(el["id"] + ".label", el["label"], lx, ly - offs, width=el.get("label_width", 30),
                                        valign="bottom", size=el.get("font_pt", self.fpt - 0.5)))
            else:
                parts.append(self.label(el["id"] + ".label", el["label"], lx, ly + offs, width=el.get("label_width", 30),
                                        size=el.get("font_pt", self.fpt - 0.5)))
        fr = el["from"] if isinstance(el["from"], str) else ",".join(map(str, el["from"]))
        to = el["to"] if isinstance(el["to"], str) else ",".join(map(str, el["to"]))
        return (f'<g id="{esc(el["id"])}" class="rv-el rv-arrow" data-type="arrow" data-from="{esc(fr)}" data-to="{esc(to)}" '
                f'data-curve="{el.get("curve", 0)}" data-route="{el.get("route", "straight")}" data-gap="{el.get("gap", 1.0)}" '
                f'data-sw="{sw}" data-both="{1 if el.get("both") else 0}" data-label-side="{el.get("label_side", "above")}">'
                f'{"".join(parts)}</g>')

    def r_bracket(self, el, o):
        """Curly-ish bracket grouping a span; x1,y1 -> x2,y2 with label."""
        x1, y1, x2, y2 = (float(el[k]) for k in ("x1", "y1", "x2", "y2"))
        tr, _, _ = self.tx(o)
        col = color_of(self.colors, el.get("color"), "#333333")
        tick = float(el.get("tick", 1.5))
        if abs(y2 - y1) < abs(x2 - x1):  # horizontal bracket under/over something
            d = f"M{x1:.2f},{y1 - tick:.2f} L{x1:.2f},{y1:.2f} L{x2:.2f},{y2:.2f} L{x2:.2f},{y2 - tick:.2f}"
            lab = self.label(el["id"] + ".label", el.get("label", ""), (x1 + x2) / 2, y1 + 0.8, width=abs(x2 - x1))
        else:
            d = f"M{x1 - tick:.2f},{y1:.2f} L{x1:.2f},{y1:.2f} L{x2:.2f},{y2:.2f} L{x2 - tick:.2f},{y2:.2f}"
            lab = self.label(el["id"] + ".label", el.get("label", ""), x1 + 1.2, (y1 + y2) / 2, anchor="start", valign="middle", width=30)
        return (f'<g id="{esc(el["id"])}" class="rv-el" data-type="bracket" data-box="{min(x1, x2)} {min(y1, y2)} 0 0"{tr}>'
                f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{self.stroke_mm * 1.2:.2f}"/>{lab}</g>')

    # -- document ------------------------------------------------------------
    def wrap_svg(self, body, els):
        meta = {"spec": self.spec, "overrides": self.ov, "credits": self.credits,
                "generator": "scientific-illustration/render_figure.py"}
        meta_json = json.dumps(meta, ensure_ascii=False).replace("--", "-\\u002d")
        credits = ""
        if self.spec.get("show_credits", True) and any(c["license"].lower().startswith("cc-by") for c in self.credits):
            seen = dict.fromkeys(f"{c['author'] or c['file']} ({c['license'].upper().replace('CC-BY-', 'CC BY ')})"
                                 for c in self.credits if c["license"].lower().startswith("cc-by"))
            txt = "Art: " + "; ".join(seen)
            credits = text_el("rv-credits", self.W - 1, self.H - 1.2, txt, max(5, self.fpt - 2), anchor="end",
                              color="#777777", valign="bottom")[0]
        return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'width="{self.W}mm" height="{self.H}mm" viewBox="0 0 {self.W} {self.H}" '
                f'font-family="{esc(self.font)}">\n'
                f'<metadata id="rv-data"><![CDATA[{meta_json}]]></metadata>\n'
                f'<rect id="rv-bg" x="0" y="0" width="{self.W}" height="{self.H}" fill="{self.bg}"/>\n'
                f'{body}\n{credits}\n</svg>\n')


def read_overrides_from_svg(path):
    raw = Path(path).read_text(encoding="utf-8")
    m = re.search(r'<metadata id="rv-data"><!\[CDATA\[(.*?)\]\]></metadata>', raw, flags=re.S)
    if not m:
        return {}
    return json.loads(m.group(1)).get("overrides", {})


def spec_from_svg(path):
    raw = Path(path).read_text(encoding="utf-8")
    m = re.search(r'<metadata id="rv-data"><!\[CDATA\[(.*?)\]\]></metadata>', raw, flags=re.S)
    return json.loads(m.group(1))["spec"] if m else None


def write_editor(svg_text, svg_path):
    tpl = (HERE / "editor.html").read_text(encoding="utf-8")
    payload = json.dumps({"svg": svg_text, "name": Path(svg_path).stem})
    out = tpl.replace("/*__RV_PAYLOAD__*/null", payload.replace("</", "<\\/"))
    ep = Path(svg_path).with_suffix(".editor.html")
    ep.write_text(out, encoding="utf-8")
    return ep


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", nargs="?", help="figure spec .json (or an SVG made by this script)")
    ap.add_argument("-o", "--out", help="output .svg path")
    ap.add_argument("--keep-edits", help="SVG previously saved from the editor; its manual edits are re-applied")
    ap.add_argument("--overrides", help="JSON file of edits {id: {dx, dy, text, color, fill, hidden, font_pt}}")
    ap.add_argument("--no-editor", action="store_true", help="do not write the .editor.html companion")
    ap.add_argument("--list-icons", action="store_true")
    a = ap.parse_args()

    if a.list_icons:
        for k in sorted(ICONS):
            print(f"{k:22s} {ICON_HELP.get(k, '')}")
        return
    if not a.spec or not a.out:
        ap.error("spec and -o are required")
    sp = Path(a.spec)
    spec = spec_from_svg(sp) if sp.suffix.lower() == ".svg" else json.loads(sp.read_text(encoding="utf-8"))
    ov = {}
    if a.keep_edits and Path(a.keep_edits).exists():
        ov.update(read_overrides_from_svg(a.keep_edits))
    if a.overrides:
        ov.update(json.loads(Path(a.overrides).read_text(encoding="utf-8")))
    r = Renderer(copy.deepcopy(spec), ov, base_dir=sp.parent)
    svg = r.render()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"SVG: {out.resolve()}  ({r.W} x {r.H} mm)")
    if not a.no_editor:
        print(f"Editor: {write_editor(svg, out).resolve()}")
    if ov:
        print(f"Re-applied {len(ov)} manual edit(s).")
    if r.placeholders:
        print(f"PLACEHOLDERS ({len(r.placeholders)}) - values the user must supply:")
        for tid, ph in r.placeholders:
            print(f"  {tid}: {ph}")
    for c in r.credits:
        print(f"CREDIT {c['id']}: {c['file']} | {c['license']} | {c['author']} | {c['source']}")
    for w in r.warnings:
        print("WARNING:", w)


if __name__ == "__main__":
    main()
