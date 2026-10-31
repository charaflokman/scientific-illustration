#!/usr/bin/env python3
"""Build an interactive 3D scene (Three.js, one self-contained HTML) from a JSON spec.

Lightweight on purpose: no Blender, no GPU install. The page lets the user orbit/zoom
with the mouse, edit colours/labels in a side panel, and save a PNG at 1x-4x.

  python render_3d.py scene.json -o out/scene.html

Spec (all lengths in arbitrary scene units):
{
 "title": "CNC in chitosan film",
 "background": "#ffffff",
 "objects": [
  {"type": "slab", "id": "matrix", "size": [10, 1.2, 6], "color": "#56B4E9", "opacity": 0.35, "label": "Chitosan matrix"},
  {"type": "rods", "id": "cnc", "count": 60, "length": 1.2, "radius": 0.06, "color": "#E69F00",
   "region": [[-4.5,4.5],[-0.4,0.4],[-2.5,2.5]], "seed": 1, "align": "random|x", "label": "CNC"},
  {"type": "spheres", "id": "np", "count": 30, "radius": 0.15, "color": "#E69F00", "region": [...], "cluster": [x,y,z,spread]},
  {"type": "sphere|box|cylinder|torus", "id": "...", "pos": [x,y,z], "size": [...], "color": "...", "label": "..."},
  {"type": "molecule", "id": "...", "atoms": [["C",x,y,z],...], "bonds": [[0,1],...], "pos": [x,y,z], "scale": 1},
  {"type": "arrow", "from": [x,y,z], "to": [x,y,z], "color": "#000", "label": "H2O"},
  {"type": "text", "pos": [x,y,z], "text": "...", "size": 14}   (any object: "labelSize", "labelPos")
 ],
 "camera": [8, 6, 10]
}
Positions are generated deterministically from `seed`, so a re-render gives the same picture.
"""
import argparse
import json
import os
import sys
from pathlib import Path

THREE = "https://cdn.jsdelivr.net/npm/three@0.160.0"

HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>__TITLE__</title>
<style>
:root{--bg:#f6f7f9;--panel:#fff;--ink:#1d2330;--line:#d8dce3}
body{margin:0;font:13px system-ui,Segoe UI,Arial;background:var(--bg);color:var(--ink);display:flex;height:100vh}
#view{flex:1;position:relative}#view canvas{display:block}
#side{width:260px;background:var(--panel);border-left:1px solid var(--line);padding:12px;overflow:auto}
h3{margin:4px 0 10px;font-size:14px}.row{display:flex;align-items:center;gap:6px;margin:6px 0}
.row input[type=text]{flex:1;min-width:0}button{margin:3px 2px;padding:5px 8px}
.lbl{position:absolute;pointer-events:auto;cursor:text;font-weight:600;background:#ffffffcc;padding:1px 5px;border-radius:4px;white-space:nowrap;transform:translate(-50%,-50%)}
</style>
<script type="importmap">{"imports":{"three":"__THREE__/build/three.module.js","three/addons/":"__THREE__/examples/jsm/"}}</script>
</head><body><div id="view"></div><div id="side"><h3>__TITLE__</h3><div id="objs"></div>
<div class="row">Background <input type="color" id="bg"></div>
<div class="row"><label><input type="checkbox" id="lbls" checked> labels</label><label><input type="checkbox" id="spin"> auto-rotate</label></div>
<div>PNG: <button data-s="1">1x</button><button data-s="2">2x</button><button data-s="4">4x</button></div>
<button id="savejson">Save spec + edits</button>
<p style="color:#667">Drag = rotate, wheel = zoom, right-drag = pan. Double-click a label to edit it.</p></div>
<script type="module">
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
const SPEC = __SPEC__;
const view = document.getElementById('view');
const renderer = new THREE.WebGLRenderer({antialias:true, preserveDrawingBuffer:true, alpha:true});
renderer.setPixelRatio(devicePixelRatio); renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping; view.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = SPEC.background === null ? null : new THREE.Color(SPEC.background || '#ffffff');
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
const cam = new THREE.PerspectiveCamera(35, 1, 0.1, 500); cam.position.set(...(SPEC.camera || [8, 6, 10]));
const ctl = new OrbitControls(cam, renderer.domElement); ctl.enableDamping = true;
const key = new THREE.DirectionalLight(0xffffff, 1.6); key.position.set(6, 12, 8); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); Object.assign(key.shadow.camera, {left:-15, right:15, top:15, bottom:-15}); scene.add(key);
scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 0.6));
const ground = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.ShadowMaterial({opacity:0.12}));
ground.rotation.x = -Math.PI/2; ground.position.y = SPEC.ground ?? -2; ground.receiveShadow = true; scene.add(ground);

