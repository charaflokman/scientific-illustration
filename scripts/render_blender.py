"""Photoreal render of a render_3d.py scene spec with Blender Cycles (runs inside Blender, headless).

Called by `render_3d.py scene.json --blender 2400x1700`; it embeds SMILES first, then runs
  blender -b --factory-startup -P render_blender.py -- scene.resolved.json out.png 2400 1700 [samples]
The layout uses the same seeded random sequence as the Three.js page, so placements match the interactive version;
the look is a modern studio render: every object gets surface and structural detail of its own.

  scaffold  style "foam" (default): open-cell foam with pores inside pores (Geometry Nodes volume -> mesh),
            "gyroid": TPMS sheet with micro-pores, "nonwoven": layered mat of curved fibres of varied diameter,
            "struts": the old strut lattice. Cut faces at the box bounds read as a cross-section.
  slab/box  rounded, bevelled; opacity < 1 or finish "glass"/"gel" -> milky gel (glass surface + scattering volume,
            "milk" sets the turbidity); otherwise frosted/satin with a fine surface bump
  spheres   finish "metal": polished silver with micro-roughness
  corona    metal core + curved ligand chains of varied length with head groups
  brush     grafted chains of varied length, slightly bent, with heads
  capsule   bacterium: wrinkled subsurface-scattering envelope, optional "pili": n and "flagella": n
  crystals  faceted, irregular crystals ("count", "radius", "region"), frosted glass
  molecule  CPK atoms with a clear coat, bonds split in the two atom colours, multiple bonds offset
Studio light: large soft key, cool fill, warm rim, soft contact shadow (shadow catcher), AgX, depth of field.
`background: null` renders with a transparent background (for insets and compositing).
Coordinates stay Three.js-style (y up) under a root object rotated into Blender's z-up.
"""
import json
import math
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
SPEC = json.load(open(args[0], encoding="utf-8"))
OUT, W, H = args[1], int(args[2]), int(args[3])
SAMPLES = int(args[4]) if len(args) > 4 else 192

# Jmol CPK colours (C darkened for print); metals in their Jmol hue, never the pink "unknown" colour.
CPK = {"H": "#f2f2f2", "C": "#4a4d55", "N": "#3b5bf0", "O": "#e8402a", "S": "#ffd030", "P": "#ff8000", "Si": "#e0a868",
       "F": "#90e050", "Cl": "#3fd04a", "Br": "#a62929", "I": "#940094", "B": "#ffb5b5", "Li": "#cc80ff",
       "Na": "#ab5cf2", "K": "#8f40d4", "Mg": "#8aff00", "Ca": "#3dff00", "Al": "#bfa6a6", "Ti": "#bfc2c7",
       "Mn": "#9c7ac7", "Fe": "#e06633", "Co": "#f090a0", "Ni": "#50d050", "Cu": "#c88033", "Zn": "#7d80b0",
       "Se": "#ffa100", "Zr": "#94e0e0", "Ag": "#c8ccd2", "Ce": "#e8e8b0", "Pt": "#d0d0e0", "Au": "#ffd123"}
RAD = {"H": .2, "C": .32, "N": .32, "O": .31, "S": .4, "Si": .42, "Cl": .38, "P": .38, "Ag": .5,
       "F": .3, "Br": .42, "I": .48, "B": .34, "Li": .45, "Na": .5, "K": .55, "Mg": .45, "Ca": .5, "Al": .45,
       "Ti": .46, "Mn": .44, "Fe": .44, "Co": .43, "Ni": .43, "Cu": .44, "Zn": .44, "Se": .42, "Zr": .48,
       "Ce": .52, "Pt": .48, "Au": .5}


def cpk(e):
    if e not in CPK:
        print(f"warning: no CPK colour for element {e}; using neutral grey")
    return CPK.get(e, "#9aa0a6")


# -- seeded random, identical to the page: s = s * 16807 % (2^31 - 1) ---------------------------------------------
class Rnd:
    def __init__(self, seed):
        self.s = seed or 1

    def __call__(self):
        self.s = (self.s * 16807) % 2147483647
        return self.s / 2147483647


def in_region(r, R):
    return Vector([r[i][0] + R() * (r[i][1] - r[i][0]) if r[i] else 0 for i in range(3)])


def hexcol(h, a=1.0):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, a)


def perp(d):
    p = d.cross(Vector((0, 1, 0)))
    return (p if p.length > 1e-4 else d.cross(Vector((1, 0, 0)))).normalized()


# -- materials ------------------------------------------------------------------------------------------------------
_mats = {}


def _bump(nt, b, scale, strength, distance, voronoi=False):
    """Fine surface relief from object-space noise (optionally with a cellular voronoi layer)."""
    N, L = nt.nodes, nt.links.new
    tc = N.new("ShaderNodeTexCoord")
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 8
    nz.inputs["Roughness"].default_value = .6
    L(tc.outputs["Object"], nz.inputs["Vector"])
    h = nz.outputs["Factor"]
    if voronoi:
        vo = N.new("ShaderNodeTexVoronoi")
        vo.feature = "SMOOTH_F1"
        vo.inputs["Scale"].default_value = scale * .55
        L(tc.outputs["Object"], vo.inputs["Vector"])
        mx = N.new("ShaderNodeMath")
        mx.operation = "MULTIPLY_ADD"
        L(vo.outputs["Distance"], mx.inputs[0])
        mx.inputs[1].default_value = .8
        L(h, mx.inputs[2])
        h = mx.outputs["Value"]
    bu = N.new("ShaderNodeBump")
    bu.inputs["Strength"].default_value = strength
    bu.inputs["Distance"].default_value = distance
    L(h, bu.inputs["Height"])
    L(bu.outputs["Normal"], b.inputs["Normal"])
    return nz


