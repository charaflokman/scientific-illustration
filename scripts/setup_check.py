#!/usr/bin/env python3
"""Report which scientific-illustration dependencies are available and how to install the missing ones.

  python setup_check.py
Nothing is installed automatically.
"""
import importlib
import os
import tempfile
import subprocess
import shutil
import sys
from pathlib import Path

PY_MODULES = [
    ("matplotlib", "plots (plot_data.py)", "pip install matplotlib"),
    ("pandas", "CSV/XLSX reading", "pip install pandas openpyxl"),
    ("numpy", "numerics", "pip install numpy"),
    ("scipy", "fitting / peak finding", "pip install scipy"),
    ("scienceplots", "journal matplotlib styles (optional)", "pip install SciencePlots"),
    ("rdkit", "molecule drawing (optional)", "pip install rdkit"),
    ("playwright", "SVG -> PNG/PDF export and layout check", "pip install playwright  (uses installed Chrome/Edge)"),
]


# pip package to install per module (Windows PyMOL: the wheel that bundles its DLLs)
PIP_NAMES = {"pymol": "pymol-open-source-whl" if os.name == "nt" else "pymol-open-source", "PyScaffolder": "PyScaffolder numpy"}


def find_browser():
    cands = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
             r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    for c in cands:
        if Path(c).exists():
            return c
    for n in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge"):
        if shutil.which(n):
            return shutil.which(n)
    return None


CACHE = Path.home() / ".cache" / "scientific-illustration"
REPORT = CACHE / "setup_report.txt"


def find_blender():
    exe = os.environ.get("BLENDER") or shutil.which("blender")
    if exe:
        return exe
    root = Path(os.environ.get("ProgramFiles", "C:/Program Files"), "Blender Foundation")
    found = sorted(root.glob("Blender*/blender.exe"))
    if found:
        return str(found[-1])
    mac = Path("/Applications/Blender.app/Contents/MacOS/Blender")
    return str(mac) if mac.exists() else None


def blender_extension(name):
    """Installed Blender extensions live in the user config folder, one subfolder per id."""
    bases = [Path(os.environ.get("APPDATA", ""), "Blender Foundation", "Blender"),
             Path.home() / "Library" / "Application Support" / "Blender", Path.home() / ".config" / "blender"]
    for b in bases:
        for p in sorted(b.glob(f"*/extensions/*/{name}")):
            return p
    return None