let s = 1; const rnd = seed => { s = seed || 1; return () => (s = (s * 16807) % 2147483647) / 2147483647; };
// per-object finish: "metal" (AgNP), "glass" (hydrogel/film, uses transmission), "matte"; default = satin plastic
let FIN = {};
const mat = (c, o = 1) => new THREE.MeshPhysicalMaterial(Object.assign({color:c, roughness:0.35, metalness:0.0, clearcoat:0.4,
  transparent:o < 1, opacity:o, depthWrite:o >= 1, side: o < 1 ? THREE.DoubleSide : THREE.FrontSide},
  FIN.metal ? {metalness:1, roughness:0.18, clearcoat:0} : {}, FIN.glass ? {transmission:0.85, thickness:0.6, roughness:0.15, ior:1.35, transparent:false, opacity:1, depthWrite:true} : {},
  FIN.matte ? {roughness:0.85, clearcoat:0} : {}));
const CPK = {H:'#f2f2f2', C:'#4a4a4a', N:'#3050f8', O:'#e8331f', S:'#ffd030', P:'#ff8000', Si:'#d9a066', Cl:'#1ff01f', Na:'#ab5cf2', Ca:'#3dff00', Ag:'#c0c0c0'};
const groups = {}, labels = [];
const inRegion = (r, R) => [0,1,2].map(i => r[i] ? r[i][0] + R() * (r[i][1] - r[i][0]) : 0);
function shadow(m){ m.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); return m; }

