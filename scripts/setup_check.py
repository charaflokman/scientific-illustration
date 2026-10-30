#!/usr/bin/env python3
"""Report which scientific-illustration dependencies are available and how to install the missing ones.

  python setup_check.py
Nothing is installed automatically.
"""
import importlib
import os
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


def main():
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
