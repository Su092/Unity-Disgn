# -*- coding: utf-8 -*-
"""蜘蛛侠·纵横宇宙风 · 风格化出租车（across-taxi）· 参数化建模（headless 安全）

数值来源：spec.md（唯一合同）。改数值要同时改 SPEC / 断面表 / spec.md。

拓扑策略：
  车身 / 车厢 / 保险杠 / 格栅 / 灯箱 / 镜 / 棋盘带 / 各细节 → 各自独立实体，
  倒角后 Boolean UNION 进车身 → 1 个连通闭合壳；
  4 个车轮各自 UNION（胎+毂+装饰）后**不焊进车身**（要能单独旋转），再 join 进同一网格
  ⇒ 交付件 = 1 对象 5 壳，量测门对整包判 AABB。

布尔纪律（上一项目的教训，写死在断言里）：
  1. 任何贴合面给 ≥5 mm 插入量，绝不共面（EXACT 求解器吃共面会随机掉面）；
  2. 单个操作数内部不许自交（自交会把 target 吃掉）；
  3. 每次 UNION 后断言"面数没崩"，收尾断言 shells == 1。

用法：
  blender -b --factory-startup --python scripts/build_taxi.py -- [--no-render]
"""

import hashlib
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

MM = 0.001
ASSET_STEM = "Modle_Vehicle_AcrossTaxi"
TEX_NAME = ASSET_STEM + "_basecolor.jpg"

# ---------------------------------------------------------------- 规格（mm，冻结）

SPEC = {
    "length": 5200.0,
    "width": 1950.0,
    "height": 2250.0,
    "body_half": 955.0,
    "door_half": 930.0,
    "sill_z": 364.0,
    "rocker_top": 560.0,
    "belt_z": 1360.0,
    "roof_z": 1980.0,
    "glass_z0": 1400.0,
    "glass_z1": 1872.0,
    "wheel_x_front": 1343.0,
    "wheel_x_rear": -1624.0,
    "wheel_y": 700.0,
    "wheel_z": 405.0,
    "tire_r": 405.0,
    "tire_w": 250.0,
    "hub_r": 240.0,
    "hub_w": 268.0,
    "arch_r": 480.0,
    "arch_y_in": 552.0,
    "checker_x0": -1900.0,
    "checker_x1": 1700.0,
    "checker_z0": 1060.0,
    "checker_z1": 1180.0,
    "checker_out": 975.0,
    "checker_in": 935.0,
    "checker_cells": 30,
    "bumper_tip": 2600.0,
    "sign_x0": -778.0,
    "sign_x1": 39.0,
    "sign_half_y": 300.0,
    "sign_z0": 1960.0,
    "sign_z1": 2250.0,
}

MAT_NAMES = [
    "M_Taxi_Paint", "M_Taxi_Glass", "M_Taxi_Chrome", "M_Taxi_Dark",
    "M_Taxi_Tire", "M_Taxi_CheckerW", "M_Taxi_Sign", "M_Taxi_Amber",
    "M_Taxi_Red",
]
MI = {n: i for i, n in enumerate(MAT_NAMES)}
PAINT, GLASS, CHROME, DARK, TIRE, CHECKW, SIGN, AMBER, RED = MAT_NAMES

MAT_LOOK = {
    PAINT:    ((0.950, 0.520, 0.015, 1.0), 0.38, 0.00),
    GLASS:    ((0.045, 0.105, 0.155, 1.0), 0.10, 0.15),
    CHROME:   ((0.880, 0.890, 0.930, 1.0), 0.16, 1.00),
    DARK:     ((0.030, 0.030, 0.035, 1.0), 0.55, 0.15),
    TIRE:     ((0.028, 0.028, 0.032, 1.0), 0.90, 0.00),
    CHECKW:   ((0.950, 0.940, 0.900, 1.0), 0.50, 0.00),
    SIGN:     ((1.000, 0.700, 0.050, 1.0), 0.40, 0.00),
    AMBER:    ((0.950, 0.420, 0.020, 1.0), 0.30, 0.20),
    RED:      ((0.720, 0.045, 0.035, 1.0), 0.28, 0.20),
}

# 下车身放样断面：(x, w_scale, z_top)
# 下车身放样断面：(x, w_scale, z_top, crown)
# crown = 顶面占半宽的比例（越小越"圆肩"）。前段收窄 ⇒ 引擎盖有冠面、翼子板有肩线；
# zt 不变 ⇒ 侧视轮廓完全不受影响（改的是横截面，不是高度）。
BODY_SECTIONS = [
    (2560.0, 0.80, 1080.0, 0.74),
    (2470.0, 0.93, 1120.0, 0.78),
    (2350.0, 1.00, 1160.0, 0.82),
    (1900.0, 1.00, 1232.0, 0.85),
    (1500.0, 1.00, 1292.0, 0.87),
    (1250.0, 1.00, 1340.0, 0.90),
    (1107.0, 1.00, 1360.0, 0.93),
    (600.0, 1.00, 1360.0, 0.93),
    (-1250.0, 1.00, 1360.0, 0.93),
    (-1733.0, 1.00, 1360.0, 0.93),
    (-1900.0, 1.00, 1290.0, 0.90),
    (-2300.0, 0.99, 1220.0, 0.86),
    (-2560.0, 0.92, 1150.0, 0.80),
]

# 车厢放样断面：(x, 底半宽 bw, 顶 zt)
# 560/200/160/-880/-920 这几站是**为 A/B/C 柱留的窄带**：柱靠"把这一条刷回车漆"实现，
# 不外加几何条（外贴条跟不平收分斜面就会浮空，实测 1→3 壳）。
CABIN_SECTIONS = [
    (1107.0, 700.0, 1420.0),
    (1010.0, 760.0, 1520.0),
    (860.0, 830.0, 1700.0),
    (760.0, 868.0, 1870.0),
    (700.0, 880.0, 1980.0),
    (660.0, 880.0, 1980.0),
    (200.0, 880.0, 1980.0),
    (160.0, 880.0, 1980.0),
    (-880.0, 880.0, 1980.0),
    (-920.0, 880.0, 1980.0),
    (-1250.0, 880.0, 1980.0),
    (-1400.0, 840.0, 1900.0),
    (-1600.0, 780.0, 1660.0),
    (-1733.0, 700.0, 1420.0),
]


# ---------------------------------------------------------------- 基础工具

