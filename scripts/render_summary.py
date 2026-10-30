#!/usr/bin/env python3
"""Turn a lesson / lecture / paper summary (JSON) into an attractive one-page visual summary.

Output is one self-contained HTML page (editable in place: click any text) plus, with --png/--pdf,
an A4/16:9 export through the same browser engine as export.py.

  python render_summary.py lesson.json -o out/lesson.html --png --pdf

Spec:
{
 "title": "Fick's laws of diffusion", "subtitle": "Lecture 4 · Transport in polymers",
 "format": "a4|slide", "accent": "#0072B2", "lang": "en|ar",
 "sections": [
   {"icon": "💧", "title": "Key idea", "points": ["...", "..."]},
   {"icon": "∑", "title": "Equations", "formulas": ["J = -D ∂C/∂x", "∂C/∂t = D ∂²C/∂x²"]},
   {"icon": "🔁", "title": "Steps", "steps": ["...", "..."]},
   {"icon": "⚖️", "title": "Compare", "table": [["", "Fickian", "Case II"], ["n", "0.5", "1.0"]]},
   {"icon": "🧠", "title": "Concept map", "map": {"center": "Diffusion", "nodes": ["Concentration gradient", "D", "Temperature"]}},
   {"icon": "⚠️", "title": "Common mistakes", "points": ["..."], "tone": "warn"}
 ],
 "takeaway": "One sentence the student must remember.",
 "source": "Crank, The Mathematics of Diffusion (1975), ch. 4"
}
Write only what the lesson says; unknown values go in as [? ...] and render red.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00"]

CSS = """
*{box-sizing:border-box}body{margin:0;background:#eef1f5;font-family:'Inter','Segoe UI',system-ui,Arial,sans-serif;color:#1d2330}
.page{margin:24px auto;background:#fff;box-shadow:0 6px 30px #0002;border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.a4{width:210mm;min-height:297mm}.slide{width:338.67mm;height:190.5mm}
header{padding:16px 22px;background:linear-gradient(120deg,var(--a),color-mix(in srgb,var(--a) 55%,#000));color:#fff}
header h1{margin:0;font-size:24pt;letter-spacing:-.3px}header p{margin:4px 0 0;opacity:.85;font-size:11pt}
.grid{flex:1;display:grid;gap:12px;padding:16px;grid-template-columns:repeat(var(--cols),1fr);align-content:start}
.card{border-radius:12px;padding:10px 12px;background:color-mix(in srgb,var(--c) 7%,#fff);border:1.5px solid color-mix(in srgb,var(--c) 35%,#fff);break-inside:avoid}
.card h2{display:flex;align-items:center;gap:8px;margin:0 0 6px;font-size:12.5pt;color:color-mix(in srgb,var(--c) 75%,#000)}
.ic{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:var(--c);color:#fff;font-size:14px;flex:none}
.num{font-weight:800;font-size:11pt;opacity:.5;margin-left:auto}
ul{margin:0;padding-left:18px}li{margin:3px 0;font-size:10pt;line-height:1.35}
.f{font-family:'Cambria Math','STIX Two Math',Cambria,serif;font-size:12pt;background:#fff;border-radius:8px;padding:6px 10px;margin:5px 0;text-align:center;border:1px dashed color-mix(in srgb,var(--c) 40%,#fff)}
ol.steps{list-style:none;padding:0;counter-reset:s}ol.steps li{counter-increment:s;position:relative;padding:4px 0 4px 30px}
ol.steps li:before{content:counter(s);position:absolute;left:0;top:3px;width:21px;height:21px;border-radius:50%;background:var(--c);color:#fff;font-size:9pt;display:grid;place-items:center;font-weight:700}
ol.steps li:not(:last-child):after{content:'';position:absolute;left:10px;top:24px;bottom:-6px;border-left:2px solid color-mix(in srgb,var(--c) 40%,#fff)}
table{border-collapse:collapse;width:100%;font-size:9.5pt}td,th{padding:4px 6px;border-bottom:1px solid #0001;text-align:left}th{color:color-mix(in srgb,var(--c) 75%,#000)}
.warn{--c:#D55E00}.wide{grid-column:1/-1}
svg.map{display:block;max-width:115mm;margin:0 auto}svg.map text{font-size:9.5pt;font-family:inherit}
.take{margin:0 16px 12px;padding:12px 16px;border-radius:12px;background:var(--a);color:#fff;font-size:12pt;font-weight:600;display:flex;gap:10px;align-items:center}
footer{padding:6px 18px 12px;font-size:8pt;color:#667}
.ph{color:#c00;font-weight:700}
[contenteditable]:hover{outline:1px dashed #0072B288}
.bar{position:fixed;top:8px;right:8px;display:flex;gap:6px}.bar button{padding:6px 10px;border-radius:8px;border:1px solid #ccd;background:#fff;cursor:pointer}
@media print{body{background:#fff}.page{margin:0;box-shadow:none;border-radius:0}.bar{display:none}}
"""


def t(s):
    s = html.escape(str(s))
    return re.sub(r"\[\?[^\]]*\]", lambda m: f'<span class="ph">{m.group(0)}</span>', s)


def concept_map(m, c):
    nodes = m.get("nodes", [])
    W, H, cx, cy = 300, 170, 150, 85
    import math
    out = [f'<svg class="map" viewBox="0 0 {W} {H}" width="100%">']
    pos = []
    for i, n in enumerate(nodes):
        a = -math.pi / 2 + 2 * math.pi * i / max(1, len(nodes))
        pos.append((cx + 115 * math.cos(a), cy + 62 * math.sin(a), n))
    for x, y, _ in pos:
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{c}" stroke-opacity=".45" stroke-width="1.5"/>')
    out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="48" ry="17" fill="{c}"/><text x="{cx}" y="{cy + 4}" text-anchor="middle" fill="#fff" font-weight="700">{t(m.get("center", ""))}</text>')
    for x, y, n in pos:
        w = min(110, 12 + 6.2 * len(str(n)))
        out.append(f'<rect x="{x - w / 2:.1f}" y="{y - 11:.1f}" width="{w:.1f}" height="22" rx="11" fill="#fff" stroke="{c}"/>'
                   f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle">{t(n)}</text>')
    return "".join(out) + "</svg>"


def section(i, s, accent_cycle):
    c = "#D55E00" if s.get("tone") == "warn" else s.get("color") or accent_cycle[i % len(accent_cycle)]
    body = []
    if s.get("points"):
        body.append("<ul>" + "".join(f"<li>{t(p)}</li>" for p in s["points"]) + "</ul>")
    for f in s.get("formulas", []):
        body.append(f'<div class="f">{t(f)}</div>')
    if s.get("steps"):
        body.append('<ol class="steps">' + "".join(f"<li>{t(p)}</li>" for p in s["steps"]) + "</ol>")
    if s.get("table"):
        rows = s["table"]
        body.append("<table><tr>" + "".join(f"<th>{t(h)}</th>" for h in rows[0]) + "</tr>"
                    + "".join("<tr>" + "".join(f"<td>{t(v)}</td>" for v in r) + "</tr>" for r in rows[1:]) + "</table>")
    if s.get("map"):
        body.append(concept_map(s["map"], c))
    wide = " wide" if s.get("wide") or s.get("map") and len(s["map"].get("nodes", [])) > 6 else ""
    return (f'<section class="card{wide}" style="--c:{c}"><h2><span class="ic">{t(s.get("icon", "•"))}</span>'
            f'<span>{t(s.get("title", ""))}</span><span class="num">{i + 1:02d}</span></h2>{"".join(body)}</section>')


def build(spec):
    fmt = spec.get("format", "a4")
    a = spec.get("accent", PALETTE[0])
    cyc = [a] + [p for p in PALETTE if p != a]
    n = len(spec.get("sections", []))
    cols = spec.get("columns") or (3 if fmt == "slide" else 2 if n > 2 else 1)
    rtl = ' dir="rtl"' if spec.get("lang") == "ar" else ""
    cards = "".join(section(i, s, cyc) for i, s in enumerate(spec.get("sections", [])))
    take = f'<div class="take"><span>★</span><span>{t(spec["takeaway"])}</span></div>' if spec.get("takeaway") else ""
    foot = f"<footer>Source: {t(spec['source'])}</footer>" if spec.get("source") else ""
    return (f'<!doctype html><html{rtl}><head><meta charset="utf-8"><title>{t(spec.get("title", "Summary"))}</title>'
            f'<style>{CSS}</style></head><body style="--a:{a}">'
            '<div class="bar"><button onclick="document.body.contentEditable=document.body.isContentEditable?\'false\':\'true\';this.textContent=document.body.isContentEditable?\'Done editing\':\'Edit text\'">Edit text</button>'
            '<button onclick="const b=document.querySelector(\'.bar\');b.remove();const a=document.createElement(\'a\');a.download=document.title+\'.html\';a.href=URL.createObjectURL(new Blob([\'<!doctype html>\'+document.documentElement.outerHTML],{type:\'text/html\'}));a.click();document.body.prepend(b)">Save HTML</button>'
            '<button onclick="print()">PDF</button></div>'
            f'<div class="page {fmt}"><header><h1>{t(spec.get("title", ""))}</h1>'
            f'{"<p>" + t(spec["subtitle"]) + "</p>" if spec.get("subtitle") else ""}</header>'
            f'<div class="grid" style="--cols:{cols}">{cards}</div>{take}{foot}</div></body></html>')


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("-o", "--out")
    ap.add_argument("--png", action="store_true", help="also write PNG (2x)")
    ap.add_argument("--pdf", action="store_true")
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    out = Path(a.out or Path(a.spec).with_suffix(".html"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(spec), encoding="utf-8")
    print(f"summary: {out.resolve()}")
    if a.png or a.pdf:
        from playwright.sync_api import sync_playwright
        from export import launch
        with sync_playwright() as p:
            br = launch(p)
            pg = br.new_page(viewport={"width": 1400, "height": 1000}, device_scale_factor=2)
            pg.goto(out.resolve().as_uri())
            pg.evaluate("document.querySelector('.bar').remove()")
            if a.png:
                pg.locator(".page").screenshot(path=str(out.with_suffix(".png")))
                print(f"PNG: {out.with_suffix('.png').resolve()}")
            if a.pdf:
                box = pg.locator(".page").bounding_box()
                pg.add_style_tag(content="body{background:#fff}.page{margin:0}")
                pg.pdf(path=str(out.with_suffix(".pdf")), width=f"{box['width']}px", height=f"{pg.locator('.page').bounding_box()['height'] + 2}px",
                       print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
                print(f"PDF: {out.with_suffix('.pdf').resolve()}")
            br.close()


if __name__ == "__main__":
    main()
