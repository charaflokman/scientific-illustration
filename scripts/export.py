#!/usr/bin/env python3
"""Export an SVG to PNG and/or PDF at journal size, and check its layout.

Rendering uses a real browser (Playwright driving the installed Chrome/Edge, or
Playwright's own Chromium), so fonts and text match what the editor shows.

  python export.py figure.svg --png 600 --pdf          # writes figure.png / figure.pdf
  python export.py figure.svg --check                  # layout report only

The check reports: text smaller than --min-pt at final size, text boxes that
overlap each other, anything that sticks out of the canvas, and [? ...]
placeholders still present. Exit code 2 when problems are found with --strict.
"""
import argparse
import json
import re
import sys
from pathlib import Path

CHECK_JS = r"""
([minPt, wmm]) => {
  const PT = 0.3528, svg = document.querySelector('svg');
  const vb = svg.viewBox.baseVal, r0 = svg.getBoundingClientRect(), k = wmm / r0.width; // mm of the final figure per screen px
  const W = wmm, H = vb.height * wmm / vb.width;
  const issues = [], boxes = [];
  const vis = el => { for (let e = el; e && e !== svg; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return false; } return true; };
  for (const t of svg.querySelectorAll('text')) {
    if (!vis(t) || !t.textContent.trim()) continue;
    const r = t.getBoundingClientRect();
    const fs = parseFloat(t.getAttribute('font-size') || getComputedStyle(t).fontSize) ;
    // getScreenCTM maps the text's user units to screen px; k converts px to mm of the final figure
    const m = t.getScreenCTM(); const pt = fs * Math.hypot(m.a, m.b) * k / PT;
    if (pt < minPt - 0.05) issues.push({kind: 'small-text', id: t.id || '', text: t.textContent.slice(0, 40), pt: +pt.toFixed(1)});
    const txt = t.textContent.replace(/\s+/g, ' ').trim(); const b = {id: t.id || txt.slice(0, 20), x: (r.left - r0.left) * k, y: (r.top - r0.top) * k, w: r.width * k, h: r.height * k, text: txt.slice(0, 40)};
    // trim the line-height padding above/below glyphs so tightly set rows (ticks vs axis title) do not "overlap"
    boxes.push({...b, y: b.y + b.h * 0.18, h: b.h * 0.64});
    if (b.x < -0.2 || b.y < -0.2 || b.x + b.w > W + 0.2 || b.y + b.h > H + 0.2)
      issues.push({kind: 'outside-canvas', id: b.id, text: b.text});
    const ph = t.textContent.match(/\[\?[^\]]*\]/g); if (ph) issues.push({kind: 'placeholder', id: b.id, text: ph.join(' ')});
  }
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
    const a = boxes[i], b = boxes[j];
    const ox = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x), oy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
    // a box mostly inside another is a sub-part (matplotlib mathtext superscripts, multi-tspan labels), not a clash
    const small = Math.min(a.w * a.h, b.w * b.h), inter = Math.max(0, ox) * Math.max(0, oy);
    if (small > 0 && inter / small > 0.6 && (a.text.trim().length <= 3 || b.text.trim().length <= 3)) continue;
    // glyph boxes include ascent/descent padding, so require a real share of the smaller box to overlap
    if (ox > 0.3 && oy > 0.3 && inter / small > 0.15) issues.push({kind: 'text-overlap', id: a.id + ' x ' + b.id, text: a.text + ' | ' + b.text});
  }
  for (const g of svg.querySelectorAll('.rv-el')) {
    if (!vis(g)) continue; const r = g.getBoundingClientRect();
    const x = (r.left - r0.left) * k, y = (r.top - r0.top) * k, w = r.width * k, h = r.height * k;
    if (x < -0.5 || y < -0.5 || x + w > W + 0.5 || y + h > H + 0.5) issues.push({kind: 'element-outside-canvas', id: g.id});
  }
  return {width_mm: W, height_mm: H, texts: boxes.length, issues};
}
"""