def _vary(nt, b, rough, hue=.012, val=.14, rvar=.1, ao=0.0):
    """Photographic variation: each primitive (mesh island, fibre, particle) gets its own tint and roughness,
    roughness drifts in broad smudges across a surface, and cavities darken by ambient occlusion."""
    N, L = nt.nodes, nt.links.new
    g = N.new("ShaderNodeNewGeometry")
    rnd = g.outputs["Random Per Island"]
    hs = N.new("ShaderNodeHueSaturation")
    hs.inputs["Color"].default_value = b.inputs["Base Color"].default_value[:]
    for sock, amp in (("Hue", hue), ("Value", val)):
        mm = N.new("ShaderNodeMapRange")
        L(rnd, mm.inputs["Value"])
        mm.inputs["To Min"].default_value = (.5 if sock == "Hue" else 1) - amp
        mm.inputs["To Max"].default_value = (.5 if sock == "Hue" else 1) + amp
        L(mm.outputs["Result"], hs.inputs[sock])
    colour = hs.outputs["Color"]
    if ao:
        occ = N.new("ShaderNodeAmbientOcclusion")
        occ.inputs["Distance"].default_value = ao
        L(colour, occ.inputs["Color"])
        mix = N.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = .55
        sock = {x.identifier: x for x in mix.inputs}
        L(colour, sock["A_Color"])
        L(occ.outputs["AO"], sock["B_Color"])
        colour = next(x for x in mix.outputs if x.identifier == "Result_Color")
    L(colour, b.inputs["Base Color"])
    tc = N.new("ShaderNodeTexCoord")
    sm = N.new("ShaderNodeTexNoise")
    sm.inputs["Scale"].default_value = 1.6
    sm.inputs["Detail"].default_value = 3
    L(tc.outputs["Object"], sm.inputs["Vector"])
    add = N.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    L(sm.outputs["Factor"], add.inputs[0])
    add.inputs[1].default_value = rvar
    add.inputs[2].default_value = rough - rvar / 2
    add2 = N.new("ShaderNodeMath")
    add2.operation = "MULTIPLY_ADD"
    L(rnd, add2.inputs[0])
    add2.inputs[1].default_value = rvar * .6
    L(add.outputs[0], add2.inputs[2])
    L(add2.outputs[0], b.inputs["Roughness"])


def mat(color, kind=None, opacity=1.0, milk=.35):
    """kind: metal | glass/gel | frosted | matte | bio | atom | None (satin with clear coat). Opacity < 1 -> gel."""
    if opacity < .95 and kind in (None, "matte"):
        kind = "gel"
    key = (color, kind, round(opacity, 2), milk)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"m{len(_mats)}_{kind}")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    col = hexcol(color)
    b.inputs["Base Color"].default_value = col
    b.inputs["Subsurface Radius"].default_value = (1.0, .6, .4)
    if kind == "metal":
        b.inputs["Base Color"].default_value = hexcol("#dfe2e6") if color.lower() in ("#c9ced6", "#dde2e8", "#c0c0c0") else col
        b.inputs["Metallic"].default_value = 1.0
        # micro-roughness: polished but not a mirror, with faint polishing marks
        nz = _bump(nt, b, 60, .08, .002)
        mr = nt.nodes.new("ShaderNodeMapRange")
        nt.links.new(nz.outputs["Factor"], mr.inputs["Value"])
        mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = .06, .26
        nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
        b.inputs["Anisotropic"].default_value = .25
    elif kind == "glass":
        b.inputs["Transmission Weight"].default_value = 1.0
        b.inputs["Roughness"].default_value = .05
        b.inputs["IOR"].default_value = 1.45
    elif kind == "gel":
        # hydrogel, not glass: water's IOR, weak and soft highlights, a cloudy scattering body, an uneven skin.
        # Embedded fibres and particles still show, softened by depth.
        b.inputs["Transmission Weight"].default_value = .96
        b.inputs["Roughness"].default_value = .07
        b.inputs["IOR"].default_value = 1.33
        b.inputs["Specular IOR Level"].default_value = .4
        b.inputs["Subsurface Weight"].default_value = .04
        b.inputs["Subsurface Scale"].default_value = .2
        b.inputs["Sheen Weight"].default_value = .2
        b.inputs["Sheen Roughness"].default_value = .6
        b.inputs["Sheen Tint"].default_value = tuple(.6 + .4 * c for c in col[:3]) + (1,)
        _bump(nt, b, 3.5, .12, .03)  # broad, soft undulation of a swollen surface
        vol = nt.nodes.new("ShaderNodeVolumePrincipled")
        vol.inputs["Color"].default_value = tuple(.6 + .4 * c for c in col[:3]) + (1,)
        vol.inputs["Density"].default_value = milk
        vol.inputs["Anisotropy"].default_value = .15
        vol.inputs["Absorption Color"].default_value = col
        nt.links.new(vol.outputs["Volume"], nt.nodes["Material Output"].inputs["Volume"])
    elif kind == "haze":  # volume only, no surface: a soft glow-free scattering shell (solvated layers, halos)
        nt.nodes.remove(b)
        vol = nt.nodes.new("ShaderNodeVolumePrincipled")
        vol.inputs["Color"].default_value = col
        vol.inputs["Density"].default_value = milk
        nt.links.new(vol.outputs["Volume"], nt.nodes["Material Output"].inputs["Volume"])
    elif kind == "frosted":
        b.inputs["Roughness"].default_value = .42
        b.inputs["Subsurface Weight"].default_value = .55
        b.inputs["Subsurface Scale"].default_value = .06
        b.inputs["Coat Weight"].default_value = .25
        b.inputs["Coat Roughness"].default_value = .3
        b.inputs["Sheen Weight"].default_value = .25
        _bump(nt, b, 40, .25, .01)
        _vary(nt, b, .42, val=.08, ao=.35)
    elif kind == "matte":
        b.inputs["Roughness"].default_value = .62
        b.inputs["Subsurface Weight"].default_value = .25
        b.inputs["Subsurface Scale"].default_value = .04
        _bump(nt, b, 35, .3, .01)
        _vary(nt, b, .62, ao=.3)
    elif kind == "bio":
        b.inputs["Roughness"].default_value = .45
        b.inputs["Subsurface Weight"].default_value = .45
        b.inputs["Subsurface Scale"].default_value = .12
        b.inputs["Coat Weight"].default_value = .35
        b.inputs["Coat Roughness"].default_value = .2
        b.inputs["Sheen Weight"].default_value = .3
        _bump(nt, b, 7, .45, .03, voronoi=True)
        _vary(nt, b, .45, hue=.02, val=.18)
    elif kind == "atom":
        b.inputs["Roughness"].default_value = .3
        b.inputs["Subsurface Weight"].default_value = .12
        b.inputs["Subsurface Scale"].default_value = .05
        b.inputs["Coat Weight"].default_value = .7
        b.inputs["Coat Roughness"].default_value = .05
        _vary(nt, b, .3, hue=.004, val=.06, rvar=.06)
    else:
        b.inputs["Roughness"].default_value = .34
        b.inputs["Subsurface Weight"].default_value = .1
        b.inputs["Subsurface Scale"].default_value = .03
        b.inputs["Coat Weight"].default_value = .4
        b.inputs["Coat Roughness"].default_value = .12
        _bump(nt, b, 30, .08, .005)
        _vary(nt, b, .34, ao=.2)
    _mats[key] = m
    return m