for (const o of SPEC.objects) {
  const g = new THREE.Group(); g.name = o.id || o.type; const c = o.color || '#888888';
  const R = rnd(o.seed || 7), op = o.opacity ?? 1; FIN = {metal: o.finish === 'metal', glass: o.finish === 'glass', matte: o.finish === 'matte'};
  if (o.type === 'scaffold') {   // porous strut lattice filling a box (scaffold / nonwoven substrate)
    const [sx, sy, sz] = o.size || [6, 1, 4], n = o.cells || [8, 2, 5], r = o.radius || .07, m = mat(c, op), pts = [];
    for (let i = 0; i <= n[0]; i++) for (let j = 0; j <= n[1]; j++) for (let k = 0; k <= n[2]; k++)
      pts.push(new THREE.Vector3(-sx/2 + sx*i/n[0] + (R()-.5)*sx/n[0]*.5, -sy/2 + sy*j/n[1], -sz/2 + sz*k/n[2] + (R()-.5)*sz/n[2]*.5));
    const lim = Math.max(sx/n[0], sy/Math.max(1,n[1]), sz/n[2]) * 1.5;
    for (let a = 0; a < pts.length; a++) for (let b = a+1; b < pts.length; b++) { const L = pts[a].distanceTo(pts[b]); if (L < lim && R() < .55) {
      const cyl = new THREE.Mesh(new THREE.CylinderGeometry(r, r, L, 10), m); cyl.position.copy(pts[a]).add(pts[b]).multiplyScalar(.5);
      cyl.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), pts[b].clone().sub(pts[a]).normalize()); g.add(cyl); } }
    for (const q of pts) { const sp = new THREE.Mesh(new THREE.SphereGeometry(r*1.6, 12, 8), m); sp.position.copy(q); g.add(sp); }
  }
  if (o.type === 'fibers') {     // long curved fibres (nanocellulose, electrospun fibres)
    const m = mat(c, op), reg = o.region || [[-3,3],[-.3,.3],[-2,2]];
    for (let i = 0; i < (o.count || 20); i++) { const p0 = new THREE.Vector3(...inRegion(reg, R)), d = new THREE.Vector3(R()-.5, (R()-.5)*.15, R()-.5).normalize();
      const L = o.length || 2, pts = [0, .33, .66, 1].map(t => p0.clone().addScaledVector(d, L*t).add(new THREE.Vector3((R()-.5)*.2, (R()-.5)*.1, (R()-.5)*.2)));
      g.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 24, o.radius || .03, 8, false), m)); }
  }
  if (o.type === 'brush') {      // grafted chains standing on a surface (silane monolayer, polymer brush)
    const m = mat(c), mh = mat(o.headColor || c), reg = o.region || [[-3,3],[0,0],[-2,2]], L = o.length || .4;
    for (let i = 0; i < (o.count || 80); i++) { const b = new THREE.Vector3(...inRegion(reg, R));
      const pts = [0, .35, .7, 1].map(t => b.clone().add(new THREE.Vector3(Math.sin(t*6 + i)*.04, L*t, Math.cos(t*5 + i)*.04)));
      g.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 10, o.radius || .012, 6, false), m));
      const h = new THREE.Mesh(new THREE.SphereGeometry((o.radius || .012) * 3, 10, 8), mh); h.position.copy(pts[3]); g.add(h); }
  }
  if (o.type === 'slab') g.add(new THREE.Mesh(new THREE.BoxGeometry(...o.size), mat(c, op)));
  if (o.type === 'box') g.add(new THREE.Mesh(new THREE.BoxGeometry(...(o.size || [1,1,1])), mat(c, op)));
  if (o.type === 'sphere') g.add(new THREE.Mesh(new THREE.SphereGeometry(o.size?.[0] || 0.5, 48, 32), mat(c, op)));
  if (o.type === 'cylinder') g.add(new THREE.Mesh(new THREE.CylinderGeometry(o.size?.[0] || .5, o.size?.[0] || .5, o.size?.[1] || 1, 48), mat(c, op)));
  if (o.type === 'torus') g.add(new THREE.Mesh(new THREE.TorusGeometry(o.size?.[0] || 1, o.size?.[1] || .2, 32, 96), mat(c, op)));
  if (o.type === 'rods' || o.type === 'spheres') {
    const geo = o.type === 'rods' ? new THREE.CapsuleGeometry(o.radius || .06, o.length || 1, 6, 12) : new THREE.SphereGeometry(o.radius || .15, 24, 16);
    const m = mat(c), inst = new THREE.InstancedMesh(geo, m, o.count || 30), d = new THREE.Object3D();
    for (let i = 0; i < inst.count; i++) {
      if (o.cluster) { const [x,y,z,sp] = o.cluster; d.position.set(x+(R()-.5)*sp, y+(R()-.5)*sp*.6, z+(R()-.5)*sp); }
      else d.position.set(...inRegion(o.region || [[-3,3],[-.3,.3],[-2,2]], R));
      if (o.type === 'rods') { if (o.align === 'x') d.rotation.set(0, (R()-.5)*.3, Math.PI/2 + (R()-.5)*.3); else d.rotation.set(R()*6.3, R()*6.3, R()*6.3); }
      d.updateMatrix(); inst.setMatrixAt(i, d.matrix);
    }
    g.add(inst);
  }
  if (o.type === 'molecule') {
    const sc = o.scale || 1, at = o.atoms.map(a => new THREE.Vector3(a[1], a[2], a[3]).multiplyScalar(sc));
    const RAD = {H: .2, C: .32, N: .31, O: .3, S: .4, Si: .42, Cl: .38, P: .38, Ag: .5};
    o.atoms.forEach((a, i) => { const m = new THREE.Mesh(new THREE.SphereGeometry((RAD[a[0]] || .35) * sc, 32, 20), mat(CPK[a[0]] || '#ff66cc')); m.position.copy(at[i]); g.add(m); });
    for (const [i, j, ord] of o.bonds || []) { const a = at[i], b = at[j], len = a.distanceTo(b), dir = b.clone().sub(a).normalize();
      const n = Math.round(ord || 1), side = new THREE.Vector3(0,0,1).cross(dir).normalize().multiplyScalar(.09*sc);
      for (let k = 0; k < n; k++) {  // double/triple bonds as parallel sticks
        const m = new THREE.Mesh(new THREE.CylinderGeometry((n > 1 ? .05 : .08)*sc, (n > 1 ? .05 : .08)*sc, len, 16), mat('#c4c4c4'));
        m.position.copy(a).add(b).multiplyScalar(.5).addScaledVector(side, (k - (n - 1) / 2) * 1.6);
        m.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), dir); g.add(m); } }
  }
  if (o.type === 'capsule') {  // rod-shaped bacterium or any pill shape; rot in radians
    const m = new THREE.Mesh(new THREE.CapsuleGeometry(o.radius || .4, o.length || 1.6, 12, 32), mat(c)); g.add(m);
  }
  if (o.type === 'corona') {  // nanoparticle with a shell of radial ligands (capping agent / steric stabiliser)
    const R0 = o.radius || 1, L = o.length || .6, n = o.count || 120, Rr = rnd(o.seed || 3);
    const core = new THREE.Mesh(new THREE.SphereGeometry(R0, 64, 48), mat(c)); g.add(core);
    const stem = mat(o.stemColor || '#2E8B6E'), head = mat(o.headColor || '#0072B2');
    for (let i = 0; i < n; i++) { const u = Rr()*2-1, ph = Rr()*6.283, s = Math.sqrt(1-u*u), d = new THREE.Vector3(s*Math.cos(ph), u, s*Math.sin(ph));
      const st = new THREE.Mesh(new THREE.CylinderGeometry(.025, .025, L, 8), stem); st.position.copy(d).multiplyScalar(R0 + L/2);
      st.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), d); g.add(st);
      const hd = new THREE.Mesh(new THREE.SphereGeometry(.07, 16, 12), head); hd.position.copy(d).multiplyScalar(R0 + L); g.add(hd); }
  }
  if (o.type === 'arrow') {
    const a = new THREE.Vector3(...o.from), b = new THREE.Vector3(...o.to), dir = b.clone().sub(a), L = dir.length(); dir.normalize();
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(.05, .05, L*.82, 16), mat(c)); const head = new THREE.Mesh(new THREE.ConeGeometry(.16, L*.18, 24), mat(c));
    const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,1,0), dir);
    shaft.quaternion.copy(q); head.quaternion.copy(q); shaft.position.copy(a).addScaledVector(dir, L*.41); head.position.copy(a).addScaledVector(dir, L*.91);
    g.add(shaft, head);
  }
  if (o.pos && o.type !== 'text') g.position.set(...o.pos);
  if (o.rot) g.rotation.set(...o.rot);
  scene.add(shadow(g)); groups[g.name] = {g, o};
  const text = o.type === 'text' ? o.text : o.label;
  if (text) {
    const at = o.type === 'text' ? new THREE.Vector3(...o.pos) : o.labelPos ? new THREE.Vector3(...o.labelPos)
      : o.type === 'arrow' ? new THREE.Vector3(...o.from).add(new THREE.Vector3(...o.to)).multiplyScalar(.5).add(new THREE.Vector3(0,.4,0))
      : new THREE.Box3().setFromObject(g).getCenter(new THREE.Vector3()).setY(new THREE.Box3().setFromObject(g).max.y + .5);
    const el = document.createElement('div'); el.className = 'lbl'; el.textContent = text; el.style.fontSize = (o.labelSize || (o.type === 'text' && o.size) || 14) + 'px';
    if (/\[\?/.test(text)) el.style.color = '#c00';
    el.ondblclick = () => { const t = prompt('Label', el.textContent); if (t !== null) { el.textContent = t; if (o.type === 'text') o.text = t; else o.label = t; } };
    view.appendChild(el); labels.push({el, at});
  }
}
// side panel: one colour + visibility row per object
const box = document.getElementById('objs');
for (const [n, {g, o}] of Object.entries(groups)) {
  if (o.type === 'text') continue;
  const r = document.createElement('div'); r.className = 'row';
  r.innerHTML = `<input type="checkbox" checked><input type="color" value="${o.color || '#888888'}"><span>${o.label || o.id || n}</span>`;
  r.children[0].onchange = e => { g.visible = e.target.checked; o.hidden = !e.target.checked; };
  r.children[1].oninput = e => { o.color = e.target.value; g.traverse(m => { if (m.isMesh && o.type !== 'molecule') m.material.color.set(e.target.value); }); };
  box.appendChild(r);
}
const bg = document.getElementById('bg'); bg.value = SPEC.background || '#ffffff';
bg.oninput = e => { scene.background = new THREE.Color(e.target.value); SPEC.background = e.target.value; };
document.getElementById('lbls').onchange = e => labels.forEach(l => l.el.style.display = e.target.checked ? '' : 'none');
document.getElementById('spin').onchange = e => ctl.autoRotate = e.target.checked;
// camera in the spec is a viewing direction; distance is fitted so the whole scene stays in frame at any window shape
const bb = new THREE.Box3(); for (const {g} of Object.values(groups)) bb.expandByObject(g);
const ctr = bb.getCenter(new THREE.Vector3()), rad = bb.getBoundingSphere(new THREE.Sphere()).radius * (SPEC.fit || 1.15);
const dir0 = new THREE.Vector3(...(SPEC.camera || [8, 6, 10])).normalize(); ctl.target.copy(ctr);
let fitted = false;
function resize(){ const w = view.clientWidth, h = view.clientHeight; renderer.setSize(w, h); cam.aspect = w / h; cam.updateProjectionMatrix();
  if (!fitted) { const f = THREE.MathUtils.degToRad(cam.fov) / 2, d = rad / Math.sin(Math.min(f, Math.atan(Math.tan(f) * cam.aspect)));
    cam.position.copy(ctr).addScaledVector(dir0, d); fitted = true; } }