def launch(p):
    for kw in ({"channel": "chrome"}, {"channel": "msedge"}, {}):
        try:
            return p.chromium.launch(**kw)
        except Exception:
            continue
    raise SystemExit("No browser found. Install Chrome, or run: python -m playwright install chromium")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("svg")
    ap.add_argument("--png", type=int, metavar="DPI", help="write PNG at this dpi (300 for review, 600 for line art)")
    ap.add_argument("--pdf", action="store_true", help="write vector PDF at exact size")
    ap.add_argument("--check", action="store_true", help="print layout report")
    ap.add_argument("--min-pt", type=float, default=5.0, help="smallest allowed text at final size (default 5 pt)")
    ap.add_argument("--strict", action="store_true", help="exit 2 if the check finds issues")
    ap.add_argument("--outdir", help="where to write exports (default: next to the SVG)")
    a = ap.parse_args()

    from playwright.sync_api import sync_playwright

    src = Path(a.svg).resolve()
    raw = src.read_text(encoding="utf-8")
    m = re.search(r'viewBox="([\d.\s-]+)"', raw)
    if not m:
        raise SystemExit("SVG has no viewBox")
    _, _, vw, vh = (float(v) for v in m.group(1).split())
    # physical width from the width attribute (matplotlib writes pt, render_figure mm, mermaid/d2 px);
    # with no width at all, render_figure-style files use mm user units, anything else CSS px
    MM_PER = {"mm": 1.0, "cm": 10.0, "in": 25.4, "pt": 25.4 / 72, "px": 25.4 / 96, "": 25.4 / 96}
    wm = re.search(r'<svg[^>]*\swidth="([\d.]+)(mm|cm|px|in|pt)?"', raw)
    if wm:
        w_mm = float(wm.group(1)) * MM_PER[wm.group(2) or ""]
    else:
        w_mm = vw if 'id="rv-data"' in raw else vw * 25.4 / 96
    h_mm = w_mm * vh / vw
    outdir = Path(a.outdir) if a.outdir else src.parent
    outdir.mkdir(parents=True, exist_ok=True)
    body = re.sub(r"<\?xml[^>]*\?>", "", raw)
    page_html = ("<!doctype html><html><head><meta charset='utf-8'><style>html,body{margin:0;padding:0;background:#fff}"
                 f"svg{{display:block;width:{w_mm}mm;height:{h_mm}mm}}</style></head><body>{body}</body></html>")
    with sync_playwright() as p:
        br = launch(p)
        if a.check or not (a.png or a.pdf):
            pg = br.new_page(viewport={"width": 1600, "height": 1200})
            pg.set_content(page_html)
            rep = pg.evaluate(CHECK_JS, [a.min_pt, w_mm])
            kinds = {}
            for i in rep["issues"]:
                kinds[i["kind"]] = kinds.get(i["kind"], 0) + 1
            print(f"CHECK {src.name}: {rep['width_mm']:.0f} x {rep['height_mm']:.0f} mm, {rep['texts']} text items, "
                  f"issues: {json.dumps(kinds) if kinds else 'none'}")
            for i in rep["issues"]:
                print(f"  - {i['kind']}: {i.get('id', '')} {i.get('text', '')} {('(' + str(i['pt']) + ' pt)') if 'pt' in i else ''}")
            pg.close()
            if a.strict and rep["issues"]:
                br.close()
                sys.exit(2)
        if a.png:
            scale = a.png / 96.0
            pg = br.new_page(viewport={"width": int(w_mm / 25.4 * 96) + 1, "height": int(h_mm / 25.4 * 96) + 1},
                             device_scale_factor=scale)
            pg.set_content(page_html)
            out = outdir / f"{src.stem}.png"
            pg.locator("svg").first.screenshot(path=str(out), omit_background=False)
            print(f"PNG: {out}  ({a.png} dpi)")
            pg.close()
        if a.pdf:
            pg = br.new_page()
            pg.set_content(page_html)
            out = outdir / f"{src.stem}.pdf"
            pg.pdf(path=str(out), width=f"{w_mm}mm", height=f"{h_mm + 0.01}mm", print_background=True,
                   margin={"top": "0", "bottom": "0", "left": "0", "right": "0"}, page_ranges="1")
            print(f"PDF: {out}")
            pg.close()
        br.close()


if __name__ == "__main__":
    main()
