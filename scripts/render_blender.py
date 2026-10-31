"""Photoreal render of a render_3d.py scene spec with Blender Cycles (runs inside Blender, headless).

Called by `render_3d.py scene.json --blender 2400x1700`; it embeds SMILES first, then runs
  blender -b --factory-startup -P render_blender.py -- scene.resolved.json out.png 2400 1700 [samples]
The geometry is generated with the same seeded random sequence as the Three.js page, so the layout matches the
interactive version; only the look changes: ray-traced glass, metals and soft shadows, studio lighting, AgX colour.
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

CPK = {"H": "#f2f2f2", "C": "#3a3a3a", "N": "#3050f8", "O": "#e8331f", "S": "#ffd030", "P": "#ff8000", "Si": "#d9a066",
       "Cl": "#1ff01f", "Na": "#ab5cf2", "Ag": "#c0c0c0"}
RAD = {"H": .2, "C": .32, "N": .31, "O": .3, "S": .4, "Si": .42, "Cl": .38, "P": .38, "Ag": .5}


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


_mats = {}


def mat(color, kind=None, opacity=1.0):
    """kind: metal | glass | matte | None (satin plastic with a light clearcoat). Opacity < 1 becomes real glass."""
    if opacity < .95 and kind is None:
        kind = "glass"
    key = (color, kind, round(opacity, 2))
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"m{len(_mats)}")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = hexcol(color)
    if kind == "metal":
        b.inputs["Metallic"].default_value = 1.0
        b.inputs["Roughness"].default_value = .16
    elif kind == "glass":
        b.inputs["Transmission Weight"].default_value = 1.0
        b.inputs["Roughness"].default_value = .06
        b.inputs["IOR"].default_value = 1.38
        # a tinted, slightly milky gel: keeps the colour readable through the slab
        b.inputs["Subsurface Weight"].default_value = .08
    elif kind == "matte":
        b.inputs["Roughness"].default_value = .75
    else:
        b.inputs["Roughness"].default_value = .38
        b.inputs["Coat Weight"].default_value = .35
        b.inputs["Coat Roughness"].default_value = .12
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

    def box(self, m, size):
        bmesh.ops.create_cube(self._bm(m), size=1.0, matrix=Matrix.Diagonal((*size, 1)))

    def flush(self, name, o):
        for key, (bm, m) in self.parts.items():
            me = bpy.data.meshes.new(f"{name}_{key}")
            bm.to_mesh(me)
            bm.free()
            for p in me.polygons:
                p.use_smooth = True
            ob = new_obj(f"{name}_{key}", me, o)
            ob.data.materials.append(m)


def tubes(name, o, paths, r, m):
    """Smooth bevelled curves (fibres, chains): one curve object, many splines."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    for pts in paths:
        sp = cu.splines.new("NURBS")
        sp.points.add(len(pts) - 1)
        for p, q in zip(sp.points, pts):
            p.co = (*q, 1)
        sp.use_endpoint_u = True
        sp.order_u = min(4, len(pts))
        sp.resolution_u = 8
    ob = new_obj(name, cu, o)
    ob.data.materials.append(m)


def catmull(pts, n=6):
    return pts  # NURBS through the 4 control points already gives a smooth tube


