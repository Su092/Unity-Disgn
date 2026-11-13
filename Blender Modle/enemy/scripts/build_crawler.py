# -*- coding: utf-8 -*-
"""Low-poly enemy crawler (~ref_crawler.png) - procedural builder v3.

  blender -b --python build_crawler.py -- stage=render res=1254 samples=96
  blender -b --python build_crawler.py -- stage=sweep    # camera search

Metres, +Z up, creature faces -Y, its right = +X.
Faceted / flat-shaded, explicit vertex data, no subdivision.
"""
import bpy, bmesh, math, os, sys, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
RENDERS = os.path.join(PROJ, "renders")
EXPORT = os.path.join(PROJ, "export")
for d in (RENDERS, EXPORT):
    os.makedirs(d, exist_ok=True)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ARGS = dict(t.split("=", 1) for t in argv if "=" in t)
RES = int(ARGS.get("res", 1254))
SAMPLES = int(ARGS.get("samples", 96))
STAGE = ARGS.get("stage", "all")

# reference measurements (px, 1254x1254)
REF = {
    "whole":     (30, 1200, 223, 1152),
    "blue":      (689, 954, 330, 478),
    "visor":     (816, 1150, 654, 748),
    "bandL":     (89, 644, 520, 723),
    "red":       (78, 1021, 224, 638),
    "legBLband": (56, 186, 778, 845),
    "legFLband": (387, 544, 882, 955),
    "legFRband": (1047, 1161, 888, 944),
}

ZS = 1.190  # global height scale: projected bbox aspect calibrated to 0.794


