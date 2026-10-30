#!/usr/bin/env python3
"""Search and fetch professional medical/biology drawings from a local Servier Medical Art library.

Servier Medical Art (smart.servier.com) is hand-drawn by medical illustrators and licensed CC BY 4.0
(free, also commercial, credit required). It is the closest free match to BioRender's look, so use it for
anatomy, skin/wounds, cells, bacteria, viruses, organelles and lab equipment; keep code-drawn icons for
materials-science parts (films, fillers, networks) that Servier does not cover.

One-time library build (Windows + PowerPoint; about 2 min per set):
  python servier.py fetch Dermatology Infectiology Intracellular-components Medical-equipment
  # downloads SMART-<set>.pptx from smart.servier.com into the cache, then runs servier_extract.ps1
Use:
  python servier.py search skin ulcer keratinocyte      # list drawings (set, slide title, nearby label, size)
  python servier.py get Dermatology/Dermatology_s4_1.png --to figdir/art --w 80
      # copies the PNG and prints a ready "image" element with licence fields and the correct aspect ratio
Other set names: see https://smart.servier.com/smart_pptx/ (e.g. Cellular-biology, Immunology, Tissues,
Blood-and-immunology, Lab-equipment...). Only the set file names are requested; nothing about the user's work is sent.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

CACHE = Path(os.environ.get("RV_CACHE", Path.home() / ".cache" / "scientific-illustration")) / "servier"
URL = "https://smart.servier.com/wp-content/uploads/2016/10/SMART-{}.pptx"
LIC = {"license": "cc-by-4.0", "author": "Servier Medical Art", "source": "https://smart.servier.com (CC BY 4.0)"}


def catalog():
    f = CACHE / "catalog.json"
    if not f.exists():
        sys.exit("No library yet: run  python servier.py fetch Dermatology Infectiology ...")
    data = json.loads(f.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, list) else [data]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("sets", nargs="+")
    s = sub.add_parser("search")
    s.add_argument("terms", nargs="+")
    g = sub.add_parser("get")
    g.add_argument("file")
    g.add_argument("--to", default="art")
    g.add_argument("--w", type=float, default=40, help="width in mm for the printed element")
    a = ap.parse_args()

    if a.cmd == "fetch":
        raw = CACHE / "raw"
        raw.mkdir(parents=True, exist_ok=True)
        for name in a.sets:
            if not re.fullmatch(r"[A-Za-z0-9\-]+", name):
                sys.exit(f"bad set name {name}")
            out = raw / f"SMART-{name}.pptx"
            if not out.exists():
                req = urllib.request.Request(URL.format(name), headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=300) as r:
                    data = r.read()
                if data[:2] != b"PK":
                    sys.exit(f"{name}: not a pptx (check the set name on smart.servier.com/smart_pptx)")
                out.write_bytes(data)
                print(f"downloaded {out.name} ({len(data) // 1024} KB)")
        ps1 = Path(__file__).with_name("servier_extract.ps1")
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps1), "-Raw", str(raw), "-Out", str(CACHE)], check=True)
        return

    if a.cmd == "search":
        terms = [t.lower() for t in a.terms]
        hits = [e for e in catalog() if any(t in f"{e['set']} {e['title']} {e['label']}".lower() for t in terms)]
        for e in hits:
            print(f"{e['file']:<48} {e['title'][:28]:<28} | {e['label'][:30]:<30} {e['w']}x{e['h']}")
        print(f"{len(hits)} match(es). Look at candidates before choosing (Read the PNG) - names come from nearby slide text.")
        return

    rel = a.file.replace("\\", "/")
    if ".." in rel:
        sys.exit("bad path")
    src = CACHE / rel
    e = next((x for x in catalog() if x["file"] == rel), None)
    if not src.exists() or e is None:
        sys.exit("not in library; use search first")
    to = Path(a.to)
    to.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, to / src.name)
    h = a.w * e["h"] / e["w"]
    el = {"type": "image", "id": src.stem.lower(), "path": str(to / src.name).replace("\\", "/"),
          "x": 0, "y": 0, "w": a.w, "h": round(h, 1), **LIC}
    print(f"copied {to / src.name}\nspec element: {json.dumps(el)}")


if __name__ == "__main__":
    main()
