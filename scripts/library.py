#!/usr/bin/env python3
"""One search over every free illustration library the skill has downloaded, with the licence of each hit.

Libraries (all in ~/.cache/scientific-illustration, built by `library.py fetch`):
  servier    Servier Medical Art   CC BY 4.0   professional medical art (PNG, via servier.py)
  togotv     DBCLS TogoTV          CC BY 4.0   ~2,000 life-science SVGs: cells, organisms, lab devices, omics
  bioicons   Bioicons              per icon (CC0 / CC BY / CC BY-SA / MIT / BSD, read from the path)
  health     Health Icons          CC0         simple medical/public-health pictograms

  python library.py fetch                      # download togotv + bioicons + health (servier: servier.py fetch)
  python library.py search fibroblast wound    # ranked hits from all libraries, public-domain first
  python library.py search cell --lib togotv --license cc-0
  python library.py get togotv:201012_Vero.svg --to figdir/art --w 30
      # copies the file (SVGs are sanitised: no scripts, event handlers or external links) and prints a
      # ready spec element (svgfile or image) with licence, author and source filled in
Only library file lists and the files themselves are downloaded; nothing about the user's work is sent.
"""
import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

CACHE = Path(os.environ.get("RV_CACHE", Path.home() / ".cache" / "scientific-illustration"))
TOGO = "https://dbarchive.biosciencedbc.jp/data/togo-pic/image/"
PUBLIC = ("cc-0", "cc0", "public-domain")


def _togotv():
    d = CACHE / "togotv"
    titles = {}
    f = d / "masterfile.csv"
    if f.exists():
        for r in csv.DictReader(f.open(encoding="utf-8", errors="replace")):
            titles[r.get("original_svg", "")] = (r.get("title_en", ""), r.get("Designed_by", ""), r.get("doi", ""))
    for p in sorted((d / "svg").glob("*.svg")):
        t, who, doi = titles.get(p.name, ("", "", ""))
        name = t or re.sub(r"^\d+_", "", p.stem).replace("_", " ")
        yield {"lib": "togotv", "key": f"togotv:{p.name}", "path": p, "name": name, "license": "cc-by-4.0",
               "author": "DBCLS TogoTV" + (f" ({who})" if who else ""),
               "source": f"https://togotv.dbcls.jp {('doi:10.7875/' + doi) if doi else ''}".strip()}


def _bioicons():
    base = CACHE / "repos" / "bioicons" / "static" / "icons"
    for p in base.rglob("*.svg"):
        rel = p.relative_to(base).as_posix()
        parts = rel.split("/")
        lic = parts[0]
        author = parts[2].replace("-", " ").replace("_", " ") if len(parts) > 3 else ""
        cat = parts[1] if len(parts) > 3 else ""
        yield {"lib": "bioicons", "key": f"bioicons:{rel}", "path": p, "name": f"{cat} {p.stem}".replace("_", " "),
               "license": lic, "author": f"{author} / Bioicons".strip(" /"), "source": f"https://bioicons.com ({rel})"}


def _health():
    base = CACHE / "repos" / "healthicons" / "public" / "icons" / "svg"
    for p in base.rglob("*.svg"):
        rel = p.relative_to(base).as_posix()
        yield {"lib": "health", "key": f"health:{rel}", "path": p, "name": rel.replace("/", " ").replace("_", " ")[:-4],
               "license": "cc-0", "author": "Health Icons", "source": "https://healthicons.org"}


def _servier():
    f = CACHE / "servier" / "catalog.json"
    if not f.exists():
        return
    data = json.loads(f.read_text(encoding="utf-8-sig"))
    for e in (data if isinstance(data, list) else [data]):
        yield {"lib": "servier", "key": f"servier:{e['file']}", "path": CACHE / "servier" / e["file"],
               "name": f"{e['set']} {e['title']} {e['label']}", "license": "cc-by-4.0", "author": "Servier Medical Art",
               "source": "https://smart.servier.com (CC BY 4.0)", "wh": (e["w"], e["h"])}


SOURCES = {"togotv": _togotv, "bioicons": _bioicons, "health": _health, "servier": _servier}


def sanitize_svg(txt):
    txt = re.sub(r"<script.*?</script>", "", txt, flags=re.S | re.I)
    txt = re.sub(r"<foreignObject.*?</foreignObject>", "", txt, flags=re.S | re.I)
    txt = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*')", "", txt, flags=re.I)
    # external references could fetch remote content when the figure is opened
    txt = re.sub(r"(xlink:href|href)\s*=\s*\"(https?:|javascript:)[^\"]*\"", "", txt, flags=re.I)
    return txt


def svg_aspect(txt):
    m = re.search(r'viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', txt)
    if m and float(m.group(1)) > 0:
        return float(m.group(2)) / float(m.group(1))
    w = re.search(r'<svg[^>]*\swidth="([\d.]+)', txt)
    h = re.search(r'<svg[^>]*\sheight="([\d.]+)', txt)
    return float(h.group(1)) / float(w.group(1)) if w and h and float(w.group(1)) else 1.0