def srgb(r, g, b):
    def c(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (c(r), c(g), c(b), 1.0)


# colours measured off the reference render (mean per material class)
PAL = {
    "RED":    dict(rgb=srgb(218, 71, 30),  rough=0.62),
    "DARK":   dict(rgb=srgb(47, 48, 52),   rough=0.66),
    "GREY":   dict(rgb=srgb(83, 87, 95),   rough=0.60),
    "ORANGE": dict(rgb=srgb(253, 172, 22), rough=0.52),
    "BLUE":   dict(rgb=srgb(86, 190, 250), rough=0.48),
    "CAVITY": dict(rgb=srgb(30, 31, 34),   rough=0.80),
    "AMBER":  dict(rgb=srgb(255, 150, 12), rough=0.45,
                   emit=srgb(255, 150, 14), emit_str=4.0),
    "GROUND": dict(rgb=srgb(127, 127, 126), rough=0.90),
}


def clear_scene():
    bpy.ops.wm.read_homefile(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0


def make_mat(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    spec = PAL[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = spec["rgb"]
    bsdf.inputs["Roughness"].default_value = spec["rough"]
    bsdf.inputs["Metallic"].default_value = 0.0
    if "emit" in spec:
        bsdf.inputs["Emission Color"].default_value = spec["emit"]
        bsdf.inputs["Emission Strength"].default_value = spec["emit_str"]
    m.diffuse_color = spec["rgb"]
    return m


def mesh_obj(name, verts, faces, mats, face_mats=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(v[0], v[1], v[2] * ZS) for v in verts], [], [tuple(f) for f in faces])
    me.validate(verbose=False)
    for mn in mats:
        me.materials.append(make_mat(mn))
    if face_mats:
        for i, mi in enumerate(face_mats):
            if i < len(me.polygons):
                me.polygons[i].material_index = mi
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def recalc(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


# ================================================================ HULL
# (y, half_width, z_top, z_chine, z_belly)
HULL_RINGS = [
    (1.100, 0.420, 0.950, 0.812, 0.660),
    (0.950, 0.600, 1.050, 0.845, 0.640),
    (0.700, 0.730, 1.130, 0.878, 0.620),
    (0.220, 0.805, 1.210, 0.918, 0.618),
    (-0.280, 0.805, 1.190, 0.905, 0.618),
    (-0.560, 0.740, 1.080, 0.862, 0.630),
    (-0.760, 0.560, 0.930, 0.790, 0.650),
]


def hull_profile(w, zt, zm, zb):
    h = zt - zb
    return [
        (0.0, zt),
        (w * 0.56, zt - 0.045 * h),
        (w * 0.97, zm),
        (w * 1.00, zm - 0.100 * h),
        (w * 0.92, zb),
        (0.0, zb),
    ]


def build_hull():
    rings = []
    for (y, w, zt, zm, zb) in HULL_RINGS:
        half = hull_profile(w, zt, zm, zb)
        loop = [(x, y, z) for (x, z) in half]
        loop += [(-x, y, z) for (x, z) in reversed(half[1:-1])]
        rings.append(loop)
    n = 10
    verts = [v for r in rings for v in r]
    faces, fmats = [], []
    red_segs = {0, 1, 8, 9}
    for i in range(len(rings) - 1):
        a0, b0 = i * n, (i + 1) * n
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((a0 + k, a0 + k2, b0 + k2, b0 + k))
            fmats.append(0 if k in red_segs else 1)
    faces.append(tuple(range(n - 1, -1, -1)))
    fmats.append(1)
    last = (len(rings) - 1) * n
    faces.append(tuple(last + k for k in range(n)))
    fmats.append(1)
    ob = mesh_obj("GEO-crawler-hull", verts, faces, ["RED", "DARK"], fmats)
    recalc(ob)
    return ob


# ================================================================ COWL
COWL_REAR_Y = -0.500
COWL_FRONT_Y = -1.300
COWL_REAR = [(0.0, 1.020), (0.290, 0.995), (0.395, 0.880), (0.415, 0.660),
             (0.355, 0.442), (0.0, 0.375)]
COWL_FRONT = [(0.0, 0.930), (0.272, 0.905), (0.372, 0.790), (0.392, 0.604),
              (0.327, 0.432), (0.0, 0.395)]

VISOR_Z = 0.655
VISOR_H = 0.112
VISOR_HALF_W = 0.345
VISOR_RISE = 0.026
VISOR_DEPTH = 0.200
VISOR_WRAP = 0.200      # ends recede by this much per metre of |x|


def ring_from_half(half):
    loop = [(x, z) for (x, z) in half]
    loop += [(-x, z) for (x, z) in reversed(half[1:-1])]
    return loop


def build_cowl():
    rear = [(x, COWL_REAR_Y, z) for (x, z) in ring_from_half(COWL_REAR)]
    front = [(x, COWL_FRONT_Y, z) for (x, z) in ring_from_half(COWL_FRONT)]
    n = 10
    verts = rear + front
    faces, fmats = [], []
    for k in range(n):
        k2 = (k + 1) % n
        faces.append((k, k2, n + k2, n + k))
        fmats.append(0)
    faces.append(tuple(range(n - 1, -1, -1)))
    fmats.append(0)
    faces.append(tuple(n + k for k in range(n)))
    fmats.append(0)
    ob = mesh_obj("GEO-crawler-cowl", verts, faces, ["GREY"], fmats)
    recalc(ob)
    return ob


def chevron(w, h, rise, z0):
    top = [(-w, z0 + h / 2 + rise), (0.0, z0 + h / 2), (w, z0 + h / 2 + rise)]
    bot = [(w, z0 - h / 2 + rise), (0.0, z0 - h / 2), (-w, z0 - h / 2 + rise)]
    return top + bot


def extrude_y(name, loop_xz, y0, y1, mat):
    n = len(loop_xz)
    verts = [(x, y0, z) for (x, z) in loop_xz] + [(x, y1, z) for (x, z) in loop_xz]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for k in range(n):
        k2 = (k + 1) % n
        faces.append((k, k2, n + k2, n + k))
    ob = mesh_obj(name, verts, faces, [mat])
    recalc(ob)
    return ob


def bent_prism(name, loop_xz, y_front, y_back, wrap, mat):
    """Same as extrude_y but the section recedes as |x| grows (prow wrap)."""
    n = len(loop_xz)
    verts, faces = [], []
    for (x, z) in loop_xz:
        dy = wrap * abs(x)
        verts.append((x, y_front + dy, z))
        verts.append((x, y_back + dy, z))
    faces.append(tuple(range(0, 2 * n, 2)))            # front cap
    faces.append(tuple(range(2 * n - 2, 0, -2)))       # back cap
    for k in range(n):
        k2 = (k + 1) % n
        faces.append((2 * k, 2 * k2, 2 * k2 + 1, 2 * k + 1))
    ob = mesh_obj(name, verts, faces, [mat])
    recalc(ob)
    return ob


def build_visor(cowl):
    loop = chevron(VISOR_HALF_W, VISOR_H, VISOR_RISE, VISOR_Z)
    cutter = bent_prism("CUT-visor", loop, COWL_FRONT_Y - 0.09,
                        COWL_FRONT_Y + VISOR_DEPTH, VISOR_WRAP, "CAVITY")
    bpy.context.view_layer.objects.active = cowl
    md = cowl.modifiers.new("visor_slot", 'BOOLEAN')
    md.operation = 'DIFFERENCE'
    md.object = cutter
    md.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier=md.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    glow = chevron(VISOR_HALF_W * 0.965, VISOR_H * 0.80, VISOR_RISE * 0.95, VISOR_Z)
    return bent_prism("GEO-crawler-visor", glow, COWL_FRONT_Y + 0.038,
                      COWL_FRONT_Y + 0.086, VISOR_WRAP, "AMBER")


# ================================================================ DECALS
def hull_params(y):
    rings = HULL_RINGS
    if y >= rings[0][0]:
        a = b = rings[0]
        t = 0.0
    elif y <= rings[-1][0]:
        a = b = rings[-1]
        t = 0.0
    else:
        for i in range(len(rings) - 1):
            y0, y1 = rings[i][0], rings[i + 1][0]
            if y1 <= y <= y0:
                t = (y0 - y) / (y0 - y1)
                a, b = rings[i], rings[i + 1]
                break
    return tuple(a[k] + (b[k] - a[k]) * t for k in (1, 2, 3, 4))   # w, zt, zm, zb


def flank_point(y, z, off):
    """Point on the hull's right flank at height z (chain chine -> belly)."""
    w, zt, zm, zb = hull_params(y)
    h = zt - zb
    chain = [(w * 0.97, zm), (w * 1.00, zm - 0.100 * h), (w * 0.92, zb)]
    for i in range(len(chain) - 1):
        (x0, z0), (x1, z1) = chain[i], chain[i + 1]
        lo, hi = min(z0, z1), max(z0, z1)
        if lo - 1e-6 <= z <= hi + 1e-6 and abs(z1 - z0) > 1e-9:
            t = (z - z0) / (z1 - z0)
            x = x0 + (x1 - x0) * t
            dx, dz = x1 - x0, z1 - z0
            ln = math.hypot(dx, dz)
            nx, nz = -dz / ln, dx / ln
            if nx < 0:
                nx, nz = -nx, -nz
            return x + nx * off, z + nz * off
    raise RuntimeError("band z=%.3f outside flank at y=%.3f" % (z, y))


# (y, z_top, z_bot) - on the flank, steps down ~60% of the way forward
BAND_WAYPOINTS = [
    (1.080, 0.795, 0.725),
    (0.980, 0.818, 0.748),
    (0.760, 0.833, 0.763),
    (0.470, 0.838, 0.768),
    (0.210, 0.830, 0.760),
    (0.030, 0.818, 0.748),
    (-0.120, 0.706, 0.650),
    (-0.300, 0.694, 0.646),
    (-0.480, 0.686, 0.654),
    (-0.640, 0.678, 0.662),
]


def build_side_band(sign):
    off = 0.005
    top, bot = [], []
    for (y, zt_, zb_) in BAND_WAYPOINTS:
        xt, z1 = flank_point(y, zt_, off)
        xb, z2 = flank_point(y, zb_, off)
        top.append((sign * xt, y, z1))
        bot.append((sign * xb, y, z2))
    verts = top + bot
    n = len(top)
    faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
    ob = mesh_obj("DECAL-band-%s" % ("R" if sign > 0 else "L"), verts, faces, ["ORANGE"])
    recalc(ob)
    return ob


def project_onto(hull, origins, direction, offset, tag):
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(hull, dg)
    out = []
    for o in origins:
        loc, nor, idx, dist = bvh.ray_cast(o, direction, 60.0)
        if loc is None:
            raise RuntimeError("decal '%s' missed the hull at %s" % (tag, o[:]))
        out.append(tuple(loc + nor * offset))
    return out


BLUE_PLATES = [   # (cx, cy), yaw of long axis (deg), length, width
    ((0.235, -0.470), 34.0, 0.300, 0.104),
    ((0.205, -0.760), 34.0, 0.300, 0.104),
]


TOP_PLATES = [   # (cx, cy), yaw of long axis (deg), length, width
    ((0.240, -0.300), 34.0, 0.310, 0.106),
    ((0.210, -0.580), 34.0, 0.310, 0.106),
]


def hull_top_z(y, x):
    """Analytic height of the hull's upper surface at (x, y)."""
    w, zt, zm, zb = hull_params(y)
    h = zt - zb
    ax = abs(x)
    if ax <= w * 0.56:
        t = ax / (w * 0.56)
        return zt + ((zt - 0.045 * h) - zt) * t
    t = min(1.0, (ax - w * 0.56) / (w * 0.97 - w * 0.56))
    return (zt - 0.045 * h) + (zm - (zt - 0.045 * h)) * t


def build_blue_plates(hull):
    """Ribbon of quads conformed analytically to the hull's top surface, so it
    follows facet creases instead of sinking through them."""
    obs = []
    SEG = 4
    for i, ((cx, cy), ang, L, W) in enumerate(TOP_PLATES):
        a = math.radians(ang)
        d = Vector((math.sin(a), -math.cos(a), 0.0))
        s = Vector((math.cos(a), math.sin(a), 0.0))
        c = Vector((cx, cy, 0.0))
        verts, faces = [], []
        for k in range(SEG + 1):
            t = -L / 2 + L * k / SEG
            for side in (-1, 1):
                p = c + d * t + s * (W / 2 * side)
                verts.append((p.x, p.y, hull_top_z(p.y, p.x) + 0.008))
        for k in range(SEG):
            a0 = k * 2
            faces.append((a0, a0 + 1, a0 + 3, a0 + 2))
        obs.append(mesh_obj("DECAL-blue-%d" % (i + 1), verts, faces, ["BLUE"]))
    return obs


# ================================================================ LEGS
LEGS = [
    ("FL", (-0.470, -0.700, 0.700), (-0.715, -0.800)),
    ("FR", (0.470, -0.700, 0.700), (0.715, -0.800)),
    ("BL", (-0.470, 0.680, 0.700), (-0.750, 0.850)),
    ("BR", (0.470, 0.680, 0.700), (0.750, 0.850)),
]
THIGH_TOP_HW = 0.186
THIGH_BOT_HW = 0.142
BAND_HW = 0.148
SHIN_TOP_HW = 0.116
SHIN_BOT_HW = 0.120
THIGH_Z = 0.340
BAND_TOP_Z = 0.315
BAND_BOT_Z = 0.215


def build_leg(name, hip, foot):
    hz = hip[2]

    def axis(z):
        t = (hz - z) / hz
        return (hip[0] + (foot[0] - hip[0]) * t, hip[1] + (foot[1] - hip[1]) * t)

    levels = [
        (hz, THIGH_TOP_HW, 1.10, 0),
        (THIGH_Z, THIGH_BOT_HW, 1.12, 0),
        (BAND_TOP_Z, BAND_HW, 1.10, 1),
        (BAND_BOT_Z, BAND_HW, 1.10, 1),
        (BAND_BOT_Z - 0.004, SHIN_TOP_HW, 1.16, 2),
        (0.075, SHIN_BOT_HW, 1.14, 2),
        (0.0, SHIN_BOT_HW * 1.03, 1.10, 2),
    ]
    verts, idx = [], []
    for (z, hw, ds, _m) in levels:
        cx, cy = axis(z)
        idx.append(len(verts))
        d = hw * ds
        verts += [(cx - hw, cy - d, z), (cx + hw, cy - d, z),
                  (cx + hw, cy + d, z), (cx - hw, cy + d, z)]
    faces, fmats = [], []
    for i in range(len(levels) - 1):
        a, b = idx[i], idx[i + 1]
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append((a + k, a + k2, b + k2, b + k))
            fmats.append(levels[i + 1][3] if i + 1 < len(levels) else 2)
    faces.append((idx[-1], idx[-1] + 1, idx[-1] + 2, idx[-1] + 3))
    fmats.append(2)
    faces.append((idx[0] + 3, idx[0] + 2, idx[0] + 1, idx[0] + 0))
    fmats.append(0)
    ob = mesh_obj("GEO-crawler-leg-%s" % name, verts, faces,
                  ["GREY", "ORANGE", "DARK"], fmats)
    recalc(ob)
    return ob


# ================================================================ SCENE
CAM_BASE = dict(az=41.0, el=15.0, lens=90.0, target=[0.02, -0.06, 0.66], dist=5.0)


def place(cam, cfg, target, dist):
    az, el = math.radians(cfg["az"]), math.radians(cfg["el"])
    d = Vector((-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam.location = target + d * dist
    cam.rotation_euler = (target - cam.location).normalized().to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()


def make_camera(cfg):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("CAM")
    cd.lens = cfg["lens"]
    cd.sensor_width = 36.0
    cam = bpy.data.objects.new("CAM", cd)
    bpy.context.collection.objects.link(cam)
    sc.camera = cam
    place(cam, cfg, Vector(cfg["target"]), cfg["dist"])
    return cam


def sample_points(objs, step=7):
    pts = []
    for ob in objs:
        mw = ob.matrix_world
        vs = ob.data.vertices
        st = 1 if len(vs) <= 400 else step
        for i in range(0, len(vs), st):
            pts.append(mw @ vs[i].co)
    return pts


def proj_box(cam, pts, res):
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    xs, ys = [], []
    for p in pts:
        co = world_to_camera_view(sc, cam, p)
        xs.append(co.x * res)
        ys.append((1.0 - co.y) * res)
    return min(xs), max(xs), min(ys), max(ys)


def fit_camera(cam, cfg, objs, ref_box, res):
    pts = sample_points(objs, 5)
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    target = (mn + mx) * 0.5
    tw, th = ref_box[1] - ref_box[0], ref_box[3] - ref_box[2]
    lo, hi = 1.0, 60.0
    for _ in range(45):
        dist = 0.5 * (lo + hi)
        place(cam, cfg, target, dist)
        b = proj_box(cam, pts, res)
        frac = max((b[1] - b[0]) / tw, (b[3] - b[2]) / th)
        if frac > 1.0:
            lo = dist
        else:
            hi = dist
    dist = 0.5 * (lo + hi)
    place(cam, cfg, target, dist)
    b = proj_box(cam, pts, res)
    rcx = (ref_box[0] + ref_box[1]) * 0.5
    rcy = (ref_box[2] + ref_box[3]) * 0.5
    cam.data.shift_x += ((b[0] + b[1]) * 0.5 - rcx) / float(res)
    cam.data.shift_y -= ((b[2] + b[3]) * 0.5 - rcy) / float(res)
    bpy.context.view_layer.update()
    cfg["target"] = list(target)
    cfg["dist"] = dist
    return proj_box(cam, pts, res)


def setup_world():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    mix = nt.nodes.new("ShaderNodeMixShader")
    lp = nt.nodes.new("ShaderNodeLightPath")
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_env = nt.nodes.new("ShaderNodeBackground")
    bg_cam.inputs[0].default_value = (0.181, 0.181, 0.179, 1.0)
    bg_cam.inputs[1].default_value = 1.0
    bg_env.inputs[0].default_value = (0.100, 0.103, 0.108, 1.0)
    bg_env.inputs[1].default_value = 1.0
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bg_env.outputs[0], mix.inputs[1])
    nt.links.new(bg_cam.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


def setup_lights():
    sun = bpy.data.lights.new("KEY", 'SUN')
    sun.energy = 3.4
    sun.angle = math.radians(6.0)
    so = bpy.data.objects.new("LIGHT-key", sun)
    so.location = (-3.2, -3.6, 4.4)
    so.rotation_euler = (Vector((0, 0, 0.55)) - Vector(so.location)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.collection.objects.link(so)

    fill = bpy.data.lights.new("FILL", 'AREA')
    fill.energy = 120.0
    fill.size = 6.0
    fo = bpy.data.objects.new("LIGHT-fill", fill)
    fo.location = (4.6, -3.0, 2.4)
    fo.rotation_euler = (Vector((0, 0, 0.7)) - Vector(fo.location)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.collection.objects.link(fo)


def setup_ground():
    me = bpy.data.meshes.new("GROUND")
    s = 60.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("GEO-ground", me)
    ob.data.materials.append(make_mat("GROUND"))
    bpy.context.collection.objects.link(ob)
    return ob


def setup_render(res, samples, transparent=False):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0


# ================================================================ BUILD
def build():
    clear_scene()
    hull = build_hull()
    cowl = build_cowl()
    visor = build_visor(cowl)
    bands = [build_side_band(-1), build_side_band(1)]
    plates = build_blue_plates(hull)
    legs = [build_leg(n, hip, foot) for (n, hip, foot) in LEGS]
    parts = [hull, cowl, visor] + bands + plates + legs
    coll = bpy.data.collections.new("COL_Crawler")
    bpy.context.scene.collection.children.link(coll)
    for ob in parts:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        coll.objects.link(ob)
    return parts, coll


LEG_CODES = {"FL": 0, "FR": 1, "BL": 2, "BR": 3}


def leg_band_points(name):
    ob = bpy.data.objects["GEO-crawler-leg-%s" % name]
    mw = ob.matrix_world
    return [mw @ ob.data.vertices[i].co for i in range(8, 16)]


def collect_boxes(cam, res):
    groups = {
        "whole": list(bpy.data.collections["COL_Crawler"].objects),
        "hull": [bpy.data.objects["GEO-crawler-hull"]],
        "cowl": [bpy.data.objects["GEO-crawler-cowl"]],
        "visor": [bpy.data.objects["GEO-crawler-visor"]],
        "bandL": [bpy.data.objects["DECAL-band-L"]],
        "blue": [bpy.data.objects["DECAL-blue-1"], bpy.data.objects["DECAL-blue-2"]],
    }
    out = {k: [round(v) for v in proj_box(cam, sample_points(o), res)]
           for k, o in groups.items()}
    for n in LEG_CODES:
        out["leg%sband" % n] = [round(v) for v in proj_box(cam, leg_band_points(n), res)]
    return out


def report(cam, res):
    bpy.context.view_layer.update()
    out = collect_boxes(cam, res)
    print("=== projected bboxes @%dpx ===" % res)
    for k, b in out.items():
        line = "  %-10s x[%4d,%4d] y[%4d,%4d] w=%4d h=%4d" % (
            k, b[0], b[1], b[2], b[3], b[1] - b[0], b[3] - b[2])
        if k in REF:
            r = REF[k]
            line += "  | REF x[%d,%d] y[%d,%d]  d=(%+d,%+d,%+d,%+d)" % (
                r[0], r[1], r[2], r[3], b[0] - r[0], b[1] - r[1], b[2] - r[2], b[3] - r[3])
        print(line)
    with open(os.path.join(RENDERS, "project_report.json"), "w") as f:
        json.dump(out, f, indent=1)
    return out


def render_to(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("WROTE", path)


def export_all(coll):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in coll.objects:
        ob.select_set(True)
    base = os.path.join(EXPORT, "crawler")
    bpy.ops.export_scene.gltf(filepath=base + ".glb", export_format='GLB',
                              use_selection=True, export_apply=True, export_yup=True)
    print("WROTE", base + ".glb")
    bpy.ops.export_scene.fbx(filepath=base + ".fbx", use_selection=True,
                             apply_scale_options='FBX_SCALE_UNITS',
                             object_types={'MESH'}, mesh_smooth_type='FACE')
    print("WROTE", base + ".fbx")


def main():
    parts, coll = build()
    setup_world()
    setup_lights()
    ground = setup_ground()
    cfg = dict(CAM_BASE)
    cam = make_camera(cfg)
    setup_render(RES, SAMPLES, transparent=False)

    if STAGE == "sweep":
        best = None
        for az in (36.0, 40.0):
            for el in (14.0, 17.0):
                c = dict(CAM_BASE)
                c["az"], c["el"] = az, el
                cam.data.shift_x = 0.0
                cam.data.shift_y = 0.0
                fit_camera(cam, c, parts, REF["whole"], RES)
                rep = collect_boxes(cam, RES)
                asp = (rep["whole"][3] - rep["whole"][2]) / float(rep["whole"][1] - rep["whole"][0])
                sc = 0.0
                for k in ("visor", "blue", "bandL", "legBLband", "legFLband", "legFRband", "cowl"):
                    if k in REF:
                        sc += sum(abs(rep[k][i] - REF[k][i]) for i in range(4))
                print("SWEEP az=%4.1f el=%4.1f aspect=%.3f (ref .794) err=%6.0f" % (az, el, asp, sc))
                if best is None or sc < best[0]:
                    best = (sc, az, el, asp)
        print("BEST", best)
        return

    fit_camera(cam, cfg, parts, REF["whole"], RES)
    print("camera fit: az=%.1f el=%.1f lens=%.0f dist=%.3f target=%s" % (
        cfg["az"], cfg["el"], cfg["lens"], cfg["dist"],
        [round(v, 3) for v in cfg["target"]]))
    report(cam, RES)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PROJ, "enemy_crawler.blend"))
    print("SAVED blend")

    if STAGE in ("all", "render"):
        render_to(os.path.join(RENDERS, "hero.png"))
        ground.hide_render = True
        bpy.context.scene.render.film_transparent = True
        render_to(os.path.join(RENDERS, "mask.png"))
        bpy.context.scene.render.film_transparent = False
        ground.hide_render = False
        for name, az in (("view_front", 2.0), ("view_side", 90.0), ("view_rear34", 205.0)):
            c2 = dict(cfg)
            c2["az"] = az
            place(cam, c2, Vector(cfg["target"]), cfg["dist"] * 1.06)
            render_to(os.path.join(RENDERS, name + ".png"))
        place(cam, cfg, Vector(cfg["target"]), cfg["dist"])

    export_all(coll)


main()















