#!/usr/bin/env python3
"""One search over every free illustration library the skill has downloaded, with the licence of each hit.

Libraries (all in ~/.cache/scientific-illustration, built by `library.py fetch`):
  servier    Servier Medical Art   CC BY 4.0   professional medical art (PNG, via servier.py)
  togotv     DBCLS TogoTV          CC BY 4.0   ~2,000 life-science SVGs: cells, organisms, lab devices, omics
  bioicons   Bioicons              per icon (CC0 / CC BY / CC BY-SA / MIT / BSD, read from the path)
  health     Health Icons          CC0         simple medical/public-health pictograms
  reactome   Reactome Icon Library CC BY 4.0   ~2,500 proteins, receptors, transporters, drugs, cell types, tissues
  scidraw    SciDraw               CC BY / CC0 ~600 neuroscience, lab animals, behaviour & lab setups (DOIs)
  phylopic   PhyloPic              CC0 / PDM / CC BY  ~11,000 organism silhouettes; search by taxon name
                                   (e.g. Chiroptera, Manis, Homo sapiens); NC and SA images are never downloaded

  python library.py fetch                      # download all of them (servier: servier.py fetch)
  python library.py fetch --only reactome phylopic   # just some libraries
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


def _catalog_lib(lib):
    """Libraries fetched from an API keep a _catalog.json next to their SVGs (written by fetch)."""
    f = CACHE / lib / "_catalog.json"
    if not f.exists():
        return
    for e in json.loads(f.read_text(encoding="utf-8")):
        p = CACHE / lib / e["file"]
        if p.exists():
            yield {"lib": lib, "key": f"{lib}:{e['file']}", "path": p, "name": e["name"], "license": e["license"],
                   "author": e["author"], "source": e["source"]}


SOURCES = {"togotv": _togotv, "bioicons": _bioicons, "health": _health, "servier": _servier,
           "reactome": lambda: _catalog_lib("reactome"), "scidraw": lambda: _catalog_lib("scidraw"),
           "phylopic": lambda: _catalog_lib("phylopic")}


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


UA = {"User-Agent": "scientific-illustration (open icon fetch)"}


def _get(url, tries=4):
    import time
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def _slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:70] or "icon"


def _save_catalog(lib, items, job):
    """Run job(item) -> catalog row (or None) 8 at a time, keep rows whose SVG was saved, write _catalog.json."""
    from concurrent.futures import ThreadPoolExecutor
    rows = []
    with ThreadPoolExecutor(8) as ex:
        for i, r in enumerate(ex.map(job, items)):
            if r:
                rows.append(r)
            if i % 1000 == 999:
                print(f"  {lib}: {i + 1}/{len(items)}", flush=True)
    (CACHE / lib / "_catalog.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{lib}: {len(rows)} items")


def _write_svg(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if b"<svg" not in data[:20000]:
        return False
    path.write_text(sanitize_svg(data.decode("utf-8", "replace")), encoding="utf-8")
    return True


def fetch_reactome():
    import html
    cats = ["arrow", "background", "cell_element", "cell_type", "compound", "human_tissue",
            "protein", "receptor", "therapeutic", "transporter"]
    ids = {}
    for c in cats:
        first = _get(f"https://reactome.org/icon-lib/{c}").decode("utf-8", "replace")
        last = max([int(x) for x in re.findall(r"page=(\d+)", first)] + [1])
        for pg in range(1, last + 1):
            page = first if pg == 1 else _get(f"https://reactome.org/icon-lib/{c}?page={pg}").decode("utf-8", "replace")
            for i, name in re.findall(r'<img src="/icon/(R-ICO-\d+)\.svg" alt="([^"]*)"', page):
                ids[i] = (c, html.unescape(name))
    print(f"Reactome: {len(ids)} icons listed")

    def job(item):
        i, (c, name) = item
        rel = f"{c}/{_slug(name)}__{i}.svg"
        try:
            p = CACHE / "reactome" / rel
            if not p.exists() and not _write_svg(p, _get(f"https://reactome.org/icon/{i}.svg")):
                return None
            meta = _get(f"https://reactome.org/icon/{i}.xml").decode("utf-8", "replace")
            designer = (re.search(r'role="designer"[^>]*>([^<]*)<', meta) or [None, "Reactome"])[1]
            desc = html.unescape((re.search(r"<description>(.*?)</description>", meta, re.S) or [None, ""])[1]).strip()
            return {"file": rel, "name": f"{c.replace('_', ' ')} {name} {desc[:120]}".strip(), "license": "cc-by-4.0",
                    "author": f"{designer} / Reactome", "source": f"https://reactome.org/icon-lib ({i})"}
        except Exception as e:
            print("  skip", i, e)
    _save_catalog("reactome", list(ids.items()), job)


def fetch_scidraw():
    lics = {"cc-by": "cc-by-4.0", "cc0": "cc-0", "cc-0": "cc-0", "public-domain": "public-domain"}
    url, items = "https://scidraw.io/api/v1/drawings/", []
    while url:
        d = json.loads(_get(url))
        items += d["results"]
        url = d.get("next")
        if url and url.startswith("http://"):
            url = "https://" + url[7:]
    print(f"SciDraw: {len(items)} drawings listed")

    def job(it):
        if not it.get("is_vector") or it.get("license") not in lics:
            return None
        cat = it.get("category_name") or "misc"
        rel = f"{_slug(cat)}/{_slug(it['name'])}__{it['id'][:8]}.svg"
        try:
            p = CACHE / "scidraw" / rel
            if not p.exists() and not _write_svg(p, _get(it["image_url"].replace("http://", "https://"))):
                return None
        except Exception as e:
            print("  skip", it["id"], e)
            return None
        who = (it.get("primary_author") or {}).get("full_name", "SciDraw contributor")
        doi = f" doi:{it['doi']}" if it.get("doi") else ""
        return {"file": rel, "name": f"{cat} {it['name']}", "license": lics[it["license"]],
                "author": f"{who} / SciDraw", "source": f"https://scidraw.io{doi}"}
    _save_catalog("scidraw", items, job)


def fetch_phylopic():
    ok = {"https://creativecommons.org/publicdomain/zero/1.0/": "cc-0",
          "https://creativecommons.org/publicdomain/mark/1.0/": "public-domain",
          "https://creativecommons.org/licenses/by/4.0/": "cc-by-4.0",
          "https://creativecommons.org/licenses/by/3.0/": "cc-by-3.0"}   # NC and SA licences are skipped
    build = json.loads(_get("https://api.phylopic.org/images"))["build"]
    pages = json.loads(_get(f"https://api.phylopic.org/images?build={build}"))["totalPages"]
    from concurrent.futures import ThreadPoolExecutor

    def page(n):
        try:
            return json.loads(_get(f"https://api.phylopic.org/images?build={build}&page={n}&embed_items=true"))["_embedded"]["items"]
        except Exception as e:
            print("  page skip", n, e)
            return []
    with ThreadPoolExecutor(6) as ex:
        items = [it for lst in ex.map(page, range(pages)) for it in lst]
    print(f"PhyloPic: {len(items)} images listed")

    def job(it):
        L = it.get("_links") or {}
        lic = ok.get((L.get("license") or {}).get("href", ""))
        vec = (L.get("vectorFile") or {}).get("href")
        if not lic or not vec:
            return None
        taxon = (L.get("specificNode") or {}).get("title", "organism")
        group = (L.get("generalNode") or {}).get("title", "") or taxon
        lineage = [n.get("title", "") for n in (L.get("nodes") or [])][:8]
        rel = f"{_slug(group)[:40]}/{_slug(taxon)}__{it['uuid'][:8]}.svg"
        try:
            p = CACHE / "phylopic" / rel
            if not p.exists() and not _write_svg(p, _get(vec)):
                return None
        except Exception as e:
            print("  skip", it["uuid"], e)
            return None
        who = it.get("attribution") or (L.get("contributor") or {}).get("title", "PhyloPic contributor")
        return {"file": rel, "name": f"{taxon} silhouette {group}" + (f" ({' > '.join(lineage[1:5])})" if lineage[1:5] else ""), "license": lic,
                "author": f"{who} / PhyloPic", "source": f"https://www.phylopic.org/images/{it['uuid']}"}
    _save_catalog("phylopic", items, job)


HDRIS = ["studio_small_09", "photo_studio_loft_hall", "brown_photostudio_02"]


def fetch_hdri():
    """Photo-studio HDRIs from Poly Haven (CC0, no attribution needed) for render_blender.py reflections and light."""
    for a in HDRIS:
        p = CACHE / "hdri" / f"{a}.hdr"
        if p.exists():
            continue
        url = json.loads(_get(f"https://api.polyhaven.com/files/{a}"))["hdri"]["2k"]["hdr"]["url"]
        if not url.startswith("https://dl.polyhaven.org/"):
            print("  skip", a, "unexpected host", url)
            continue
        p.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "scientific-illustration"}),
                                             timeout=300).read())
        print("  HDRI", a)


def fetch(only=None):
    want = set(only or ["togotv", "bioicons", "health", "reactome", "scidraw", "phylopic", "hdri"])
    for lib, fn in (("reactome", fetch_reactome), ("scidraw", fetch_scidraw), ("phylopic", fetch_phylopic),
                    ("hdri", fetch_hdri)):
        if lib in want:
            (CACHE / lib).mkdir(parents=True, exist_ok=True)
            fn()
    if not want & {"togotv", "bioicons", "health"}:
        return
    _fetch_original(want)


def _fetch_original(want):
    (CACHE / "togotv" / "svg").mkdir(parents=True, exist_ok=True)
    (CACHE / "repos").mkdir(parents=True, exist_ok=True)
    ua = {"User-Agent": "scientific-illustration"}
    if "togotv" in want:
        _fetch_togotv(ua)
    repos = CACHE / "repos"
    if "bioicons" in want and not (repos / "bioicons").exists():
        subprocess.run(["git", "clone", "-q", "--depth", "1", "https://github.com/duerrsimon/bioicons", str(repos / "bioicons")], check=True)
    if "health" in want and not (repos / "healthicons").exists():
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse",
                        "https://github.com/resolvetosavelives/healthicons", str(repos / "healthicons")], check=True)
        subprocess.run(["git", "-C", str(repos / "healthicons"), "sparse-checkout", "set", "public/icons/svg"], check=True)
    for k, fn in SOURCES.items():
        print(f"{k}: {sum(1 for _ in fn())} items")


def _fetch_togotv(ua):
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


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--only", nargs="+", choices=["togotv", "bioicons", "health", "reactome", "scidraw", "phylopic", "hdri"])
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
        return fetch(a.only)
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
        order = {"servier": 0, "togotv": 1, "reactome": 2, "bioicons": 3, "scidraw": 4, "health": 5, "phylopic": 6}
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
