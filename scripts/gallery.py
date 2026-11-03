"""Capability gallery: one Blender render per object type / style of render_3d.py, then a labelled contact sheet.
Show it to a new client so they can point at the look they want.
  python gallery.py --out <folder>            # write tile specs, render missing tiles, build <folder>/gallery.png
  python gallery.py --out <folder> --force    # re-render every tile
"""
import json
import subprocess
import sys
from pathlib import Path

R3D = Path(__file__).with_name("render_3d.py")
HERE = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Path.cwd() / "gallery"
AG = dict(color="#DDE2E8", stemColor="#2E8B6E", headColor="#1F6FB5")
CAM = {"camera": [5, 4.5, 8], "background": None, "fit": 0.8, "blur": 0.004}
TILES = [
    ("foam", "Porous foam scaffold", "style foam: pores within pores, cut faces as a cross-section",
     [{"type": "scaffold", "style": "foam", "size": [5, 2, 4], "pore": 0.7, "color": "#F4F6F9", "seed": 3}]),
    ("gyroid", "TPMS gyroid scaffold", "style gyroid: triply periodic minimal surface with micropores",
     [{"type": "scaffold", "style": "gyroid", "size": [5, 2, 4], "pore": 1.1, "color": "#E9D8C4", "seed": 4}]),
    ("nonwoven", "Electrospun fibre mat", "style nonwoven: SEM-like web of fine meandering fibres, cut edges",
     [{"type": "scaffold", "style": "nonwoven", "size": [5, 0.5, 4], "count": 900, "radius": 0.014, "color": "#DCEAF6",
       "seed": 2}]),
    ("struts", "Strut lattice (old style)", "style struts: the former cylinder lattice, for comparison",
     [{"type": "scaffold", "style": "struts", "size": [5, 1, 4], "cells": [8, 2, 6], "radius": 0.05, "color": "#EDEAE4",
       "seed": 2}]),
    ("hydrogel", "Hydrogel composite", "translucent gel (opacity < 1) with CNC needles, Ag NPs and drug",
     [{"type": "slab", "size": [5, 1.6, 4], "color": "#CFE5F4", "opacity": 0.6, "milk": 0.14},
      {"type": "rods", "count": 120, "length": 0.6, "lengthVar": 0.6, "radius": 0.014, "color": "#FFFFFF", "seed": 5,
       "region": [[-2.1, 2.1], [-0.55, 0.55], [-1.7, 1.7]]},
      {"type": "spheres", "count": 10, "radius": 0.24, "color": "#C9CED6", "finish": "metal", "seed": 8,
       "region": [[-2, 2], [-0.4, 0.4], [-1.5, 1.5]]},
      {"type": "spheres", "count": 25, "radius": 0.1, "color": "#3FB5C8", "seed": 9,
       "region": [[-2.1, 2.1], [-0.5, 0.5], [-1.7, 1.7]]}]),
    ("finishes", "Surface finishes", "satin, matte, frosted (SSS), metal (back); glass, gel (front)",
     [{"type": "sphere", "pos": [-3, 0, 0], "size": [0.75], "color": "#2F6FAE"},
      {"type": "sphere", "pos": [-1.2, 0, 0], "size": [0.75], "color": "#E69F00", "finish": "matte"},
      {"type": "sphere", "pos": [0.6, 0, 0], "size": [0.75], "color": "#F2EEE8", "finish": "frosted"},
      {"type": "sphere", "pos": [2.4, 0, 0], "size": [0.75], "color": "#C9CED6", "finish": "metal"},
      {"type": "sphere", "pos": [-0.9, 0, 2], "size": [0.75], "color": "#E8F1F8", "finish": "glass"},
      {"type": "sphere", "pos": [0.9, 0, 2], "size": [0.75], "color": "#9CD3EE", "opacity": 0.6}]),
    ("agnp_smooth", "Silane-capped Ag NP", "faceted core, curved ligands of varied length, steric haze",
     [dict(type="corona", radius=1.0, length=0.75, count=420, seed=2, **AG)]),
    ("agnp_atomic", "Ag NP, atomic lattice (ASE)", "Ag309 icosahedron atom by atom, ligand shell cut away",
     [dict(type="corona", core="icosahedron", shells=5, radius=1.0, length=0.75, count=420, cutaway=42, halo=False,
           seed=2, **AG)]),
    ("habits", "Metal NP habits (ASE)", "icosahedron, decahedron, truncated octahedron, cuboctahedron",
     [dict(type="corona", core=s, shells=4, radius=0.9, count=0, halo=False, pos=[x, 0, 0], color="#DDE2E8")
      for s, x in (("icosahedron", -3.3), ("decahedron", -1.1), ("octahedron", 1.1), ("cuboctahedron", 3.3))]),
    ("brush", "Grafted monolayer", "brush chains of varied length with head groups on a substrate",
     [{"type": "slab", "pos": [0, -0.3, 0], "size": [5, 0.5, 4], "color": "#D5DAE1", "finish": "frosted"},
      {"type": "brush", "count": 260, "length": 0.9, "radius": 0.02, "color": "#2E8B6E", "headColor": "#1F6FB5",
       "region": [[-2.3, 2.3], [-0.05, -0.05], [-1.8, 1.8]], "seed": 3}]),
    ("bacteria", "Bacteria", "capsule envelope with surface relief, pili and flagella",
     [{"type": "capsule", "pos": [-0.8, 0, 0], "radius": 0.55, "length": 2.2, "rot": [0, 0.3, 1.4], "color": "#6E9FD1",
       "pili": 90, "flagella": 3, "seed": 4},
      {"type": "capsule", "pos": [1.6, 0.8, -1.4], "radius": 0.5, "length": 1.8, "rot": [0.5, 0, 0.9],
       "color": "#7FB069", "pili": 60, "flagella": 2, "seed": 9}]),
    ("crystals", "Crystals", "faceted irregular crystallites (only for crystalline materials)",
     [{"type": "crystals", "count": 14, "radius": 0.35, "color": "#DCEBF7", "seed": 6,
       "region": [[-2, 2], [-0.6, 0.6], [-1.5, 1.5]]}]),
    ("molecules", "Molecules from SMILES", "APTES, GPTMS and a QAS analogue: RDKit 3D geometry, CPK colours",
     [{"type": "molecule", "smiles": "CCO[Si](CCCN)(OCC)OCC", "hydrogens": False, "pos": [-3, 0, 0], "scale": 0.45,
       "atomScale": 1.2},
      {"type": "molecule", "smiles": "CO[Si](CCCOCC1CO1)(OC)OC", "hydrogens": False, "pos": [0, 0, 0], "scale": 0.45,
       "atomScale": 1.2},
      {"type": "molecule", "smiles": "CO[Si](CCC[N+](C)(C)CCCCCCCCCC)(OC)OC", "hydrogens": False, "pos": [3.2, 0, 0],
       "scale": 0.45, "atomScale": 1.2}]),
    ("fibres_rods", "Fibres and rods", "flexible microfibres (fibers) and rigid CNC-like needles (rods, lengthVar)",
     [{"type": "fibers", "count": 30, "length": 3, "radius": 0.04, "color": "#C99A4B", "seed": 5,
       "region": [[-2.5, 1], [-0.5, 0.5], [-1.8, 0.5]]},
      {"type": "rods", "count": 26, "length": 0.9, "radius": 0.07, "color": "#2F6FAE", "align": "x", "seed": 3,
       "region": [[-2, 2], [0.9, 1.6], [-1.5, 1.5]]}]),
]
NO_SHADOW = {"agnp_smooth", "agnp_atomic", "bacteria", "crystals", "molecules"}


