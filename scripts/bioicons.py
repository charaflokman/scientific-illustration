#!/usr/bin/env python3
"""Find and fetch Bioicons (https://bioicons.com, repo duerrsimon/bioicons) with their licence.

Bioicons stores every icon at static/icons/<licence>/<category>/<author>/<name>.svg,
so the licence and author come from the path itself. Licences differ per icon
(cc-0, cc-by-3.0, cc-by-4.0, cc-by-sa-3.0/4.0, mit, bsd); CC-BY icons need an
attribution line, which render_figure.py prints and adds to the figure.

  python bioicons.py search beaker flask            # list matches (uses a cached index)
  python bioicons.py search mouse --license cc-0    # only public-domain icons
  python bioicons.py get cc-0/Lab_apparatus/KeHan/sonicator.svg --to icons/
  python bioicons.py search sonicator --local C:/path/to/bioicons   # use a local clone, no network

`get` writes the SVG plus <name>.license.json; reference it from a figure spec as
{"type": "svgfile", "path": "icons/sonicator.svg", "license": ..., "author": ..., "source": ...}
(the printed snippet has these filled in).
Only icon file names and paths are requested from GitHub; nothing about the user's work is sent.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO = "duerrsimon/bioicons"
TREE_URL = f"https://api.github.com/repos/{REPO}/git/trees/main?recursive=1"
RAW = f"https://raw.githubusercontent.com/{REPO}/main/static/icons/"
CACHE = Path(os.environ.get("RV_CACHE", Path.home() / ".cache" / "scientific-illustration"))
ATTRIB = {
    "cc-0": "", "mit": "MIT", "bsd": "BSD",
    "cc-by-3.0": "CC BY 3.0", "cc-by-4.0": "CC BY 4.0", "cc-by-sa-3.0": "CC BY-SA 3.0", "cc-by-sa-4.0": "CC BY-SA 4.0",
}


def index(local=None):
    if local:
        base = Path(local) / "static" / "icons"
        return [str(p.relative_to(base)).replace("\\", "/") for p in base.rglob("*.svg")]
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / "bioicons_index.json"
    if f.exists() and time.time() - f.stat().st_mtime < 30 * 86400:
        return json.loads(f.read_text())
    req = urllib.request.Request(TREE_URL, headers={"User-Agent": "scientific-illustration", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        tree = json.load(r)["tree"]
    paths = [t["path"][len("static/icons/"):] for t in tree
             if t["path"].startswith("static/icons/") and t["path"].endswith(".svg")]
    f.write_text(json.dumps(paths))
    return paths


def meta(rel):
    parts = rel.split("/")
    lic, cat, author = parts[0], parts[1] if len(parts) > 3 else "", parts[2] if len(parts) > 3 else ""
    return {"license": lic, "category": cat, "author": author.replace("-", " ").replace("_", " "),
            "source": f"https://bioicons.com (github.com/{REPO}, static/icons/{rel})",
            "attribution": (f"{author.replace('-', ' ')} / Bioicons, {ATTRIB.get(lic, lic)}" if ATTRIB.get(lic) else "")}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("terms", nargs="+")
    s.add_argument("--license", help="filter, e.g. cc-0 or cc-by-4.0")
    s.add_argument("--local", help="path to a local clone of duerrsimon/bioicons")
    s.add_argument("--limit", type=int, default=40)
    g = sub.add_parser("get")
    g.add_argument("relpath", help="path as printed by search, e.g. cc-0/Chemistry/Hanna/Beaker_water_stir_bar.svg")
    g.add_argument("--to", default="icons")
    g.add_argument("--local")
    a = ap.parse_args()

    if a.cmd == "search":
        paths = index(a.local)
        terms = [t.lower() for t in a.terms]
        hits = [p for p in paths if any(t in p.lower() for t in terms)]
        if a.license:
            hits = [p for p in hits if p.startswith(a.license + "/")]
        hits.sort(key=lambda p: (not p.startswith("cc-0/"), p))   # public-domain first
        for p in hits[:a.limit]:
            m = meta(p)
            print(f"{p}    [{m['license']}{', attribution required' if m['attribution'] else ''}]")
        print(f"{len(hits)} match(es){' (showing ' + str(a.limit) + ')' if len(hits) > a.limit else ''}")
        return

    rel = a.relpath.strip("/")
    if not re.fullmatch(r"[\w.\-()/ ]+\.svg", rel) or ".." in rel:
        sys.exit("unexpected icon path")
    out = Path(a.to)
    out.mkdir(parents=True, exist_ok=True)
    name = Path(rel).name.replace(" ", "_")
    if a.local:
        data = (Path(a.local) / "static" / "icons" / rel).read_bytes()
    else:
        url = RAW + urllib.request.quote(rel)
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "scientific-illustration"}), timeout=60) as r:
            data = r.read()
    if b"<svg" not in data[:4000]:
        sys.exit("download is not an SVG")
    # strip scripts / event handlers: icons are pictures, nothing in them should run
    txt = data.decode("utf-8", errors="replace")
    txt = re.sub(r"<script.*?</script>", "", txt, flags=re.S | re.I)
    txt = re.sub(r"\son\w+=\"[^\"]*\"", "", txt)
    (out / name).write_text(txt, encoding="utf-8")
    m = meta(rel)
    (out / (Path(name).stem + ".license.json")).write_text(json.dumps(m, indent=1), encoding="utf-8")
    print(f"saved {out / name}  licence={m['license']}  {('attribution: ' + m['attribution']) if m['attribution'] else 'no attribution needed'}")
    snippet = {"type": "svgfile", "id": Path(name).stem.lower(), "path": str(out / name).replace("\\", "/"),
               "x": 0, "y": 0, "w": 20, "license": m["license"], "author": m["author"], "source": m["source"]}
    print("spec element:", json.dumps(snippet))


if __name__ == "__main__":
    main()
