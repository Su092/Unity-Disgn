# -*- coding: utf-8 -*-
"""红色经典敞篷跑车 · 参考图重建（只依据 refs/ 的跑车参考图）

设计口径：
  X: 车头 +X，车尾 -X，原点在轴距中心
  Y: 左右对称，+Y 为车身左侧
  Z: 地面 = 0

主要体量（m）：
  车长 4.25，车宽 1.72（轮外 1.96），车高 1.15
  轴距 2.40，前轴 x=+1.25，后轴 x=-1.15
  轮胎外径 0.68，轮心 z=0.34

构件策略：分件装配。车身是闭合 loft，轮/胎/轮毂/内饰/镀铬件各自闭合；
构件之间在不可见处交叠。逐件跑 mesh / normals / selfint / buried_true。
"""

import bpy
import bmesh
import math
import os
import random

from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)

COLL = None
MATS = {}
OBJS = []
TAU = 2.0 * math.pi


# ---------------------------------------------------------------- 基础网格

def _finish(name, verts, faces, mat):
    me = bpy.data.meshes.new("MESH-" + name)
    me.from_pydata(verts, [], faces)
    me.validate(verbose=False)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    COLL.objects.link(obj)
    obj.data.materials.append(MATS[mat])
    OBJS.append(obj)
    return obj