def new_object(name, bm, mats, face_mats=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for m in mats:
        me.materials.append(m)
    if face_mats is not None:
        assert len(face_mats) == len(me.polygons), \
            "%s: face_mats %d != polygons %d" % (name, len(face_mats), len(me.polygons))
        for p, mi in zip(me.polygons, face_mats):
            p.material_index = mi
    return obj


def apply_mod(obj, mod):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def bevelize(obj, width_mm, segments=2, angle_deg=30.0):
    m = obj.modifiers.new("bev", "BEVEL")
    m.width = width_mm * MM
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle_deg)
    m.miter_outer = "MITER_ARC"
    apply_mod(obj, m)
    return obj


def bool_op(target, operand, op="UNION"):
    m = target.modifiers.new("bool_" + operand.name, "BOOLEAN")
    m.operation = op
    m.solver = "EXACT"
    m.object = operand
    m.material_mode = "TRANSFER"
    apply_mod(target, m)
    bpy.data.objects.remove(operand, do_unlink=True)


def loft(name, sections, profile_fn, face_mat_fn, mats, default_mat):
    bm = bmesh.new()
    rings = []
    for sec in sections:
        pts = profile_fn(sec)
        rings.append([bm.verts.new((sec["x"] * MM, y * MM, z * MM)) for (y, z) in pts])
    n = len(rings[0])
    for r in rings[1:]:
        assert len(r) == n, "放样断面点数不一致"

    face_mats = []
    for si in range(len(rings) - 1):
        a, b = rings[si], rings[si + 1]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
            face_mats.append(MI[face_mat_fn(si, i)])
    bm.faces.new(list(reversed(rings[0])))
    face_mats.append(MI[default_mat])
    bm.faces.new(rings[-1])
    face_mats.append(MI[default_mat])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, mats, face_mats)


def box(name, x0, x1, y0, y1, z0, z1, mat_name):
    xs = sorted((x0, x1))
    ys = sorted((y0, y1))
    zs = sorted((z0, z1))
    bm = bmesh.new()
    v = [bm.verts.new((x * MM, y * MM, z * MM))
         for x in xs for y in ys for z in zs]
    idx = lambda a, b, c: a * 4 + b * 2 + c
    quads = [
        (idx(0, 0, 0), idx(0, 1, 0), idx(0, 1, 1), idx(0, 0, 1)),
        (idx(1, 0, 0), idx(1, 0, 1), idx(1, 1, 1), idx(1, 1, 0)),
        (idx(0, 0, 0), idx(0, 0, 1), idx(1, 0, 1), idx(1, 0, 0)),
        (idx(0, 1, 0), idx(1, 1, 0), idx(1, 1, 1), idx(0, 1, 1)),
        (idx(0, 0, 0), idx(1, 0, 0), idx(1, 1, 0), idx(0, 1, 0)),
        (idx(0, 0, 1), idx(0, 1, 1), idx(1, 1, 1), idx(1, 0, 1)),
    ]
    for q in quads:
        bm.faces.new([v[i] for i in q])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, [bpy.data.materials[mat_name]],
                      [0] * len(bm.faces))


def cylinder(name, axis, c, r, a0, a1, segments, mat_name):
    """轴对齐圆柱：axis='X'|'Y'|'Z'；a0/a1 沿轴；c 是另两轴中心。"""
    bm = bmesh.new()
    rings = []
    for a in (a0, a1):
        ring = []
        for s in range(segments):
            ang = 2.0 * math.pi * s / segments
            u, v = r * math.cos(ang), r * math.sin(ang)
            if axis == "X":
                p = (a, c[0] + u, c[1] + v)
            elif axis == "Y":
                p = (c[0] + u, a, c[1] + v)
            else:
                p = (c[0] + u, c[1] + v, a)
            ring.append(bm.verts.new((p[0] * MM, p[1] * MM, p[2] * MM)))
        rings.append(ring)
    for s in range(segments):
        t = (s + 1) % segments
        bm.faces.new((rings[0][s], rings[0][t], rings[1][t], rings[1][s]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, [bpy.data.materials[mat_name]],
                      [0] * len(bm.faces))


def bm_add_box(bm, x0, x1, y0, y1, z0, z1):
    xs, ys, zs = sorted((x0, x1)), sorted((y0, y1)), sorted((z0, z1))
    v = [bm.verts.new((x * MM, y * MM, z * MM))
         for x in xs for y in ys for z in zs]
    idx = lambda a, b, c: a * 4 + b * 2 + c
    quads = [
        (idx(0, 0, 0), idx(0, 1, 0), idx(0, 1, 1), idx(0, 0, 1)),
        (idx(1, 0, 0), idx(1, 0, 1), idx(1, 1, 1), idx(1, 1, 0)),
        (idx(0, 0, 0), idx(0, 0, 1), idx(1, 0, 1), idx(1, 0, 0)),
        (idx(0, 1, 0), idx(1, 1, 0), idx(1, 1, 1), idx(0, 1, 1)),
        (idx(0, 0, 0), idx(1, 0, 0), idx(1, 1, 0), idx(0, 1, 0)),
        (idx(0, 0, 1), idx(0, 1, 1), idx(1, 1, 1), idx(1, 0, 1)),
    ]
    for q in quads:
        bm.faces.new([v[i] for i in q])


def bm_add_prism(bm, pts_xz, y0, y1):
    n = len(pts_xz)
    a = [bm.verts.new((x * MM, y0 * MM, z * MM)) for (x, z) in pts_xz]
    b = [bm.verts.new((x * MM, y1 * MM, z * MM)) for (x, z) in pts_xz]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)


def bm_add_prism_x(bm, pts_yz, x0, x1):
    """把 YZ 平面上的闭合多边形沿 X 挤出成柱体（两端封口）。"""
    n = len(pts_yz)
    a = [bm.verts.new((x0 * MM, y * MM, z * MM)) for (y, z) in pts_yz]
    b = [bm.verts.new((x1 * MM, y * MM, z * MM)) for (y, z) in pts_yz]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)


def multi_box(name, boxes, mat_name):
    bm = bmesh.new()
    for b in boxes:
        bm_add_box(bm, *b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, [bpy.data.materials[mat_name]],
                      [0] * len(bm.faces))