for o in SPEC["objects"]:
    t, name, c = o["type"], o.get("id", o["type"]), o.get("color", "#888888")
    if o.get("hidden") or t == "text":
        continue
    R = Rnd(o.get("seed", 7))
    op = o.get("opacity", 1.0)
    kind = o.get("finish")
    mb = MeshBuilder()
    if t == "scaffold":
        sx, sy, sz = o.get("size", [6, 1, 4])
        n = o.get("cells", [8, 2, 5])
        r = o.get("radius", .07)
        m = mat(c, kind or "matte" if kind != "glass" else kind, op)
        pts = []
        for i in range(n[0] + 1):
            for j in range(n[1] + 1):
                for k in range(n[2] + 1):
                    pts.append(Vector((-sx / 2 + sx * i / n[0] + (R() - .5) * sx / n[0] * .5, -sy / 2 + sy * j / n[1],
                                       -sz / 2 + sz * k / n[2] + (R() - .5) * sz / n[2] * .5)))
        lim = max(sx / n[0], sy / max(1, n[1]), sz / n[2]) * 1.5
        for a in range(len(pts)):
            for b in range(a + 1, len(pts)):
                L = (pts[a] - pts[b]).length
                if L < lim and R() < .55:
                    mb.cyl(m, pts[a], pts[b], r, 10)
        for q in pts:
            mb.sphere(m, q, r * 1.6, 12)
    elif t == "fibers":
        reg = o.get("region", [[-3, 3], [-.3, .3], [-2, 2]])
        paths = []
        for i in range(o.get("count", 20)):
            p0 = in_region(reg, R)
            d = Vector((R() - .5, (R() - .5) * .15, R() - .5)).normalized()
            L = o.get("length", 2)
            paths.append([p0 + d * (L * s) + Vector(((R() - .5) * .2, (R() - .5) * .1, (R() - .5) * .2)) for s in (0, .33, .66, 1)])
        tubes(name, o, paths, o.get("radius", .03), mat(c, kind, op))
        continue
    elif t == "brush":
        reg = o.get("region", [[-3, 3], [0, 0], [-2, 2]])
        L = o.get("length", .4)
        rr = o.get("radius", .012)
        paths, heads = [], []
        for i in range(o.get("count", 80)):
            b = in_region(reg, R)
            pts = [b + Vector((math.sin(s * 6 + i) * .04, L * s, math.cos(s * 5 + i) * .04)) for s in (0, .35, .7, 1)]
            paths.append(pts)
            heads.append(pts[3])
        tubes(name, o, paths, rr, mat(c, kind))
        mh = mat(o.get("headColor", c))
        for h in heads:
            mb.sphere(mh, h, rr * 3, 12)
    elif t in ("slab", "box"):
        mb.box(mat(c, kind, op), o.get("size", [1, 1, 1]))
    elif t == "sphere":
        mb.sphere(mat(c, kind, op), (0, 0, 0), (o.get("size") or [.5])[0], 64)
    elif t == "cylinder":
        s = o.get("size") or [.5, 1]
        mb.cyl(mat(c, kind, op), (0, -s[1] / 2, 0), (0, s[1] / 2, 0), s[0], 48)
    elif t == "capsule":
        r, L = o.get("radius", .4), o.get("length", 1.6)
        m = mat(c, kind, op)
        mb.cyl(m, (0, -L / 2, 0), (0, L / 2, 0), r, 48)
        mb.sphere(m, (0, -L / 2, 0), r, 48)
        mb.sphere(m, (0, L / 2, 0), r, 48)
    elif t in ("spheres", "rods"):
        m = mat(c, kind)
        for i in range(o.get("count", 30)):
            if o.get("cluster"):
                x, y, z, sp = o["cluster"]
                p = Vector((x + (R() - .5) * sp, y + (R() - .5) * sp * .6, z + (R() - .5) * sp))
            else:
                p = in_region(o.get("region", [[-3, 3], [-.3, .3], [-2, 2]]), R)
            if t == "spheres":
                mb.sphere(m, p, o.get("radius", .15), 24)
            else:
                if o.get("align") == "x":
                    e = Euler((0, (R() - .5) * .3, math.pi / 2 + (R() - .5) * .3))
                else:
                    e = Euler((R() * 6.3, R() * 6.3, R() * 6.3))
                L = o.get("length", 1)
                d = e.to_matrix() @ Vector((0, L / 2, 0))
                r = o.get("radius", .06)
                mb.cyl(m, p - d, p + d, r, 12)
                mb.sphere(m, p - d, r, 12)
                mb.sphere(m, p + d, r, 12)
    elif t == "molecule":
        sc = o.get("scale", 1)
        at = [Vector(a[1:4]) * sc for a in o["atoms"]]
        for a, p in zip(o["atoms"], at):
            mb.sphere(mat(CPK.get(a[0], "#ff66cc")), p, RAD.get(a[0], .35) * sc, 32)
        bm_ = mat("#c4c4c4")
        for bd in o.get("bonds", []):
            i, j = bd[0], bd[1]
            n = int(round(bd[2])) if len(bd) > 2 else 1
            a, b = at[i], at[j]
            d = (b - a).normalized()
            side = Vector((0, 0, 1)).cross(d)
            side = (side.normalized() if side.length > 1e-6 else Vector((1, 0, 0))) * .09 * sc
            for k in range(n):
                off = side * ((k - (n - 1) / 2) * 1.6)
                mb.cyl(bm_, a + off, b + off, (.05 if n > 1 else .08) * sc, 12)
    elif t == "corona":
        R0, L, n = o.get("radius", 1), o.get("length", .6), o.get("count", 120)
        Rr = Rnd(o.get("seed", 3))
        mb.sphere(mat(c, kind or "metal" if c.lower() in ("#c9ced6", "#dde2e8", "#c0c0c0") else kind), (0, 0, 0), R0, 64)
        ms, mh = mat(o.get("stemColor", "#2E8B6E")), mat(o.get("headColor", "#0072B2"))
        for i in range(n):
            u, ph = Rr() * 2 - 1, Rr() * 6.283
            s = math.sqrt(1 - u * u)
            d = Vector((s * math.cos(ph), u, s * math.sin(ph)))
            mb.cyl(ms, d * R0, d * (R0 + L), .025, 8)
            mb.sphere(mh, d * (R0 + L), .07, 12)
    elif t == "arrow":
        a, b = Vector(o["from"]), Vector(o["to"])
        d = b - a
        m = mat(c)
        mb.cyl(m, a, a + d * .82, .05, 16)
        mb.cone(m, a + d * .82, b, .16)
        o = dict(o, pos=None)
    mb.flush(name, o)

