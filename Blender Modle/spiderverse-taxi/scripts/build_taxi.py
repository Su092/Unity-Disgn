# -*- coding: utf-8 -*-
"""蜘蛛侠纵横宇宙风 · 风格化出租车 · 参数化建模（headless 安全）

写代码前 checklist（技能强制，逐条对过）：
  1. (长, 宽, 薄) = (局部 X 5200 mm, 局部 Y 1900 mm, 局部 Z 1720 mm)
     车身是沿 X 放样的长条实体；棋盘带贴在**宽轴面**（±Y），即英雄机位（−Y）那一侧。
  2. 收尖：车头/车尾端面用"断面收窄 + 端面封盖"，不是把一圈顶点缩到接近 0；
     轮胎/轮毂是回转体，端面本身是平盘，不倒成尖。
  3. headless：建网格只用 bmesh + data API；只有 modifier_add/apply 与 bake 走 ops。
     没有 object.mode_set / mesh.* / transform.* / uv.*。

拓扑策略：
  车身/车厢/保险杠/灯箱/镜/棋盘带 → 各自独立实体，倒角后 **Boolean UNION** 进车身，
  得到 1 个连通闭合壳；4 个车轮各自 UNION（胎+毂）后**不焊进车身**（要能单独旋转），
  再 join 进同一网格对象 ⇒ 交付件是 1 对象 5 壳，量测门对整包判 AABB。

UV 策略：分岛展开 + 装箱（同 medieval-street-lamp 的实测结论，箱式/柱面投影会重叠上千对）。

贴图策略：Cycles DIFFUSE(color-only) 烘焙进 1024² 图 —— UV 不重叠，一张图涵盖全部材质区；
  烘焙不可用时退回"平涂 + 程序化颗粒贴图"，并在回执里写明走了哪条通路。

用法：
  blender -b --factory-startup --python scripts/build_taxi.py [-- --no-text]
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

MM = 0.001

ASSET_STEM = "Modle_Vehicle_SpiderTaxi"
TEX_NAME = ASSET_STEM + "_basecolor.jpg"

# ---------------------------------------------------------------- 规格（mm，冻结）

SPEC = {
    "length": 5200.0,
    "width": 1900.0,
    "height": 1720.0,
    "body_half": 930.0,
    "belt_z": 1000.0,
    "sill_z": 300.0,
    "wheel_x": 1700.0,
    "wheel_y": 760.0,
    "tire_r": 400.0,
    "tire_w": 250.0,
    "hub_r": 240.0,
    "hub_w": 264.0,
    "arch_r": 470.0,
    "arch_y_in": 620.0,
    "cabin_floor": 940.0,
    "sign_z0": 1540.0,
    "sign_z1": 1720.0,
    "checker_x0": -1150.0,
    "checker_x1": 950.0,
    "checker_z0": 600.0,
    "checker_z1": 740.0,
    "checker_out": 938.0,
    "checker_in": 900.0,
    "checker_cells": 15,
    "bumper_tip": 2600.0,
}

MAT_NAMES = [
    "M_Taxi_Paint",
    "M_Taxi_Glass",
    "M_Taxi_Trim",
    "M_Taxi_Tire",
    "M_Taxi_Rim",
    "M_Taxi_CheckerW",
    "M_Taxi_Sign",
]
MI = {n: i for i, n in enumerate(MAT_NAMES)}
PAINT, GLASS, TRIM, TIRE, RIM, CHECKW, SIGN = ("M_Taxi_Paint", "M_Taxi_Glass",
                                               "M_Taxi_Trim", "M_Taxi_Tire",
                                               "M_Taxi_Rim", "M_Taxi_CheckerW",
                                               "M_Taxi_Sign")

# 车身放样断面：(x, y_scale, z_top)
BODY_SECTIONS = [
    (-2450.0, 0.86, 1000.0),
    (-2280.0, 0.96, 1000.0),
    (-1900.0, 1.00, 1000.0),
    (-1350.0, 1.00, 1000.0),
    (-900.0, 1.00, 1000.0),
    (950.0, 1.00, 1000.0),
    (1700.0, 1.00, 1000.0),
    (2150.0, 0.97, 990.0),
    (2450.0, 0.90, 950.0),
]

# 车厢放样断面：(x, 底半宽 bw, 顶 zt)
CABIN_SECTIONS = [
    (1000.0, 700.0, 985.0),
    (940.0, 730.0, 1060.0),
    (820.0, 790.0, 1180.0),
    (640.0, 845.0, 1330.0),
    (430.0, 875.0, 1470.0),
    (300.0, 885.0, 1560.0),
    (-980.0, 885.0, 1560.0),
    (-1120.0, 860.0, 1500.0),
    (-1260.0, 800.0, 1330.0),
    (-1350.0, 750.0, 1150.0),
    (-1420.0, 700.0, 985.0),
]

# 材质外观（渲染/烘焙都用它）
MAT_LOOK = {
    PAINT:    ((1.000, 0.706, 0.075, 1.0), 0.42, 0.00),
    GLASS:    ((0.055, 0.075, 0.140, 1.0), 0.14, 0.10),
    TRIM:     ((0.055, 0.050, 0.052, 1.0), 0.52, 0.20),
    TIRE:     ((0.032, 0.032, 0.036, 1.0), 0.88, 0.00),
    RIM:      ((0.760, 0.775, 0.800, 1.0), 0.30, 0.75),
    CHECKW:   ((0.930, 0.905, 0.860, 1.0), 0.45, 0.00),
    SIGN:     ((1.000, 0.945, 0.820, 1.0), 0.35, 0.00),
}


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
    """沿 X 放样。sections 为 dict 列表（含 x）；profile_fn(sec)->[(y,z)]；face_mat_fn(si,i)->材质名。"""
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
    # 索引：x*4 + y*2 + z
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
    """轴对齐圆柱：axis='X'|'Y'|'Z'；a0/a1 是沿轴的两端坐标；c 是另两轴中心。

    X: c=(y,z) · Y: c=(x,z) · Z: c=(x,y)
    """
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
    """往已有 bmesh 里加一个轴对齐盒（8 顶点 / 6 面），不做 recalc。"""
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
    """把 XZ 平面上的闭合多边形沿 Y 挤出成柱体（两端封口）。"""
    n = len(pts_xz)
    a = [bm.verts.new((x * MM, y0 * MM, z * MM)) for (x, z) in pts_xz]
    b = [bm.verts.new((x * MM, y1 * MM, z * MM)) for (x, z) in pts_xz]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)


def multi_box(name, boxes, mat_name):
    """多个互不相连的盒合成一个对象：布尔前少跑几次 op，也少一堆中间对象。"""
    bm = bmesh.new()
    for b in boxes:
        bm_add_box(bm, *b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, [bpy.data.materials[mat_name]],
                      [0] * len(bm.faces))


def ring(name, axis, c, r_in, r_out, a0, a1, segments, mat_name):
    """轴对齐垫圈（washer）：r_in..r_out 的环，沿轴 a0→a1。语义同 cylinder。"""
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
    o0, i0, o1, i1 = loops           # a0 外环 / a0 内环 / a1 外环 / a1 内环
    for s in range(segments):
        t = (s + 1) % segments
        bm.faces.new((o0[s], o0[t], o1[t], o1[s]))      # 外壁
        bm.faces.new((i0[t], i0[s], i1[s], i1[t]))      # 内壁
        bm.faces.new((o0[t], o0[s], i0[s], i0[t]))      # a0 端环
        bm.faces.new((o1[s], o1[t], i1[t], i1[s]))      # a1 端环
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(name, bm, [bpy.data.materials[mat_name]],
                      [0] * len(bm.faces))


def checker_strip(name, x0, x1, y_out, y_in, z0, z1, cells):
    """凸起的棋盘带：±Y 两个面上按格交替材质（黑白），其余面同格。"""
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
            m = CHECKW if (i % 2 == 0) else TRIM
            for k in range(4):
                k2 = (k + 1) % 4
                bm.faces.new((a[k], a[k2], b[k2], b[k]))
                face_mats.append(MI[m] if k != 2 else MI[TRIM])   # k=2 是内表面
        # 两端封口
        bm.faces.new(list(reversed(rows[0])))
        face_mats.append(MI[TRIM])
        bm.faces.new(rows[-1])
        face_mats.append(MI[TRIM])
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
            bsdf.inputs["Emission Strength"].default_value = 0.35
        m.diffuse_color = col
    return [bpy.data.materials[n] for n in MAT_NAMES]


def normalize_slots(obj):
    """Boolean TRANSFER 会搬空槽/重复槽：按 MAT_NAMES 顺序重建槽位并重映射面索引。"""
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
    lambda p: (-p.y, p.z),   # +X
    lambda p: (p.y, p.z),    # -X
    lambda p: (p.x, p.z),    # +Y
    lambda p: (-p.x, p.z),   # -Y
    lambda p: (p.x, p.y),    # +Z
    lambda p: (p.x, -p.y),   # -Z
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
        islands_data.append({
            "faces": pts_per_face, "minx": minx, "miny": miny,
            "w": max(w * scale, 1e-9), "h": max(h * scale, 1e-9), "scale": scale,
        })

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
                uvl.data[li].uv = (px + (u - d["minx"]) * s,
                                   py + (v - d["miny"]) * s)
    uvl.active_render = True
    me.update()
    print("[build] uv: %d islands / %d faces / k=%.5f"
          % (len(islands_data), len(me.polygons), lo))
    return uv_audit(obj)


class _UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, a):
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def uv_audit(obj):
    me = obj.data
    if not me.uv_layers:
        return {"verdict": "fail", "reason": "无 UV 层"}
    uvl = me.uv_layers[0]

    def loop_uv(li):
        u = uvl.data[li].uv
        return (round(u[0], 6), round(u[1], 6))

    edge_map = {}
    for poly in me.polygons:
        uvs = [loop_uv(li) for li in poly.loop_indices]
        m = len(poly.vertices)
        for i in range(m):
            v0, v1 = poly.vertices[i], poly.vertices[(i + 1) % m]
            uv0, uv1 = uvs[i], uvs[(i + 1) % m]
            key = (min(v0, v1), max(v0, v1))
            edge_map.setdefault(key, []).append((poly.index, uv0, uv1))

    uf = _UF(len(me.polygons))
    for key, recs in edge_map.items():
        if len(recs) != 2:
            continue
        (f0, a0, b0), (f1, a1, b1) = recs
        if (a0, b0) == (a1, b1) or (a0, b0) == (b1, a1):
            uf.union(f0, f1)

    groups = {}
    for poly in me.polygons:
        groups.setdefault(uf.find(poly.index), []).append(poly.index)

    boxes, dense = [], []
    for faces in groups.values():
        us, vs, a_uv, a_3d = [], [], 0.0, 0.0
        for fi in faces:
            poly = me.polygons[fi]
            pts = [loop_uv(li) for li in poly.loop_indices]
            us.extend(p[0] for p in pts)
            vs.extend(p[1] for p in pts)
            a_uv += abs(_poly_area2(pts))
            a_3d += poly.area
        boxes.append((min(us), min(vs), max(us), max(vs)))
        if a_3d > 1e-12:
            dense.append(a_uv / a_3d)
    allu = [d.uv[0] for d in uvl.data]
    allv = [d.uv[1] for d in uvl.data]

    overlaps = 0
    for i in range(len(boxes)):
        a = boxes[i]
        for j in range(i + 1, len(boxes)):
            b = boxes[j]
            if a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 \
               and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6:
                overlaps += 1

    covered = sum((b[2] - b[0]) * (b[3] - b[1]) for b in boxes)
    ratio = (max(dense) / min(dense)) if dense and min(dense) > 1e-12 else 0.0
    degenerate = sum(1 for poly in me.polygons
                     if len(set(loop_uv(li) for li in poly.loop_indices)) < 3)
    data = {
        "uv_islands": len(groups),
        "uv_range": [[round(min(allu), 4), round(max(allu), 4)],
                     [round(min(allv), 4), round(max(allv), 4)]],
        "island_bbox_overlaps": overlaps,
        "coverage": round(covered, 4),
        "texel_density_ratio": round(ratio, 4),
        "degenerate_faces": degenerate,
    }
    ok = (overlaps == 0 and degenerate == 0
          and min(allu) >= -1e-4 and max(allu) <= 1 + 1e-4
          and min(allv) >= -1e-4 and max(allv) <= 1 + 1e-4
          and covered >= 0.15 and 0 < ratio <= 1.05)
    data["verdict"] = "pass" if ok else "fail"
    return data


# ---------------------------------------------------------------- 贴图：烘焙 / 退路

def bake_basecolor(obj, path, size=1024):
    """Cycles DIFFUSE(color-only) 烘焙：UV 不重叠 ⇒ 一张图含全部材质区。"""
    try:
        sc = bpy.context.scene
        img = bpy.data.images.new("BAKE_BaseColor", size, size, alpha=False)
        for slot in obj.material_slots:
            m = slot.material
            if not m or not m.use_nodes:
                continue
            nt = m.node_tree
            node = nt.nodes.new("ShaderNodeTexImage")
            node.image = img
            node.location = (-900, 400)
            node.select = True
            nt.nodes.active = node
        sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = 1
        bake = sc.render.bake
        bake.margin = 8
        bake.use_clear = True
        bake.use_pass_direct = False
        bake.use_pass_indirect = False
        bake.use_pass_color = True
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.bake(type="DIFFUSE")
        out = path
        img.filepath_raw = out
        img.file_format = "JPEG"
        img.save()
        # 烘焙产物是 "generated" 图，FBX 导出器不认（AUTO 模式下写不出贴图路径）。
        # 落盘后重新按文件加载，与 lamp 的贴图通路保持一致（source=FILE ⇒ 可 pack、可导出）。
        bpy.data.images.remove(img)
        img = bpy.data.images.load(out)
        img.name = TEX_NAME
        print("[build] bake ok -> %s (%dx%d) source=%s" % (out, size, size, img.source))
        return img
    except Exception as exc:                     # noqa: BLE001
        print("[build] WARN: bake 失败，退回程序化颗粒贴图: %s" % exc)
        return None


def grain_image(size=512):
    """退路贴图：无缝纸纹 + 淡半调，几乎不改变平涂色。"""
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
            # 45° 网点（周期 16 px）
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


def wire_texture(obj, img, path=None):
    """给每个材质接 UVMap → Image → Base Color（Vector 口显式接，不靠隐式 UV）。"""
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
    if path:
        try:
            if img.filepath != "//" + TEX_NAME:
                if not img.packed_file:
                    img.pack()
                img.filepath = "//" + TEX_NAME
            print("[build] texture packed into .blend: %s" % img.name)
        except RuntimeError as exc:
            print("[build] WARN: 打包失败 %s: %s" % (img.name, exc))


# ---------------------------------------------------------------- 装配

def build_body(mats):
    secs = [{"x": x, "w": SPEC["body_half"] * s, "zt": zt} for (x, s, zt) in BODY_SECTIONS]

    def profile(sec):
        w, zt = sec["w"], sec["zt"]
        return [
            (-0.86 * w, SPEC["sill_z"]),
            (-1.00 * w, 390.0),
            (-1.00 * w, zt - 120.0),
            (-0.94 * w, zt),
            (0.94 * w, zt),
            (1.00 * w, zt - 120.0),
            (1.00 * w, 390.0),
            (0.86 * w, SPEC["sill_z"]),
        ]

    body = loft("GEO-Body", secs, profile, lambda si, i: PAINT, mats, PAINT)
    bevelize(body, 22.0, 2)
    return body


def build_cabin(mats):
    secs = [{"x": x, "bw": bw, "zt": zt} for (x, bw, zt) in CABIN_SECTIONS]

    def profile(sec):
        b, zt = sec["bw"], sec["zt"]
        z0 = SPEC["cabin_floor"]
        zA = z0 + 0.26 * (zt - z0)
        zB = max(zA + 10.0, zt - 105.0)
        zC = min(zt - 5.0, max(zB + 8.0, zt - 60.0))
        return [
            (b, z0), (b, zA), (0.995 * b, zB), (0.86 * b, zC), (0.74 * b, zt),
            (-0.74 * b, zt), (-0.86 * b, zC), (-0.995 * b, zB), (-b, zA), (-b, z0),
        ]

    def face_mat(si, i):
        # 窗带不按断面环索引判（环索引只能盖住左右两侧，风挡/后窗会漏），
        # 改成建完按面中心高度整片贴玻璃 —— 见下方 paint_cabin_glass()。
        return PAINT

    cabin = loft("GEO-Cabin", secs, profile, face_mat, mats, PAINT)
    paint_cabin_glass(cabin)
    bevelize(cabin, 20.0, 2)
    return cabin


GLASS_Z0, GLASS_Z1 = 1085.0, 1460.0


def paint_cabin_glass(obj):
    """车厢上整条"玻璃腰带"：z 中心落在 [1085,1460] 的面全部改玻璃。

    这样前风挡/后窗（斜面过渡那一圈）与侧窗连成一条连续玻璃带，
    顶棚与顶棚肩（>1460）保持车漆 —— 正是风格化车该有的图形分区。
    """
    me = obj.data
    n = 0
    for p in me.polygons:
        z = p.center.z / MM
        if GLASS_Z0 <= z <= GLASS_Z1:
            p.material_index = MI[GLASS]
            n += 1
    print("[build] cabin glass faces: %d / %d" % (n, len(me.polygons)))


def build_sign(mats, want_text):
    s0, s1 = SPEC["sign_z0"], SPEC["sign_z1"]
    sign = box("GEO-Sign", -250, 250, -115, 115, s0, s1, SIGN)
    bevelize(sign, 18.0, 2)
    if not want_text:
        return sign

    for side in (-1, 1):
        txt = text_solid("TAXI", 62.0, 9.0)
        if txt is None:
            print("[build] WARN: 造字失败，跳过刻字")
            return sign
        # 局部 X(读向) → 世界 +X(-Y 面) / -X(+Y 面)；局部 Y → +Z；局部 Z(挤出) → ∓Y
        if side < 0:
            rot = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))   # 列: X->+X, Y->+Z, Z->-Y
            ty = -111.5
        else:
            rot = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))   # 列: X->-X, Y->+Z, Z->+Y
            ty = 111.5
        bm = bmesh.new()
        bm.from_mesh(txt.data)
        bm.transform(Matrix.Translation((0.0, ty * MM, 1640.0 * MM)) @ rot.to_4x4())
        bm.to_mesh(txt.data)
        bm.free()
        txt.data.update()
        try:
            before = nonmanifold_edges(sign)
            bool_op(sign, txt, "DIFFERENCE")
            after = nonmanifold_edges(sign)
            print("[build] carve text side=%+d: nonmanifold %d -> %d" % (side, before, after))
            if after > 0:
                raise RuntimeError("刻字引入非流形边 %d" % after)
        except Exception as exc:                 # noqa: BLE001
            print("[build] WARN: 刻字失败(%s)，该侧保留平面" % exc)
    return sign


def text_solid(text, size_mm, extrude_mm):
    """把 FONT 曲线求值成实体网格，居中到原点（米制）。"""
    cu = bpy.data.curves.new("TXT", type="FONT")
    cu.body = text
    cu.size = size_mm * MM
    cu.extrude = extrude_mm * 0.5 * MM
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    obj = bpy.data.objects.new("TXT", cu)
    bpy.context.scene.collection.objects.link(obj)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    bpy.data.objects.remove(obj, do_unlink=True)
    if not me.polygons:
        bpy.data.meshes.remove(me)
        return None
    out = bpy.data.objects.new("GEO-SignText", me)
    bpy.context.scene.collection.objects.link(out)
    out.data.materials.append(bpy.data.materials[TRIM])
    for p in out.data.polygons:
        p.material_index = 0
    return out


def build_wheel(name, cx, cy):
    tire = cylinder(name + "_Tire", "Y", (cx, 400.0), SPEC["tire_r"],
                    cy - SPEC["tire_w"] * 0.5, cy + SPEC["tire_w"] * 0.5, 32, TIRE)
    bevelize(tire, 55.0, 3)
    hub = cylinder(name + "_Hub", "Y", (cx, 400.0), SPEC["hub_r"],
                   cy - SPEC["hub_w"] * 0.5, cy + SPEC["hub_w"] * 0.5, 32, RIM)
    bevelize(hub, 18.0, 2)
    bool_op(tire, hub, "UNION")

    # 白壁圈（胎侧 CHECKW 环）+ 五辐 + 中心盖（TRIM 凸台）——**只做朝外那一侧**。
    # 内侧（朝轮井）加装饰会顶到轮拱内壁 |y|=620，直接被 buried 判成埋入。
    # 交叠：环压进胎侧 7 mm / 凸 5 mm；辐条压进轮毂 8 mm / 凸 4 mm；
    # 盖压进轮毂 8 mm / 凸 8 mm。辐条外端 r=228 < 轮毂 r=240，不越界。
    sg = 1.0 if cy > 0.0 else -1.0
    wall = ring(name + "_Wall", "Y", (cx, 400.0), 258.0, 342.0,
                cy + sg * 118.0, cy + sg * 130.0, 32, CHECKW)
    bool_op(tire, wall, "UNION")

    bm2 = bmesh.new()
    for k in range(5):
        th = 2.0 * math.pi * k / 5.0 + math.pi * 0.5
        ca, sa = math.cos(th), math.sin(th)
        pts = []
        for (r, s) in ((80.0, -21.0), (228.0, -21.0), (228.0, 21.0), (80.0, 21.0)):
            pts.append((cx + r * ca - s * sa, 400.0 + r * sa + s * ca))
        bm_add_prism(bm2, pts, cy + sg * 124.0, cy + sg * 136.0)
    bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces)
    spokes = new_object(name + "_Spokes", bm2, [bpy.data.materials[TRIM]],
                        [0] * len(bm2.faces))
    bool_op(tire, spokes, "UNION")

    cap = cylinder(name + "_Cap", "Y", (cx, 400.0), 86.0,
                   cy + sg * 124.0, cy + sg * 140.0, 24, TRIM)
    bevelize(cap, 8.0, 2)
    bool_op(tire, cap, "UNION")

    tire.name = name
    return tire


def build_details(mats):
    """细节层：一律按 spec.md §5b 的交叠量压进车身，逐件 UNION。

    纪律：**任何贴合面都要给 5 mm 以上的插入量**，否则 EXACT 布尔要吃共面，
    结果是随机掉面 / 非流形。所以下面的 925 / 2470 / 2438 这些"比表面低一点"的数
    都有用，改动前先看 §5b。
    """
    parts = []

    def add(part, bev=0.0):
        if bev > 0.0:
            bevelize(part, bev, 2)
        parts.append(part)
        return part

    # ① 前风挡雨刮 ×2：平行四边形沿 Y 挤出，贴着风挡斜面（x+z=2000 那一面）。
    #    插入 4 mm / 凸 9 mm，刃厚 13 mm。
    bm = bmesh.new()
    d = (-0.70710678, 0.70710678)          # 顺风挡向上
    nrm = (0.70710678, 0.70710678)         # 风挡外法线
    for (px, pz, y0, y1) in ((872.0, 1128.0, -340.0, -12.0),
                             (888.0, 1112.0, 12.0, 340.0)):
        qx, qz = px + d[0] * 64.0, pz + d[1] * 64.0
        pts = [
            (px - nrm[0] * 4.0, pz - nrm[1] * 4.0),
            (qx - nrm[0] * 4.0, qz - nrm[1] * 4.0),
            (qx + nrm[0] * 9.0, qz + nrm[1] * 9.0),
            (px + nrm[0] * 9.0, pz + nrm[1] * 9.0),
        ]
        bm_add_prism(bm, pts, y0, y1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    add(new_object("GEO-Wiper", bm, [bpy.data.materials[TRIM]],
                   [0] * len(bm.faces)))

    # ② 前格栅横条 ×3（压进栅板 5 mm，凸 5 mm）
    add(multi_box("GEO-GrilleBars",
                  [(2470.0, 2480.0, -348.0, 348.0, z, z + 12.0)
                   for z in (648.0, 698.0, 748.0)], RIM), 2.0)

    # ③ 前后车牌（压进端面 12 mm，凸 12 mm）+ 牌面数字条（TRIM，凸 2 mm）
    add(multi_box("GEO-Plates",
                  [(2438.0, 2462.0, -185.0, 185.0, 512.0, 600.0),
                   (-2462.0, -2438.0, -185.0, 185.0, 512.0, 600.0)], CHECKW), 3.0)
    add(multi_box("GEO-PlateText",
                  [(2450.0, 2464.0, -140.0, 140.0, 545.0, 567.0),
                   (-2464.0, -2450.0, -140.0, 140.0, 545.0, 567.0)], TRIM))

    # ④ 前下巴 / 后扩散器（压进保险杠 16 mm，往下探 44 mm）
    add(multi_box("GEO-Chin",
                  [(2370.0, 2596.0, -600.0, 600.0, 296.0, 356.0),
                   (-2560.0, -2380.0, -580.0, 580.0, 296.0, 356.0)], TRIM), 5.0)

    # ⑤ 排气尾管 ×2（穿过后扩散器，尾端 -2599 仍在内）
    for sy in (1.0, -1.0):
        cyl = cylinder("GEO-Exhaust%s" % ("L" if sy > 0 else "R"), "X",
                       (400.0 * sy, 316.0), 44.0, -2599.0, -2440.0, 20, RIM)
        bevelize(cyl, 6.0, 2)
        add(cyl)

    # ⑥ 门把手 ×4（压进侧围 5 mm，凸 17 mm）
    add(multi_box("GEO-Handles",
                  [(x0, x0 + 110.0, 925.0 * sy, 947.0 * sy, 812.0, 866.0)
                   for sy in (1.0, -1.0)
                   for x0 in (250.0, -760.0)], TRIM), 4.0)

    # ⑦ 门缝凸条（PAINT，宽 12 mm / 凸 6 mm；靠 inverted-hull 描边读成门缝）
    add(multi_box("GEO-DoorSeam",
                  [(x0, x0 + 12.0, 925.0 * sy, 936.0 * sy, 405.0, 870.0)
                   for sy in (1.0, -1.0)
                   for x0 in (146.0, -906.0)], PAINT), 2.0)

    # ⑧ 侧转向灯 ×2
    add(multi_box("GEO-SideMarker",
                  [(1180.0, 1250.0, 925.0 * sy, 939.0 * sy, 700.0, 742.0)
                   for sy in (1.0, -1.0)], RIM), 2.0)

    # ⑨ 油箱盖（−Y 侧，压进 5 mm）
    add(cylinder("GEO-FuelCap", "Y", (-1450.0, 800.0), 58.0,
                 -938.0, -925.0, 24, RIM), 2.0)

    # ⑩ 车顶天线（压进车顶 12 mm）
    add(cylinder("GEO-Antenna", "Z", (-880.0, -560.0), 8.0,
                 1548.0, 1662.0, 12, TRIM), 1.5)

    # ⑪ 灯箱底座（压进车顶 14 mm，四边比灯箱宽 22 mm）
    add(box("GEO-SignBase", -272.0, 272.0, -132.0, 132.0, 1546.0, 1566.0, TRIM), 6.0)

    # ⑫ 后视镜镜面 ×2（贴在镜壳背面前 6 mm）
    add(multi_box("GEO-MirrorGlass",
                  [(764.0, 776.0, 848.0 * sy, 942.0 * sy, 1038.0, 1132.0)
                   for sy in (1.0, -1.0)], GLASS), 2.0)

    # ⑬ 后备箱小鸭尾（楔形，压在行李箱盖 z=1000 上 12 mm）
    bm = bmesh.new()
    bm_add_prism(bm, [(-2432.0, 992.0), (-2282.0, 992.0),
                      (-2290.0, 1032.0), (-2432.0, 1024.0)], -700.0, 700.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    add(new_object("GEO-Ducktail", bm, [bpy.data.materials[TRIM]],
                   [0] * len(bm.faces)), 6.0)

    return parts


def build_taxi(want_text=True):
    mats = build_materials()
    body = build_body(mats)
    parts = [build_cabin(mats)]

    # 保险杠
    for sx in (1, -1):
        tip = SPEC["bumper_tip"] * sx
        inner = 2400.0 * sx
        parts.append(box("GEO-Bumper", inner, tip, -950, 950, 340, 500, TRIM))
        bevelize(parts[-1], 22.0, 2)

    # 大灯 + 格栅
    for sy in (1, -1):
        parts.append(cylinder("GEO-Headlight", "X", (620.0 * sy, 810.0), 95.0,
                              2440.0, 2485.0, 24, RIM))
        bevelize(parts[-1], 12.0, 2)
    grille = box("GEO-Grille", 2445, 2475, -360, 360, 620, 790, TRIM)
    bevelize(grille, 10.0, 2)
    parts.append(grille)

    # 尾灯（后脸，略凸）
    for sy in (1, -1):
        tail = box("GEO-Taillight", -2470, -2430, 560 * sy, 700 * sy, 790, 860, TRIM)
        bevelize(tail, 12.0, 2)
        parts.append(tail)

    # 后视镜
    for sy in (1, -1):
        stalk = box("GEO-MirrorStalk", 790, 830, 770 * sy, 860 * sy, 1050, 1095, TRIM)
        head = box("GEO-MirrorHead", 770, 880, 840 * sy, 950 * sy, 1030, 1140, TRIM)
        bevelize(head, 15.0, 2)
        parts += [stalk, head]

    # 棋盘带
    parts.append(checker_strip("GEO-Checker", SPEC["checker_x0"], SPEC["checker_x1"],
                               SPEC["checker_out"], SPEC["checker_in"],
                               SPEC["checker_z0"], SPEC["checker_z1"],
                               SPEC["checker_cells"]))

    parts.append(build_sign(mats, want_text))

    # 细节层（雨刮 / 格栅条 / 车牌 / 前后唇 / 排气 / 把手 / 门缝 / 侧灯 /
    # 油箱盖 / 天线 / 灯箱底座 / 镜面）—— 交叠量见 spec.md §5b
    parts += build_details(mats)

    for p in parts:
        n0 = len(body.data.polygons)
        bool_op(body, p, "UNION")
        n1 = len(body.data.polygons)
        # 布尔只该"吃进"图元，不该把主体吃掉。掉面超过一半 = 求解器把目标丢了。
        if n1 < n0 * 0.5:
            raise RuntimeError("UNION(%s) 疑似丢失主体：%d -> %d 面" % (p.name, n0, n1))
    print("[build] union done: %d verts / %d faces"
          % (len(body.data.vertices), len(body.data.polygons)))
    sc = shells_count(body)
    print("[build] shells after union: %d" % sc)
    assert sc == 1, "UNION 后车身不是单一壳（%d）：有图元没并进去" % sc

    # 轮拱切削（只切外侧，留轮井内壁 |y|>=620）
    for sx in (1, -1):
        for sy in (1, -1):
            cut = cylinder("GEO-ArchCut", "Y", (SPEC["wheel_x"] * sx, 400.0),
                           SPEC["arch_r"], SPEC["arch_y_in"] * sy, 985.0 * sy, 32, TRIM)
            bool_op(body, cut, "DIFFERENCE")

    # 车轮
    wheels = []
    for sx in (1, -1):
        for sy in (1, -1):
            wheels.append(build_wheel("GEO-Wheel%s%s" % ("F" if sx > 0 else "R",
                                                        "L" if sy > 0 else "R"),
                                      SPEC["wheel_x"] * sx, SPEC["wheel_y"] * sy))

    normalize_slots(body)
    bpy.ops.object.select_all(action="DESELECT")
    for w in wheels:
        w.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.name = "GEO-TaxiSpider"
    normalize_slots(body)

    for p in body.data.polygons:
        p.use_smooth = False

    body.location = (0.0, 0.0, 0.0)
    body.rotation_euler = (0.0, 0.0, 0.0)
    body.scale = (1.0, 1.0, 1.0)
    return body


# ---------------------------------------------------------------- 渲染装置

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

    world = bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.22, 0.22, 0.26, 1.0)
    bg.inputs["Strength"].default_value = 0.45

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 4.2
    sun_data.angle = math.radians(3.0)
    sun = bpy.data.objects.new("Sun", sun_data)
    sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), 0.0, math.radians(35))

    fill_data = bpy.data.lights.new("Fill", "AREA")
    fill_data.energy = 600.0
    fill_data.size = 9.0
    fill = bpy.data.objects.new("Fill", fill_data)
    sc.collection.objects.link(fill)
    fill.location = (-6.0, -7.0, 4.5)
    fill.rotation_euler = (math.radians(62), 0.0, math.radians(-40))

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 62.0
    cam = bpy.data.objects.new("Cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam

    # 地面（只用于 QC，不导出）
    ground = bpy.data.meshes.new("QC_Ground")
    bmg = bmesh.new()
    bmesh.ops.create_grid(bmg, x_segments=1, y_segments=1, size=14.0)
    bmg.to_mesh(ground)
    bmg.free()
    g = bpy.data.objects.new("QC_Ground", ground)
    sc.collection.objects.link(g)
    gm = bpy.data.materials.new("M_QC_Ground")
    gm.use_nodes = True
    gb = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    gb.inputs["Base Color"].default_value = (0.16, 0.16, 0.18, 1.0)
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


# ---------------------------------------------------------------- 主流程

def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    want_text = "--no-text" not in argv

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "out")
    shot_dir = os.path.join(root, "renders")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(shot_dir, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    cam = setup_scene()

    obj = build_taxi(want_text)
    audit_uv = unwrap_uv(obj, pad=0.003)

    # basecolor：先烘，失败退程序化颗粒
    tex_path = os.path.join(out_dir, TEX_NAME)
    img = bake_basecolor(obj, tex_path, 1024)
    if img is None:
        img = grain_image(512)
        img.filepath_raw = tex_path
        img.file_format = "JPEG"
        img.save()
        print("[build] fallback texture saved -> %s" % tex_path)
    wire_texture(obj, img, tex_path)

    # 交付状态
    obj.data.update()
    print("[build] verts=%d faces=%d shells=%d tris=%d"
          % (len(obj.data.vertices), len(obj.data.polygons), shells_count(obj),
             sum(len(p.vertices) - 2 for p in obj.data.polygons)))
    print("[build] uv audit: %s" % audit_uv)
    print("[build] material slots: %d" % len(obj.data.materials))

    # QC 渲染
    aim(cam, (3.6, -7.2, 2.6), (0.0, 0.0, 0.85))
    render_to(os.path.join(shot_dir, "qc-hero-color.png"), 1280, 720)

    # 侧视正交（对参考图复核比例）
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 6.0
    aim(cam, (0.0, -9.0, 0.86), (0.0, 0.0, 0.86))
    render_to(os.path.join(shot_dir, "qc-side.png"), 1280, 720)
    cam.data.type = "PERSP"

    # 后 3/4（看尾部与后窗）
    aim(cam, (-4.2, -6.0, 2.4), (0.0, 0.0, 0.9))
    render_to(os.path.join(shot_dir, "qc-rear.png"), 960, 540)

    # UV 棋盘证据
    saved = swap_material(obj, make_checker_mat())
    aim(cam, (3.6, -7.2, 2.6), (0.0, 0.0, 0.85))
    render_to(os.path.join(shot_dir, "qc-uv-checker.png"), 1280, 720)
    restore_material(obj, saved)
    assert len(obj.data.materials) >= 1

    # 存档状态
    aim(cam, (3.6, -7.2, 2.6), (0.0, 0.0, 0.85))
    bpy.context.scene.render.resolution_x = 1280
    bpy.context.scene.render.resolution_y = 720
    bpy.context.scene.render.filepath = "//../renders/qc-hero-color.png"
    blend_path = os.path.join(out_dir, "taxi.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("[build] saved %s" % blend_path)


if __name__ == "__main__":
    main()