def render(force=False):
    (HERE / "tiles").mkdir(parents=True, exist_ok=True)
    for key, _, _, objs in TILES:
        spec = dict(CAM, title=key, objects=objs, shadow=key not in NO_SHADOW)
        if key == "habits":
            spec.update(camera=[0, 2.5, 10], fit=1.05)
        p = HERE / "tiles" / f"{key}.json"
        p.write_text(json.dumps(spec), encoding="utf-8")
        png = HERE / "tiles" / f"{key}_render.png"
        if force or not png.exists():
            r = subprocess.run([sys.executable, str(R3D), str(p), "--blender", "900x900", "--samples", "96"],
                               capture_output=True, text=True)
            print(key, "ok" if r.returncode == 0 else "FAILED " + (r.stderr or r.stdout)[-600:], flush=True)


def sheet():
    from PIL import Image, ImageDraw, ImageFont
    cols, tw, th, cap = 4, 600, 600, 110
    rows = -(-len(TILES) // cols)
    img = Image.new("RGB", (cols * tw, 200 + rows * (th + cap)), "#F5F8FB")
    d = ImageDraw.Draw(img)

    def f(s, b=False):
        return ImageFont.truetype("arialbd.ttf" if b else "arial.ttf", s)
    d.text((40, 50), "scientific-illustration: what the photoreal 3D renderer can make", font=f(46, True), fill="#123B63")
    d.text((40, 115), "Blender Cycles via render_3d.py --blender; one tile per object type or style; molecules from "
           "SMILES (RDKit), metal lattices from ASE; studio HDRI from Poly Haven (CC0)", font=f(24), fill="#4B5563")
    for i, (key, title, note, _) in enumerate(TILES):
        x, y = (i % cols) * tw, 200 + (i // cols) * (th + cap)
        png = HERE / "tiles" / f"{key}_render.png"
        if png.exists():
            t = Image.open(png).convert("RGBA").resize((tw - 20, th - 20))
            bg = Image.new("RGBA", t.size, "#FFFFFF")
            bg.alpha_composite(t)
            img.paste(bg.convert("RGB"), (x + 10, y))
        d.text((x + 20, y + th - 8), f"{i + 1}. {title}", font=f(26, True), fill="#123B63")
        line, ly = "", y + th + 28
        for w in note.split():
            if d.textlength(line + " " + w, font=f(20)) > tw - 40:
                d.text((x + 20, ly), line, font=f(20), fill="#4B5563")
                line, ly = w, ly + 25
            else:
                line = (line + " " + w).strip()
        d.text((x + 20, ly), line, font=f(20), fill="#4B5563")
    img.save(HERE / "gallery.png")
    print("gallery:", HERE / "gallery.png")


if __name__ == "__main__":
    render("--force" in sys.argv)
    sheet()