def heavy_tools():
    """3D, render and art-library tools; each line says what it adds and how to get it."""
    out = []
    b = find_blender()
    out.append((bool(b), "blender", b or "missing (photoreal renders via render_3d.py --blender). Install: blender.org, or set BLENDER"))
    gpu = shutil.which("nvidia-smi")
    out.append((bool(gpu), "nvidia gpu", "found (Cycles uses OptiX/CUDA)" if gpu else "not found: Cycles renders on CPU (slower, same result)"))
    mn = blender_extension("molecularnodes")
    out.append((bool(mn), "molecular nodes", str(mn) if mn else
                "missing (Blender add-on, GPL-3.0: proteins/PDB structures). Get the build matching your Blender from "
                "github.com/BradyAJohnston/MolecularNodes/releases, then: blender -b --command extension install-file -r user_default -e <zip>"))
    hdr = sorted((CACHE / "hdri").glob("*.hdr"))
    out.append((bool(hdr), "studio hdri", f"{len(hdr)} files (Poly Haven, CC0)" if hdr else "missing: python library.py fetch --only hdri"))
    for lib in ("servier", "togotv", "reactome", "phylopic", "scidraw", "repos/bioicons", "repos/healthicons"):
        ok = (CACHE / lib).exists() and any((CACHE / lib).iterdir())
        out.append((ok, lib.split("/")[-1], "cached" if ok else f"missing: python library.py fetch --only {lib.split('/')[-1].replace('healthicons', 'health')}"))
    for ext, what in (("atomic_blender_cluster", "nanoparticles/clusters"), ("atomic_blender_pdb_xyz", "PDB/XYZ import"),
                      ("blentom", "ASE structures, orbitals")):
        p = blender_extension(ext)
        out.append((bool(p), ext, str(p) if p else f"missing (Blender add-on, {what}): extensions.blender.org or the project's GitHub"))
    for venv, mod, lic in (("scaffold", "PyScaffolder", "MIT, TPMS scaffolds"), ("microgen", "microgen", "GPL-3.0, TPMS meshes"),
                           ("atomistic", "ase", "LGPL, metal NP lattices for render_3d.py"), ("atomistic", "ovito", "MIT, atomistic rendering"),
                           ("pymol", "pymol", "open-source PyMOL, proteins"), ("vase", "v_ase", "AGPL, ASE viewer + Blender export"),
                           ("cellpack", "cellpack", "MIT, mesoscale cell packing; Python 3.9")):
        py = CACHE / "venvs" / venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        site = list((CACHE / "venvs" / venv).glob("**/site-packages"))
        ok = py.exists() and any(p.name.lower().startswith(mod.lower()) for s in site for p in s.iterdir())
        if ok:  # a folder is not enough: PyMOL once installed without its DLLs, PyScaffolder without numpy
            try:
                r = subprocess.run([str(py), "-I", "-c", f"import {mod}"], capture_output=True, text=True, timeout=120,
                                   cwd=tempfile.gettempdir())  # cellpack writes ./.creds on import
                ok, err = r.returncode == 0, (r.stderr.strip().splitlines() or [""])[-1]
            except Exception as e:
                ok, err = False, str(e)
        pkg = PIP_NAMES.get(mod, mod)
        out.append((ok, mod.lower(), f"venv {py.parent.parent} ({lic})" if ok else
                    f"broken: {err} -> <venv python> -m pip install {pkg}" if py.exists() and site else
                    f"missing (optional): python -m venv {CACHE / 'venvs' / venv} && <venv python> -m pip install {pkg}"))
    rem = (CACHE / "remotion" / "node_modules").exists()
    out.append((rem, "remotion", "ready (render_video.py)" if rem else "missing: render_video.py installs it on first use (needs node)"))
    node = shutil.which("node")
    out.append((bool(node), "node", node or "missing (video and 3D page export). Install: nodejs.org"))
    return out


def main():
    if "--first-run" in sys.argv and REPORT.exists():
        import time
        age = (time.time() - REPORT.stat().st_mtime) / 86400
        if age < 30:
            print(f"Tools checked {age:.0f} days ago (report: {REPORT}). Run without --first-run to check again.")
            print(REPORT.read_text(encoding="utf-8"))
            return
    lines = []
    real_print = print

    def say(*a):
        line = " ".join(str(x) for x in a)
        lines.append(line)
        real_print(line)
    globals()["print"] = say
    try:
        core()
        print("3D, rendering and art libraries:")
        for ok, name, note in heavy_tools():
            print(f"  {'OK ' if ok else '-- '}  {name:15s} {note}")
    finally:
        globals()["print"] = real_print
    CACHE.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def core():
    print(f"Python {sys.version.split()[0]} at {sys.executable}")
    for mod, why, how in PY_MODULES:
        try:
            m = importlib.import_module(mod)
            print(f"  OK   {mod:13s} {getattr(m, '__version__', '')}  - {why}")
        except Exception:
            print(f"  --   {mod:13s} missing - {why}.  Install: {how}")
    b = find_browser()
    print(f"  {'OK ' if b else '-- '}  browser       {b or 'none found (needed for export.py and mermaid). Install Chrome, or: python -m playwright install chromium'}")
    mmdc = os.environ.get("RV_MMDC") or shutil.which("mmdc")
    print(f"  {'OK ' if mmdc else '-- '}  mermaid-cli   {mmdc or 'missing. Install: npm install -g @mermaid-js/mermaid-cli  (or set RV_MMDC; npx works too)'}")
    d2 = os.environ.get("RV_D2") or shutil.which("d2")
    print(f"  {'OK ' if d2 else '-- '}  d2            {d2 or 'missing (optional). Windows: winget install Terrastruct.D2 ; or download from github.com/terrastruct/d2/releases; set RV_D2'}")
    dot = shutil.which("dot")
    print(f"  {'OK ' if dot else '-- '}  graphviz      {dot or 'missing (optional). Windows: winget install Graphviz.Graphviz'}")
    print("Figure mode needs only Python + a browser for export; render_figure.py itself is pure Python.")


if __name__ == "__main__":
    main()