def box(name, x0, x1, y0, y1, z0, z1, mat):
    verts = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7),
        (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    return _finish(name, verts, faces, mat)


def beam(name, p0, p1, width, depth, mat):
    p0, p1 = Vector(p0), Vector(p1)
    axis = (p1 - p0).normalized()
    ref = Vector((0.0, 1.0, 0.0))
    if abs(axis.dot(ref)) > 0.9:
        ref = Vector((0.0, 0.0, 1.0))
    side = axis.cross(ref).normalized()
    up = side.cross(axis).normalized()
    verts = []
    for p in (p0, p1):
        for s, u in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            verts.append(tuple(p + side * (s * width * 0.5) + up * (u * depth * 0.5)))
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7),
        (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    return _finish(name, verts, faces, mat)


def panel_quad(name, quad, offset, mat):
    off = Vector(offset)
    a = [Vector(p) for p in quad]
    b = [p + off for p in a]
    verts = [tuple(p) for p in a + b]
    faces = [
        (0, 1, 2, 3), (7, 6, 5, 4),
        (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    return _finish(name, verts, faces, mat)


def loft_body(name, stations, n, mat):
    rings = []
    for (x, w, zb, zt) in stations:
        ring = []
        cz = 0.5 * (zb + zt)
        hz = 0.5 * (zt - zb)
        for i in range(n):
            a = TAU * i / n
            cy, sz = math.cos(a), math.sin(a)
            y = w * math.copysign(abs(cy) ** 0.65, cy)
            z = cz + hz * math.copysign(abs(sz) ** 1.35, sz)
            ring.append((x, y, z))
        rings.append(ring)
    verts = [p for ring in rings for p in ring]
    faces = []
    for r in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((r * n + i, r * n + j, (r + 1) * n + j, (r + 1) * n + i))
    faces.append(tuple(reversed(range(n))))
    faces.append(tuple((len(rings) - 1) * n + i for i in range(n)))
    return _finish(name, verts, faces, mat)


def _basis(axis):
    axis = Vector(axis).normalized()
    ref = Vector((1.0, 0.0, 0.0))
    if abs(axis.dot(ref)) > 0.9:
        ref = Vector((0.0, 1.0, 0.0))
    u = (ref - axis * ref.dot(axis)).normalized()
    v = axis.cross(u).normalized()
    return axis, u, v


def cylinder_axis(name, center, axis, radius, length, mat, n=24):
    axis, u, v = _basis(axis)
    c = Vector(center)
    verts = []
    for side in (-1, 1):
        cc = c + axis * (side * length * 0.5)
        for i in range(n):
            a = TAU * i / n
            verts.append(tuple(cc + u * (radius * math.cos(a)) + v * (radius * math.sin(a))))
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return _finish(name, verts, faces, mat)


def torus_axis(name, center, axis, major, minor, mat, nm=24, nn=8):
    axis, u, v = _basis(axis)
    c = Vector(center)
    verts = []
    for i in range(nm):
        a = TAU * i / nm
        radial = u * math.cos(a) + v * math.sin(a)
        cc = c + radial * major
        for j in range(nn):
            b = TAU * j / nn
            p = cc + radial * (minor * math.cos(b)) + axis * (minor * math.sin(b))
            verts.append(tuple(p))
    faces = []
    for i in range(nm):
        ni = (i + 1) % nm
        for j in range(nn):
            nj = (j + 1) % nn
            faces.append((i * nn + j, ni * nn + j, ni * nn + nj, i * nn + nj))
    return _finish(name, verts, faces, mat)


def ellipsoid(name, center, scale, mat, useg=20, vseg=10):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=useg, v_segments=vseg, radius=1.0)
    c = Vector(center)
    sx, sy, sz = scale
    for v in bm.verts:
        v.co = c + Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    me = bpy.data.meshes.new("MESH-" + name)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    COLL.objects.link(obj)
    obj.data.materials.append(MATS[mat])
    OBJS.append(obj)
    return obj


def ellipse_ring_x(name, x, yc, zc, ry, rz, thick, depth, mat, n=28):
    verts = []
    for xoff in (-depth * 0.5, depth * 0.5):
        for r_scale in (1.0, 1.0 - thick):
            for i in range(n):
                a = TAU * i / n
                verts.append((x + xoff, yc + ry * r_scale * math.cos(a),
                              zc + rz * r_scale * math.sin(a)))
    # 0..n outer front, n..2n inner front, 2n..3n outer back, 3n..4n inner back
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
        faces.append((2 * n + i, 3 * n + i, 3 * n + j, 2 * n + j))
        faces.append((i, 2 * n + i, 2 * n + j, j))
        faces.append((n + i, n + j, 3 * n + j, 3 * n + i))
    return _finish(name, verts, faces, mat)


def ellipse_disc_x(name, x, yc, zc, ry, rz, depth, mat, n=28):
    verts = []
    for xoff in (-depth * 0.5, depth * 0.5):
        for i in range(n):
            a = TAU * i / n
            verts.append((x + xoff, yc + ry * math.cos(a), zc + rz * math.sin(a)))
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return _finish(name, verts, faces, mat)


def disc_axis(name, center, axis, radius, depth, mat, n=28):
    axis, u, v = _basis(axis)
    c = Vector(center)
    verts = []
    for side in (-1, 1):
        cc = c + axis * (side * depth * 0.5)
        for i in range(n):
            a = TAU * i / n
            verts.append(tuple(cc + u * (radius * math.cos(a)) + v * (radius * math.sin(a))))
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return _finish(name, verts, faces, mat)


# ---------------------------------------------------------------- 材质 / UV

def _noise(x, y, seed):
    r = random.Random(seed * 7919 + x * 31 + y)
    return r.random()


def make_texture(name, kind, base, seed):
    size = 256
    img = bpy.data.images.new(name, width=size, height=size, alpha=False)
    px = [0.0] * (size * size * 4)
    for y in range(size):
        for x in range(size):
            n = _noise(x, y, seed)
            r, g, b = base
            if kind == "paint":
                r *= 0.97 + 0.05 * n
                g *= 0.97 + 0.05 * n
                b *= 0.97 + 0.05 * n
            elif kind == "chrome":
                line = 0.5 + 0.5 * math.sin(y * 0.45)
                r = r * (0.82 + 0.22 * line) + 0.02 * n
                g = g * (0.82 + 0.22 * line) + 0.02 * n
                b = b * (0.82 + 0.22 * line) + 0.02 * n
            elif kind == "rubber":
                if (x + y) % 24 < 3 or (x - y) % 24 < 3:
                    r, g, b = 0.012, 0.012, 0.012
                else:
                    r *= 0.8 + 0.4 * n
                    g *= 0.8 + 0.4 * n
                    b *= 0.8 + 0.4 * n
            elif kind == "leather":
                r *= 0.75 + 0.5 * n
                g *= 0.75 + 0.5 * n
                b *= 0.75 + 0.5 * n
            elif kind == "glass":
                r *= 0.85 + 0.25 * n
                g *= 0.88 + 0.20 * n
                b *= 0.9 + 0.18 * n
            elif kind == "silver":
                line = 0.5 + 0.5 * math.sin(y * 0.6)
                r = r * (0.86 + 0.16 * line)
                g = g * (0.86 + 0.16 * line)
                b = b * (0.86 + 0.16 * line)
            elif kind == "lens":
                ring = 0.5 + 0.5 * math.sin(math.hypot(x - 128, y - 128) * 0.22)
                r *= 0.8 + 0.35 * ring
                g *= 0.8 + 0.35 * ring
                b *= 0.8 + 0.35 * ring
            elif kind == "grille":
                if x % 16 < 2 or y % 16 < 2:
                    r, g, b = 0.02, 0.02, 0.02
                else:
                    r *= 0.7 + 0.4 * n
                    g *= 0.7 + 0.4 * n
                    b *= 0.7 + 0.4 * n
            elif kind == "perf":
                if (x % 20 - 10) ** 2 + (y % 20 - 10) ** 2 < 18:
                    r, g, b = 0.02, 0.02, 0.02
                else:
                    r *= 0.8 + 0.25 * n
                    g *= 0.8 + 0.25 * n
                    b *= 0.8 + 0.25 * n
            i = (y * size + x) * 4
            px[i:i + 4] = [max(0.0, min(1.0, r)), max(0.0, min(1.0, g)),
                           max(0.0, min(1.0, b)), 1.0]
    img.pixels[:] = px
    path = os.path.join(OUT, "Modle_%s_basecolor.jpg" % name)
    img.filepath_raw = path
    img.file_format = "JPEG"
    img.save()
    img.pack()
    return img


def make_material(name, img, metal=0.0, rough=0.5):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    if name == "M_Glass":
        bsdf.inputs["Alpha"].default_value = 0.32
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            pass
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "UVMap"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = "REPEAT"
    nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def build_materials():
    specs = [
        ("PaintRed", "paint", (0.62, 0.025, 0.02), 1, 0.25, 0.24),
        ("Chrome", "chrome", (0.72, 0.72, 0.74), 2, 1.0, 0.12),
        ("Rubber", "rubber", (0.025, 0.025, 0.025), 3, 0.0, 0.9),
        ("Interior", "leather", (0.035, 0.033, 0.032), 4, 0.0, 0.78),
        ("Glass", "glass", (0.30, 0.38, 0.42), 5, 0.0, 0.08),
        ("Silver", "silver", (0.72, 0.72, 0.68), 6, 0.8, 0.3),
        ("RedLens", "lens", (0.55, 0.02, 0.02), 7, 0.15, 0.2),
        ("DarkGrille", "grille", (0.06, 0.06, 0.06), 8, 0.4, 0.55),
        ("Perf", "perf", (0.30, 0.30, 0.28), 9, 0.85, 0.38),
    ]
    for (name, kind, base, seed, metal, rough) in specs:
        img = make_texture(name, kind, base, seed)
        MATS[name] = make_material("M_" + name, img, metal, rough)


def unwrap_all():
    scale = 1.0
    for o in OBJS:
        me = o.data
        while me.uv_layers:
            me.uv_layers.remove(me.uv_layers[0])
        uvl = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            n = poly.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for li, vi in zip(poly.loop_indices, poly.vertices):
                co = me.vertices[vi].co
                if ax == 0:
                    uv = (co.y / scale, co.z / scale)
                elif ax == 1:
                    uv = (co.x / scale, co.z / scale)
                else:
                    uv = (co.x / scale, co.y / scale)
                uvl.data[li].uv = uv
        uvl.active_render = True


# ---------------------------------------------------------------- 车身

STATIONS = [
    (-2.10, 0.55, 0.42, 0.70),
    (-1.95, 0.72, 0.34, 0.78),
    (-1.55, 0.82, 0.30, 0.82),
    (-1.10, 0.86, 0.28, 0.82),
    (-0.65, 0.86, 0.27, 0.80),
    (-0.20, 0.84, 0.27, 0.78),
    (0.25, 0.83, 0.27, 0.77),
    (0.75, 0.82, 0.28, 0.75),
    (1.25, 0.80, 0.29, 0.72),
    (1.70, 0.78, 0.31, 0.68),
    (2.00, 0.72, 0.35, 0.62),
    (2.15, 0.62, 0.40, 0.56),
]


def wheel(name, cx, cy, side):
    y_out = cy + side * 0.10
    torus_axis(name + "_tire", (cx, cy, 0.34), (0, 1, 0), 0.24, 0.10,
               "Rubber", nm=28, nn=10)
    cylinder_axis(name + "_rim", (cx, cy, 0.34), (0, 1, 0), 0.17, 0.18,
                  "DarkGrille", n=28)
    torus_axis(name + "_lip", (cx, y_out, 0.34), (0, 1, 0), 0.172, 0.012,
               "Chrome", nm=28, nn=8)
    cylinder_axis(name + "_hub", (cx, y_out, 0.34), (0, 1, 0), 0.045, 0.03,
                  "Chrome", n=16)
    for i in range(5):
        a = TAU * i / 5.0 + math.pi / 10.0
        p0 = (cx + 0.035 * math.cos(a), 0.34 + 0.035 * math.sin(a))
        p1 = (cx + 0.155 * math.cos(a), 0.34 + 0.155 * math.sin(a))
        # 平面 Y 内的辐条
        beam_plane(name + "_spoke%d" % i, "Y", y_out, side, p0, p1, 0.035, 0.02,
                   "DarkGrille")


def beam_plane(name, plane, coord, sign, p0, p1, width, depth, mat):
    du = p1[0] - p0[0]
    dv = p1[1] - p0[1]
    length = math.hypot(du, dv)
    if length < 1e-9:
        return None
    su, sv = -dv / length, du / length
    center = coord + sign * (depth * 0.5 + 0.01)
    verts = []
    for p in (p0, p1):
        for a, layer in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            u = p[0] + su * a * width * 0.5
            v = p[1] + sv * a * width * 0.5
            off = center + sign * layer * depth * 0.5
            verts.append((off, u, v) if plane == "X" else (u, off, v))
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7),
        (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    return _finish(name, verts, faces, mat)


def build():
    global COLL
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    COLL = bpy.data.collections.new("SportsCar")
    sc.collection.children.link(COLL)

    build_materials()

    # 车身主壳
    loft_body("GEO-Body", STATIONS, 20, "PaintRed")

    # 四个翼子板鼓包
    for side, ys in (("L", 0.76), ("R", -0.76)):
        ellipsoid("GEO-FrontFender" + side, (1.25, 0.72, 0.66), (0.68, 0.14, 0.15), "PaintRed")
        ellipsoid("GEO-RearFender" + side, (-1.15, 0.72, 0.68), (0.65, 0.15, 0.17), "PaintRed")

    # 四个轮
    wheel("GEO-WheelFL", 1.25, 0.88, 1)
    wheel("GEO-WheelFR", 1.25, -0.88, -1)
    wheel("GEO-WheelRL", -1.15, 0.88, 1)
    wheel("GEO-WheelRR", -1.15, -0.88, -1)

    # 座舱：深色开口 + 红色围边 + 座椅
    box("GEO-CockpitWell", -0.68, 0.36, -0.54, 0.54, 0.755, 0.785, "Interior")
    box("GEO-CockpitSillF", 0.36, 0.44, -0.58, 0.58, 0.76, 0.80, "PaintRed")
    box("GEO-CockpitSillR", -0.76, -0.68, -0.58, 0.58, 0.76, 0.80, "PaintRed")
    box("GEO-CockpitSillL", -0.68, 0.36, 0.54, 0.62, 0.76, 0.80, "PaintRed")
    box("GEO-CockpitSillR2", -0.68, 0.36, -0.62, -0.54, 0.76, 0.80, "PaintRed")
    for side, yc in (("L", 0.28), ("R", -0.28)):
        box("GEO-SeatCushion" + side, -0.35, 0.02, yc - 0.17, yc + 0.17,
            0.79, 0.87, "Interior")
        box("GEO-SeatBack" + side, -0.47, -0.37, yc - 0.17, yc + 0.17,
            0.86, 1.05, "Interior")
        ellipsoid("GEO-Headrest" + side, (-0.43, yc, 1.06), (0.07, 0.10, 0.07), "Interior")
    box("GEO-Dashboard", 0.27, 0.37, -0.55, 0.55, 0.78, 0.90, "Interior")

    # 方向盘 + 转向柱
    torus_axis("GEO-SteeringWheel", (0.14, -0.28, 0.93), (1, 0, 0), 0.15, 0.018,
               "Silver", nm=24, nn=8)
    cylinder_axis("GEO-SteeringHub", (0.14, -0.28, 0.93), (1, 0, 0), 0.04, 0.04,
                  "Interior", n=16)
    beam("GEO-SteeringColumn", (0.14, -0.28, 0.93), (0.30, -0.28, 0.86),
         0.03, 0.03, "Interior")

    # 风挡 + 镀铬框
    panel_quad("GEO-Windshield",
               [(0.36, -0.55, 0.80), (0.36, 0.55, 0.80),
                (0.52, 0.55, 1.06), (0.52, -0.55, 1.06)],
               (0.02, 0.0, 0.0), "Glass")
    beam("GEO-WindshieldPostL", (0.36, 0.55, 0.80), (0.52, 0.55, 1.06),
         0.035, 0.035, "Chrome")
    beam("GEO-WindshieldPostR", (0.36, -0.55, 0.80), (0.52, -0.55, 1.06),
         0.035, 0.035, "Chrome")
    beam("GEO-WindshieldTop", (0.52, -0.57, 1.06), (0.52, 0.57, 1.06),
         0.035, 0.035, "Chrome")
    box("GEO-Mirror", 0.48, 0.54, -0.06, 0.06, 1.01, 1.06, "Chrome")

    # 折叠软顶
    box("GEO-FoldedTop", -0.86, -0.56, -0.55, 0.55, 0.79, 0.90, "Interior")

    # 前格栅：椭圆镀铬环 + 黑色底板 + 横向镀铬条
    ellipse_disc_x("GEO-GrillePanel", 2.15, 0.0, 0.47, 0.42, 0.13, 0.04,
                   "DarkGrille", n=28)
    ellipse_ring_x("GEO-GrilleRing", 2.17, 0.0, 0.47, 0.44, 0.14, 0.10, 0.08,
                   "Chrome", n=28)
    for i, z in enumerate((0.36, 0.41, 0.46, 0.51, 0.56)):
        box("GEO-GrilleSlat%d" % i, 2.18, 2.20, -0.36, 0.36,
            z - 0.010, z + 0.010, "Chrome")

    # 头灯 + 小灯
    for side, y in (("L", 0.52), ("R", -0.52)):
        ellipsoid("GEO-HeadlightPod" + side, (2.02, y, 0.58),
                  (0.12, 0.14, 0.11), "PaintRed", useg=16, vseg=8)
        torus_axis("GEO-HeadlightRing" + side, (2.16, y, 0.60), (1, 0, 0),
                   0.145, 0.022, "Chrome", nm=24, nn=8)
        disc_axis("GEO-HeadlightLens" + side, (2.16, y, 0.60), (1, 0, 0),
                  0.132, 0.03, "Glass", n=24)
        cylinder_axis("GEO-TurnSignal" + side, (2.15, y * 0.92, 0.42), (1, 0, 0),
                      0.05, 0.04, "Chrome", n=16)
        disc_axis("GEO-TurnLens" + side, (2.18, y * 0.92, 0.42), (1, 0, 0),
                  0.04, 0.01, "Glass", n=16)

    # 前保险杠 + 防撞柱
    cylinder_axis("GEO-FrontBumper", (2.20, 0.0, 0.33), (0, 1, 0),
                  0.038, 1.66, "Chrome", n=16)
    for side, y in (("L", 0.30), ("R", -0.30)):
        box("GEO-BumperPost" + side, 2.16, 2.24, y - 0.045, y + 0.045,
            0.27, 0.44, "Chrome")

    # 侧排气管 + 隔热罩
    for side, y in (("L", 0.92), ("R", -0.92)):
        cylinder_axis("GEO-SidePipe" + side, (-0.05, y, 0.27), (1, 0, 0),
                      0.055, 1.35, "Chrome", n=20)
        cylinder_axis("GEO-SideShield" + side, (0.10, y, 0.27), (1, 0, 0),
                      0.068, 0.62, "Perf", n=20)
        box("GEO-SidePipeBracket" + side, -0.55, -0.45, y - 0.03, y + 0.03,
            0.27, 0.35, "Chrome")

    # 侧通风口 + 门把手
    for side, y in (("L", 0.845), ("R", -0.845)):
        for i in range(3):
            box("GEO-SideVent%s%d" % (side, i), 0.45, 0.65,
                y - 0.012, y + 0.012, 0.53 + i * 0.045, 0.555 + i * 0.045,
                "DarkGrille")
        box("GEO-DoorHandle" + side, -0.22, -0.10, y - 0.012, y + 0.012,
            0.62, 0.65, "Chrome")

    # 银色赛车条纹（车头 + 车尾）
    hood = [
        (0.45, 0.75, 0.770), (0.75, 1.05, 0.750), (1.05, 1.35, 0.720),
        (1.35, 1.65, 0.685), (1.65, 1.90, 0.650), (1.90, 2.05, 0.610),
    ]
    for i, (x0, x1, z) in enumerate(hood):
        box("GEO-StripeHood%d" % i, x0, x1, -0.055, 0.055, z, z + 0.012, "Silver")
        box("GEO-HoodTrim%d" % i, x0, x1, -0.012, 0.012, z + 0.010, z + 0.017, "Chrome")
    disc_axis("GEO-HoodEmblem", (2.02, 0.0, 0.635), (1, 0, 0), 0.045, 0.02,
              "Chrome", n=20)
    deck = [
        (-2.00, -1.65, 0.795), (-1.65, -1.30, 0.815), (-1.30, -0.95, 0.818),
        (-0.95, -0.68, 0.800),
    ]
    for i, (x0, x1, z) in enumerate(deck):
        box("GEO-StripeDeck%d" % i, x0, x1, -0.055, 0.055, z, z + 0.012, "Silver")

    # 引擎盖进气鼓包
    box("GEO-HoodScoop", 0.80, 1.30, -0.18, 0.18, 0.735, 0.770, "PaintRed")

    # 尾部：尾灯、后保险杠、排气管、油箱盖
    for side, y in (("L", 0.42), ("R", -0.42)):
        for j, z in enumerate((0.52, 0.62)):
            torus_axis("GEO-TailRing%s%d" % (side, j), (-2.12, y, z), (1, 0, 0),
                       0.070, 0.014, "Chrome", nm=20, nn=8)
            disc_axis("GEO-TailLens%s%d" % (side, j), (-2.12, y, z), (1, 0, 0),
                      0.058, 0.02, "RedLens", n=20)
    cylinder_axis("GEO-RearBumper", (-2.20, 0.0, 0.33), (0, 1, 0),
                  0.038, 1.62, "Chrome", n=16)
    for side, y in (("L", 0.30), ("R", -0.30)):
        box("GEO-RearBumperPost" + side, -2.24, -2.16, y - 0.045, y + 0.045,
            0.27, 0.44, "Chrome")
    for side, y in (("L", 0.42), ("R", -0.42)):
        cylinder_axis("GEO-Exhaust" + side, (-2.16, y, 0.24), (1, 0, 0),
                      0.05, 0.14, "Chrome", n=16)
    cylinder_axis("GEO-FuelCap", (-1.55, 0.58, 0.83), (0, 0, 1), 0.075, 0.02,
                  "Chrome", n=20)
    box("GEO-TrunkHandle", -2.05, -1.98, -0.10, 0.10, 0.63, 0.66, "Chrome")

    # 车身分缝：只做很浅的深色线，增强钣金读法
    for side, y in (("L", 0.855), ("R", -0.855)):
        box("GEO-DoorSeamF" + side, 0.36, 0.375, y - 0.008, y + 0.008,
            0.40, 0.77, "DarkGrille")
        box("GEO-DoorSeamR" + side, -0.69, -0.675, y - 0.008, y + 0.008,
            0.40, 0.78, "DarkGrille")
    box("GEO-HoodSeam", 0.37, 0.385, -0.68, 0.68, 0.762, 0.772, "DarkGrille")
    box("GEO-TrunkSeam", -1.90, -1.885, -0.64, 0.64, 0.788, 0.798, "DarkGrille")

    # 单根：车身作为根网格
    root = bpy.data.objects["GEO-Body"]
    for o in OBJS:
        if o is not root:
            o.parent = root

    unwrap_all()

    tris = sum(len(p.vertices) - 2 for o in OBJS for p in o.data.polygons)
    mn = [1e9] * 3
    mx = [-1e9] * 3
    for o in OBJS:
        for v in o.data.vertices:
            p = o.matrix_world @ v.co
            for k in range(3):
                mn[k] = min(mn[k], p[k])
                mx[k] = max(mx[k], p[k])
    size = [round(mx[k] - mn[k], 3) for k in range(3)]
    print("[build] objects=%d tris=%d" % (len(OBJS), tris))
    print("[build] AABB size_m=%s min_m=%s max_m=%s"
          % (size, [round(v, 3) for v in mn], [round(v, 3) for v in mx]))
    print("[build] materials=%s" % ", ".join(sorted(MATS)))

    blend = os.path.join(OUT, "sports_car.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print("[build] saved %s" % blend)


if __name__ == "__main__":
    build()