for ob in list(bpy.data.objects):  # factory scene: default cube, light and camera
    bpy.data.objects.remove(ob, do_unlink=True)

ROOT = bpy.data.objects.new("root", None)
bpy.context.scene.collection.objects.link(ROOT)
ROOT.rotation_euler = (math.pi / 2, 0, 0)  # Three.js y-up -> Blender z-up


def new_obj(name, data, o):
    ob = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = ROOT
    if o.get("pos") and o["type"] != "text":
        ob.location = Vector(o["pos"])
    if o.get("rot"):
        ob.rotation_euler = Euler(o["rot"], "XYZ")
    return ob


class MeshBuilder:
    """Collects spheres and cylinders per material into one mesh: thousands of primitives stay fast."""

    def __init__(self):
        self.parts = {}

    def _bm(self, m):
        if m.name not in self.parts:
            self.parts[m.name] = (bmesh.new(), m)
        return self.parts[m.name][0]

    def sphere(self, m, c, r, seg=24):
        bmesh.ops.create_uvsphere(self._bm(m), u_segments=seg, v_segments=max(8, seg // 2), radius=r,
                                  matrix=Matrix.Translation(Vector(c)))

    def cyl(self, m, a, b, r, seg=12):
        a, b = Vector(a), Vector(b)
        d = b - a
        if d.length < 1e-6:
            return
        rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(self._bm(m), cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length,
                              matrix=Matrix.Translation((a + b) / 2) @ rot)

    def cone(self, m, a, b, r):
        a, b = Vector(a), Vector(b)
        d = b - a
        rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(self._bm(m), cap_ends=True, segments=32, radius1=r, radius2=0, depth=d.length,
                              matrix=Matrix.Translation((a + b) / 2) @ rot)

    def crystal(self, m, c, r, R):
        """Irregular faceted crystal: a low-poly icosphere, stretched and rotated."""
        sc = Matrix.Diagonal((r * (.7 + .8 * R()), r * (.9 + 1.4 * R()), r * (.7 + .6 * R()), 1))
        rot = Euler((R() * 6.3, R() * 6.3, R() * 6.3)).to_matrix().to_4x4()
        bmesh.ops.create_icosphere(self._bm(m), subdivisions=1, radius=1, matrix=Matrix.Translation(Vector(c)) @ rot @ sc)

    def flush(self, name, o, smooth=True):
        obs = []
        for key, (bm, m) in self.parts.items():
            me = bpy.data.meshes.new(f"{name}_{key}")
            bm.to_mesh(me)
            bm.free()
            for p in me.polygons:
                p.use_smooth = smooth
            ob = new_obj(f"{name}_{key}", me, o)
            ob.data.materials.append(m)
            obs.append(ob)
        return obs


def tubes(name, o, paths, r, m, radii=None, res=3, wobble=.18):
    """Smooth bevelled curves (fibres, chains): one curve object, many splines; radii scales each spline,
    wobble lets the diameter swell and narrow along it (0 for uniform electrospun fibres)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    for i, pts in enumerate(paths):
        sp = cu.splines.new("NURBS")
        sp.points.add(len(pts) - 1)
        ph = i * 1.7
        for k, (p, q) in enumerate(zip(sp.points, pts)):
            p.co = (*q, 1)
            p.radius = (radii[i] if radii else 1.0) * (1 + wobble * math.sin(ph + k * 1.3))
        sp.use_endpoint_u = True
        sp.order_u = min(4, len(pts))
        sp.resolution_u = 8 if len(pts) < 8 else 4
    ob = new_obj(name, cu, o)
    ob.data.materials.append(m)
    return ob


def bevelled_box(name, o, size, m):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((*size, 1)))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = new_obj(name, me, o)
    ob.data.materials.append(m)
    bv = ob.modifiers.new("bevel", "BEVEL")
    soft = m.name.endswith("_gel")
    bv.width = o.get("bevel", min(size) * (.18 if soft else .14))  # gels get pillow-soft edges
    bv.segments = 10 if soft else 6
    bv.harden_normals = True
    return ob


# -- procedural porous solids (Geometry Nodes: density field -> volume -> mesh) --------------------------------------
def porous(name, o, size, m, style, cell, seed):
    """Foam: big voronoi pores that overlap into open windows, plus small pores in the struts (pores inside pores).
    Gyroid: TPMS sheet, domain-warped for an organic look, with micro-pores. Solid where density > 0."""
    me = bpy.data.meshes.new(name)
    ob = new_obj(name, me, o)
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links.new

    def node(t, **ops):
        n = N.new(t)
        for k, v in ops.items():
            setattr(n, k, v)
        return n

    def math(op, a, b=None, c=None):
        n = node("ShaderNodeMath", operation=op)
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L(v, n.inputs[i])
        return n.outputs[0]

    pos = node("GeometryNodeInputPosition").outputs[0]
    # domain warp: organic, non-repeating walls
    wn = node("ShaderNodeTexNoise", noise_dimensions="4D")
    wn.inputs["Scale"].default_value = .35 / cell
    wn.inputs["Detail"].default_value = 3
    wn.inputs["W"].default_value = seed
    L(pos, wn.inputs["Vector"])
    sub = node("ShaderNodeVectorMath", operation="SUBTRACT")
    L(wn.outputs["Color"], sub.inputs[0])
    sub.inputs[1].default_value = (.5, .5, .5)
    sc = node("ShaderNodeVectorMath", operation="SCALE")
    L(sub.outputs[0], sc.inputs[0])
    sc.inputs["Scale"].default_value = cell * .9
    add = node("ShaderNodeVectorMath", operation="ADD")
    L(pos, add.inputs[0])
    L(sc.outputs[0], add.inputs[1])
    p = add.outputs[0]

    def voro(scale, r):  # signed distance to spherical pores, in scene units
        v = node("ShaderNodeTexVoronoi", voronoi_dimensions="4D")
        v.inputs["Scale"].default_value = scale
        v.inputs["W"].default_value = seed * 1.7
        v.inputs["Randomness"].default_value = .85
        L(p, v.inputs["Vector"])
        return math("MULTIPLY", math("SUBTRACT", v.outputs["Distance"], r), 1 / scale)

    if style == "gyroid":
        k = 2 * math_pi / cell
        sep = node("ShaderNodeSeparateXYZ")
        L(p, sep.inputs[0])
        x, y, z = (math("MULTIPLY", sep.outputs[i], k) for i in range(3))
        g = math("ADD", math("ADD", math("MULTIPLY", math("SINE", x), math("COSINE", y)),
                             math("MULTIPLY", math("SINE", y), math("COSINE", z))),
                 math("MULTIPLY", math("SINE", z), math("COSINE", x)))
        d = math("DIVIDE", math("SUBTRACT", .55, math("ABSOLUTE", g)), k)  # sheet thickness ~ .55/k
        d = math("MINIMUM", d, voro(1 / (cell * .16), .38))
    else:
        d = math("MINIMUM", voro(1 / cell, .64), voro(1 / (cell * .22), .36))
        d = math("MINIMUM", d, voro(1 / (cell * .07), .3))  # micro-porosity on the walls
    hs = Vector(size) / 2
    vox = max(max(size) / 420, cell * .035)
    cube = node("GeometryNodeVolumeCube")
    L(d, cube.inputs["Density"])
    cube.inputs["Background"].default_value = -1.0
    cube.inputs["Min"].default_value = -hs
    cube.inputs["Max"].default_value = hs
    for ax, s in zip("XYZ", size):
        cube.inputs[f"Resolution {ax}"].default_value = max(8, int(s / vox))
    v2m = node("GeometryNodeVolumeToMesh")
    L(cube.outputs[0], v2m.inputs["Volume"])
    v2m.inputs["Threshold"].default_value = 0.0
    sm = node("GeometryNodeSetShadeSmooth")
    L(v2m.outputs[0], sm.inputs["Mesh"])
    sma = node("GeometryNodeSetMaterial")
    L(sm.outputs[0], sma.inputs["Geometry"])
    sma.inputs["Material"].default_value = m
    L(sma.outputs[0], node("NodeGroupOutput").inputs[0])
    node("NodeGroupInput")
    mod = ob.modifiers.new("porous", "NODES")
    mod.node_group = ng
    return ob


math_pi = math.pi

for o in SPEC["objects"]:
    t, name, c = o["type"], o.get("id", o["type"]), o.get("color", "#888888")
    if o.get("hidden") or t == "text":
        continue
    R = Rnd(o.get("seed", 7))
    V = Rnd((o.get("seed", 7) * 7919 + 101) % 2147483646 + 1)  # extra variation, keeps R aligned with the page
    op = o.get("opacity", 1.0)
    kind = o.get("finish")
    mb = MeshBuilder()
    if t == "scaffold":
        size = o.get("size", [6, 1, 4])
        style = o.get("style", "foam")
        if style in ("foam", "gyroid"):
            cell = o.get("pore", max(size) / 9)
            porous(name, o, size, mat(c, kind or "frosted", op), style, cell, o.get("seed", 7))
            continue
        if style == "nonwoven":
            # SEM look of an electrospun mat: many fine fibres of constant (but fibre-to-fibre lognormal) diameter,
            # each running across the whole sample with gentle bends, weaving up and down through the thickness,
            # and cut where it leaves the sample, like a real cut edge
            sx, sy, sz = size
            paths, radii = [], []
            for i in range(o.get("count", 900)):
                # the heading drifts smoothly (two incommensurate sines): fibres meander and curl as in SEM images
                ang, a1, a2 = V() * math.pi, .5 + .7 * V(), .2 + .4 * V()
                f1, f2, k1, k2 = 2 + 4 * V(), 7 + 8 * V(), V() * 6.3, V() * 6.3
                Lf = (sx + sz) * 1.4
                n_pt = 90
                pt = Vector(((V() - .5) * sx, (V() - .5) * sy * .7, (V() - .5) * sz))
                pt -= Vector((math.cos(ang), 0, math.sin(ang))) * Lf / 2
                y0, pts = pt.y, []
                for j in range(n_pt):
                    t = j / (n_pt - 1)
                    h = ang + a1 * math.sin(k1 + t * f1) + a2 * math.sin(k2 + t * f2)
                    pt = pt + Vector((math.cos(h), 0, math.sin(h))) * (Lf / n_pt)
                    pts.append(Vector((pt.x, y0 + math.sin(k2 * 1.7 + t * 31) * sy * .22, pt.z)))
                best, cur = [], []
                for pt in pts:
                    if abs(pt.x) <= sx / 2 and abs(pt.z) <= sz / 2:
                        cur.append(pt)
                    else:
                        best, cur = max(best, cur, key=len), []
                best = max(best, cur, key=len)
                if len(best) >= 4:
                    paths.append(best)
                    radii.append(math.exp(.35 * (V() + V() + V() - 1.5) * 2))
            tubes(name, o, paths, o.get("radius", .02), mat(c, kind or "frosted", op), radii, 2, wobble=.02)
            continue
        sx, sy, sz = size  # "struts": the original lattice
        n = o.get("cells", [8, 2, 5])
        r = o.get("radius", .07)
        m = mat(c, kind or "frosted", op)
        pts = []
        for i in range(n[0] + 1):
            for j in range(n[1] + 1):
                for k in range(n[2] + 1):
                    pts.append(Vector((-sx / 2 + sx * i / n[0] + (R() - .5) * sx / n[0] * .5, -sy / 2 + sy * j / n[1],
                                       -sz / 2 + sz * k / n[2] + (R() - .5) * sz / n[2] * .5)))
        lim = max(sx / n[0], sy / max(1, n[1]), sz / n[2]) * 1.5
        for a in range(len(pts)):
            for b in range(a + 1, len(pts)):
                if (pts[a] - pts[b]).length < lim and R() < .55:
                    mb.cyl(m, pts[a], pts[b], r, 10)
        for q in pts:
            mb.sphere(m, q, r * 1.6, 12)
    elif t == "fibers":
        reg = o.get("region", [[-3, 3], [-.3, .3], [-2, 2]])
        paths, radii = [], []
        for i in range(o.get("count", 20)):
            p0 = in_region(reg, R)
            d = Vector((R() - .5, (R() - .5) * .15, R() - .5)).normalized()
            L = o.get("length", 2)
            pts = [p0 + d * (L * s) + Vector(((R() - .5) * .2, (R() - .5) * .1, (R() - .5) * .2)) for s in (0, .33, .66, 1)]
            if o.get("clip"):  # keep fibres inside their host slab: clamp to the half-sizes given
                pts = [Vector([max(-h, min(h, v)) for v, h in zip(q, o["clip"])]) for q in pts]
            paths.append(pts)
            radii.append(.7 + .6 * V())
        tubes(name, o, paths, o.get("radius", .03), mat(c, kind or "satin", op), radii)
        continue
    elif t == "brush":
        reg = o.get("region", [[-3, 3], [0, 0], [-2, 2]])
        L = o.get("length", .4)
        rr = o.get("radius", .012)
        paths, heads = [], []
        for i in range(o.get("count", 80)):
            b = in_region(reg, R)
            Li = L * (.7 + .5 * V())
            tilt = Vector(((V() - .5) * .5, 0, (V() - .5) * .5))
            pts = [b + Vector((math.sin(s * 6 + i) * .04, Li * s, math.cos(s * 5 + i) * .04)) + tilt * Li * s * s
                   for s in (0, .25, .5, .75, 1)]
            paths.append(pts)
            heads.append(pts[-1])
        tubes(name, o, paths, rr, mat(c, kind or "atom"))
        mh = mat(o.get("headColor", c), "atom")
        for h in heads:
            mb.sphere(mh, h, rr * (2.6 + .8 * V()), 14)
    elif t in ("slab", "box"):
        size = o.get("size", [1, 1, 1])
        bevelled_box(name, o, size, mat(c, kind, op, o.get("milk", .35)))
        continue
    elif t == "sphere":
        mb.sphere(mat(c, kind, op), (0, 0, 0), (o.get("size") or [.5])[0], 64)
    elif t == "cylinder":
        s = o.get("size") or [.5, 1]
        mb.cyl(mat(c, kind, op), (0, -s[1] / 2, 0), (0, s[1] / 2, 0), s[0], 48)
    elif t == "capsule":
        r, L = o.get("radius", .4), o.get("length", 1.6)
        m = mat(c, kind if kind not in (None, "matte") else "bio", op)
        bm = mb._bm(m)
        bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=48, radius=r)
        for v in bm.verts:  # stretch the sphere's two halves apart: a smooth capsule
            v.co.y += (L / 2) * (1 if v.co.y > 0 else -1)
        appendages, radii = [], []
        for i in range(o.get("pili", 0)):
            u = Vector((V() - .5, V() - .5, V() - .5)).normalized()
            base = u * r + Vector((0, L / 2 * (1 if u.y > 0 else -1), 0))
            q = perp(u)
            ln = r * (.35 + .5 * V())
            appendages.append([base, base + u * ln * .5 + q * ln * .1, base + u * ln + q * ln * .05])
            radii.append(.6)
        for i in range(o.get("flagella", 0)):
            u = Vector(((V() - .5) * .8, -1, (V() - .5) * .8)).normalized()
            base = u * r * .9 + Vector((0, -L / 2, 0))
            q, q2 = perp(u), u.cross(perp(u))
            ln = L * (1.6 + .8 * V())
            appendages.append([base + u * ln * s + (q * math.sin(s * 14 + i) + q2 * math.cos(s * 14 + i)) * r * .22 * min(1, s * 4)
                               for s in [k / 23 for k in range(24)]])
            radii.append(1.0)
        if appendages:
            tubes(name + "_app", o, appendages, o.get("appendageRadius", r * .035), mat(o.get("appendageColor", c), "bio"), radii, 2)
    elif t == "crystals":
        m = mat(c, kind or "frosted", op)
        for i in range(o.get("count", 12)):
            mb.crystal(m, in_region(o.get("region", [[-1, 1], [-1, 1], [-1, 1]]), R), o.get("radius", .15), V)
        mb.flush(name, o, smooth=False)
        continue
    elif t in ("spheres", "rods"):
        m = mat(c, kind)
        for i in range(o.get("count", 30)):
            if o.get("cluster"):
                x, y, z, sp = o["cluster"]
                p = Vector((x + (R() - .5) * sp, y + (R() - .5) * sp * .6, z + (R() - .5) * sp))
            else:
                p = in_region(o.get("region", [[-3, 3], [-.3, .3], [-2, 2]]), R)
            if t == "spheres":
                mb.sphere(m, p, o.get("radius", .15) * (.85 + .3 * V()), 32)
            else:
                if o.get("align") == "x":
                    e = Euler((0, (R() - .5) * .3, math.pi / 2 + (R() - .5) * .3))
                else:
                    e = Euler((R() * 6.3, R() * 6.3, R() * 6.3))
                L = o.get("length", 1) * (1 + o.get("lengthVar", 0) * (V() - .5))  # e.g. CNC: 0.6 = +/-30 %
                d = e.to_matrix() @ Vector((0, L / 2, 0))
                r = o.get("radius", .06)
                mb.cyl(m, p - d, p + d, r, 16)
                mb.sphere(m, p - d, r, 16)
                mb.sphere(m, p + d, r, 16)
    elif t == "molecule":
        sc = o.get("scale", 1)
        az = o.get("atomScale", 1)  # thicker balls and sticks when a small molecule must read at figure size
        at = [Vector(a[1:4]) * sc for a in o["atoms"]]
        el = [a[0] for a in o["atoms"]]
        for e, p in zip(el, at):
            mb.sphere(mat(cpk(e), "atom"), p, RAD.get(e, .35) * sc * az, 40)
        for bd in o.get("bonds", []):
            i, j = bd[0], bd[1]
            n = int(round(bd[2])) if len(bd) > 2 else 1
            a, b = at[i], at[j]
            d = (b - a).normalized()
            side = Vector((0, 0, 1)).cross(d)
            side = (side.normalized() if side.length > 1e-6 else Vector((1, 0, 0))) * .1 * sc
            mid = (a + b) / 2
            for k in range(n):  # each half takes its atom's colour
                off = side * ((k - (n - 1) / 2) * 1.6)
                rb = (.055 if n > 1 else .085) * sc * az
                mb.cyl(mat(cpk(el[i]), "atom"), a + off, mid + off, rb, 16)
                mb.cyl(mat(cpk(el[j]), "atom"), mid + off, b + off, rb, 16)
    elif t == "corona":
        R0, L, n = o.get("radius", 1), o.get("length", .6), o.get("count", 120)
        Rr = Rnd(o.get("seed", 3))
        core_kind = kind or ("metal" if c.lower() in ("#c9ced6", "#dde2e8", "#c0c0c0") else None)
        if o.get("clusterAtoms"):  # real lattice from ASE (render_3d.py embeds it): one polished sphere per atom
            ma = mat(c, core_kind or "metal")
            for _, x, y, z in o["clusterAtoms"]:
                mb.sphere(ma, (x, y, z), o["clusterAtomRadius"], 20)
        elif o.get("core", "icosahedral" if core_kind == "metal" else "sphere") == "icosahedral":
            # multiply-twinned icosahedral habit (common for Ag/Au NPs), edges rounded by a bevel
            bm = bmesh.new()
            bmesh.ops.create_icosphere(bm, subdivisions=1, radius=R0 * 1.04)
            me = bpy.data.meshes.new(name + "_core")
            bm.to_mesh(me)
            bm.free()
            core = new_obj(name + "_core", me, o)
            core.data.materials.append(mat(c, core_kind))
            bv = core.modifiers.new("bevel", "BEVEL")
            bv.width, bv.segments, bv.harden_normals = R0 * .08, 4, True
            for p in me.polygons:
                p.use_smooth = True
        else:
            mb.sphere(mat(c, core_kind), (0, 0, 0), R0, 96)
        if o.get("halo", True):  # the solvated steric layer: faint, milky, so particles visibly keep their distance
            mb.sphere(mat(o.get("haloColor", "#BFE6D8"), "haze", 1, o.get("haloDensity", .35)), (0, 0, 0), R0 + L * 1.05, 64)
        mh = mat(o.get("headColor", "#0072B2"), "atom")
        paths, radii = [], []
        for i in range(n):
            u, ph = Rr() * 2 - 1, Rr() * 6.283
            s = math.sqrt(1 - u * u)
            d = Vector((s * math.cos(ph), u, s * math.sin(ph)))
            if o.get("cutaway") and d.dot(Vector(SPEC.get("camera", [8, 6, 10])).normalized()) > math.cos(math.radians(o["cutaway"])):
                continue  # open a window in the shell towards the camera: the core stays visible
            q = perp(d)
            q = (q * math.cos(V() * 6.3) + d.cross(q) * math.sin(V() * 6.3)).normalized()
            Li = L * (.7 + .55 * V())
            bend = (.08 + .22 * V()) * Li
            pts = [d * (R0 * .98 + Li * k) + q * bend * math.sin(k * math.pi * .9) for k in (0, .25, .5, .75, 1)]
            paths.append(pts)
            radii.append(.85 + .3 * V())
            mb.sphere(mh, pts[-1], .065 * (.85 + .35 * V()) * o.get("headScale", 1), 16)
        tubes(name + "_lig", o, paths, o.get("ligandRadius", .022), mat(o.get("stemColor", "#2E8B6E"), "atom"), radii, 2)
    elif t == "arrow":
        a, b = Vector(o["from"]), Vector(o["to"])
        d = b - a
        m = mat(c)
        mb.cyl(m, a, a + d * .8, .05, 24)
        mb.cone(m, a + d * .8, b, .15)
        o = dict(o, pos=None)
    mb.flush(name, o)

# -- frame the scene ------------------------------------------------------------------------------------------------
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
pts = [ob.matrix_world @ Vector(c) for ob in bpy.context.scene.objects if ob.type in ("MESH", "CURVE")
       for c in ob.evaluated_get(dg).bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)])
hi = Vector([max(p[i] for p in pts) for i in range(3)])
center, radius = (lo + hi) / 2, (hi - lo).length / 2

cam_dir = Vector(SPEC.get("camera", [8, 6, 10]))
cam_dir = Vector((cam_dir.x, -cam_dir.z, cam_dir.y)).normalized()  # y-up -> z-up
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
bpy.context.scene.collection.objects.link(cam)
cam.data.lens = SPEC.get("lens", 70)
cam.data.sensor_fit = "HORIZONTAL"
cam.rotation_euler = (-cam_dir).to_track_quat("-Z", "Y").to_euler()
# tight framing: project every bounding-box corner into the camera frame and back off until the widest one fits,
# so the hero fills the picture instead of floating small inside a bounding sphere
tx = math.tan(math.atan(cam.data.sensor_width / 2 / cam.data.lens))
ty = tx * H / W
inv = cam.rotation_euler.to_matrix().transposed()
need = 0.0
for p in pts:
    q = inv @ (p - center)  # camera space, camera looks down -z
    need = max(need, q.z + abs(q.x) / tx, q.z + abs(q.y) / ty)
dist = need * SPEC.get("fit", 1.06)
cam.location = center + cam_dir * dist
cam.data.clip_end = dist * 10
if SPEC.get("dof", True):
    # aperture as a fraction of the camera distance, so the blur looks the same at any scene scale
    cam.data.dof.use_dof = True
    focus = Vector(SPEC["focus"]) if SPEC.get("focus") else None
    cam.data.dof.focus_distance = (Vector((focus.x, -focus.z, focus.y)) - cam.location).length if focus else dist
    cam.data.dof.aperture_fstop = (cam.data.lens / 1000) / (SPEC.get("blur", .012) * dist)
bpy.context.scene.camera = cam


# studio lighting: large soft key from upper left, cool fill, warm rim from behind, soft top bounce
def area(name, loc, size, energy, color):
    li = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
    li.data.shape = "DISK"
    li.data.size = size * radius
    li.data.energy = energy * radius ** 2
    li.data.color = color
    li.location = center + Vector(loc) * radius
    li.rotation_euler = (center - li.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(li)


right = cam_dir.cross(Vector((0, 0, 1))).normalized()
area("key", (cam_dir * 2.0 - right * 2.4 + Vector((0, 0, 3.0))), 2.6, 320 * SPEC.get("key", 1), (1.0, .96, .91))
area("fill", (cam_dir * 2.6 + right * 2.6 + Vector((0, 0, .5))), 3.6, 38, (.86, .93, 1.0))
area("rim", (-cam_dir * 2.6 + right * 1.2 + Vector((0, 0, 2.0))), 1.8, 220, (1.0, .94, .86))
area("top", (Vector((0, 0, 3.6))), 4.0, 45, (1.0, 1.0, 1.0))


def softbox(name, loc, w, h, strength):
    """Bright card seen only in reflections: gives metals and clear coats crisp studio highlights."""
    bpy.ops.mesh.primitive_plane_add(size=1, location=center + Vector(loc) * radius)
    sb = bpy.context.active_object
    sb.name = name
    sb.scale = (w * radius, h * radius, 1)
    sb.rotation_euler = (center - sb.location).to_track_quat("Z", "Y").to_euler()
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    e = m.node_tree.nodes.new("ShaderNodeEmission")
    e.inputs["Strength"].default_value = strength
    m.node_tree.links.new(e.outputs[0], m.node_tree.nodes["Material Output"].inputs["Surface"])
    sb.data.materials.append(m)
    sb.visible_camera = sb.visible_diffuse = sb.visible_shadow = sb.visible_volume_scatter = False


if SPEC.get("softboxes", True):
    softbox("strip_l", cam_dir * 1.2 - right * 2.6 + Vector((0, 0, 2.2)), .5, 2.6, 6)
    softbox("strip_r", cam_dir * .6 + right * 2.8 + Vector((0, 0, 1.4)), .35, 2.2, 4)
    softbox("ceiling", Vector((0, 0, 3.4)) + cam_dir * .8, 2.2, 1.2, 3)

world = bpy.data.worlds.new("w")
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
bgc = SPEC.get("background")
bg.inputs["Color"].default_value = hexcol(bgc or "#f4f6f8")
bg.inputs["Strength"].default_value = .55
# what reflections see: a studio with a darker floor, a horizon band and a bright soft ceiling, so metals read as metal
env = nt.nodes.new("ShaderNodeBackground")
grad = nt.nodes.new("ShaderNodeValToRGB")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
coord = nt.nodes.new("ShaderNodeTexCoord")
nt.links.new(coord.outputs["Generated"], sep.inputs[0])
nt.links.new(sep.outputs["Z"], grad.inputs["Fac"])
grad.color_ramp.elements[0].color = hexcol("#262b33")
grad.color_ramp.elements[0].position = .44
grad.color_ramp.elements[1].color = hexcol("#f5f7fa")
grad.color_ramp.elements[1].position = .7
mid = grad.color_ramp.elements.new(.52)
mid.color = hexcol("#9aa6b4")
nt.links.new(grad.outputs["Color"], env.inputs["Color"])
env.inputs["Strength"].default_value = .9
# a real photo-studio HDRI (Poly Haven, CC0) when cached: `library.py fetch --only hdri`; "hdri": null keeps the gradient
hd = SPEC.get("hdri", "studio_small_09")
if hd:
    import os
    hp = hd if os.path.isfile(hd) else os.path.join(os.path.expanduser("~"), ".cache", "scientific-illustration", "hdri", hd + ".hdr")
    if os.path.isfile(hp):
        et = nt.nodes.new("ShaderNodeTexEnvironment")
        et.image = bpy.data.images.load(hp)
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (0, 0, math.radians(SPEC.get("hdriRotation", 0)))
        nt.links.new(coord.outputs["Generated"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], et.inputs["Vector"])
        nt.links.new(et.outputs["Color"], env.inputs["Color"])
        env.inputs["Strength"].default_value = SPEC.get("hdriStrength", .5)
lp = nt.nodes.new("ShaderNodeLightPath")
mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
nt.links.new(env.outputs["Background"], mix.inputs[1])
nt.links.new(bg.outputs["Background"], mix.inputs[2])
nt.links.new(mix.outputs["Shader"], nt.nodes["World Output"].inputs["Surface"])
bpy.context.scene.world = world

# soft contact shadow on an invisible floor (kept with a transparent background too)
if SPEC.get("shadow", True):
    # catcher only a little larger than the footprint: a huge catcher under broad lights gave a grey band that
    # dwarfed the objects; `shadowSize` scales the margin
    gz = lo.z - .01 * radius
    m = SPEC.get("shadowSize", 1.25)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(center.x, center.y, gz))
    pl = bpy.context.active_object
    pl.scale = ((hi.x - lo.x) * m, (hi.y - lo.y) * m, 1)
    pl.is_shadow_catcher = True
    pl.visible_glossy = False

sc = bpy.context.scene
sc.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
for backend in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
    try:
        prefs.compute_device_type = backend
        prefs.get_devices()
        if any(d.type == backend for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == backend
            sc.cycles.device = "GPU"
            break
    except Exception:
        continue
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 10
sc.cycles.transmission_bounces = 10
sc.cycles.volume_bounces = 2
sc.cycles.volume_step_rate = 2.0
sc.cycles.caustics_reflective = False
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.film_transparent = bgc is None
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
try:
    sc.view_settings.view_transform = "AgX"
    # "Punchy" keeps pale palettes from washing out to grey-white; a slight negative exposure keeps highlights
    sc.view_settings.look = SPEC.get("look", "AgX - Punchy")
except Exception:
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
sc.view_settings.exposure = SPEC.get("exposure", -0.25)
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("BLENDER_PNG", OUT, sc.cycles.device)
