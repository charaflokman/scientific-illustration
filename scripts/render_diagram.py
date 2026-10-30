#!/usr/bin/env python3
"""Render a Mermaid / D2 / Graphviz diagram to SVG locally (optional PNG/PDF).

  python render_diagram.py flow.mmd                      # -> flow.svg
  python render_diagram.py flow.d2 -o out/flow.svg --png 600 --pdf
  python render_diagram.py model.dot --theme plain
  python render_diagram.py flow.mmd --width-mm 170 --check
  python render_diagram.py --classdefs                   # print recommended classDef / class lines

Everything runs on this machine: mmdc (mermaid-cli, headless Chrome), d2, dot.
Nothing is sent to an online renderer (no Kroki, no mermaid.ink).

Tool lookup order
  Mermaid : --mmdc, $RV_MMDC, mmdc on PATH, then `npx -y @mermaid-js/mermaid-cli`
            (npx downloads the CLI from npm once; the diagram text never leaves the machine)
  D2      : --d2, $RV_D2, d2 on PATH
  Graphviz: --dot, $RV_DOT, dot on PATH  (install: winget install Graphviz.Graphviz)
  Browser : --browser, $RV_BROWSER, $PUPPETEER_EXECUTABLE_PATH, installed Chrome/Edge/Chromium.
            A puppeteer config pointing to it is written automatically, so puppeteer's own
            Chromium download is not needed.
PNG/PDF are made by export.py (same folder) with $RV_PYTHON or this Python (needs playwright).

Theme "research" (default): Arial/Helvetica, neutral greys, Okabe-Ito accents available as
classes, real <text> labels (Mermaid htmlLabels=false) so text stays editable in
Inkscape / PowerPoint. "plain" keeps the tool's colours but still forces editable text.
"none" passes nothing.

Exit codes: 0 ok, 1 syntax/render error (message printed with line numbers), 3 tool missing.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT_STACK = "Arial, Helvetica, sans-serif"

# Okabe-Ito accents (colour-blind safe) and light tints used as fills behind dark text
OKABE = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73", "vermillion": "#D55E00",
         "purple": "#CC79A7", "sky": "#56B4E9"}
TINT = {"blue": "#DCEBF7", "orange": "#FBEBD0", "green": "#D5EFE6", "vermillion": "#F8DFD2",
        "purple": "#F5E3EE", "sky": "#E1F1FB"}
INK, GREY, LINE, FILL, PAPER = "#1A1A1A", "#4D4D4D", "#BDBDBD", "#F5F5F5", "#FFFFFF"

MERMAID_RESEARCH = {
    "theme": "base",
    "look": "classic",
    "htmlLabels": False,
    "markdownAutoWrap": False,
    "fontFamily": FONT_STACK,
    # edge labels: opaque white box (Mermaid default is 50% opacity, so the arrow shows through the text)
    "themeCSS": ".edgeLabel rect{opacity:1 !important;fill:#FFFFFF !important}"
                ".edgeLabel text{font-size:14px}",
    "themeVariables": {
        "fontFamily": FONT_STACK, "fontSize": "16px",
        "background": PAPER, "primaryColor": FILL, "primaryTextColor": INK, "primaryBorderColor": GREY,
        "secondaryColor": TINT["blue"], "secondaryTextColor": INK, "secondaryBorderColor": OKABE["blue"],
        "tertiaryColor": PAPER, "tertiaryTextColor": INK, "tertiaryBorderColor": LINE,
        "lineColor": GREY, "textColor": INK, "titleColor": INK, "edgeLabelBackground": PAPER,
        "clusterBkg": "#FAFAFA", "clusterBorder": LINE, "nodeTextColor": INK,
        "noteBkgColor": TINT["orange"], "noteTextColor": INK, "noteBorderColor": OKABE["orange"],
        "actorBkg": FILL, "actorBorder": GREY, "actorTextColor": INK, "actorLineColor": GREY,
        "signalColor": GREY, "signalTextColor": INK, "labelBoxBkgColor": FILL, "labelBoxBorderColor": GREY,
        "labelTextColor": INK, "loopTextColor": INK, "activationBkgColor": TINT["blue"],
        "activationBorderColor": OKABE["blue"], "sequenceNumberColor": PAPER,
        # gantt
        "taskBkgColor": TINT["blue"], "taskBorderColor": OKABE["blue"], "taskTextColor": INK,
        "taskTextOutsideColor": INK, "taskTextLightColor": INK, "taskTextDarkColor": INK,
        "activeTaskBkgColor": TINT["orange"], "activeTaskBorderColor": OKABE["orange"],
        "doneTaskBkgColor": "#E0E0E0", "doneTaskBorderColor": GREY, "critBkgColor": TINT["vermillion"],
        "critBorderColor": OKABE["vermillion"], "gridColor": "#E0E0E0", "todayLineColor": OKABE["vermillion"],
        "sectionBkgColor": "#FAFAFA", "altSectionBkgColor": PAPER, "sectionBkgColor2": "#F0F0F0",
        # timeline / mindmap / journey colour scale: light tints, dark labels
        **{f"cScale{i}": c for i, c in enumerate(
            [TINT["blue"], TINT["orange"], TINT["green"], TINT["vermillion"], TINT["purple"], TINT["sky"],
             "#EEEEEE", TINT["blue"], TINT["orange"], TINT["green"], TINT["vermillion"], TINT["purple"]])},
        **{f"cScaleLabel{i}": INK for i in range(12)},
        **{f"cScalePeer{i}": GREY for i in range(12)},
        # pie / xychart
        **{f"pie{i + 1}": c for i, c in enumerate(list(OKABE.values()) + ["#999999"])},
        "pieStrokeColor": PAPER, "pieOuterStrokeColor": GREY,
    },
    "flowchart": {"htmlLabels": False, "curve": "basis", "padding": 12, "nodeSpacing": 40,
                  "rankSpacing": 45, "wrappingWidth": 480, "useMaxWidth": False},
    "sequence": {"useMaxWidth": False, "mirrorActors": False},
    "gantt": {"useMaxWidth": False},
    "timeline": {"useMaxWidth": False},
    "mindmap": {"useMaxWidth": False},
    "class": {"htmlLabels": False}, "state": {"htmlLabels": False},
}
MERMAID_PLAIN = {"htmlLabels": False, "flowchart": {"htmlLabels": False, "useMaxWidth": False},
                 "class": {"htmlLabels": False}, "fontFamily": FONT_STACK,
                 "themeVariables": {"fontFamily": FONT_STACK}}

MERMAID_CLASSDEFS = f"""%% research theme classes (paste after the diagram body; use  A:::material  or  class A,B step)
classDef material fill:{TINT['blue']},stroke:{OKABE['blue']},stroke-width:1.5px,color:{INK}
classDef step fill:{FILL},stroke:{GREY},stroke-width:1px,color:{INK}
classDef condition fill:{TINT['orange']},stroke:{OKABE['orange']},stroke-width:1.5px,color:{INK}
classDef output fill:{TINT['green']},stroke:{OKABE['green']},stroke-width:1.5px,color:{INK}
classDef excluded fill:{TINT['vermillion']},stroke:{OKABE['vermillion']},stroke-width:1px,color:{INK}
classDef note fill:{PAPER},stroke:{LINE},stroke-dasharray:4 3,color:{GREY}
classDef missing fill:{PAPER},stroke:{OKABE['vermillion']},stroke-width:1.5px,stroke-dasharray:5 3,color:{OKABE['vermillion']}
classDef header fill:{GREY},stroke:{GREY},color:{PAPER},font-weight:bold"""

# D2: theme 0 (Neutral Default) re-coloured to neutral greys; extra colours via classes
D2_THEME_ID = 0
D2_OVERRIDES = {"N1": INK, "N2": GREY, "N3": "#757575", "N4": "#9E9E9E", "N5": LINE, "N6": "#EEEEEE",
                "N7": PAPER, "B1": GREY, "B2": GREY, "B3": "#9E9E9E", "B4": "#EBEBEB", "B5": "#F2F2F2",
                "B6": FILL, "AA2": OKABE["blue"], "AA4": TINT["blue"], "AA5": "#EEF5FB",
                "AB4": TINT["orange"], "AB5": "#FDF5E7"}
D2_CLASSES = f"""# research theme classes (use  a.class: material  or  a: {{class: [material]}})
classes: {{
  material:  {{style: {{fill: "{TINT['blue']}"; stroke: "{OKABE['blue']}"; stroke-width: 2; font-color: "{INK}"}}}}
  step:      {{style: {{fill: "{FILL}"; stroke: "{GREY}"; font-color: "{INK}"}}}}
  condition: {{style: {{fill: "{TINT['orange']}"; stroke: "{OKABE['orange']}"; stroke-width: 2; font-color: "{INK}"}}}}
  output:    {{style: {{fill: "{TINT['green']}"; stroke: "{OKABE['green']}"; stroke-width: 2; font-color: "{INK}"}}}}
  excluded:  {{style: {{fill: "{TINT['vermillion']}"; stroke: "{OKABE['vermillion']}"; font-color: "{INK}"}}}}
  missing:   {{style: {{fill: "{PAPER}"; stroke: "{OKABE['vermillion']}"; stroke-dash: 4; font-color: "{OKABE['vermillion']}"}}}}
  note:      {{shape: text; style: {{font-color: "{GREY}"; italic: true}}}}
}}"""

DOT_RESEARCH = [f"-Gfontname={FONT_STACK.split(',')[0]}", "-Nfontname=Arial", "-Efontname=Arial",
                "-Gfontsize=14", "-Nfontsize=14", "-Efontsize=12", "-Gpad=0.15", "-Gbgcolor=white",
                "-Nshape=box", "-Nstyle=rounded,filled", f"-Nfillcolor={FILL}", f"-Ncolor={GREY}",
                f"-Nfontcolor={INK}", f"-Ecolor={GREY}", f"-Efontcolor={INK}", "-Earrowsize=0.7",
                "-Nmargin=0.15,0.08"]


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def exe(path):
    """Resolve a user/env path; on Windows accept npm shims without extension."""
    if not path:
        return None
    p = Path(path)
    if os.name == "nt":
        for ext in (".cmd", ".exe", ".bat"):
            if p.suffix.lower() != ext and Path(str(p) + ext).exists():
                return str(Path(str(p) + ext))
    if p.exists():
        return str(p)
    return shutil.which(path)


def find_browser(arg):
    for c in (arg, os.environ.get("RV_BROWSER"), os.environ.get("PUPPETEER_EXECUTABLE_PATH")):
        if c and Path(c).exists():
            return c
    cands = []
    if os.name == "nt":
        for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
            if base:
                cands += [Path(base, "Google/Chrome/Application/chrome.exe"),
                          Path(base, "Microsoft/Edge/Application/msedge.exe")]
    elif sys.platform == "darwin":
        cands += [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                  Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
                  Path("/Applications/Chromium.app/Contents/MacOS/Chromium")]
    for c in cands:
        if c.exists():
            return str(c)
    for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "chrome", "msedge"):
        w = shutil.which(n)
        if w:
            return w
    return None  # let puppeteer use its own download, if any


def find_fonts():
    """Arial (or metric-compatible Liberation Sans) TTFs so D2 lays text out with real Arial metrics."""
    dirs = [Path(os.environ.get("WINDIR", "C:/Windows"), "Fonts"), Path("/System/Library/Fonts/Supplemental"),
            Path("/Library/Fonts"), Path("/usr/share/fonts/truetype/liberation"), Path("/usr/share/fonts/liberation-sans"),
            Path("/usr/share/fonts/truetype/msttcorefonts")]
    sets = [("arial.ttf", "arialbd.ttf", "ariali.ttf"), ("Arial.ttf", "Arial Bold.ttf", "Arial Italic.ttf"),
            ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf", "LiberationSans-Italic.ttf")]
    for d in dirs:
        for s in sets:
            fs = [d / f for f in s]
            if all(f.exists() for f in fs):
                return fs
    return None


def svg_size_fix(svg_path, width_mm=None):
    """Give the root <svg> explicit width/height (px, or mm if asked) taken from its viewBox.
    Apps (PowerPoint, Inkscape, export.py) then open it at the right size."""
    s = Path(svg_path).read_text(encoding="utf-8")
    m = re.search(r"<svg\b[^>]*>", s)
    if not m:
        return None
    tag = m.group(0)
    vb = re.search(r'viewBox="\s*([-\d.eE]+)[\s,]+([-\d.eE]+)[\s,]+([\d.eE]+)[\s,]+([\d.eE]+)\s*"', tag)
    if not vb:
        return None
    vw, vh = float(vb.group(3)), float(vb.group(4))
    unit = ""
    w0 = re.search(r'\swidth="([\d.]+)(pt|px)?"', tag)
    if w0 and w0.group(2) == "pt":  # graphviz: keep physical size, express in px
        k = 96 / 72
        vw_px, vh_px = float(w0.group(1)) * k, float(re.search(r'\sheight="([\d.]+)pt"', tag).group(1)) * k
    else:
        vw_px, vh_px = vw, vh
    if width_mm:
        w, h, unit = width_mm, width_mm * vh / vw, "mm"
    else:
        w, h, unit = vw_px, vh_px, "px"
    new = re.sub(r'\s(width|height)="[^"]*"', "", tag)
    new = re.sub(r"max-width:\s*[\d.]+px;?\s*", "", new)
    new = new.replace("<svg", f'<svg width="{w:.2f}{unit}" height="{h:.2f}{unit}"', 1)
    s = s.replace(tag, new, 1)
    Path(svg_path).write_text(s, encoding="utf-8")
    return w, h, unit


def report_error(kind, src, text, line_offset=0):
    """Print the tool's own message, trimmed of stack traces, with line numbers mapped to the source file."""
    lines = [l for l in text.replace("\r", "").split("\n")]
    keep = []
    for l in lines:
        if re.match(r"\s+at\s", l) or "node_modules" in l or l.startswith("Node.js v") or l.startswith("info:"):
            continue
        keep.append(l)
    msg = "\n".join(keep).strip()
    if kind == "d2":
        def fix(m):
            return f"{src.name}:{int(m.group(1)) - line_offset}:{m.group(2)}"
        msg = re.sub(r"(?:-|[^\s:]*\.d2|[A-Za-z]:\\[^:]*\.d2):(\d+):(\d+)", fix, msg)
        msg = msg.replace("failed to compile -:", f"failed to compile {src.name}:")
    msg = msg.replace("Error: Evaluation failed: ", "")
    pat = r"(?:line|Line)\s+(\d+)|" + re.escape(src.name) + r":(\d+)"
    nums = sorted({int(g) for tup in re.findall(pat, msg) for g in tup if g})
    print(f"\nRENDER FAILED ({kind}) for {src}\n{'-' * 60}\n{msg[:4000]}\n{'-' * 60}", file=sys.stderr)
    if nums:
        src_lines = src.read_text(encoding="utf-8").split("\n")
        for n in nums[:3]:
            lo, hi = max(1, n - 1), min(len(src_lines), n + 1)
            print(f"Source around line {n}:", file=sys.stderr)
            for i in range(lo, hi + 1):
                print(f"  {'>' if i == n else ' '}{i:4d} | {src_lines[i - 1]}", file=sys.stderr)
    if kind == "mermaid":
        print("Hints: quote labels with special characters  A[\"Dry (40 °C, 48 h)\"];  edge labels  -->|\"text\"|;"
              "  no <sub>: use Unicode (H₂O);  'end' is reserved as a node id.", file=sys.stderr)
    sys.exit(1)