addEventListener('resize', resize); resize();
const v = new THREE.Vector3();
function placeLabels(){ for (const l of labels) { v.copy(l.at).project(cam); l.el.style.left = (v.x*.5+.5)*view.clientWidth + 'px'; l.el.style.top = (-v.y*.5+.5)*view.clientHeight + 'px'; } }
(function loop(){ requestAnimationFrame(loop); ctl.update(); renderer.render(scene, cam); placeLabels(); })();
// PNG export at k x resolution, labels drawn into the image
for (const b of document.querySelectorAll('[data-s]')) b.onclick = () => {
  const k = +b.dataset.s, w = view.clientWidth, h = view.clientHeight;
  renderer.setPixelRatio(k * devicePixelRatio); renderer.setSize(w, h); renderer.render(scene, cam);
  const c = document.createElement('canvas'); c.width = renderer.domElement.width; c.height = renderer.domElement.height;
  const x = c.getContext('2d'), f = c.width / w; x.drawImage(renderer.domElement, 0, 0);
  if (document.getElementById('lbls').checked) for (const l of labels) { if (l.el.style.display === 'none') continue;
    const fs = parseFloat(l.el.style.fontSize) * f; x.font = `600 ${fs}px system-ui,Arial`; x.textAlign = 'center'; x.textBaseline = 'middle';
    const px = parseFloat(l.el.style.left) * f, py = parseFloat(l.el.style.top) * f, tw = x.measureText(l.el.textContent).width;
    x.fillStyle = '#ffffffcc'; x.fillRect(px - tw/2 - 5*f, py - fs*.7, tw + 10*f, fs*1.4); x.fillStyle = l.el.style.color || '#1d2330'; x.fillText(l.el.textContent, px, py); }
  const a = document.createElement('a'); a.download = (SPEC.name || 'scene') + `_${k}x.png`; a.href = c.toDataURL('image/png'); a.click();
  renderer.setPixelRatio(devicePixelRatio); resize();
};
document.getElementById('savejson').onclick = () => {
  SPEC.camera = cam.position.clone().sub(ctl.target).toArray().map(n => +n.toFixed(2));
  const a = document.createElement('a'); a.download = (SPEC.name || 'scene') + '.json';
  a.href = URL.createObjectURL(new Blob([JSON.stringify(SPEC, null, 1)], {type:'application/json'})); a.click();
};
if (location.hash === '#export') { document.body.style.background = 'transparent'; document.getElementById('side').style.display = 'none'; labels.forEach(l => l.el.style.display = 'none'); ground.visible = SPEC.shadow !== false; resize(); fitted = false; resize(); }
window.__ready = true;
</script></body></html>"""


def embed_smiles(o):
    """Molecule objects may give "smiles" instead of atoms: RDKit builds a force-field-optimised 3D geometry, so bond
    lengths and angles are chemically right. "hydrogens": false hides H; "bond_orders" draws double/triple bonds."""
    from rdkit import Chem
    from rdkit.Chem import AllChem
    m = Chem.AddHs(Chem.MolFromSmiles(o["smiles"]))
    AllChem.EmbedMolecule(m, randomSeed=o.get("seed", 7))
    try:
        AllChem.MMFFOptimizeMolecule(m)
    except Exception:
        AllChem.UFFOptimizeMolecule(m)
    if o.get("extended", True):  # all-anti chains: no gauche kinks that read as fake rings in a 2D view
        from rdkit.Chem import rdMolTransforms as T
        conf0 = m.GetConformer()
        for bd in m.GetBonds():
            i, j = bd.GetBeginAtom(), bd.GetEndAtom()
            if bd.IsInRing() or bd.GetBondTypeAsDouble() != 1 or i.GetDegree() < 2 or j.GetDegree() < 2:
                continue
            a0 = next((n.GetIdx() for n in i.GetNeighbors() if n.GetIdx() != j.GetIdx() and n.GetSymbol() != "H"), None)
            d0 = next((n.GetIdx() for n in j.GetNeighbors() if n.GetIdx() != i.GetIdx() and n.GetSymbol() != "H"), None)
            if a0 is not None and d0 is not None:
                try:
                    T.SetDihedralDeg(conf0, a0, i.GetIdx(), j.GetIdx(), d0, 180.0)
                except Exception:
                    pass
    keep = [a.GetIdx() for a in m.GetAtoms() if o.get("hydrogens", True) or a.GetSymbol() != "H"]
    idx = {k: i for i, k in enumerate(keep)}
    conf = m.GetConformer()
    c = [sum(conf.GetAtomPosition(k)[d] for k in keep) / len(keep) for d in range(3)]
    P = {k: [conf.GetAtomPosition(k)[d] for d in range(3)] for k in keep}
    if "anchor" in o:  # stand the molecule up: anchor atom (SMILES order) at the origin, body pointing +y
        import numpy as np
        ax = np.array(P[o["anchor"]])
        X = np.array([P[k] for k in keep]) - ax
        v = X.mean(0)
        v /= np.linalg.norm(v) or 1
        y = np.array([0.0, 1.0, 0.0])
        w = np.cross(v, y)
        s, cth = np.linalg.norm(w), float(v @ y)
        if s < 1e-8:
            R = np.eye(3) if cth > 0 else np.diag([1.0, -1.0, -1.0])
        else:
            K = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]]) / s
            R = np.eye(3) + s * K + (1 - cth) * K @ K
        X = X @ R.T
        P = {k: list(X[i]) for i, k in enumerate(keep)}
        c = [0.0, 0.0, 0.0]
    o["atoms"] = [[m.GetAtomWithIdx(k).GetSymbol()] + [round(P[k][d] - c[d], 3) for d in range(3)] for k in keep]
    o["bonds"] = [[idx[b.GetBeginAtomIdx()], idx[b.GetEndAtomIdx()], int(b.GetBondTypeAsDouble())] for b in m.GetBonds()
                  if b.GetBeginAtomIdx() in idx and b.GetEndAtomIdx() in idx]


CLUSTER = r"""
import json, sys
from ase.cluster import Icosahedron, Decahedron, Octahedron
el, shape, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
a = {"icosahedron": lambda: Icosahedron(el, noshells=n),
     "decahedron": lambda: Decahedron(el, p=n, q=1, r=0),
     "octahedron": lambda: Octahedron(el, length=2 * n + 1, cutoff=n),   # truncated octahedron
     "cuboctahedron": lambda: Octahedron(el, length=2 * n + 1, cutoff=n + 1)}[shape]()
