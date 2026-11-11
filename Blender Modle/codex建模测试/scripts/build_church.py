# -*- coding: utf-8 -*-
"""Codex 建模测试 · 木制哥特式教堂（单西塔 + 中殿 + 侧廊 + 半圆室）

设计口径（全部米制，1 BU = 1 m）：
  X: 西外皮 = 0，向东为正
  Y: 长轴中线 = 0
  Z: 地面 = 0

建筑体量：
  西塔 6 x 6，塔身到 15.0，八角尖塔到 23.5
  中殿 14 长 x 9 宽，檐口 7.2，脊 12.0
  两侧侧廊各 2.3 宽，檐口 4.2，单坡到 5.8
  东端八角半圆室，半径 4.8，墙到 6.5，顶到 8.8
  西侧门廊 4.4 宽，山墙顶 6.6

构件策略：分件装配。每个对象都是闭合网格；构件之间在不可见处留
小交叠/贴面，保留木构真实缝隙。逐件跑 mesh / normals / buried_true。

用法：
  blender -b --factory-startup --python scripts/build_church.py
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

GAP = 0.008
COLL = None
MATS = {}
OBJS = []


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


def beam_plane(name, plane, coord, sign, p0, p1, width, depth, mat):
    """在给定平面内画一根有宽度的梁：宽度沿平面内法向，厚度沿平面法线。"""
    du = p1[0] - p0[0]
    dv = p1[1] - p0[1]
    length = math.hypot(du, dv)
    if length < 1e-9:
        return None
    su, sv = -dv / length, du / length
    verts = []
    center = coord + sign * (depth * 0.5 + 0.01)
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


def polygon_prism(name, cx, cy, r0, r1, n, z0, z1, mat, rot=0.0):
    """n 边形棱柱 / 截锥；r1=0 时收成尖顶。"""
    def ring(r, z):
        return [(cx + r * math.cos(rot + 2.0 * math.pi * i / n),
                 cy + r * math.sin(rot + 2.0 * math.pi * i / n), z)
                for i in range(n)]

    bottom = ring(r0, z0)
    verts = list(bottom)
    faces = []
    if r1 <= 1e-9:
        apex = len(verts)
        verts.append((cx, cy, z1))
        for i in range(n):
            faces.append((i, (i + 1) % n, apex))
        faces.append(tuple(reversed(range(n))))
    else:
        top = ring(r1, z1)
        verts += top
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, n + j, n + i))
        faces.append(tuple(reversed(range(n))))
        faces.append(tuple(range(n, 2 * n)))
    return _finish(name, verts, faces, mat)


def quad_slab(name, quad, dz, mat):
    top = [Vector(p) for p in quad]
    bot = [p + Vector((0.0, 0.0, -dz)) for p in top]
    verts = [tuple(p) for p in top + bot]
    faces = [
        (0, 1, 2, 3), (7, 6, 5, 4),
        (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    return _finish(name, verts, faces, mat)


def gable_roof(name, x0, x1, y_half, z_eave, z_ridge, overhang, thick, mat):
    xa, xb = x0 - overhang, x1 + overhang
    y = y_half + overhang
    quad_slab(name + "_S",
              [(xa, y, z_eave), (xb, y, z_eave), (xb, 0.0, z_ridge), (xa, 0.0, z_ridge)],
              thick, mat)
    quad_slab(name + "_N",
              [(xa, -y, z_eave), (xb, -y, z_eave), (xb, 0.0, z_ridge), (xa, 0.0, z_ridge)],
              thick, mat)


def shed_roof(name, x0, x1, y_out, y_in, z_out, z_in, thick, mat):
    quad_slab(name,
              [(x0, y_out, z_out), (x1, y_out, z_out), (x1, y_in, z_in), (x0, y_in, z_in)],
              thick, mat)


def tri_prism(name, x0, x1, y_half, z0, z1, mat):
    """沿 X 挤出的三角形山墙。"""
    verts = [
        (x0, -y_half, z0), (x0, y_half, z0), (x0, 0.0, z1),
        (x1, -y_half, z0), (x1, y_half, z0), (x1, 0.0, z1),
    ]
    faces = [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]
    return _finish(name, verts, faces, mat)


# ---------------------------------------------------------------- 平面构件

def plane_box(name, plane, coord, sign, u0, u1, v0, v1, depth, mat, inset=0.0):
    if plane == "Y":
        if sign > 0:
            y0, y1 = coord - inset, coord + depth
        else:
            y0, y1 = coord - depth, coord + inset
        return box(name, u0, u1, y0, y1, v0, v1, mat)
    if plane == "X":
        if sign > 0:
            x0, x1 = coord - inset, coord + depth
        else:
            x0, x1 = coord - depth, coord + inset
        return box(name, x0, x1, u0, u1, v0, v1, mat)
    raise ValueError(plane)


def plane_point(plane, coord, sign, u, v, depth_mid):
    if plane == "Y":
        return (u, coord + sign * depth_mid, v)
    return (coord + sign * depth_mid, u, v)


def arch_curve(w, h, v0, spring_ratio=0.62, n=7):
    """左半尖券外缘：从左侧起拱点到顶点。"""
    vs = v0 + spring_ratio * h
    pts = []
    for i in range(n + 1):
        t = i / float(n)
        u = (1 - t) ** 2 * (-w * 0.5) + 2 * (1 - t) * t * (-w * 0.5)
        v = (1 - t) ** 2 * vs + 2 * (1 - t) * t * (v0 + h) + t * t * (v0 + h)
        pts.append((u, v))
    return pts, vs


def arch_polygon(w, h, v0, spring_ratio=0.62, n=7):
    left, vs = arch_curve(w, h, v0, spring_ratio, n)
    right = [(-u, v) for (u, v) in reversed(left[:-1])]
    pts = [(-w * 0.5, v0)] + left + right + [(w * 0.5, v0)]
    # 去掉重复的底部点，保持闭合
    out = []
    for p in pts:
        if not out or (abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1])) > 1e-7:
            out.append(p)
    return out


def arch_panel(name, plane, coord, sign, u_c, w, h, v0, depth, mat, inset=0.0):
    pts = arch_polygon(w, h, v0)
    n = len(pts)
    front = [plane_point(plane, coord, sign, u_c + u, v, depth + inset) for (u, v) in pts]
    back = [plane_point(plane, coord, sign, u_c + u, v, inset) for (u, v) in pts]
    verts = front + back
    faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return _finish(name, verts, faces, mat)


def arch_frame(name, plane, coord, sign, u_c, w, h, v0, depth, mat, t=0.10):
    """尖券窗框：两根边梃 + 顶部两段弧 + 窗台 + 中梃/横档。
    各段之间留 GAP，保证同一对象内不互穿。"""
    spring = 0.62
    vs = v0 + spring * h
    # 边梃
    plane_box(name + "_jambL", plane, coord, sign, u_c - w * 0.5, u_c - w * 0.5 + t,
              v0, vs - GAP, depth, mat)
    plane_box(name + "_jambR", plane, coord, sign, u_c + w * 0.5 - t, u_c + w * 0.5,
              v0, vs - GAP, depth, mat)
    # 窗台
    plane_box(name + "_sill", plane, coord, sign, u_c - w * 0.5 + t + GAP,
              u_c + w * 0.5 - t - GAP, v0, v0 + t, depth, mat)
    # 左右弧段
    left, _ = arch_curve(w, h, v0, spring, 7)
    for side, pts in (("L", left), ("R", [(-u, v) for (u, v) in left])):
        for i in range(len(pts) - 1):
            (u0, v0p), (u1, v1p) = pts[i], pts[i + 1]
            if i == 0:
                v0p += GAP
            if i == len(pts) - 2:
                # 收尖处留缝，避免左右两段在顶点互穿
                u1 *= 1.0 - 0.02
                v1p -= GAP * 2.0
            beam_plane(name + "_arch%s%d" % (side, i), plane, coord, sign,
                       (u_c + u0, v0p), (u_c + u1, v1p), t, depth, mat)
    # 中梃（分两段避开窗台与顶点）
    plane_box(name + "_mullion", plane, coord, sign, u_c - 0.035, u_c + 0.035,
              v0 + t + GAP, v0 + h - t - GAP, depth * 0.8, mat, inset=0.01)
    # 横档（左右两段，避开中梃）
    zt = v0 + h * 0.56
    plane_box(name + "_transomL", plane, coord, sign, u_c - w * 0.5 + t + GAP,
              u_c - 0.035 - GAP, zt - 0.03, zt + 0.03, depth * 0.8, mat, inset=0.01)
    plane_box(name + "_transomR", plane, coord, sign, u_c + 0.035 + GAP,
              u_c + w * 0.5 - t - GAP, zt - 0.03, zt + 0.03, depth * 0.8, mat, inset=0.01)


def annulus(name, plane, coord, sign, u_c, v_c, r_out, r_in, depth, mat, n=32, inset=0.0):
    of, inf, ob, inb = [], [], [], []
    for i in range(n):
        a = 2.0 * math.pi * i / n
        co, si = math.cos(a), math.sin(a)
        of.append(plane_point(plane, coord, sign, u_c + r_out * co, v_c + r_out * si, depth + inset))
        inf.append(plane_point(plane, coord, sign, u_c + r_in * co, v_c + r_in * si, depth + inset))
        ob.append(plane_point(plane, coord, sign, u_c + r_out * co, v_c + r_out * si, inset))
        inb.append(plane_point(plane, coord, sign, u_c + r_in * co, v_c + r_in * si, inset))
    verts = of + inf + ob + inb
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))                  # front
        faces.append((2 * n + i, 3 * n + i, 3 * n + j, 2 * n + j))  # back
        faces.append((i, 2 * n + i, 2 * n + j, j))          # outer wall
        faces.append((n + i, n + j, 3 * n + j, 3 * n + i))  # inner wall
    return _finish(name, verts, faces, mat)


def disc(name, plane, coord, sign, u_c, v_c, r, depth, mat, n=32, inset=0.0):
    pts = [(math.cos(2 * math.pi * i / n) * r, math.sin(2 * math.pi * i / n) * r)
           for i in range(n)]
    front = [plane_point(plane, coord, sign, u_c + u, v_c + v, depth + inset) for (u, v) in pts]
    back = [plane_point(plane, coord, sign, u_c + u, v_c + v, inset) for (u, v) in pts]
    verts = front + back
    faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return _finish(name, verts, faces, mat)


# ---------------------------------------------------------------- 材质 / UV

def _noise(x, y, seed):
    r = random.Random(seed * 7919 + x * 31 + y)
    return r.random()


def make_texture(name, kind, base, seed):
    size = 512
    img = bpy.data.images.new(name, width=size, height=size, alpha=False)
    px = [0.0] * (size * size * 4)
    for y in range(size):
        for x in range(size):
            n = _noise(x, y, seed)
            r, g, b = base
            if kind == "plank":
                if x % 64 < 6:
                    r, g, b = r * 0.45, g * 0.45, b * 0.45
                grain = 0.5 + 0.5 * math.sin(x * 0.055 + math.sin(y * 0.012) * 2.0)
                r *= 0.94 + 0.06 * grain + 0.03 * n
                g *= 0.94 + 0.06 * grain + 0.03 * n
                b *= 0.94 + 0.06 * grain + 0.03 * n
            elif kind == "timber":
                grain = 0.5 + 0.5 * math.sin(x * 0.09 + math.sin(y * 0.012) * 3.0)
                r *= 0.86 + 0.18 * grain + 0.03 * n
                g *= 0.86 + 0.18 * grain + 0.03 * n
                b *= 0.86 + 0.18 * grain + 0.03 * n
            elif kind == "shingle":
                row = y // 40
                if y % 40 < 6:
                    r, g, b = r * 0.36, g * 0.36, b * 0.36
                elif (x + row * 24) % 64 < 3:
                    r, g, b = r * 0.60, g * 0.60, b * 0.60
                r *= 0.94 + 0.08 * n
                g *= 0.94 + 0.08 * n
                b *= 0.94 + 0.08 * n
            elif kind == "glass":
                lead = (abs(((x + y) % 72) - 36) < 2
                        or abs(((x - y) % 72) - 36) < 2)
                if lead:
                    r, g, b = 0.035, 0.030, 0.025
                else:
                    r *= 0.75 + 0.35 * n
                    g *= 0.85 + 0.25 * n
                    b *= 0.90 + 0.25 * n
            elif kind == "iron":
                r *= 0.85 + 0.25 * n
                g *= 0.85 + 0.25 * n
                b *= 0.85 + 0.25 * n
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


def make_material(name, img, metal=0.0, rough=0.7):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "UVMap"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = "REPEAT"
    tex.interpolation = "Linear"
    nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def build_materials():
    specs = [
        ("TimberDark", "timber", (0.18, 0.10, 0.055), 1, 0.0, 0.68),
        ("PlankPale", "plank", (0.62, 0.44, 0.24), 2, 0.0, 0.62),
        ("Shingle", "shingle", (0.33, 0.27, 0.21), 3, 0.0, 0.74),
        ("Glass", "glass", (0.10, 0.18, 0.20), 4, 0.1, 0.25),
        ("Iron", "iron", (0.055, 0.052, 0.05), 5, 0.75, 0.45),
    ]
    for (name, kind, base, seed, metal, rough) in specs:
        img = make_texture(name, kind, base, seed)
        MATS[name] = make_material("M_" + name, img, metal, rough)


def unwrap_all():
    """全局箱式投影：按世界坐标 / texel_scale 铺 UV。

    比逐件 smart_project 更适合建筑：板缝、瓦行在整栋上保持同一实际尺度，
    不会因为每个对象各自装箱而出现"每块面一套随机纹理"的花斑。
    代价：UV 会超出 [0,1]（repeat 平铺），不满足 UV 门"全在 0..1"的口径。
    """
    texel_scale = 2.0
    for o in OBJS:
        me = o.data
        while me.uv_layers:
            me.uv_layers.remove(me.uv_layers[0])
        uvl = me.uv_layers.new(name="UVMap")
        roof_like = ("Roof" in o.name) or ("Spire" in o.name)
        for poly in me.polygons:
            n = poly.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for li, vi in zip(poly.loop_indices, poly.vertices):
                co = me.vertices[vi].co
                if roof_like:
                    uv = (co.x / texel_scale, co.z / texel_scale)
                elif ax == 0:
                    uv = (co.y / texel_scale, co.z / texel_scale)
                elif ax == 1:
                    uv = (co.x / texel_scale, co.z / texel_scale)
                else:
                    uv = (co.x / texel_scale, co.y / texel_scale)
                uvl.data[li].uv = uv
        uvl.active_render = True


# ---------------------------------------------------------------- 建筑

def build():
    global COLL
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    COLL = bpy.data.collections.new("Church")
    sc.collection.children.link(COLL)

    build_materials()

    # 台基
    box("GEO-Plinth", -1.9, 25.0, -7.5, 7.5, 0.0, 0.35, "PlankPale")
    box("GEO-PlinthStep", -2.1, 25.2, -7.7, 7.7, 0.0, 0.16, "TimberDark")

    # 西塔
    box("GEO-TowerShaft", 0.0, 6.0, -3.0, 3.0, 0.35, 15.0, "PlankPale")
    for x in (0.0, 5.75):
        for y in (-3.0, 2.75):
            box("GEO-TowerCorner_%d_%d" % (int(x * 10), int(y * 10)),
                x, x + 0.25, y, y + 0.25, 0.35, 15.0, "TimberDark")
    box("GEO-TowerCornice", -0.35, 6.35, -3.35, 3.35, 14.85, 15.35, "TimberDark")
    polygon_prism("GEO-TowerSpire", 3.0, 0.0, 3.15, 0.0, 8, 15.35, 23.5,
                  "Shingle", rot=math.pi / 8.0)

    # 塔顶角尖
    for i, (x, y) in enumerate(((0.55, 2.55), (5.45, 2.55), (0.55, -2.55), (5.45, -2.55))):
        polygon_prism("GEO-TowerPinnacle%d" % i, x, y, 0.42, 0.0, 4,
                      15.0, 17.2, "TimberDark", rot=math.pi / 4.0)

    # 塔身腰线
    for z in (4.0, 8.0, 12.0):
        box("GEO-TowerBand%d" % int(z * 10), -0.12, 6.12, -3.12, 3.12,
            z - 0.09, z + 0.09, "TimberDark")

    # 玫瑰窗（西面）
    annulus("GEO-RoseRing", "X", 0.0, -1, 3.0, 9.2, 1.72, 1.44, 0.16, "TimberDark", n=32)
    disc("GEO-RoseGlass", "X", 0.0, -1, 3.0, 9.2, 1.45, 0.05, "Glass", n=32, inset=0.02)
    disc("GEO-RoseHub", "X", 0.0, -1, 3.0, 9.2, 0.18, 0.18, "PlankPale", n=16)
    for i in range(8):
        a = 2.0 * math.pi * i / 8.0
        p0 = (3.0 + 0.20 * math.cos(a), 9.2 + 0.20 * math.sin(a))
        p1 = (3.0 + 1.40 * math.cos(a), 9.2 + 1.40 * math.sin(a))
        beam_plane("GEO-RoseSpoke%d" % i, "X", 0.0, -1, p0, p1, 0.10, 0.09, "PlankPale")

    # 门廊 + 尖券门
    box("GEO-Porch", -1.85, 0.2, -2.2, 2.2, 0.35, 5.2, "PlankPale")
    tri_prism("GEO-PorchGable", -1.85, -1.55, 2.2, 5.2, 6.7, "PlankPale")
    gable_roof("GEO-PorchRoof", -1.85, 0.2, 2.2, 5.2, 6.7, 0.18, 0.22, "Shingle")
    arch_panel("GEO-MainDoor", "X", -1.86, -1, 0.0, 2.35, 3.85, 0.35, 0.12,
               "TimberDark", inset=0.0)
    for i in range(4):
        box("GEO-DoorPlank%d" % i, -1.94, -1.90, -1.05 + i * 0.55, -1.01 + i * 0.55,
            0.45, 3.95, "TimberDark")
    for i, z in enumerate((1.0, 2.1, 3.2)):
        box("GEO-DoorHinge%d" % i, -1.99, -1.93, -1.15, 1.15, z - 0.05, z + 0.05, "Iron")

    # 中殿墙 + 侧廊墙
    box("GEO-NaveWallS", 6.0, 20.0, 4.35, 4.65, 0.35, 7.2, "PlankPale")
    box("GEO-NaveWallN", 6.0, 20.0, -4.65, -4.35, 0.35, 7.2, "PlankPale")
    box("GEO-NaveEndE", 19.7, 20.0, -4.65, 4.65, 0.35, 7.2, "PlankPale")
    box("GEO-AisleWallS", 6.0, 20.0, 6.65, 6.95, 0.35, 4.2, "PlankPale")
    box("GEO-AisleWallN", 6.0, 20.0, -6.95, -6.65, 0.35, 4.2, "PlankPale")
    box("GEO-AisleEndW_S", 6.0, 6.3, 4.65, 6.65, 0.35, 4.2, "PlankPale")
    box("GEO-AisleEndW_N", 6.0, 6.3, -6.65, -4.65, 0.35, 4.2, "PlankPale")
    box("GEO-AisleEndE_S", 19.7, 20.0, 4.65, 6.65, 0.35, 4.2, "PlankPale")
    box("GEO-AisleEndE_N", 19.7, 20.0, -6.65, -4.65, 0.35, 4.2, "PlankPale")

    # 中殿 / 侧廊屋面
    gable_roof("GEO-NaveRoof", 5.9, 20.1, 4.9, 7.2, 12.0, 0.35, 0.28, "Shingle")
    shed_roof("GEO-AisleRoofS", 6.0, 20.0, 6.95, 4.45, 4.2, 5.85, 0.22, "Shingle")
    shed_roof("GEO-AisleRoofN", 6.0, 20.0, -6.95, -4.45, 4.2, 5.85, 0.22, "Shingle")
    box("GEO-RidgeBeam", 5.5, 20.45, -0.14, 0.14, 11.9, 12.2, "TimberDark")
    # 细瓦楞条：只做很薄的横向凸起，让屋面读出瓦行
    for side, sy in (("S", 1), ("N", -1)):
        for row in range(1, 13):
            t = row / 13.0
            y = sy * (4.9 + (0.0 - 4.9) * t)
            z = 7.2 + (12.0 - 7.2) * t + 0.02
            box("GEO-Batten%s%d" % (side, row), 5.7, 20.3,
                y - 0.018, y + 0.018, z - 0.012, z + 0.012, "Shingle")
    for side, sy in (("S", 1), ("N", -1)):
        for row in range(1, 9):
            t = row / 9.0
            y = sy * (6.9 + (4.45 - 6.9) * t)
            z = 4.2 + (5.85 - 4.2) * t + 0.02
            box("GEO-AisleBatten%s%d" % (side, row), 6.0, 20.0,
                y - 0.016, y + 0.016, z - 0.01, z + 0.01, "Shingle")

    # 东端半圆室
    polygon_prism("GEO-Apse", 20.0, 0.0, 4.8, 4.8, 8, 0.35, 6.5,
                  "PlankPale", rot=math.pi / 8.0)
    polygon_prism("GEO-ApseRoof", 20.0, 0.0, 5.1, 0.0, 8, 6.5, 8.8,
                  "Shingle", rot=math.pi / 8.0)
    box("GEO-ApseBand", 19.8, 24.5, -4.95, 4.95, 6.3, 6.55, "TimberDark")

    # 扶壁：下段 / 上段 / 尖顶（各一组，互不重叠）
    for side, ys in (("S", 6.95), ("N", -6.95)):
        for i, x in enumerate((6.9, 10.4, 13.9, 17.4)):
            polygon_prism("GEO-ButtressLow%s%d" % (side, i), x, ys, 0.38, 0.26, 4,
                          0.35, 4.05, "TimberDark", rot=math.pi / 4.0)
            polygon_prism("GEO-ButtressUp%s%d" % (side, i), x, ys, 0.26, 0.18, 4,
                          4.02, 6.6, "TimberDark", rot=math.pi / 4.0)
            polygon_prism("GEO-ButtressPin%s%d" % (side, i), x, ys, 0.20, 0.0, 4,
                          6.55, 7.6, "TimberDark", rot=math.pi / 4.0)
    # 窗：侧廊长窗 + 高侧窗
    for side, ys in (("S", 6.95), ("N", -6.95)):
        for i, x in enumerate((8.1, 11.6, 15.1, 18.6)):
            arch_frame("GEO-AisleWin%s%d" % (side, i), "Y", ys, (1 if ys > 0 else -1),
                       x, 1.65, 3.2, 0.95, 0.14, "TimberDark")
            arch_panel("GEO-AisleGlass%s%d" % (side, i), "Y", ys, (1 if ys > 0 else -1),
                       x, 1.38, 2.95, 1.05, 0.05, "Glass", inset=-0.06)
    for side, ys in (("S", 4.65), ("N", -4.65)):
        for i, x in enumerate((8.1, 11.6, 15.1, 18.6)):
            arch_frame("GEO-ClerWin%s%d" % (side, i), "Y", ys, (1 if ys > 0 else -1),
                       x, 1.30, 1.15, 5.95, 0.12, "TimberDark")
            arch_panel("GEO-ClerGlass%s%d" % (side, i), "Y", ys, (1 if ys > 0 else -1),
                       x, 1.05, 0.95, 6.02, 0.04, "Glass", inset=-0.05)

    # 塔身百叶窗（四面）
    arch_frame("GEO-LouverW", "X", 0.0, -1, 0.0, 1.55, 2.2, 11.6, 0.14, "TimberDark")
    arch_frame("GEO-LouverE", "X", 6.0, 1, 0.0, 1.55, 2.2, 11.6, 0.14, "TimberDark")
    arch_frame("GEO-LouverS", "Y", 3.0, 1, 3.0, 1.55, 2.2, 11.6, 0.14, "TimberDark")
    arch_frame("GEO-LouverN", "Y", -3.0, -1, 3.0, 1.55, 2.2, 11.6, 0.14, "TimberDark")
    plane_box("GEO-LouverPanelW", "X", 0.0, -1, -0.68, 0.68,
              11.7, 13.7, 0.04, "Iron", inset=0.02)
    plane_box("GEO-LouverPanelE", "X", 6.0, 1, -0.68, 0.68,
              11.7, 13.7, 0.04, "Iron", inset=0.02)
    plane_box("GEO-LouverPanelS", "Y", 3.0, 1, 3.0 - 0.68, 3.0 + 0.68,
              11.7, 13.7, 0.04, "Iron", inset=0.02)
    plane_box("GEO-LouverPanelN", "Y", -3.0, -1, 3.0 - 0.68, 3.0 + 0.68,
              11.7, 13.7, 0.04, "Iron", inset=0.02)

    # 半圆室东面窗
    arch_frame("GEO-ApseWin0", "X", 24.35, 1, 0.0, 1.5, 2.4, 1.9, 0.14, "TimberDark")
    arch_panel("GEO-ApseGlass0", "X", 24.35, 1, 0.0, 1.25, 2.15, 2.0, 0.04,
               "Glass", inset=-0.05)
    for i, yy in enumerate((-2.9, 2.9)):
        arch_frame("GEO-ApseWin%d" % (i + 1), "Y", yy, (1 if yy > 0 else -1),
                   22.6, 1.0, 2.0, 1.9, 0.12, "TimberDark")
        arch_panel("GEO-ApseGlass%d" % (i + 1), "Y", yy, (1 if yy > 0 else -1),
                   22.6, 0.8, 1.8, 2.0, 0.04, "Glass", inset=-0.05)

    # 木构框架：竖柱 + 腰线 + 斜撑（所有段之间留缝）
    xs = (6.35, 9.85, 13.35, 16.85, 19.95)
    for side, ys, sign in (("S", 6.95, 1), ("N", -6.95, -1)):
        for i, x in enumerate(xs):
            plane_box("GEO-Post%s%d" % (side, i), "Y", ys, sign,
                      x - 0.11, x + 0.11, 0.4, 6.9, 0.10, "TimberDark")
        for zi, z in enumerate((0.75, 4.05, 6.55)):
            for i in range(len(xs) - 1):
                plane_box("GEO-Rail%s%d%d" % (side, zi, i), "Y", ys, sign,
                          xs[i] + 0.13, xs[i + 1] - 0.13, z - 0.08, z + 0.08,
                          0.09, "TimberDark")
        # 檐口下沿的连续压条
        plane_box("GEO-StringCourse%s" % side, "Y", ys, sign, 6.1, 20.0,
                  7.02, 7.18, 0.12, "TimberDark")

    # 塔正面木框
    for i, y in enumerate((-2.7, -1.0, 1.0, 2.7)):
        plane_box("GEO-TowerPost%d" % i, "X", 0.0, -1, y - 0.10, y + 0.10,
                  0.4, 14.6, 0.10, "TimberDark")
    for zi, z in enumerate((3.0, 7.0, 11.0, 14.0)):
        plane_box("GEO-TowerRail%d" % zi, "X", 0.0, -1, -2.55, 2.55,
                  z - 0.08, z + 0.08, 0.09, "TimberDark")

    # 门廊木框
    for i, y in enumerate((-1.9, 0.0, 1.9)):
        plane_box("GEO-PorchPost%d" % i, "X", -1.85, -1, y - 0.09, y + 0.09,
                  0.4, 5.0, 0.09, "TimberDark")
    plane_box("GEO-PorchRail", "X", -1.85, -1, -2.0, 2.0, 4.55, 4.72,
              0.09, "TimberDark")

    # 塔尖十字
    beam("GEO-CrossV", (3.0, 0.0, 23.3), (3.0, 0.0, 24.6), 0.10, 0.10, "Iron")
    beam("GEO-CrossH", (2.55, 0.0, 24.05), (3.45, 0.0, 24.05), 0.10, 0.10, "Iron")

    # 单根：用台基作为唯一根网格。全部网格挂到它下面，
    # 这样 FBX 导出（只选 MESH）也会保留 ≤1 根的层级。
    root = bpy.data.objects["GEO-Plinth"]
    for o in OBJS:
        if o is not root:
            o.parent = root

    unwrap_all()

    # 统计
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

    blend = os.path.join(OUT, "church.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print("[build] saved %s" % blend)


if __name__ == "__main__":
    build()