def fetch():
    (CACHE / "togotv" / "svg").mkdir(parents=True, exist_ok=True)
    (CACHE / "repos").mkdir(parents=True, exist_ok=True)
    ua = {"User-Agent": "scientific-illustration"}
    listing = urllib.request.urlopen(urllib.request.Request(TOGO, headers=ua), timeout=120).read().decode("utf-8", "replace")
    names = sorted(set(re.findall(r'href="([^"?/]+\.svg)"', listing)))
    csvs = sorted(re.findall(r'href="([^"?/]+_togopic_masterfile\.csv)"', listing))
    if csvs:
        (CACHE / "togotv" / "masterfile.csv").write_bytes(urllib.request.urlopen(
            urllib.request.Request(TOGO + csvs[-1], headers=ua), timeout=120).read())
    new = [n for n in names if not (CACHE / "togotv" / "svg" / n).exists()]
    print(f"TogoTV: {len(names)} SVGs listed, {len(new)} to download")
    def one(n):
        try:
            data = urllib.request.urlopen(urllib.request.Request(TOGO + urllib.request.quote(n), headers=ua), timeout=120).read()
            if b"<svg" in data[:5000]:
                (CACHE / "togotv" / "svg" / n).write_text(sanitize_svg(data.decode("utf-8", "replace")), encoding="utf-8")
        except Exception as e:
            print("  skip", n, e)
    from concurrent.futures import ThreadPoolExecutor   # the archive server is slow per file, so fetch 8 at a time
    with ThreadPoolExecutor(8) as ex:
        for i, _ in enumerate(ex.map(one, new)):
            if i % 200 == 199:
                print(f"  {i + 1}/{len(new)}", flush=True)
    repos = CACHE / "repos"
    if not (repos / "bioicons").exists():
        subprocess.run(["git", "clone", "-q", "--depth", "1", "https://github.com/duerrsimon/bioicons", str(repos / "bioicons")], check=True)
    if not (repos / "healthicons").exists():
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse",
                        "https://github.com/resolvetosavelives/healthicons", str(repos / "healthicons")], check=True)
        subprocess.run(["git", "-C", str(repos / "healthicons"), "sparse-checkout", "set", "public/icons/svg"], check=True)
    for k, fn in SOURCES.items():
        print(f"{k}: {sum(1 for _ in fn())} items")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch")
    s = sub.add_parser("search")
    s.add_argument("terms", nargs="+")
    s.add_argument("--lib", choices=list(SOURCES))
    s.add_argument("--license")
    s.add_argument("--limit", type=int, default=40)
    g = sub.add_parser("get")
    g.add_argument("key")
    g.add_argument("--to", default="art")
    g.add_argument("--w", type=float, default=30, help="width in mm for the printed element")
    sub.add_parser("stats")
    a = ap.parse_args()

    if a.cmd == "fetch":
        return fetch()
    if a.cmd == "stats":
        for k, fn in SOURCES.items():
            print(f"{k:<9} {sum(1 for _ in fn())}")
        return
    if a.cmd == "search":
        terms = [t.lower() for t in a.terms]
        hits = []
        for k, fn in SOURCES.items():
            if a.lib and k != a.lib:
                continue
            for it in fn():
                text = f"{it['name']} {it['key']}".lower()
                score = sum(t in text for t in terms)
                if score and (not a.license or it["license"].startswith(a.license)):
                    hits.append((score, it))
        # most terms matched first, then professional art, then public domain
        order = {"servier": 0, "togotv": 1, "bioicons": 2, "health": 3}
        hits.sort(key=lambda h: (-h[0], order[h[1]["lib"]], h[1]["license"] not in PUBLIC))
        for _, it in hits[:a.limit]:
            print(f"{it['key']:<70} [{it['license']}] {it['name'][:50]}")
        print(f"{len(hits)} match(es). Read a few candidate files before choosing; names can be loose.")
        return

    lib, _, rest = a.key.partition(":")
    it = next((x for x in SOURCES.get(lib, lambda: [])() if x["key"] == a.key), None)
    if it is None or ".." in rest:
        sys.exit("unknown key; copy it from `search`")
    to = Path(a.to)
    to.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^\w.\-]", "_", Path(rest).name)
    dst = to / f"{lib}_{name}"
    meta = {"license": it["license"], "author": it["author"], "source": it["source"]}
    if dst.suffix.lower() == ".svg":
        txt = sanitize_svg(it["path"].read_text(encoding="utf-8", errors="replace"))
        dst.write_text(txt, encoding="utf-8")
        el = {"type": "svgfile", "id": dst.stem.lower(), "path": dst.as_posix(), "x": 0, "y": 0, "w": a.w,
              "h": round(a.w * svg_aspect(txt), 1), **meta}
    else:
        shutil.copy2(it["path"], dst)
        w, h = it.get("wh", (1, 1))
        el = {"type": "image", "id": dst.stem.lower(), "path": dst.as_posix(), "x": 0, "y": 0, "w": a.w,
              "h": round(a.w * h / w, 1), **meta}
    (to / (dst.stem + ".license.json")).write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"copied {dst}  licence={it['license']}")
    print("spec element:", json.dumps(el, ensure_ascii=False))


if __name__ == "__main__":
    main()