a.center(about=(0, 0, 0))
print(json.dumps({"atoms": [[s, *map(float, p)] for s, p in zip(a.get_chemical_symbols(), a.positions)]}))
"""


def embed_cluster(o):
    """corona/nanoparticle with "core": "icosahedron" | "decahedron" | "octahedron" | "cuboctahedron": ASE builds the
    real metal lattice (fcc, multiply twinned or truncated) atom by atom; it is scaled so its outer radius = "radius"."""
    import subprocess
    venv = Path.home() / ".cache" / "scientific-illustration" / "venvs" / "atomistic"
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not py.exists():
        print(f"ASE venv missing ({venv}); {o.get('id')} keeps a smooth core. See setup_check.py")
        return
    r = subprocess.run([str(py), "-I", "-c", CLUSTER, o.get("element", "Ag"), o["core"], str(o.get("shells", 4))],
                       capture_output=True, text=True, check=True)
    atoms = json.loads(r.stdout)["atoms"]
    rmax = max((x * x + y * y + z * z) ** .5 for _, x, y, z in atoms) or 1
    metallic = {"Ag": 1.445, "Au": 1.442, "Pt": 1.387, "Cu": 1.278, "Pd": 1.376}.get(o.get("element", "Ag"), 1.4)  # Å
    k = o.get("radius", 1) / (rmax + metallic)       # outer atom surfaces touch the requested radius
    o["clusterAtoms"] = [[s, round(x * k, 4), round(y * k, 4), round(z * k, 4)] for s, x, y, z in atoms]
    o["clusterAtomRadius"] = round(metallic * k, 4)


def photo_finish(png, spec):
    """What a macro lens adds and a renderer does not: bloom around highlights, fine sensor grain, a faint vignette.
    Alpha is kept, so transparent renders still composite. "photo": false skips it; "grain", "bloom", "vignette" tune."""
    import numpy as np
    from PIL import Image, ImageFilter
    im = Image.open(png).convert("RGBA")
    a = np.asarray(im).astype(np.float32) / 255
    rgb, al = a[..., :3], a[..., 3:]
    h, w = al.shape[:2]
    hi = np.clip((rgb.max(-1, keepdims=True) - .82) / .18, 0, 1) * rgb * al
    glow = np.asarray(Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(w / 160))) / 255
    rgb = rgb + glow * spec.get("bloom", .35) * (1 - rgb)
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2))[..., None]
    rgb = rgb * (1 - spec.get("vignette", .1) * np.clip(r - .45, 0, 1) ** 2)
    rng = np.random.default_rng(7)
    rgb = rgb + rng.normal(0, spec.get("grain", .012), (h, w, 1)) * al
    out = np.concatenate([np.clip(rgb, 0, 1), al], -1)
    Image.fromarray((out * 255 + .5).astype(np.uint8), "RGBA").save(png)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("-o", "--out")
    ap.add_argument("--blender", metavar="WxH", help="photoreal PNG with Blender Cycles (GPU if available), e.g. 2400x1700")
    ap.add_argument("--samples", type=int, default=192, help="Cycles samples for --blender (more = cleaner, slower)")
    ap.add_argument("--png", metavar="WxH", help="also render a transparent PNG without labels, e.g. 2400x1600 (for compositing)")
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    spec.setdefault("name", Path(a.spec).stem)
    for o in spec["objects"]:
        if o.get("type") == "molecule" and o.get("smiles") and not o.get("atoms"):
            embed_smiles(o)
        if o.get("type") == "corona" and o.get("core") in ("icosahedron", "decahedron", "octahedron", "cuboctahedron") \
                and not o.get("clusterAtoms"):
            embed_cluster(o)
    out = Path(a.out or Path(a.spec).with_suffix(".html"))
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(spec, ensure_ascii=False).replace("</", "<\\/")
    title = spec.get("title", spec["name"]).replace("<", "&lt;")
    out.write_text(HTML.replace("__THREE__", THREE).replace("__TITLE__", title).replace("__SPEC__", payload), encoding="utf-8")
    ph = [o.get("label") or o.get("text") for o in spec["objects"] if "[?" in str(o.get("label") or o.get("text") or "")]
    print(f"3D scene: {out.resolve()}")
    if ph:
        print("placeholders to confirm:", "; ".join(ph))
    if a.blender:
        import shutil
        import subprocess
        exe = os.environ.get("BLENDER") or shutil.which("blender") or next(
            (str(p) for p in sorted(Path(os.environ.get("ProgramFiles", "C:/Program Files"), "Blender Foundation").glob("Blender*/blender.exe"))[::-1]), None)
        if not exe:
            sys.exit("Blender not found: install it (blender.org) or set BLENDER=path/to/blender")
        resolved = out.with_suffix(".resolved.json")
        resolved.write_text(json.dumps(spec), encoding="utf-8")
        w, h = a.blender.lower().split("x")
        png = out.with_name(out.stem + "_render.png").resolve()
        r = subprocess.run([exe, "-b", "--factory-startup", "-P", str(Path(__file__).with_name("render_blender.py")), "--",
                            str(resolved.resolve()), str(png), w, h, str(a.samples)], capture_output=True, text=True)
        line = [l for l in r.stdout.splitlines() if l.startswith("BLENDER_PNG")]
        if not line:
            sys.exit("Blender render failed: " + (r.stderr or r.stdout)[-2500:])
        if spec.get("photo", True):
            photo_finish(png, spec)
        print("Photoreal PNG:", png, "(" + line[0].split()[-1] + ")")
    if a.png:
        w, h = (int(v) for v in a.png.lower().split("x"))
        from playwright.sync_api import sync_playwright
        sys.path.insert(0, str(Path(__file__).parent))
        from export import launch
        png = out.with_suffix(".png")
        with sync_playwright() as p:
            br = launch(p)
            pg = br.new_page(viewport={"width": w // 2, "height": h // 2}, device_scale_factor=2)
            pg.goto(out.resolve().as_uri() + "#export")
            pg.wait_for_function("window.__ready === true", timeout=60000)
            pg.wait_for_timeout(1500)
            pg.locator("#view canvas").screenshot(path=str(png), omit_background=True)
            br.close()
        print(f"PNG: {png.resolve()}")


if __name__ == "__main__":
    main()