def ring(name, axis, c, r_in, r_out, a0, a1, segments, mat_name):
    bm = bmesh.new()
    loops = []
    for a in (a0, a1):
        for r in (r_out, r_in):
            loop = []
            for s in range(segments):
                ang = 2.0 * math.pi * s / segments
                u, v = r * math.cos(ang), r * math.sin(ang)
                if axis == "X":
                    p = (a, c[0] + u, c[1] + v)
                elif axis == "Y":
                    p = (c[0] + u, a, c[1] + v)
                else:
                    p = (c[0] + u, c[1] + v, a)
                loop.append(bm.verts.new((p[0] * MM, p[1] * MM, p[2] * MM)))
            loops.append(loop)
    o0, i0, o1, i1 = loops
    for s in range(segments):
        t = (s + 1) % segments
        bm.faces.new((o0[s], o0[t], o1[t], o1[s]))
        bm.faces.new((i0[t], i0[s], i1[s], i1[t]))
        bm.faces.new((o0[t], o0[s], i0[s], i0[t]))
        bm.faces.new((o1[s], o1[t], i1[t], i1[s]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, [bpy.data.materials[mat_name]],
                      [0] * len(bm.faces))


def rect_ring(name, x0, x1, y_out, y_in, z0, z1, t, mat_name):
    """矩形垫圈：外框 (±y_out, z0..z1) − 内孔 (±y_in, z0+t..z1−t)，沿 X 挤出。

    单个闭合实体，**不是四根互相重叠的条** —— 自交的操作数会把 target 吃掉
    （上一项目的教训 #5：GEO-GrilleFrame 用 multi_box 拼四根条，UNION 后车身 956 面 → 0）。
    """
    xs = (x0, x1)
    outer = [(y_out, z0), (y_out, z1), (-y_out, z1), (-y_out, z0)]
    inner = [(y_in, z0 + t), (y_in, z1 - t), (-y_in, z1 - t), (-y_in, z0 + t)]
    bm = bmesh.new()
    rings_o, rings_i = [], []
    for x in xs:
        rings_o.append([bm.verts.new((x * MM, y * MM, z * MM)) for (y, z) in outer])
        rings_i.append([bm.verts.new((x * MM, y * MM, z * MM)) for (y, z) in inner])
    o0, o1 = rings_o
    i0, i1 = rings_i
    for k in range(4):
        k2 = (k + 1) % 4
        bm.faces.new((o0[k], o0[k2], o1[k2], o1[k]))      # 外壁
        bm.faces.new((i0[k2], i0[k], i1[k], i1[k2]))      # 内壁
        bm.faces.new((o0[k2], o0[k], i0[k], i0[k2]))      # x0 端环
        bm.faces.new((o1[k], o1[k2], i1[k2], i1[k]))      # x1 端环
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, [bpy.data.materials[mat_name]],
                      [0] * len(bm.faces))


def checker_strip(name, x0, x1, y_out, y_in, z0, z1, cells):
    bm = bmesh.new()
    face_mats = []
    xs = [x0 + (x1 - x0) * i / cells for i in range(cells + 1)]
    for side in (1.0, -1.0):
        yo, yi = y_out * side, y_in * side
        rows = []
        for x in xs:
            rows.append([
                bm.verts.new((x * MM, yo * MM, z0 * MM)),
                bm.verts.new((x * MM, yo * MM, z1 * MM)),
                bm.verts.new((x * MM, yi * MM, z1 * MM)),
                bm.verts.new((x * MM, yi * MM, z0 * MM)),
            ])
        for i in range(cells):
            a, b = rows[i], rows[i + 1]
            m = CHECKW if (i % 2 == 0) else DARK
            for k in range(4):
                k2 = (k + 1) % 4
                bm.faces.new((a[k], a[k2], b[k2], b[k]))
                face_mats.append(MI[m] if k != 2 else MI[DARK])
        bm.faces.new(list(reversed(rows[0])))
        face_mats.append(MI[DARK])
        bm.faces.new(rows[-1])
        face_mats.append(MI[DARK])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mats = [bpy.data.materials[n] for n in MAT_NAMES]
    return new_object(name, bm, mats, face_mats)