def run(cmd, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    except FileNotFoundError as e:
        die(f"Could not start {cmd[0]}: {e}", 3)


def render_mermaid(src, out, a, tmp):
    mmdc = exe(a.mmdc) or exe(os.environ.get("RV_MMDC")) or shutil.which("mmdc")
    base = [mmdc] if mmdc else None
    if not base:
        npx = shutil.which("npx")
        if not npx:
            die("Mermaid CLI not found. Install Node.js, then: npm install -g @mermaid-js/mermaid-cli\n"
                "or pass --mmdc PATH / set RV_MMDC.", 3)
        base = [npx, "-y", "@mermaid-js/mermaid-cli"]
        print("mmdc not found; using npx @mermaid-js/mermaid-cli (first run downloads the CLI from npm).")
    env = dict(os.environ)
    cmd = base + ["-i", str(src), "-o", str(out), "-b", a.background, "--no-font-embed", "-q"]
    browser = find_browser(a.browser)
    if browser:
        pcfg = Path(tmp, "puppeteer.json")
        pcfg.write_text(json.dumps({"executablePath": browser, "args": ["--no-sandbox"], "headless": True}), encoding="utf-8")
        cmd += ["-p", str(pcfg)]
        env["PUPPETEER_SKIP_DOWNLOAD"] = "1"
    conf = {"research": MERMAID_RESEARCH, "plain": MERMAID_PLAIN}.get(a.theme)
    if conf:
        c = Path(tmp, "mermaid.json")
        c.write_text(json.dumps(conf, indent=1), encoding="utf-8")
        cmd += ["-c", str(c)]
    r = run(cmd, env=env)
    if r.returncode != 0 or not out.exists():
        err = (r.stderr or "") + (r.stdout or "")
        if "Could not find Chrome" in err or "Failed to launch" in err:
            die(f"Mermaid CLI could not start a browser.\n{err.strip()[:1500]}\n"
                "Install Chrome or Edge, or pass --browser PATH (or set RV_BROWSER).", 3)
        report_error("mermaid", src, err)
    s = out.read_text(encoding="utf-8")
    if "<foreignObject" in s:
        print("WARNING: some labels are HTML <foreignObject> (not editable as SVG text in Inkscape/PowerPoint). "
              "This diagram type ignores htmlLabels=false, or the source sets htmlLabels itself.")


def render_d2(src, out, a, tmp):
    d2 = exe(a.d2) or exe(os.environ.get("RV_D2")) or shutil.which("d2")
    if not d2:
        die("D2 not found. Install from https://d2lang.com/tour/install (Windows: winget install Terrastruct.D2, "
            "or unzip the release and pass --d2 PATH / set RV_D2).", 3)
    text = src.read_text(encoding="utf-8")
    offset = 0
    cmd = [d2, f"--pad={a.pad}", f"--layout={a.layout}", "--omit-version"]
    if a.layout == "elk":
        cmd += ["--elk-nodeNodeBetweenLayers=45", "--elk-edgeNodeBetweenLayers=30"]
    if a.theme == "research":
        ov = "; ".join(f'{k}: "{v}"' for k, v in D2_OVERRIDES.items())
        # regular-weight labels (D2 default is bold); a node's own style.bold: true still wins
        head = f"vars: {{d2-config: {{theme-id: {D2_THEME_ID}; theme-overrides: {{{ov}}}}}}}; **.style.bold: false\n"
        text = head + text  # one line, so error line numbers shift by exactly 1; user's own d2-config still wins
        offset = 1
    fonts = find_fonts() if a.theme != "none" else None
    if fonts:
        cmd += [f"--font-regular={fonts[0]}", f"--font-bold={fonts[1]}", f"--font-italic={fonts[2]}",
                f"--font-semibold={fonts[1]}"]
    cmd += ["-", str(out)]
    r = run(cmd, input=text, cwd=str(src.parent))
    if r.returncode != 0 or not out.exists():
        report_error("d2", src, (r.stderr or "") + (r.stdout or ""), offset)
    if fonts:
        # Drop the embedded font subsets: editors would otherwise fall back to a default font when a
        # letter outside the subset is typed. Layout was computed with real Arial metrics above.
        s = out.read_text(encoding="utf-8")
        s = re.sub(r"@font-face\s*\{[^}]*\}", "", s)
        s = re.sub(r'font-family:\s*"?d2-[\w-]+-font-(regular|bold|italic|semibold)"?',
                   lambda m: f"font-family: {FONT_STACK}" + ("; font-weight: bold" if m.group(1) in ("bold", "semibold")
                                                             else "; font-style: italic" if m.group(1) == "italic" else ""), s)
        out.write_text(s, encoding="utf-8")


def render_dot(src, out, a, tmp):
    dot = exe(a.dot) or exe(os.environ.get("RV_DOT")) or shutil.which("dot")
    if not dot:
        die("Graphviz 'dot' not found. Install it:\n  Windows: winget install Graphviz.Graphviz  (then open a new terminal)\n"
            "  macOS: brew install graphviz    Linux: sudo apt install graphviz\n"
            "or pass --dot PATH / set RV_DOT. Alternatively rewrite the diagram in Mermaid or D2.", 3)
    cmd = [dot, "-Tsvg", "-o", str(out)] + (DOT_RESEARCH if a.theme == "research" else []) + [str(src)]
    r = run(cmd)
    if r.returncode != 0 or not out.exists():
        report_error("graphviz", src, (r.stderr or "") + (r.stdout or ""))


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", help=".mmd/.mermaid, .d2, or .dot/.gv source")
    ap.add_argument("-o", "--output", help="output SVG (default: input name with .svg)")
    ap.add_argument("--png", type=int, metavar="DPI", help="also export PNG at this dpi via export.py")
    ap.add_argument("--pdf", action="store_true", help="also export vector PDF via export.py")
    ap.add_argument("--check", action="store_true", help="run export.py layout check (small text, overlaps, [? ] placeholders)")
    ap.add_argument("--theme", default="research", choices=["research", "plain", "none"])
    ap.add_argument("--width-mm", type=float, help="set the physical width (e.g. 85 one column, 174 two columns)")
    ap.add_argument("--layout", default="dagre", choices=["dagre", "elk"],
                    help="D2 layout: dagre (default; edge labels sit cleanly mid-edge) or elk (orthogonal elbows, more compact)")
    ap.add_argument("--pad", type=int, default=24, help="D2 padding in px (default 24)")
    ap.add_argument("--background", default="white", help="Mermaid background (white or transparent)")
    ap.add_argument("--mmdc"), ap.add_argument("--d2"), ap.add_argument("--dot"), ap.add_argument("--browser")
    ap.add_argument("--classdefs", action="store_true", help="print the research-theme classDef (Mermaid) and classes (D2)")
    a = ap.parse_args()

    if a.classdefs:
        print(MERMAID_CLASSDEFS + "\n\n" + D2_CLASSES)
        return
    if not a.input:
        ap.error("input file required")
    src = Path(a.input).resolve()
    if not src.exists():
        die(f"No such file: {src}")
    ext = src.suffix.lower()
    kind = {".mmd": "mermaid", ".mermaid": "mermaid", ".d2": "d2", ".dot": "dot", ".gv": "dot"}.get(ext)
    if not kind:
        die("Input must end in .mmd/.mermaid, .d2, .dot or .gv")
    out = Path(a.output).resolve() if a.output else src.with_suffix(".svg")
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    with tempfile.TemporaryDirectory(prefix="rv-diagram-") as tmp:
        {"mermaid": render_mermaid, "d2": render_d2, "dot": render_dot}[kind](src, out, a, tmp)

    size = svg_size_fix(out, a.width_mm)
    s = out.read_text(encoding="utf-8")
    n_text = len(re.findall(r"<text\b", s))
    n_fo = len(re.findall(r"<foreignObject\b", s))
    plain = re.sub(r"\s+", " ", re.sub(r"<(?!/text)[^>]+>", "", s))  # labels are split into per-word <tspan>s
    ph = sorted(set(re.findall(r"\[\?[^\]<]*\]", plain)))
    dims = f"{size[0]:.0f} x {size[1]:.0f} {size[2]}" if size else "size unknown"
    print(f"SVG: {out}  ({dims}, {n_text} <text> elements, {n_fo} foreignObject)")
    if ph:
        print(f"Placeholders still to fill ({len(ph)}): {' '.join(ph[:12])}{' ...' if len(ph) > 12 else ''}")

    if a.png or a.pdf or a.check:
        py = os.environ.get("RV_PYTHON") or sys.executable
        cmd = [py, str(HERE / "export.py"), str(out)]
        if a.png:
            cmd += ["--png", str(a.png)]
        if a.pdf:
            cmd += ["--pdf"]
        if a.check:
            cmd += ["--check"]
        r = run(cmd)
        sys.stdout.write(r.stdout)
        if r.returncode != 0:
            die(f"export.py failed (needs playwright: pip install playwright):\n{r.stderr.strip()[-1500:]}", 1)


if __name__ == "__main__":
    main()