# -- frame the scene ------------------------------------------------------------------------------------------------
bpy.context.view_layer.update()
pts = [ob.matrix_world @ Vector(c) for ob in bpy.context.scene.objects if ob.type in ("MESH", "CURVE") for c in ob.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)])
hi = Vector([max(p[i] for p in pts) for i in range(3)])
center, radius = (lo + hi) / 2, (hi - lo).length / 2

cam_dir = Vector(SPEC.get("camera", [8, 6, 10]))
cam_dir = Vector((cam_dir.x, -cam_dir.z, cam_dir.y)).normalized()  # y-up -> z-up
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
bpy.context.scene.collection.objects.link(cam)
cam.data.lens = 70
fov = 2 * math.atan(cam.data.sensor_width / 2 / cam.data.lens) * (min(1, H / W) if W > H else 1)
dist = radius / math.sin(fov / 2) * SPEC.get("fit", 1.15)
cam.location = center + cam_dir * dist
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.clip_end = dist * 10
if SPEC.get("dof", True):
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = dist
    cam.data.dof.aperture_fstop = SPEC.get("fstop", 6.0)
bpy.context.scene.camera = cam

# studio lighting: large soft key from upper left, cool fill, warm rim from behind
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
area("key", (cam_dir * 2.2 - right * 2.2 + Vector((0, 0, 3.0))), 2.5, 260, (1.0, .97, .93))
area("fill", (cam_dir * 2.5 + right * 2.6 + Vector((0, 0, .6))), 3.0, 70, (.88, .94, 1.0))
area("rim", (-cam_dir * 2.6 + right * .8 + Vector((0, 0, 2.2))), 1.6, 180, (1.0, .95, .88))

world = bpy.data.worlds.new("w")
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
bgc = SPEC.get("background")
bg.inputs["Color"].default_value = hexcol(bgc or "#f4f6f8")
bg.inputs["Strength"].default_value = .55
# what reflections see: a studio with a darker floor and a bright soft ceiling, so metals read as metal
env = nt.nodes.new("ShaderNodeBackground")
grad = nt.nodes.new("ShaderNodeValToRGB")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
coord = nt.nodes.new("ShaderNodeTexCoord")
nt.links.new(coord.outputs["Generated"], sep.inputs[0])
nt.links.new(sep.outputs["Z"], grad.inputs["Fac"])
grad.color_ramp.elements[0].color = hexcol("#2a2f36")
grad.color_ramp.elements[1].color = hexcol("#f3f5f8")
grad.color_ramp.elements[0].position = .45
grad.color_ramp.elements[1].position = .62
nt.links.new(grad.outputs["Color"], env.inputs["Color"])
env.inputs["Strength"].default_value = .9
lp = nt.nodes.new("ShaderNodeLightPath")
mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
nt.links.new(env.outputs["Background"], mix.inputs[1])
nt.links.new(bg.outputs["Background"], mix.inputs[2])
nt.links.new(mix.outputs["Shader"], nt.nodes["World Output"].inputs["Surface"])
bpy.context.scene.world = world

# soft contact shadow on an invisible floor (kept even with a transparent background)
ground = SPEC.get("ground")
if ground is not None or True:
    gz = lo.z - .02 * radius
    bpy.ops.mesh.primitive_plane_add(size=radius * 12, location=(center.x, center.y, gz))
    fl = bpy.context.active_object
    fl.is_shadow_catcher = True

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
sc.cycles.max_bounces = 8
sc.cycles.transmission_bounces = 8
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.film_transparent = bgc is None
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
try:
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("BLENDER_PNG", OUT, sc.cycles.device)