def nonmanifold_edges(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    n = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    bm.free()
    return n


def shells_count(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    seen, count = set(), 0
    for v in bm.verts:
        if v.index in seen:
            continue
        count += 1
        stack = [v]
        seen.add(v.index)
        while stack:
            cur = stack.pop()
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
    bm.free()
    return count


# ---------------------------------------------------------------- 材质

def build_materials():
    for name in MAT_NAMES:
        m = bpy.data.materials.get(name)
        if m:
            bpy.data.materials.remove(m)
    for name in MAT_NAMES:
        col, rough, metal = MAT_LOOK[name]
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = col
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        if name == SIGN:
            bsdf.inputs["Emission Color"].default_value = col
            bsdf.inputs["Emission Strength"].default_value = 0.06
        m.diffuse_color = col
    return [bpy.data.materials[n] for n in MAT_NAMES]


def normalize_slots(obj):
    me = obj.data
    n_before = len(me.materials)
    per_face = []
    for p in me.polygons:
        mat = me.materials[p.material_index] if p.material_index < len(me.materials) else None
        per_face.append(mat)
    used = []
    for mat in per_face:
        if mat is not None and mat not in used:
            used.append(mat)
    order = [bpy.data.materials[n] for n in MAT_NAMES if bpy.data.materials.get(n) in used]
    order += [m for m in used if m not in order]
    me.materials.clear()
    for m in order:
        me.materials.append(m)
    index = {m: i for i, m in enumerate(order)}
    fallback = index.get(bpy.data.materials[PAINT], 0)
    for p, mat in zip(me.polygons, per_face):
        p.material_index = index.get(mat, fallback)
    print("[build] material slots: %d -> %d (%s)"
          % (n_before, len(me.materials), ", ".join(m.name for m in me.materials)))
    return len(me.materials)


# ---------------------------------------------------------------- UV：分岛展开 + 装箱

_BUCKET_PROJ = [
    lambda p: (-p.y, p.z), lambda p: (p.y, p.z),
    lambda p: (p.x, p.z), lambda p: (-p.x, p.z),
    lambda p: (p.x, p.y), lambda p: (p.x, -p.y),
]


def _bucket_of(normal):
    ax = max(range(3), key=lambda i: abs(normal[i]))
    return ax * 2 + (1 if normal[ax] < 0 else 0)


def _poly_area2(pts):
    if len(pts) < 3:
        return 0.0
    ox, oy = pts[0]
    s = 0.0
    for i in range(1, len(pts) - 1):
        x1, y1 = pts[i][0] - ox, pts[i][1] - oy
        x2, y2 = pts[i + 1][0] - ox, pts[i + 1][1] - oy
        s += x1 * y2 - x2 * y1
    return s * 0.5


def _split_islands(me, buckets):
    edge_faces = {}
    for poly in me.polygons:
        for ek in poly.edge_keys:
            edge_faces.setdefault(ek, []).append(poly.index)
    seen = [False] * len(me.polygons)
    islands = []
    for start in range(len(me.polygons)):
        if seen[start]:
            continue
        b = buckets[start]
        stack, comp = [start], []
        seen[start] = True
        while stack:
            fi = stack.pop()
            comp.append(fi)
            for ek in me.polygons[fi].edge_keys:
                for nf in edge_faces.get(ek, ()):
                    if not seen[nf] and buckets[nf] == b:
                        seen[nf] = True
                        stack.append(nf)
        islands.append(comp)
    return islands


def _shelf_pack(rects, pad, box=1.0):
    order = sorted(range(len(rects)), key=lambda i: -rects[i][1])
    x = y = shelf = 0.0
    pos = [None] * len(rects)
    for i in order:
        w, h = rects[i]
        if w > box or h > box:
            return None
        if x + w > box:
            x = 0.0
            y += shelf + pad
            shelf = 0.0
            if y + h > box:
                return None
        pos[i] = (x, y)
        x += w + pad
        shelf = max(shelf, h)
    if y + shelf > box:
        return None
    return pos


def unwrap_uv(obj, pad=0.003):
    me = obj.data
    if me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    uvl = me.uv_layers.new(name="UVMap")

    buckets = [_bucket_of(poly.normal) for poly in me.polygons]
    islands = _split_islands(me, buckets)

    islands_data = []
    for comp in islands:
        b = buckets[comp[0]]
        proj = _BUCKET_PROJ[b]
        pts_per_face, area3, area2 = [], 0.0, 0.0
        for fi in comp:
            poly = me.polygons[fi]
            pts = [proj(me.vertices[me.loops[li].vertex_index].co)
                   for li in poly.loop_indices]
            pts_per_face.append((fi, pts))
            area3 += poly.area
            area2 += abs(_poly_area2(pts))
        xs = [p[0] for _, pts in pts_per_face for p in pts]
        ys = [p[1] for _, pts in pts_per_face for p in pts]
        minx, miny = min(xs), min(ys)
        w, h = max(xs) - minx, max(ys) - miny
        scale = math.sqrt(area3 / area2) if area2 > 1e-12 else 1.0
        islands_data.append({"faces": pts_per_face, "minx": minx, "miny": miny,
                             "w": max(w * scale, 1e-9), "h": max(h * scale, 1e-9),
                             "scale": scale})

    lo, hi, best = 1e-6, 4.0, None
    for _ in range(48):
        mid = 0.5 * (lo + hi)
        rects = [(d["w"] * mid, d["h"] * mid) for d in islands_data]
        pos = _shelf_pack(rects, pad)
        if pos is None:
            hi = mid
        else:
            lo, best = mid, pos
    if best is None:
        raise RuntimeError("UV 装箱失败：岛数 %d" % len(islands_data))

    for d, (px, py) in zip(islands_data, best):
        s = d["scale"] * lo
        for fi, pts in d["faces"]:
            poly = me.polygons[fi]
            for li, (u, v) in zip(poly.loop_indices, pts):
                uvl.data[li].uv = (px + (u - d["minx"]) * s, py + (v - d["miny"]) * s)
    uvl.active_render = True
    me.update()
    print("[build] uv: %d islands / %d faces / k=%.5f"
          % (len(islands_data), len(me.polygons), lo))


# ---------------------------------------------------------------- 贴图：烘焙 / 退路

def bake_basecolor(obj, path, size=1024):
    """烘焙 basecolor。

    用 **EMIT** 而不是 DIFFUSE：金属材质没有漫反射，DIFFUSE(color-only) 会把
    metallic=1 的面烤成纯黑（本项目实测：镀铬保险杠/亮条全黑）。EMIT 只取发光色，
    等价于"逐面反照率"，对金属/介质都正确。
    """
    tmp = []
    try:
        sc = bpy.context.scene
        img = bpy.data.images.new("BAKE_BaseColor", size, size, alpha=False)
        for slot in obj.material_slots:
            m = slot.material
            if not m or not m.use_nodes:
                continue
            nt = m.node_tree
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
            col = tuple(bsdf.inputs["Base Color"].default_value)
            emit = nt.nodes.new("ShaderNodeEmission")
            emit.inputs["Color"].default_value = col
            nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = img
            tex.select = True
            nt.nodes.active = tex
            tmp.append((nt, out, tex, emit))
        sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = 1
        bake = sc.render.bake
        bake.margin = 8
        bake.use_clear = True
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        still = sc.render.image_settings.file_format
        bpy.ops.object.bake(type="EMIT")
        sc.render.image_settings.file_format = still
        img.filepath_raw = path
        img.file_format = "JPEG"
        img.save()
        bpy.data.images.remove(img)
        img = bpy.data.images.load(path)
        img.name = TEX_NAME
        print("[build] bake(EMIT) ok -> %s (%dx%d)" % (path, size, size))
        return img
    except Exception as exc:                     # noqa: BLE001
        print("[build] WARN: bake 失败，退回程序化贴图: %s" % exc)
        return None
    finally:
        for nt, out, tex, emit in tmp:
            try:
                nt.nodes.remove(tex)
                nt.nodes.remove(emit)
                bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
                nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
            except Exception:                    # noqa: BLE001
                pass


def grain_image(size=512):
    img = bpy.data.images.get("TEX_Grain")
    if img:
        return img
    img = bpy.data.images.new("TEX_Grain", width=size, height=size, alpha=False)
    px = [0.0] * (size * size * 4)
    seed = 12345
    for y in range(size):
        for x in range(size):
            seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            n = (seed / 0x7FFFFFFF) * 0.10 + 0.90
            u = ((x + y) % 16) - 8.0
            v = ((x - y) % 16) - 8.0
            dot = 1.0 - 0.06 * max(0.0, 1.0 - math.hypot(u, v) / 7.0)
            c = max(0.0, min(1.0, n * dot))
            i = (y * size + x) * 4
            px[i] = px[i + 1] = px[i + 2] = c
            px[i + 3] = 1.0
    img.pixels = px
    img.pack()
    return img


def wire_texture(obj, img):
    for slot in obj.material_slots:
        m = slot.material
        if not m or not m.use_nodes:
            continue
        nt = m.node_tree
        for n in [n for n in nt.nodes if n.type == "TEX_IMAGE"]:
            nt.nodes.remove(n)
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvnode = nt.nodes.new("ShaderNodeUVMap")
        uvnode.uv_map = "UVMap"
        uvnode.location = (-820, 120)
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.location = (-600, 120)
        tex.interpolation = "Linear"
        tex.extension = "EXTEND"
        nt.links.new(uvnode.outputs["UV"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    try:
        if not img.packed_file:
            img.pack()
        img.filepath = "//" + TEX_NAME
        print("[build] texture packed: %s" % img.name)
    except RuntimeError as exc:
        print("[build] WARN: 打包失败 %s: %s" % (img.name, exc))


# ---------------------------------------------------------------- 主体几何

def build_body(mats):
    secs = [{"x": x, "w": SPEC["body_half"] * s, "zt": zt, "c": c}
            for (x, s, zt, c) in BODY_SECTIONS]
    z0 = SPEC["sill_z"]
    z1 = SPEC["rocker_top"] - 76.0

    def profile(sec):
        w, zt, c = sec["w"], sec["zt"], sec["c"]
        return [
            (-0.88 * w, z0), (-1.00 * w, z1), (-1.00 * w, zt - 165.0),
            (-0.985 * w, zt - 60.0), (-c * w, zt),
            (c * w, zt), (0.985 * w, zt - 60.0), (1.00 * w, zt - 165.0),
            (1.00 * w, z1), (0.88 * w, z0),
        ]

    body = loft("GEO-Body", secs, profile, lambda si, i: PAINT, mats, PAINT)
    bevelize(body, 22.0, 2)
    return body


def build_cabin(mats):
    secs = [{"x": x, "bw": bw, "zt": zt} for (x, bw, zt) in CABIN_SECTIONS]

    def profile(sec):
        b, zt = sec["bw"], sec["zt"]
        z0 = SPEC["belt_z"] - 40.0
        zA = z0 + 0.26 * (zt - z0)
        zB = max(zA + 10.0, zt - 105.0)
        zC = min(zt - 5.0, max(zB + 8.0, zt - 60.0))
        return [
            (b, z0), (b, zA), (0.995 * b, zB), (0.86 * b, zC), (0.74 * b, zt),
            (-0.74 * b, zt), (-0.86 * b, zC), (-0.995 * b, zB), (-b, zA), (-b, z0),
        ]

    cabin = loft("GEO-Cabin", secs, profile, lambda si, i: PAINT, mats, PAINT)
    paint_cabin_glass(cabin)
    paint_pillars(cabin)
    bevelize(cabin, 20.0, 2)
    return cabin


def paint_cabin_glass(obj):
    me = obj.data
    n = 0
    for p in me.polygons:
        z = p.center.z / MM
        if SPEC["glass_z0"] <= z <= SPEC["glass_z1"]:
            p.material_index = MI[GLASS]
            n += 1
    print("[build] cabin glass faces: %d / %d" % (n, len(me.polygons)))


def paint_pillars(obj):
    """把车厢上 A/B/C 柱 X 区间内的玻璃面刷回车漆 —— 得到 4 个独立侧窗。

    比"外加镀铬立柱条"可靠：条要跟随车厢的收分斜面，贴不平就会浮空（实测 1→3 壳）。
    """
    me = obj.data
    n = 0
    for p in me.polygons:
        if p.material_index != MI[GLASS]:
            continue
        # 只对"侧窗"面生效（法线朝侧），否则会把前风挡也切断
        if abs(p.normal.y) < 0.50:
            continue
        x = p.center.x / MM
        if any(abs(x - px) < 24.0 for px in (680.0, 180.0, -900.0)):
            p.material_index = MI[PAINT]
            n += 1
    print("[build] pillar repaint faces: %d" % n)


def paint_rocker(obj):
    """下裙黑带：只把「车漆面」的侧面下部改黑（不动铬件/棋盘带）。"""
    me = obj.data
    n = 0
    for p in me.polygons:
        c = p.center / MM
        if (p.material_index == MI[PAINT] and c.z < SPEC["rocker_top"]
                and abs(c.y) > 0.74 * SPEC["body_half"]):
            p.material_index = MI[DARK]
            n += 1
    print("[build] rocker dark faces: %d" % n)


def build_wheel(name, cx, cy):
    r = SPEC["tire_r"]
    z = SPEC["wheel_z"]
    tire = cylinder(name + "_Tire", "Y", (cx, z), r,
                    cy - SPEC["tire_w"] * 0.5, cy + SPEC["tire_w"] * 0.5, 32, TIRE)
    bevelize(tire, 52.0, 3)
    hub = cylinder(name + "_Hub", "Y", (cx, z), SPEC["hub_r"],
                   cy - SPEC["hub_w"] * 0.5, cy + SPEC["hub_w"] * 0.5, 32, CHROME)
    bevelize(hub, 18.0, 2)
    bool_op(tire, hub, "UNION")

    # 只做朝外那一侧（朝轮井那侧加件会顶到轮拱内壁 → buried 判埋入）
    sg = 1.0 if cy > 0.0 else -1.0
    # 轮毂面暗槽（凸 6）+ 中心亮盖（凸 22）
    # 注：原先还做过一圈 r296..344 的凸起亮环，UNION 后留下 16 条开边（3mm 薄 collar 没封住），
    # 改成"把镀铬轮毂盘直接做到 r300"，视觉等价、拓扑干净。
    bool_op(tire, ring(name + "_Groove", "Y", (cx, z), 132.0, 152.0,
                       cy + sg * 132.0, cy + sg * 140.0, 32, DARK), "UNION")
    dome = cylinder(name + "_Dome", "Y", (cx, z), 128.0,
                    cy + sg * 130.0, cy + sg * 156.0, 32, CHROME)
    bevelize(dome, 10.0, 2)
    bool_op(tire, dome, "UNION")

    tire.name = name
    return tire


def build_details(mats):
    """细节层：交叠量见 spec.md §8，全部 ≥5 mm。"""
    parts = []
    bt = SPEC["bumper_tip"]

    def add(part, bev=0.0):
        if bev > 0.0:
            bevelize(part, bev, 2)
        parts.append(part)
        return part

    # ① 保险杠（前/后）：chrome。比车身侧面（955）宽 3mm，整条都能露出来，
    #    车身端面 ±2560，保险杠/立柱/格栅跨到 ±2600
    for sx in (1.0, -1.0):
        b = box("GEO-Bumper%s" % ("F" if sx > 0 else "R"),
                (2380.0 if sx > 0 else -2586.0), (2586.0 if sx > 0 else -2380.0),
                -975.0, 975.0, 320.0, 600.0, CHROME)
        add(b, 20.0)

    # ② 保险杠立柱 ×4（穿过保险杠、向上顶到车身）
    add(multi_box("GEO_BumperGuards",
                  [(2546.0 * sx, 2600.0 * sx, -375.0, -285.0, 380.0, 700.0)
                   for sx in (1.0, -1.0)]
                  + [(2546.0 * sx, 2600.0 * sx, 285.0, 375.0, 380.0, 700.0)
                     for sx in (1.0, -1.0)], CHROME), 10.0)

    # ③ 格栅：暗底板（跨过车头端面 2560）+ 铬横条 ×5 + 铬框
    add(box("GEO-GrillePanel", 2530.0, 2578.0, -430.0, 430.0, 620.0, 980.0, DARK), 6.0)
    add(multi_box("GEO-GrilleBars",
                  [(2572.0, 2600.0, -400.0, 400.0, z, z + 20.0)
                   for z in (655.0, 720.0, 785.0, 850.0, 915.0)], CHROME), 3.0)
    add(rect_ring("GEO-GrilleFrame", 2570.0, 2600.0, 430.0, 408.0, 620.0, 980.0, 24.0, CHROME), 4.0)

    # ④ 前大灯：铬圈（环 r78..108）+ 玻璃面（r80，内凹 4）
    for sy in (1.0, -1.0):
        tag = "L" if sy > 0 else "R"
        add(ring("GEO_HeadlightRing%s" % tag, "X", (690.0 * sy, 900.0),
                 78.0, 108.0, 2540.0, 2600.0, 28, CHROME), 6.0)
        add(cylinder("GEO_HeadlightGlass%s" % tag, "X", (690.0 * sy, 900.0),
                     80.0, 2540.0, 2596.0, 28, CHECKW), 6.0)

    # ⑤ 转向灯（前脸下部，琥珀；跨过车头端面）
    add(multi_box("GEO-TurnSignals",
                  [(2540.0, 2600.0, -670.0, -555.0, 630.0, 700.0),
                   (2540.0, 2600.0, 555.0, 670.0, 630.0, 700.0)], AMBER), 4.0)

    # ⑥ 尾灯（竖条：红 + 下白；跨过后端面 −2560）
    for sy in (1.0, -1.0):
        add(box("GEO_Taillight%s" % ("L" if sy > 0 else "R"),
                -2600.0, -2540.0, 690.0 * sy, 880.0 * sy, 820.0, 1060.0, RED), 8.0)
        add(box("GEO_TaillightLow%s" % ("L" if sy > 0 else "R"),
                -2598.0, -2540.0, 700.0 * sy, 870.0 * sy, 762.0, 815.0, CHECKW), 5.0)

    # ⑦ 棋盘带
    parts.append(checker_strip("GEO-Checker", SPEC["checker_x0"], SPEC["checker_x1"],
                               SPEC["checker_out"], SPEC["checker_in"],
                               SPEC["checker_z0"], SPEC["checker_z1"],
                               SPEC["checker_cells"]))

    # ⑧ 腰线镀铬条（两侧，贴在肩线下方的车身上）
    add(multi_box("GEO-BeltTrim",
                  [(-1700.0, 1080.0, 900.0 * sy, 968.0 * sy, 1252.0, 1272.0)
                   for sy in (1.0, -1.0)], CHROME), 4.0)

    # ⑨ 车窗立柱：不建几何，改为把车厢上对应 X 区间的玻璃面刷回车漆（见 paint_pillars）

    # ⑩ 门把手 ×4
    add(multi_box("GEO-Handles",
                  [(780.0, 890.0, 940.0 * sy, 975.0 * sy, 1190.0, 1235.0)
                   for sy in (1.0, -1.0)]
                  + [(-720.0, -610.0, 940.0 * sy, 975.0 * sy, 1190.0, 1235.0)
                     for sy in (1.0, -1.0)], CHROME), 5.0)

    # ⑪ 门缝条（贴面细条，靠描边读成门缝）
    add(multi_box("GEO-DoorSeam",
                  [(x0, x0 + 12.0, 950.0 * sy, 960.0 * sy, 620.0, 1330.0)
                   for sy in (1.0, -1.0)
                   for x0 in (118.0, -700.0)], DARK), 2.0)

    # 后视镜：细杆（圆柱，沿 Y）+ 圆头；高度放在腰线，那里车厢表面才够宽（z1458 处已收到 588）
    for sy in (1.0, -1.0):
        tag = "L" if sy > 0 else "R"
        add(cylinder("GEO_MirrorStalk%s" % tag, "Y", (1064.0, 1400.0), 15.0,
                     610.0 * sy, 900.0 * sy, 12, CHROME), 2.0)
        add(cylinder("GEO_MirrorHead%s" % tag, "Y", (1064.0, 1400.0), 80.0,
                     890.0 * sy, 950.0 * sy, 24, CHROME), 10.0)
        add(cylinder("GEO_MirrorFace%s" % tag, "Y", (1064.0, 1400.0), 66.0,
                     946.0 * sy, 956.0 * sy, 24, CHECKW), 4.0)

    # ⑬ 雨刮 ×2（贴风挡斜面：z = 1420 + (1107 − x)·1.1，法线 (0.74, 0.67)）
    bm = bmesh.new()
    nrm = (0.74, 0.67)
    for (p0, p1, y0, y1) in (((1075.0, 1456.0), (1012.0, 1528.0), -370.0, -20.0),
                             ((1082.0, 1448.0), (1019.0, 1520.0), 20.0, 370.0)):
        pts = [
            (p0[0] - nrm[0] * 3.0, p0[1] - nrm[1] * 3.0),
            (p1[0] - nrm[0] * 3.0, p1[1] - nrm[1] * 3.0),
            (p1[0] + nrm[0] * 7.0, p1[1] + nrm[1] * 7.0),
            (p0[0] + nrm[0] * 7.0, p0[1] + nrm[1] * 7.0),
        ]
        bm_add_prism(bm, pts, y0, y1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    add(new_object("GEO-Wiper", bm, [bpy.data.materials[DARK]], [0] * len(bm.faces)))

    # ⑭ 车牌（前 / 后）：压在保险杠外面 14 mm
    add(multi_box("GEO-Plates",
                  [(2586.0, 2600.0, -190.0, 190.0, 420.0, 510.0),
                   (-2600.0, -2586.0, -190.0, 190.0, 420.0, 510.0)], CHECKW), 3.0)

    # ⑮ 天线
    add(cylinder("GEO-Antenna", "Z", (-1100.0, -600.0), 8.0, 1960.0, 2100.0, 12, DARK), 1.5)

    # ⑯ 排气 ×2（穿过保险杠下缘）
    for sy in (1.0, -1.0):
        add(cylinder("GEO_Exhaust%s" % ("L" if sy > 0 else "R"), "X",
                     (380.0 * sy, 400.0), 45.0, -2600.0, -2450.0, 20, CHROME), 6.0)

    # ⑰ 油箱盖（−Y 侧）+ 侧转向灯（前轮后方，避开轮拱切削范围）
    add(cylinder("GEO-FuelCap", "Y", (-1450.0, 900.0), 62.0,
                 -975.0, -930.0, 24, CHROME), 3.0)
    add(multi_box("GEO-SideMarker",
                  [(1930.0, 2010.0, 950.0 * sy, 972.0 * sy, 900.0, 950.0)
                   for sy in (1.0, -1.0)], AMBER), 3.0)

    # ⑱ 车顶灯箱（梯形罩：底面宽 500，顶面 430）+ 深色底座
    s0, s1 = SPEC["sign_z0"], SPEC["sign_z1"]
    x0, x1 = SPEC["sign_x0"], SPEC["sign_x1"]
    sy = SPEC["sign_half_y"]
    bm = bmesh.new()
    bm_add_prism_x(bm, [(-sy, s0 - 20.0), (sy, s0 - 20.0),
                        (0.86 * sy, s1), (-0.86 * sy, s1)], x0, x1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    sign = new_object("GEO-SignBody", bm, [bpy.data.materials[SIGN]],
                      [0] * len(bm.faces))
    add(sign, 26.0)
    add(box("GEO-SignBase", x0 - 26.0, x1 + 26.0, -sy * 1.02, sy * 1.02,
            s0 - 44.0, s0 - 8.0, DARK), 8.0)

    return parts


def clean_mesh(obj, dist_mm=0.02):
    """收尾清理：折叠零长边（消退化面）+ 合并重合点 + 重算法线。

    dist 取得极小（0.02 mm），远小于最细的细节（3 mm 宽的门缝条 / 车顶灯箱底座），
    不会把正常几何焊在一起；车轮与轮拱内壁之间有 20 mm 间隙，也不会被焊上。
    """
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    n0 = len(bm.faces)
    bmesh.ops.dissolve_degenerate(bm, dist=dist_mm * MM, edges=bm.edges)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist_mm * MM)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    print("[build] clean_mesh: faces %d -> %d" % (n0, len(me.polygons)))


def build_taxi():
    mats = build_materials()
    body = build_body(mats)
    parts = [build_cabin(mats)]
    parts += build_details(mats)

    prev = 1
    for p in parts:
        name = p.name
        n0 = len(body.data.polygons)
        bool_op(body, p, "UNION")
        n1 = len(body.data.polygons)
        sc_now = shells_count(body)
        if sc_now != prev:
            print("[build] !! shell jump after %s: %d -> %d" % (name, prev, sc_now))
            prev = sc_now
        if n1 < n0 * 0.5:
            raise RuntimeError("UNION(%s) 疑似丢失主体：%d -> %d 面" % (name, n0, n1))
    print("[build] union done: %d verts / %d faces"
          % (len(body.data.vertices), len(body.data.polygons)))
    sc = shells_count(body)
    print("[build] shells after union: %d" % sc)
    assert sc == 1, "UNION 后车身不是单一壳（%d）：有图元没并进去" % sc

    # 下裙黑带：并完再刷，避免被布尔搬走材质索引
    paint_rocker(body)

    # 轮拱切削（只切外侧，留轮井内壁 |y|>=arch_y_in）
    wxs = [SPEC["wheel_x_front"], SPEC["wheel_x_rear"]]
    for wx in wxs:
        for sy in (1.0, -1.0):
            cut = cylinder("GEO-ArchCut", "Y", (wx, SPEC["wheel_z"]),
                           SPEC["arch_r"], SPEC["arch_y_in"] * sy, 1010.0 * sy, 40, CHROME)
            bool_op(body, cut, "DIFFERENCE")

    wheels = []
    for wx, tag in ((SPEC["wheel_x_front"], "F"), (SPEC["wheel_x_rear"], "R")):
        for sy, side in ((1.0, "L"), (-1.0, "R")):
            wheels.append(build_wheel("GEO-Wheel%s%s" % (tag, side),
                                      wx, SPEC["wheel_y"] * sy))

    normalize_slots(body)
    bpy.ops.object.select_all(action="DESELECT")
    for w in wheels:
        w.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.name = "GEO-TaxiAcross"
    normalize_slots(body)

    for p in body.data.polygons:
        p.use_smooth = False

    clean_mesh(body)

    body.location = (0.0, 0.0, 0.0)
    body.rotation_euler = (0.0, 0.0, 0.0)
    body.scale = (1.0, 1.0, 1.0)
    return body


# ---------------------------------------------------------------- 场景 / 渲染

def setup_scene():
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            sc.render.engine = engine
            break
        except TypeError:
            continue
    print("[build] engine: %s" % sc.render.engine)
    # 风格化平涂：Standard 视图变换，保住高饱和黄（AgX 会把黄色洗成奶油色）
    try:
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
        sc.view_settings.exposure = 0.0
        print("[build] view transform: %s" % sc.view_settings.view_transform)
    except Exception as exc:                     # noqa: BLE001
        print("[build] WARN: view transform 设置失败 %s" % exc)

    world = bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    # 上亮下暗的渐变环境：金属（保险杠/轮毂/亮条）要有东西可反射，
    # 否则 metallic=1 在一片灰世界下会渲染成暗灰块。
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1.0
    mr.inputs["From Max"].default_value = 1.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.42
    ramp.color_ramp.elements[0].color = (0.055, 0.055, 0.062, 1.0)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (0.62, 0.66, 0.74, 1.0)
    nt.links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.85

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 4.6
    sun_data.angle = math.radians(2.0)
    sun = bpy.data.objects.new("Sun", sun_data)
    sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(48), 0.0, math.radians(35))

    fill_data = bpy.data.lights.new("Fill", "AREA")
    fill_data.energy = 900.0
    fill_data.size = 12.0
    fill = bpy.data.objects.new("Fill", fill_data)
    sc.collection.objects.link(fill)
    fill.location = (-7.0, -8.0, 5.0)
    fill.rotation_euler = (math.radians(60), 0.0, math.radians(-40))

    rim_data = bpy.data.lights.new("Rim", "AREA")
    rim_data.energy = 700.0
    rim_data.size = 8.0
    rim = bpy.data.objects.new("Rim", rim_data)
    sc.collection.objects.link(rim)
    rim.location = (-6.0, 7.0, 4.0)
    rim.rotation_euler = (math.radians(55), 0.0, math.radians(150))

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 65.0
    cam = bpy.data.objects.new("Cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam

    ground = bpy.data.meshes.new("QC_Ground")
    bmg = bmesh.new()
    bmesh.ops.create_grid(bmg, x_segments=1, y_segments=1, size=16.0)
    bmg.to_mesh(ground)
    bmg.free()
    g = bpy.data.objects.new("QC_Ground", ground)
    sc.collection.objects.link(g)
    gm = bpy.data.materials.new("M_QC_Ground")
    gm.use_nodes = True
    gb = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    gb.inputs["Base Color"].default_value = (0.20, 0.20, 0.22, 1.0)
    gb.inputs["Roughness"].default_value = 0.9
    ground.materials.append(gm)
    return cam


def aim(cam, loc, target):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def render_to(path, w, h, samples=48):
    sc = bpy.context.scene
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path
    ee = getattr(sc, "eevee", None)
    if ee is not None and hasattr(ee, "taa_render_samples"):
        ee.taa_render_samples = samples
    bpy.ops.render.render(write_still=True)
    print("[build] render -> %s (%dx%d)" % (path, w, h))


def make_checker_mat(size=512, cells=8):
    img = bpy.data.images.new("UV_Checker", width=size, height=size, alpha=False)
    cell = size / cells
    px = [0.0] * (size * size * 4)
    light, dark = (0.78, 0.75, 0.70, 1.0), (0.16, 0.15, 0.15, 1.0)
    for y in range(size):
        cy = int(y // cell) % 2
        base = y * size * 4
        for x in range(size):
            c = light if (int(x // cell) + cy) % 2 == 0 else dark
            i = base + x * 4
            px[i], px[i + 1], px[i + 2], px[i + 3] = c
    img.pixels = px
    img.pack()
    mat = bpy.data.materials.new("M_QC_Checker")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.6
    uvnode = nt.nodes.new("ShaderNodeUVMap")
    uvnode.uv_map = "UVMap"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = "CLIP"
    nt.links.new(uvnode.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def swap_material(obj, mat):
    saved = [p.material_index for p in obj.data.polygons]
    old = [m for m in obj.data.materials]
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.material_index = 0
    return saved, old


def restore_material(obj, saved):
    idx, old = saved
    obj.data.materials.clear()
    for m in old:
        obj.data.materials.append(m)
    for p, i in zip(obj.data.polygons, idx):
        p.material_index = i


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- 主流程

def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    want_render = "--no-render" not in argv

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "out")
    shot_dir = os.path.join(root, "renders")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(shot_dir, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    cam = setup_scene()

    obj = build_taxi()
    unwrap_uv(obj, pad=0.003)

    tex_path = os.path.join(out_dir, TEX_NAME)
    img = bake_basecolor(obj, tex_path, 1024)
    if img is None:
        img = grain_image(512)
        img.filepath_raw = tex_path
        img.file_format = "JPEG"
        img.save()
        print("[build] fallback texture -> %s" % tex_path)
    wire_texture(obj, img)

    obj.data.update()
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    bbox = obj.bound_box
    xs = [v[0] for v in bbox]
    ys = [v[1] for v in bbox]
    zs = [v[2] for v in bbox]
    dims_mm = [round((max(xs) - min(xs)) * 1000, 1),
               round((max(ys) - min(ys)) * 1000, 1),
               round((max(zs) - min(zs)) * 1000, 1)]
    print("[build] verts=%d faces=%d shells=%d tris=%d dims_mm=%s"
          % (len(obj.data.vertices), len(obj.data.polygons), shells_count(obj),
             tris, dims_mm))
    print("[build] nonmanifold_edges=%d" % nonmanifold_edges(obj))

    if want_render:
        aim(cam, (4.6, -8.0, 3.0), (0.0, 0.0, 1.0))
        render_to(os.path.join(shot_dir, "qc-hero.png"), 1280, 720)

        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 6.4
        aim(cam, (0.0, -10.0, 1.15), (0.0, 0.0, 1.15))
        render_to(os.path.join(shot_dir, "qc-side.png"), 1400, 700)
        cam.data.type = "PERSP"

        aim(cam, (-5.0, -7.0, 2.8), (0.0, 0.0, 1.0))
        render_to(os.path.join(shot_dir, "qc-rear34.png"), 1200, 700)

        aim(cam, (10.0, 0.0, 1.35), (0.0, 0.0, 1.1))
        render_to(os.path.join(shot_dir, "qc-front.png"), 1100, 800)

        saved = swap_material(obj, make_checker_mat())
        aim(cam, (4.6, -8.0, 3.0), (0.0, 0.0, 1.0))
        render_to(os.path.join(shot_dir, "qc-uv-checker.png"), 1000, 600)
        restore_material(obj, saved)

    aim(cam, (4.6, -8.0, 3.0), (0.0, 0.0, 1.0))
    bpy.context.scene.render.resolution_x = 1280
    bpy.context.scene.render.resolution_y = 720
    blend_path = os.path.join(out_dir, "taxi.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("[build] saved %s" % blend_path)

    manifest = {
        "asset": ASSET_STEM,
        "units": "mm",
        "objects": ["GEO-TaxiAcross"],
        "dims_mm": dims_mm,
        "expected_mm": [SPEC["length"], SPEC["width"], SPEC["height"]],
        "verts": len(obj.data.vertices),
        "faces": len(obj.data.polygons),
        "tris": tris,
        "shells": shells_count(obj),
        "nonmanifold_edges": nonmanifold_edges(obj),
        "materials": [m.name for m in obj.data.materials],
        "texture": TEX_NAME,
        "spec": "spec.md",
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("[build] manifest ok")


if __name__ == "__main__":
    main()
