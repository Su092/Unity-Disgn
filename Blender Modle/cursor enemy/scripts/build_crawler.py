# -*- coding: utf-8 -*-
"""cursor enemy / 参考图还原建模 v2（低模四足机械虫）。

  blender -b --factory-startup --python scripts/build_crawler.py -- [stage=build|render|all] [res=1254]

坐标系：+Z 上，米制；面朝 −Y；其右侧 +X；落地 z = 0。

尺寸来自 spec.md §2（像素量测 + 总高 1240 mm 标定）：
  总长 1.90 m（y −1.02 … +0.88）  总宽 1.55 m（腿外沿 x ±0.775）  总高 1.24 m

结构（对参考图逐条对齐）：
  · 壳顶是**屋脊**（沿 Y 的棱线），前坡带两条蓝色发光条 → 对应参考图两条平行蓝条
  · 橙色壳包到侧裙 zc，zc 从后 0.78 降到前 0.62 → 参考图橙/灰分界随前后下降
  · 琥珀人字条在 zc 下 40 mm，沿侧面随 zc 走 → 参考图人字带
  · 头是前伸的方块，visor（0.60×0.12 m）是**凹槽**，槽底自发光 → 参考图 recessed visor
  · 四条粗柱腿，外侧带琥珀环，脚是外扩的矮方墩

流程（对应 blender-asset-pipeline）：
  1. 每件先建闭合网格 → 布尔 UNION 成**单壳**（避免壳互相埋入）
  2. visor 用 DIFFERENCE 切槽（槽底=自发光材质，仍是单壳）
  3. 面材质在构造期按 profile 段索引给定，不靠布尔后猜索引
  4. UV：法线分桶三平面投影 → 分岛 → 货架装箱
  5. 贴图：把各面材质基色**光栅化**进 UV（确定性，不跑 Cycles 烘焙）
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
RENDERS = os.path.join(PROJ, "renders")
EXPORT = os.path.join(PROJ, "export")
REFS = os.path.join(PROJ, "refs_out")
for d in (RENDERS, EXPORT, REFS):
    os.makedirs(d, exist_ok=True)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ARGS = dict(t.split("=", 1) for t in argv if "=" in t)
RES = int(ARGS.get("res", 1254))
STAGE = ARGS.get("stage", "all")
BLEND_PATH = os.path.join(PROJ, "crawler.blend")
TEX_NAME = "Modle_Enemy_Crawler_basecolor.jpg"
SPEC = json.load(open(os.path.join(PROJ, "spec.json"), "r", encoding="utf-8"))

# spec.json 用毫米；建模用米
MM = 0.001

# 琥珀带在截面上的位置（相对 zc 下移量 / 带厚），来自 spec.json
AMBER_OFFSET = SPEC["shell"]["amber_offset"] * MM
AMBER_H = SPEC["shell"]["amber_h"] * MM

# ================================================================ 材质
def srgb(hex_value, alpha=1.0):
    v = hex_value.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(v[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, alpha)


PALETTE_ORDER = ["orange", "dark", "grey", "amber", "blue", "visor", "cavity"]
M_ORANGE, M_DARK, M_GREY, M_AMBER, M_BLUE, M_VISOR, M_CAVITY = range(7)


def build_materials():
    mats = []
    for key in PALETTE_ORDER:
        spec = SPEC["materials"][key]
        name = "MAT-" + key.capitalize()
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = srgb(spec["hex"])
        bsdf.inputs["Roughness"].default_value = spec["rough"]
        bsdf.inputs["Metallic"].default_value = 0.0
        try:
            if "emit" in spec:
                bsdf.inputs["Emission Color"].default_value = srgb(spec["emit"])
                bsdf.inputs["Emission Strength"].default_value = spec["emit_strength"]
            else:
                bsdf.inputs["Emission Strength"].default_value = 0.0
        except KeyError:
            pass
        m.diffuse_color = srgb(spec["hex"])
        mats.append(m)
    return mats


# ================================================================ 网格原语
def mesh_from(name, verts, faces, face_mats, mats):
    me = bpy.data.meshes.new("MESH-" + name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate(verbose=False)
    for m in mats:
        me.materials.append(m)
    for poly, mi in zip(me.polygons, face_mats):
        poly.material_index = mi
        poly.use_smooth = False
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return obj


# 横截面轮廓（右半，从屋脊顶顺时针到腹中线）。索引 = 该点之后那一段的编号。
# 参考图分层（scanlines.py）：橙壳到最宽处(zc) → 深灰裙 → 琥珀带(内含) → 深灰 → 腹
def hull_half(w, zb, zc, zt):
    """右半轮廓（从屋脊顶顺时针到腹中线）。索引 = 该点之后那一段的编号。

    ⚠ 琥珀带的位置必须由**截面自身高度**决定，不能只按绝对高度做 clamp：
    尾段截面 zt−zb 只有 0.24 m 时，固定 42 mm 的带会挤到轮廓上相邻顶点
    之间只剩 1 mm，端盖扇形三角随之自交（实测 selfint=12 对）。
    这里的做法：带厚 = min(spec 带厚, 0.60 × (zc − 下裙顶点))，并且只在
    (zc − 下裙顶点) ≥ 0.06 m 时才画带；否则退化为"无带的深灰裙"，
    靠材质整段判断（见 body_seg_mat 的 band 判定）。
    """
    h = zt - zb
    skirt_z = zb + 0.180 * h
    room = zc - skirt_z
    band_top = zc - AMBER_OFFSET
    band_bot = band_top - AMBER_H
    thickness = min(AMBER_H, 0.60 * max(room - AMBER_OFFSET, 0.0))
    band_bot = band_top - thickness
    if room < 0.075 or thickness < 0.022:
        # 完全并入下裙：不留亚毫米缝隙（否则厚度门会抓到 0.8 mm 薄片）
        band_top = band_bot = skirt_z
    return [
        (0.00 * w, zt),                          # 0 屋脊顶
        (0.52 * w, zt - 0.030 * h),              # 1 屋脊侧（棱面加宽：0.30w/5%h 会在
                                                 #   前坡与屋脊交线处留下 1.1 mm 楔形薄片，
                                                 #   厚度门 min_mm 抓到的就是它）
        (0.66 * w, zc + 0.340 * (zt - zc)),      # 2 肩斜
        (0.94 * w, zc + 0.110 * (zt - zc)),      # 3 侧裙上
        (1.00 * w, zc),                          # 4 最宽处 = 橙/灰分界
        (0.965 * w, band_top),                   # 5 琥珀带上沿（内收 3.5%：
                                                 #   与最宽处重合会被自身轮廓挡掉，
                                                 #   3/4 视角下完全看不见 → 实测 sideband 缺失）
        (0.960 * w, band_bot),                   # 6 琥珀带下沿
        (0.90 * w, skirt_z),                     # 7 下裙
        (0.58 * w, zb),                          # 8 腹沿
        (0.00 * w, zb),                          # 9 腹中线
    ]


def loft_y(name, sections, seg_of_face, cap_mat, mats, ring=None):
    """沿 Y 放样（sections 从后 +Y 到前 −Y，必须单调）。"""
    ring = ring or hull_half
    loops = []
    for s in sections:
        half = ring(s["w"], s["zb"], s["zc"], s["zt"])
        loop = [(x, s["y"], z) for (x, z) in half]
        loop += [(-x, s["y"], z) for (x, z) in reversed(half[1:-1])]
        loops.append(loop)
    count = len(loops[0])
    verts = [v for lo in loops for v in lo]
    faces, fmats = [], []
    # 段索引 k 与"截面上的第 k 条边"一一对应（0..count-1），左右对称
    for i in range(len(loops) - 1):
        a0, b0 = i * count, (i + 1) * count
        mid_y = 0.5 * (sections[i]["y"] + sections[i + 1]["y"])
        for k in range(count):
            k2 = (k + 1) % count
            faces.append((a0 + k, a0 + k2, b0 + k2, b0 + k))
            seg = k if k < count // 2 else (count - 1 - k)
            fmats.append(seg_of_face(seg, mid_y))
    for ring_index, rev in ((0, False), (len(loops) - 1, True)):
        off = ring_index * count
        y = sections[ring_index]["y"]
        cz = sum(v[2] for v in loops[ring_index]) / count
        centre = len(verts)
        verts.append((0.0, y, cz))
        for k in range(count):
            k2 = (k + 1) % count
            faces.append((off + k2, off + k, centre) if rev else (off + k, off + k2, centre))
            fmats.append(cap_mat)
    return mesh_from(name, verts, faces, fmats, mats)


# 截面段 → 材质。段 k 是"点 k → 点 k+1"那条边扫出的面。
# 参考图：橙壳覆盖屋脊到最宽处(4)；4→6 是琥珀带；6 以下是深灰裙与腹。
def body_seg_mat(seg, mid_y):
    return {
        0: M_ORANGE,   # 屋脊
        1: M_ORANGE,   # 屋脊侧
        2: M_ORANGE,   # 肩斜
        3: M_ORANGE,   # 侧裙上
        4: M_AMBER,    # 琥珀带（上）
        5: M_AMBER,    # 琥珀带（下）
        6: M_DARK,     # 下裙
        7: M_DARK,     # 腹沿
        8: M_DARK,     # 腹中
    }[seg]


def head_half(w, zb, zc, zt):
    """头部截面：没有琥珀带（参考图头部纯深灰），肩斜更平。

    头部截面矮（h≈0.24 m），套用带琥珀带的 body 轮廓会把带压成零厚度，
    端盖扇形因此自交（实测 selfint=12）。头单独一份轮廓。
    """
    h = zt - zb
    return [
        (0.00 * w, zt),                          # 0 顶
        (0.40 * w, zt - 0.045 * h),              # 1 顶侧
        (0.82 * w, zt - 0.200 * h),              # 2 肩斜
        (0.98 * w, zt - 0.440 * h),              # 3 侧上
        (1.00 * w, zt - 0.520 * h),              # 4 最宽
        (0.99 * w, zt - 0.640 * h),              # 5 侧下
        (0.92 * w, zb + 0.170 * h),              # 6 下裙
        (0.60 * w, zb),                          # 7 腹沿
        (0.00 * w, zb),                          # 8 腹中
    ]


def head_seg_mat_half(seg, mid_y):
    return M_GREY


# 截面：y 从后到前；zc 是橙/灰分界线（= 琥珀带所在高度）。数值来自 spec.json（mm→m）
BODY = [{k: (v * MM if k != "y" else v * MM) for k, v in s.items()} for s in SPEC["sections"]]
HEAD = [{k: (v * MM) for k, v in s.items()} for s in SPEC["head_sections"]]


# ================================================================ 腿
LEGS_Y = {"FR": SPEC["legs"]["y_front"] * MM, "RR": SPEC["legs"]["y_rear"] * MM}
LEG_LEVELS = [(lv["z"] * MM, lv["hx"] * MM, lv["hy"] * MM, lv["cx"] * MM,
               {"dark": M_DARK, "amber": M_AMBER, "orange": M_ORANGE,
                "grey": M_GREY}[lv["mat"]])
              for lv in SPEC["legs"]["levels"]]


def leg_ring(cx, cy, z, hx, hy):
    c = 0.34
    pts = [
        (hx, -hy + c * hy), (hx, hy - c * hy), (hx - c * hx, hy), (-hx + c * hx, hy),
        (-hx, hy - c * hy), (-hx, -hy + c * hy), (-hx + c * hx, -hy), (hx - c * hx, -hy),
    ]
    return [(cx + dx, cy + dy, z) for dx, dy in pts]


def build_leg(name, cy, sign, mats):
    verts, faces, fmats = [], [], []
    n = 8
    for (z, hx, hy, cx, _m) in LEG_LEVELS:
        verts.extend(leg_ring(sign * cx, cy, z, hx, hy))
    for i in range(len(LEG_LEVELS) - 1):
        a0, b0 = i * n, (i + 1) * n
        mat = LEG_LEVELS[i + 1][4]
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((a0 + k, a0 + k2, b0 + k2, b0 + k))
            fmats.append(mat)
    for ring_index, rev in ((0, True), (len(LEG_LEVELS) - 1, False)):
        off = ring_index * n
        z = LEG_LEVELS[ring_index][0]
        centre = len(verts)
        verts.append((sign * LEG_LEVELS[ring_index][3], cy, z))
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((off + k2, off + k, centre) if rev else (off + k, off + k2, centre))
            fmats.append(M_DARK)
    return mesh_from(name, verts, faces, fmats, mats)


# ================================================================ 蓝色发光条
VENT = {"x": SPEC["vents"]["x"] * MM, "half_w": SPEC["vents"]["half_w"] * MM,
        "y0": SPEC["vents"]["y0"] * MM, "y1": SPEC["vents"]["y1"] * MM,
        "depth": SPEC["vents"]["depth"] * MM}


def surface_hits(obj, points, direction, offset):
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(obj, dg)
    out = []
    for p in points:
        loc, nor, idx, dist = bvh.ray_cast(Vector(p), Vector(direction), 50.0)
        if loc is None:
            raise RuntimeError("strip vertex missed body at %s" % (tuple(p),))
        out.append((Vector(loc), Vector(nor)))
    return out


def build_vent_cutters(mats, body_global):
    """两条蓝色发光条：在壳的**前坡**上切两道浅槽，槽底给自发光材质。

    为什么不做"贴片"：贴片要么扎进壳里（buried-true 判真内部面，实测 57 张），
    要么浮在壳外（变成浮空件）。切槽保持**单壳**，槽底就是可见的发光面 ——
    与 visor 同一套做法，也和参考图"蓝色凹槽"的语义一致。

    槽的朝向按坡面法线：每槽用 3×7 网格逐点下打射线取贴合点与该点法线，
    取平均法线作为切刀方向，切刀从外面沿 −法线插进去 depth。
    """
    NU, NV = 3, 7
    x0 = VENT["x"] - VENT["half_w"]
    x1 = VENT["x"] + VENT["half_w"]
    y0, y1 = VENT["y0"], VENT["y1"]
    depth = VENT["depth"]

    objs = []
    for sign in (-1, 1):
        flat = []
        for j in range(NV):
            ty = j / float(NV - 1)
            for i in range(NU):
                tx = i / float(NU - 1)
                flat.append((sign * (x0 + (x1 - x0) * tx),
                             y0 + (y1 - y0) * ty, 6.0))
        hits = surface_hits(body_global, flat, (0.0, 0.0, -1.0), 0.0)
        nrm = Vector((0.0, 0.0, 0.0))
        for _loc, n in hits:
            nrm += n
        nrm.normalize()
        ctr = Vector((0.0, 0.0, 0.0))
        for loc, _n in hits:
            ctr += loc
        ctr /= len(hits)

        # 切刀：沿 nrm 方向的两层四边形（外层在坡面上方 40 mm，内层到 depth）
        u = Vector((1.0, 0.0, 0.0))
        v = nrm.cross(u).normalized()
        u = v.cross(nrm).normalized()
        half_u = (x1 - x0) * 0.5
        half_v = (y1 - y0) * 0.5
        verts = []
        for off in (0.040, -depth):
            for (su, sv) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                verts.append(tuple(ctr + u * (su * half_u) + v * (sv * half_v) + nrm * off))
        faces = [(0, 3, 2, 1),            # 外端盖（朝 −nrm 之外，被布尔吃掉）
                 (4, 5, 6, 7),            # 内端盖 = 槽底 → 自发光
                 (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        fmats = [M_CAVITY, M_BLUE, M_CAVITY, M_CAVITY, M_CAVITY, M_CAVITY]
        objs.append(mesh_from("CUT-Vent-%s" % ("R" if sign > 0 else "L"),
                              verts, faces, fmats, mats))
    return objs


# ================================================================ visor 凹槽
VISOR = {"x": SPEC["visor"]["half_w"] * MM,
         "z0": SPEC["visor"]["z0"] * MM, "z1": SPEC["visor"]["z1"] * MM,
         "depth": SPEC["visor"]["depth"] * MM}


def head_front_y(mats):
    """头部最前端 y（取 HEAD 最后一个截面），凹槽从这里往里切。"""
    return HEAD[-1]["y"]


def build_visor_cutter(mats):
    """从头部前端面往里切一个扁平凹槽。

    切刀必须**穿过**前端面：起点 y 比前端面再外 40 mm，终点往里 depth。
    槽底（+Y 面）给自发光材质 —— 它才是可见的"眼睛"。
    """
    x, z0, z1 = VISOR["x"], VISOR["z0"], VISOR["z1"]
    y0 = head_front_y(mats) - 0.040           # 起点在头外面
    y1 = y0 + 0.040 + VISOR["depth"]          # 终点 = 前端面 + depth
    verts = [
        (-x, y0, z0), (x, y0, z0), (x, y0, z1), (-x, y0, z1),
        (-x, y1, z0), (x, y1, z0), (x, y1, z1), (-x, y1, z1),
    ]
    # 面序：前(−Y)、后(+Y=槽底)、下、上、−X、+X
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
             (3, 0, 4, 7), (1, 2, 6, 5)]
    fmats = [M_CAVITY, M_VISOR, M_CAVITY, M_CAVITY, M_CAVITY, M_CAVITY]
    return mesh_from("CUT-Visor", verts, faces, fmats, mats)


# ================================================================ 布尔
def select_only(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]


def boolean_apply(target, operands, operation):
    """布尔 apply。

    solver 用 MANIFOLD（Blender 5.2 新增）：实测在 body∪head 上
      EXACT  → 空网格（共面处退化，v=0）
      MANIFOLD → 1 壳、0 开边、0 非流形（v=588 / f=507）
    FLOAT 也能出结果但可能残留自交；MANIFOLD 要求输入是闭合流形，本脚本的
    原语都满足。若某次调用失败（非闭合输入），退回 FLOAT 并打印告警。
    """
    for o in operands:
        md = target.modifiers.new("bool_" + o.name, "BOOLEAN")
        md.operation = operation
        md.object = o
        md.solver = "MANIFOLD"
        md.material_mode = "TRANSFER"
        select_only([target])
        try:
            bpy.ops.object.modifier_apply(modifier=md.name)
        except RuntimeError as exc:
            print("[build] WARN MANIFOLD 失败(%s)，退回 FLOAT: %s" % (o.name, exc))
            md = target.modifiers.new("bool_" + o.name + "_f", "BOOLEAN")
            md.operation = operation
            md.object = o
            md.solver = "FLOAT"
            md.material_mode = "TRANSFER"
            select_only([target])
            bpy.ops.object.modifier_apply(modifier=md.name)
        if len(target.data.vertices) < 20:
            print("[build] ERROR 布尔后网格几乎为空（%d 顶点），operand=%s"
                  % (len(target.data.vertices), o.name))
    for o in operands:
        bpy.data.objects.remove(o, do_unlink=True)


def normalize_slots(obj, mats):
    me = obj.data
    per_face = []
    for p in me.polygons:
        mat = me.materials[p.material_index] if p.material_index < len(me.materials) else None
        per_face.append(mat)
    used = []
    for mat in per_face:
        if mat is not None and mat not in used:
            used.append(mat)
    order = [m for m in mats if m in used]
    order += [m for m in used if m not in order]
    me.materials.clear()
    for m in order:
        me.materials.append(m)
    index = {m: i for i, m in enumerate(order)}
    fallback = index.get(mats[M_DARK], 0)
    for p, mat in zip(me.polygons, per_face):
        p.material_index = index.get(mat, fallback)
    print("[build] slots: %s" % ", ".join(m.name for m in me.materials))


def clean(obj, dist=2e-5):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    for p in me.polygons:
        p.use_smooth = False


# ================================================================ UV
_BUCKET_PROJ = [
    lambda p: (-p.y, p.z),
    lambda p: (p.y, p.z),
    lambda p: (p.x, p.z),
    lambda p: (-p.x, p.z),
    lambda p: (p.x, p.y),
    lambda p: (p.x, -p.y),
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


def unwrap_uv(obj, pad=0.004):
    me = obj.data
    if me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    uvl = me.uv_layers.new(name="UVMap")
    buckets = [_bucket_of(p.normal) for p in me.polygons]
    islands = _split_islands(me, buckets)

    data = []
    for comp in islands:
        proj = _BUCKET_PROJ[buckets[comp[0]]]
        pts_per_face, area3, area2 = [], 0.0, 0.0
        for fi in comp:
            poly = me.polygons[fi]
            pts = [proj(me.vertices[me.loops[li].vertex_index].co) for li in poly.loop_indices]
            pts_per_face.append((fi, pts))
            area3 += poly.area
            area2 += abs(_poly_area2(pts))
        xs = [p[0] for _, pts in pts_per_face for p in pts]
        ys = [p[1] for _, pts in pts_per_face for p in pts]
        minx, miny = min(xs), min(ys)
        w, h = max(xs) - minx, max(ys) - miny
        scale = math.sqrt(area3 / area2) if area2 > 1e-12 else 1.0
        data.append({"faces": pts_per_face, "minx": minx, "miny": miny,
                     "w": max(w * scale, 1e-9), "h": max(h * scale, 1e-9), "scale": scale})

    lo, hi, best = 1e-6, 4.0, None
    for _ in range(48):
        mid = 0.5 * (lo + hi)
        rects = [(d["w"] * mid, d["h"] * mid) for d in data]
        pos = _shelf_pack(rects, pad)
        if pos is None:
            hi = mid
        else:
            lo, best = mid, pos
    if best is None:
        raise RuntimeError("UV 装箱失败：岛数 %d" % len(data))

    for d, (px, py) in zip(data, best):
        s = d["scale"] * lo
        for fi, pts in d["faces"]:
            poly = me.polygons[fi]
            for li, (u, v) in zip(poly.loop_indices, pts):
                uvl.data[li].uv = (px + (u - d["minx"]) * s, py + (v - d["miny"]) * s)
    uvl.active_render = True
    me.update()
    print("[build] uv: %d islands / %d faces / k=%.5f" % (len(data), len(me.polygons), lo))


# ================================================================ 贴图
def base_color_of(mat):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    return tuple(bsdf.inputs["Base Color"].default_value)[:3]


def _fill_tri(px, filled, tri, colour, size):
    xs = [p[0] for p in tri]
    ys = [p[1] for p in tri]
    x0 = max(0, int(math.floor(min(xs))))
    x1 = min(size - 1, int(math.ceil(max(xs))))
    y0 = max(0, int(math.floor(min(ys))))
    y1 = min(size - 1, int(math.ceil(max(ys))))
    if x1 < x0 or y1 < y0:
        return
    (ax, ay), (bx, by), (cx, cy) = tri
    den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(den) < 1e-12:
        return
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
    w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
    w2 = 1.0 - w0 - w1
    mask = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
    if not mask.any():
        return
    px[y0:y1 + 1, x0:x1 + 1][mask] = colour
    filled[y0:y1 + 1, x0:x1 + 1] |= mask


def make_texture(obj, size=1024):
    me = obj.data
    uvl = me.uv_layers[0]
    px = np.zeros((size, size, 3), np.float32)
    filled = np.zeros((size, size), bool)
    for poly in me.polygons:
        mat = me.materials[poly.material_index]
        colour = base_color_of(mat)
        pts = [(uvl.data[li].uv[0] * size, uvl.data[li].uv[1] * size) for li in poly.loop_indices]
        for i in range(1, len(pts) - 1):
            _fill_tri(px, filled, [pts[0], pts[i], pts[i + 1]], colour, size)
    for _ in range(8):
        empty = ~filled
        if not empty.any():
            break
        acc = np.zeros_like(px)
        cnt = np.zeros((size, size), np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sf = np.zeros_like(filled)
            sp = np.zeros_like(px)
            ys_from = slice(max(0, dy), size + min(0, dy))
            xs_from = slice(max(0, dx), size + min(0, dx))
            ys_to = slice(max(0, -dy), size + min(0, -dy))
            xs_to = slice(max(0, -dx), size + min(0, -dx))
            sf[ys_to, xs_to] = filled[ys_from, xs_from]
            sp[ys_to, xs_to] = px[ys_from, xs_from]
            acc += sp * sf[:, :, None]
            cnt += sf
        grow = empty & (cnt > 0)
        px[grow] = acc[grow] / cnt[grow][:, None]
        filled |= grow

    img = bpy.data.images.new("TEX-BaseColor", size, size, alpha=False)
    img.colorspace_settings.name = "sRGB"
    rgba = np.ones((size, size, 4), np.float32)
    rgba[:, :, :3] = px
    img.pixels = rgba.ravel().tolist()
    path = os.path.join(EXPORT, TEX_NAME)
    img.filepath_raw = path
    img.file_format = "JPEG"
    img.save()
    bpy.data.images.remove(img)
    img = bpy.data.images.load(path)
    img.name = "TEX-BaseColor"
    img.pack()
    print("[build] texture -> %s (coverage %.1f%%)" % (path, filled.mean() * 100))
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
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "UVMap"
        uvn.location = (-820, 120)
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.location = (-600, 120)
        tex.extension = "EXTEND"
        nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])


# ================================================================ 导出
def export_unity_fbx(obj, out_path):
    select_only([obj])
    bpy.ops.export_scene.fbx(
        filepath=out_path, use_selection=True, object_types={"MESH"},
        axis_forward="-Z", axis_up="Y", apply_scale_options="FBX_SCALE_ALL",
        apply_unit_scale=True, bake_anim=False, add_leaf_bones=False,
        mesh_smooth_type="FACE", use_mesh_modifiers=True, use_tspace=False,
        path_mode="AUTO", embed_textures=False,
    )
    print("[build] fbx -> %s" % out_path)


# ================================================================ 场景
def setup_scene():
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"
    sc.render.resolution_x = RES
    sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.film_transparent = False
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        sc.render.engine = "CYCLES"
        sc.cycles.samples = 64
    if hasattr(sc, "eevee") and hasattr(sc.eevee, "taa_render_samples"):
        sc.eevee.taa_render_samples = 96
    try:
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
    except Exception:
        pass


def setup_studio(mats):
    sc = bpy.context.scene
    world = bpy.data.worlds.new("WORLD-Crawler")
    world.use_nodes = True
    sc.world = world
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = srgb("#777776")
    bg.inputs["Strength"].default_value = 1.0

    me = bpy.data.meshes.new("GROUND")
    s = 30.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new("ENV-Ground", me)
    bpy.context.scene.collection.objects.link(ground)
    gm = bpy.data.materials.new("MAT-Ground")
    gm.use_nodes = True
    gb = gm.node_tree.nodes.get("Principled BSDF")
    gb.inputs["Base Color"].default_value = srgb("#7B7B7A")
    gb.inputs["Roughness"].default_value = 0.9
    me.materials.append(gm)

    def add_area(name, loc, energy, size, colour):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = srgb(colour)[:3]
        obj = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (Vector((0, 0, 0.6)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return obj

    add_area("LIGHT-Key", (-4.2, -3.2, 5.0), 1100.0, 5.0, "#FFF4E8")
    add_area("LIGHT-Fill", (4.6, -2.0, 2.6), 320.0, 6.0, "#DEE9FF")
    add_area("LIGHT-Rim", (-1.4, 4.6, 3.8), 320.0, 4.0, "#FFE9D2")

    cd = bpy.data.cameras.new("CAM-Hero")
    cd.lens = 85.0
    cd.sensor_width = 36.0
    cam = bpy.data.objects.new("CAM-Hero", cd)
    bpy.context.scene.collection.objects.link(cam)
    sc.camera = cam
    return cam, ground


def place_camera(cam, cfg):
    az, el = math.radians(cfg["az"]), math.radians(cfg["el"])
    target = Vector(cfg["target"])
    d = Vector((-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam.location = target + d * cfg["dist"]
    cam.rotation_euler = (target - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = cfg.get("lens", 85.0)
    cam.data.shift_x = cfg.get("shift_x", 0.0)
    cam.data.shift_y = cfg.get("shift_y", 0.0)
    bpy.context.view_layer.update()


def fit_framing(obj, cam, cfg, res, margin=0.90):
    """解 dist + shift，把模型整体装进画幅（留 margin 边距），并以 bbox 中心对中。

    为什么必须在构建脚本里做：机位来自 refs_out/camera.json（拟合产物），
    它与当前几何尺寸是耦合的；几何一改就可能出画（实测 1254 宽下右侧被切）。
    """
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    tw = th = margin * res

    def bbox_at(dist, sx=0.0, sy=0.0):
        c = dict(cfg)
        c["dist"] = dist
        c["shift_x"] = sx
        c["shift_y"] = sy
        place_camera(cam, c)
        xs, ys = [], []
        for p in pts:
            co = world_to_camera_view(sc, cam, p)
            xs.append(co.x * res)
            ys.append((1.0 - co.y) * res)
        return min(xs), max(xs), min(ys), max(ys)

    lo, hi = 0.3, 120.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        x0, x1, y0, y1 = bbox_at(mid, cfg.get("shift_x", 0.0), cfg.get("shift_y", 0.0))
        if max(x1 - x0, y1 - y0) > max(tw, th):
            lo = mid
        else:
            hi = mid
    cfg["dist"] = 0.5 * (lo + hi)
    x0, x1, y0, y1 = bbox_at(cfg["dist"], cfg.get("shift_x", 0.0), cfg.get("shift_y", 0.0))
    cfg["shift_x"] = cfg.get("shift_x", 0.0) + (0.5 * res - 0.5 * (x0 + x1)) / res
    cfg["shift_y"] = cfg.get("shift_y", 0.0) - (0.5 * res - 0.5 * (y0 + y1)) / res
    x0, x1, y0, y1 = bbox_at(cfg["dist"], cfg["shift_x"], cfg["shift_y"])
    place_camera(cam, cfg)
    print("[build] framing: dist=%.3f shift=(%.4f,%.4f) bbox x[%.0f,%.0f] y[%.0f,%.0f] of %d"
          % (cfg["dist"], cfg["shift_x"], cfg["shift_y"], x0, x1, y0, y1, res))
    return cfg


# ================================================================ 主流程
def build_all():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    setup_scene()
    mats = build_materials()

    body = loft_y("GEO-Body", BODY, body_seg_mat, M_ORANGE, mats)
    head = loft_y("GEO-Head", HEAD, head_seg_mat_half, M_GREY, mats, ring=head_half)
    legs = []
    for name, cy in LEGS_Y.items():
        for sign, tag in ((1, "R"), (-1, "L")):
            legs.append(build_leg("GEO-Leg-%s-%s" % (name, tag), cy, sign, mats))
    # 蓝条 = 壳前坡上的两道浅槽（槽底自发光），与 visor 同一套做法 → 单壳
    vents = build_vent_cutters(mats, body)

    boolean_apply(body, legs + [head], "UNION")
    clean(body)

    cutter = build_visor_cutter(mats)
    boolean_apply(body, [cutter] + vents, "DIFFERENCE")
    clean(body)

    body.name = "GEO-Enemy-Crawler"
    body.data.name = "MESH-Enemy-Crawler"
    normalize_slots(body, mats)

    unwrap_uv(body)
    img = make_texture(body, 1024)
    wire_texture(body, img)

    cam, ground = setup_studio(mats)
    cfg = {"az": 55.0, "el": 24.0, "dist": 4.6, "lens": 85.0,
           "target": [0.0, -0.06, 0.62], "shift_x": 0.0, "shift_y": 0.0}
    cam_path = os.path.join(REFS, "camera.json")
    if os.path.exists(cam_path):
        with open(cam_path, "r", encoding="utf-8") as fh:
            cfg.update({k: v for k, v in json.load(fh).items() if k in cfg})
        print("[build] camera from camera.json: %s" % cfg)
    place_camera(cam, cfg)

    mw = body.matrix_world
    pts = [mw @ v.co for v in body.data.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    print("[build] AABB min=%s max=%s size=%s" % (
        [round(v, 4) for v in mn], [round(v, 4) for v in mx],
        [round(v, 4) for v in (mx - mn)]))
    print("[build] verts=%d faces=%d tris=%d" % (len(body.data.vertices),
                                                 len(body.data.polygons), tris))

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    print("[build] saved %s" % BLEND_PATH)

    export_unity_fbx(body, os.path.join(EXPORT, "Modle_Enemy_Crawler.fbx"))
    select_only([body])
    bpy.ops.export_scene.gltf(filepath=os.path.join(EXPORT, "crawler.glb"),
                              export_format="GLB", use_selection=True, export_apply=True)
    return body, cam, ground, cfg


def main():
    if STAGE in ("build", "all"):
        body, cam, ground, cfg = build_all()
    else:
        bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)
        body = bpy.data.objects["GEO-Enemy-Crawler"]
        cam = bpy.data.objects["CAM-Hero"]
        ground = bpy.data.objects.get("ENV-Ground")
        cfg = {"az": 55.0, "el": 24.0, "dist": 4.6, "lens": 85.0, "target": [0, -0.06, 0.62]}
        cam_path = os.path.join(REFS, "camera.json")
        if os.path.exists(cam_path):
            with open(cam_path, "r", encoding="utf-8") as fh:
                cfg.update({k: v for k, v in json.load(fh).items() if k in cfg})

    if STAGE in ("render", "all"):
        sc = bpy.context.scene
        # ★ stage=render 会打开已存的 .blend，其中保存的 1254×1254 会盖掉 res 参数。
        #   不显式重设 → 小分辨率渲染时模型被画幅裁切，量测出的 H/L 全是错的
        #   （实测裁到 1254 宽后 H/L 从 0.760 虚高到 0.894）。
        sc.render.resolution_x = sc.render.resolution_y = RES
        sc.render.resolution_percentage = 100
        cfg = fit_framing(body, cam, cfg, RES, margin=0.90)
        place_camera(cam, cfg)
        if ground:
            ground.hide_render = False
        sc.render.film_transparent = False
        sc.render.image_settings.color_mode = "RGB"
        sc.render.filepath = os.path.join(RENDERS, "hero.png")
        bpy.ops.render.render(write_still=True)
        print("[build] hero -> %s" % sc.render.filepath)

        if ground:
            ground.hide_render = True
        sc.render.film_transparent = True
        sc.render.image_settings.color_mode = "RGBA"
        sc.render.filepath = os.path.join(RENDERS, "silhouette.png")
        bpy.ops.render.render(write_still=True)
        print("[build] silhouette -> %s" % sc.render.filepath)
        if ground:
            ground.hide_render = False
        sc.render.film_transparent = False
        sc.render.image_settings.color_mode = "RGB"

        for name, az, el in (("view_front", 0.0, 8.0), ("view_left", 90.0, 8.0),
                             ("view_rear34", 150.0, 20.0), ("view_top", 55.0, 62.0)):
            c2 = dict(cfg)
            c2.update({"az": az, "el": el, "shift_x": 0.0, "shift_y": 0.0})
            place_camera(cam, c2)
            sc.render.filepath = os.path.join(RENDERS, name + ".png")
            bpy.ops.render.render(write_still=True)
            print("[build] %s -> %s" % (name, sc.render.filepath))
        place_camera(cam, cfg)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

    print("[build] done")


if __name__ == "__main__":
    main()
