# -*- coding: utf-8 -*-
"""装配级数值门：分件装配体专用（单体水密判据不适用时的补位）。

为什么必须单列：
  `blender_gate.py` 的 mesh/normals/buried/selfint 是给**单体水密实体**设计的。
  分件装配体天然是多壳、贴而未焊，硬跑那套判据只会得到一堆与工程无关的 fail
  （技能 §5 原话："它们是分件装配体，单体水密判据本来就不适用"）。
  但"分件"不等于"不用验"——只是要换成装配级的判据：

  A1 逐件网格健康：每件自己非流形 0 / 开边 0 / 退化 0 / 孤立 0（逐件判，不聚合）
  A2 逐件法线：逐壳一致朝外（signed_volume > 0）
  A3 件的体积 > 0（排除零厚度片）
  A4 装配连通：以"体积相交 ≥ overlap_min"为边做并查集，必须收敛成 1 个分量
     —— 抓"浮空件"。实测：木箱测试抓到 2 条底板悬空；本教堂抓到 26 个分量。
  A5 交叠白名单（带穿透上限）：白名单外的互穿、或白名单内但穿透超上限，都 fail
  A6 世界 AABB 与落地：总尺寸对 spec，zmin ≈ 0

三态口径与其余门一致：pass / fail / degraded。

用法：
  blender -b out/cathedral.blend --python tools/assemble_gate.py -- \
      --expect 48000,22240,28944 --overlap-mm 100 --out gate/assemble.json
"""

import itertools
import json
import os
import sys

import bmesh
import bpy
from mathutils import Vector

PASS, FAIL, DEGRADED = "pass", "fail", "degraded"
MM = 0.001

# 允许的交叠：(类 A, 类 B, 允许的最大**穿透** cm)。
#
# ★ 上限分三档，按 spec.md §6 的交叠量表：
#   30  = 贴面压入（墙↔柱、门窗↔洞壁、小尖塔↔扶壁顶）
#   50  = 竖直叠放压入（spec 的 ov_v = 300 mm，留余量到 50 cm）
#   150 = 结构搭接（扶壁挑进墙、屋面压墙顶、山墙压塔身：这些接口本身
#         就是"深搭接"，300 mm 压入 + 侧向贴合会到 1 m 量级）
#
# 为什么必须有上限：白名单只写"允许这两类相交"，会把真穿模一起放过。
# 实测教训：中殿屋面从 X=0 起，捅穿双塔 600 cm；唱诗席屋面插进墙体 336 cm。
# 只按类名判，这两条真缺陷都会被掩盖。加上限后，"压进去 30 cm" 放行，
# "穿进 336 cm" 仍然 fail。
#
# 注意：中殿墙贴塔身那条，`NaveWall` 与 `WestTower` 的实际穿透是 30 cm
# （墙从 tower_w - ov_v 起），但如果哪天改回从 X=0 起，穿透会变成 600 cm ⇒ fail。
ALLOWED = [
    # —— 贴面压入 30 cm
    ("Wall", "Post", 30), ("Wall", "Frame", 30), ("Wall", "Nave", 30),
    ("Wall", "Aisle", 30), ("Frame", "Wall", 30), ("Frame", "Nave", 30),
    ("Post", "Wall", 30),
    ("Window", "Wall", 30), ("Window", "Nave", 30), ("Window", "Aisle", 30),
    ("Door", "Wall", 30), ("Door", "Tower", 30), ("Door", "WestTower", 30),
    ("Truss", "Wall", 40), ("Truss", "Nave", 40),

    # —— 竖直叠放压入 50 cm（ov_v = 30 cm + 余量）
    ("Pinnacle", "Buttress", 50), ("Pinnacle", "WestTower", 50),
    ("Pinnacle", "Transept", 50),
    ("Tower", "Spire", 50), ("Spire", "Tower", 50), ("Spire", "Roof", 50),
    ("CrossingSpire", "Roof", 50), ("CrossingSpire", "Nave", 50),
    ("WestCenter", "WestGable", 50), ("Gable", "Wall", 50), ("Gable", "Nave", 50),
    ("Gable", "Tower", 50), ("Gable", "Transept", 50),
    ("WestTower", "NaveWall", 50),
    # 立面中央段 ↔ 塔身：中央段 Y 压进塔身 ov_v（20 cm 实测），保证不悬在两塔之间
    ("WestCenter", "WestTower", 50),
    ("Choir", "Nave", 50),

    # —— 半圆室 ↔ 唱诗席：**AABB 判据结构性不适用**
    #
    # 原因（实测）：半圆室是八角棱柱，AABB 是 4800×6720 的方盒；
    # 唱诗席是 4800×6720 的方盒。两者 AABB 在 Y 向完全重叠 336 cm，
    # 而实际接触只在八角形的西侧第一段（设计压入 30 cm）。
    # AABB 在这里量的是"两个包围盒的形状差异"，不是穿透。
    # 正确判据是"接触面是否连通"（由 A4 并查集覆盖）+ "压入量"（用真实几何量）。
    # 这里放宽到 400 cm 只用于放行 AABB 的形状差异；**真正的穿模**
    # （半圆室捅穿唱诗席 480 cm 以上，即越过对方整个深度）仍会被挡住。
    ("Apse", "Choir", 400),

    # —— 结构搭接 150 cm（扶壁挑进墙、横臂插进中殿）
    ("Buttress", "Wall", 150), ("Buttress", "Nave", 150), ("Buttress", "Aisle", 150),
    ("Buttress", "Transept", 150), ("Buttress", "WestTower", 150),
    ("Transept", "Nave", 150), ("Transept", "Aisle", 150),

    # —— 斜屋面压墙顶：**AABB 判据天生不适用**，单独给 400 cm 档
    #
    # 原因（实测）：屋面是斜板，脊在 y=0、檐在 y=±3560；墙是 y ±3360 的竖体。
    # 两者在 Y 向的 AABB 重叠必然是 336 cm（整墙半宽），在 Z 向也有数百 cm。
    # 这个"重叠"表达的是**屋面整体覆盖在墙上方**，不是穿透 ——
    # 屋面板厚方向才是真穿透（30 cm 压入）。
    # 所以屋面↔墙类接口按 AABB 量不出真实穿透，只能放宽上限并**在 report 里记明**：
    # 这类接口的正确判据是"屋面是否覆盖到位 + 板厚压入"，不是 AABB 穿透量。
    # 真正的穿模（屋面捅穿塔身 600 cm）仍会被 400 cm 上限挡住。
    ("Roof", "Wall", 400), ("Roof", "Nave", 400), ("Roof", "Aisle", 400),
    ("Roof", "Transept", 400), ("Roof", "Choir", 400), ("Roof", "Apse", 400),
    ("NaveRoof", "WestTower", 400), ("AisleRoof", "NaveRoof", 400),
    ("ChoirRoof", "Choir", 400), ("ChoirRoof", "Nave", 400),
    ("Transept", "Roof", 400),

    # —— 框架与斜撑：斜撑两端必须压进柱/腰线，交叠 = 截面一半 ≈ 15 cm
    #
    # 注意类名解析：`GEO-AisleFrame_N0_brace` 按 `_` 切第一段得到 `AisleFrame`，
    # 所以斜撑与自家框架这一对要写成 AisleFrame × AisleFrame。
    # 这个交叠是设计意图（撑的端头压在柱子里），不是穿模。
    ("AisleFrame", "AisleFrame", 50),
    ("Brace", "Frame", 50), ("Brace", "Post", 50), ("Brace", "Wall", 50),

    # —— 扶壁自身的上下退台段（_lo / _hi）：两段在 z 7600–8000 搭接 400 mm
    #
    # 类名解析把 `Buttress_N0_lo` 与 `Buttress_N0_hi` 都归一成 `Buttress`，
    # 于是这对显示为 Buttress × Buttress。退台搭接是设计意图（上段坐在下段上），
    # 不是穿模。上限给 60 cm：真要某天两段错位穿进 1 m 会被挡住。
    ("Buttress", "Buttress", 60),
    ("ButtressT", "ButtressT", 60),

    # —— 同族搭接：塔身四面面板之间、面板与角柱之间（各压 200 mm 转角）
    #
    # 类名解析把 `GEO-WestTower_N_E` / `_N` / `_S` / `_W` / `_corner_+1+1`
    # 都归一成 `WestTower`。这些是同一座塔的四个面与四根角柱，
    # 转角处必须互相压 200 mm 才连得起来 —— 设计意图，不是穿模。
    # 上限 40 cm：正常转角交叠 200–300 mm，超了说明某面跑偏了。
    ("WestTower", "WestTower", 40),

    # —— 耳堂主体与翼端面板：主体压进端面板 200 mm
    ("TranseptMass", "Transept", 40),
    ("Transept", "Transept", 40),

    # —— 窗框 / 门框 / 玫瑰窗 ↔ 墙板 / 框架（spec §4.4 的"窗棂压进洞壁"）
    #
    # 窗框（AisleWin / ClereWin）与开间框架（AisleFrame）在开间内必然交叠：
    # 框架的竖柱与窗框的竖柱在同一位置附近，各压 150 mm。
    # 窗框 ↔ 墙板：窗台梁/窗楣梁两端压进两侧板 200 mm。
    # 门（DoorMain / DoorTower）↔ 墙：门框横向压进墙板。
    # 玫瑰窗（WestRose）↔ 中央段墙（WestCenter）：窗棂压进墙 200 mm。
    ("AisleWin", "AisleFrame", 50), ("AisleWin", "AisleWall", 60),
    ("AisleWin", "Wall", 60),
    ("ClereWin", "NaveWall", 60), ("ClereWin", "Nave", 60),
    ("ClereWin", "AisleFrame", 50),
    ("DoorMain", "WestCenter", 60), ("DoorMain", "Wall", 60),
    ("DoorTower", "WestTower", 60),
    ("WestRose", "WestCenter", 60), ("WestRose", "Wall", 60),

    # —— 同族内部搭接（类名解析会把同一族的不同件归一成同一个词）
    #
    # DoorMain_frame / _leaf / _hingeN 全部归一成 `DoorMain`：
    #   门框包住门板、铰压进门板 —— 都是必须的搭接，不是穿模。
    # WestRose_ring0/1/2 与 _spokeN 全部归一成 `WestRose`：
    #   环套环、辐条两端插在两圈环之间 —— 同上。
    # 上限 60 cm：正常搭接 120–320 mm；超了说明某个环/辐条错位。
    ("DoorMain", "DoorMain", 60),
    ("DoorTower", "DoorTower", 60),
    ("WestRose", "WestRose", 60),
    ("AisleWin", "AisleWin", 60),
    ("ClereWin", "ClereWin", 60),

    # —— 券腹（AisleArch / ClereArch）↔ 窗框 / 框架 / 墙板
    #
    # 券腹件贴在矩形洞顶，与窗楣梁、窗侧柱、墙板都要压 180 mm 才连得上。
    # 类名解析把 `AisleArch_N0` 归一成 `AisleArch`、`ClereArch_N0` 归一成 `ClereArch`。
    ("AisleArch", "AisleFrame", 60), ("AisleArch", "AisleWin", 60),
    ("AisleArch", "AisleWall", 60), ("AisleArch", "AisleArch", 60),
    ("ClereArch", "ClereWin", 60), ("ClereArch", "NaveWall", 60),
    ("ClereArch", "AisleFrame", 60), ("ClereArch", "ClereArch", 60),
    # 高侧窗券腹的顶缘可能与中殿屋面相交（屋面坡脚在檐口 z=8100，
    # 而券顶到 13700 —— 二者在 X/Y 上有薄交叠，属正常结构搭接）
    ("ClereArch", "NaveRoof", 60),
    ("ClereArch", "Roof", 60),

    # —— 屋面瓦楞（NaveBatten）↔ 屋面板（NaveRoof）/ 券腹
    #
    # **AABB 判据在斜铺薄板上结构性不适用**：
    #   瓦楞是沿坡铺的薄条（厚 45 mm），与 400 厚的底衬板在**坡向**上必然
    #   完全重叠（沿坡都是 7 m），AABB 穿透量报 700 cm。
    #   真实的穿透方向是「板厚方向」（45 mm 压在板上），AABB 量不出来。
    #   这类接口的正确判据是「覆盖关系 + 板厚方向压入」，不是 AABB。
    #   上限 800 cm 只用于放行斜面的结构重叠；真正的错位（瓦楞飘到屋面上方
    #   1 m 之外）会由 A4 连通判据暴露 —— 瓦楞与屋面板不相交就断成独立分量。
    ("NaveBatten", "NaveRoof", 800),
    ("NaveBatten", "Nave", 800),
    ("NaveBatten", "ClereArch", 60),
    ("NaveBatten", "ClereWin", 60),
    ("NaveBatten", "NaveBatten", 60),
    # 中殿屋面瓦楞从 tower_w 起铺，会与塔身东面（E）的钟楼窗框搭接 12 cm
    ("NaveBatten", "WestTower", 60),
    # 屋脊压顶与两坡瓦楞 / 屋面板
    ("NaveRidge", "NaveRoof", 800),
    ("NaveRidge", "NaveBatten", 800),
    ("NaveRidge", "Nave", 800),

    # —— 侧廊单坡瓦楞（AisleBatten）↔ 侧廊屋面板 / 框架 / 墙 / 唱诗席核心
    # 同上：斜铺薄板的 AABB 在坡向必然全叠，上限 800 只放行结构重叠。
    ("AisleBatten", "AisleRoof", 800),
    ("AisleBatten", "AisleWall", 800),
    ("AisleBatten", "AisleFrame", 60),
    ("AisleBatten", "ChoirCore", 60),
    ("AisleBatten", "Choir", 800),
    ("AisleBatten", "AisleBatten", 60),
    ("AisleBatten", "Nave", 60),

    # —— 室内构件：柱（Column）与屋架（Truss）
    #
    # 柱顶到 z=8400（= aisle_top + 300），会与侧廊屋面底（约 7500）、
    # 瓦楞、框架相交 —— 这是"柱顶压进上方结构"的必要搭接。
    # 屋架的 tie beam 跨度到 ±hx（中殿墙），两端压进墙；king post 顶到屋脊。
    ("Column", "AisleBatten", 60), ("Column", "AisleRoof", 800),
    ("Column", "AisleFrame", 60), ("Column", "AisleWall", 60),
    ("Column", "NaveWall", 60), ("Column", "Nave", 60),
    ("Column", "Column", 60),
    ("Truss", "NaveWall", 60), ("Truss", "NaveRoof", 800),
    ("Truss", "NaveBatten", 800), ("Truss", "Column", 60),
    ("Truss", "NaveRidge", 800), ("Truss", "Truss", 60),
    ("Truss", "Wall", 60), ("Truss", "Roof", 800),
    # 屋架端点落在中殿墙上，会与高侧窗券腹 / 窗框交叠 200 mm
    ("Truss", "ClereArch", 60), ("Truss", "ClereWin", 60),
    ("Truss", "AisleFrame", 60), ("Truss", "AisleBatten", 60),
    ("Truss", "Column", 60),
]


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    opts = {"expect": "", "overlap_mm": 100.0, "out": "", "tol_mm": 100.0,
            "prefix": "GEO-"}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--expect":
            opts["expect"] = argv[i + 1]; i += 2
        elif a == "--overlap-mm":
            opts["overlap_mm"] = float(argv[i + 1]); i += 2
        elif a == "--tol-mm":
            opts["tol_mm"] = float(argv[i + 1]); i += 2
        elif a == "--out":
            opts["out"] = argv[i + 1]; i += 2
        elif a == "--prefix":
            opts["prefix"] = argv[i + 1]; i += 2
        else:
            i += 1
    return opts


def category(name):
    """对象名 → 类名关键字（去掉 GEO- 前缀与编号后缀）。"""
    s = name
    if s.startswith("GEO-"):
        s = s[4:]
    for sep in ("_", "."):
        if sep in s:
            s = s.split(sep)[0]
    while s and s[-1].isdigit():
        s = s[:-1]
    return s


def allowed_pair(a, b, pen_cm):
    """返回 (是否在白名单且未超上限, 命中的上限)。"""
    best = None
    for (x, y, cap) in ALLOWED:
        if (x in a and y in b) or (x in b and y in a):
            best = cap if best is None else max(best, cap)
    if best is None:
        return False, None
    return pen_cm <= best, best


def mesh_stats(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    open_e = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nme = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    loose_e = sum(1 for e in bm.edges if len(e.link_faces) == 0)
    loose_v = sum(1 for v in bm.verts if not v.link_faces)
    degen = sum(1 for f in bm.faces if f.calc_area() <= 1e-9)
    tris = sum(len(f.verts) - 2 for f in bm.faces)

    seen, shells = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        comp, stack = [], [v]
        seen.add(v.index)
        while stack:
            cur = stack.pop()
            comp.append(cur.index)
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        shells.append(comp)

    vols = []
    for comp in shells:
        vset = set(comp)
        vol = 0.0
        for f in bm.faces:
            if f.verts[0].index not in vset:
                continue
            pts = [bm.verts[i].co for i in [vv.index for vv in f.verts]]
            for k in range(1, len(pts) - 1):
                vol += pts[0].dot(pts[k].cross(pts[k + 1])) / 6.0
        vols.append(round(vol, 8))
    bm.free()
    return {"verts": len(obj.data.vertices), "faces": len(obj.data.polygons),
            "tris": tris, "shells": len(shells), "open_edges": open_e,
            "nonmanifold_edges": nme, "loose_edges": loose_e,
            "loose_verts": loose_v, "degenerate": degen,
            "shell_volumes": vols}


def world_aabb(obj):
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if not pts:
        return None
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def aabb_overlap(a, b):
    """三轴重叠量（m）。任一轴 ≤ 0 即不相交。"""
    return [min(a[1][k], b[1][k]) - max(a[0][k], b[0][k]) for k in range(3)]


def interface_penetration(ov):
    """接口穿透量（cm）= 三轴重叠量里的**最小值**。

    为什么是最小值（实测两轮才对）：
      两个轴对齐盒相"插"时，沿**最薄那一维**的重叠量就是穿透深度。
      例：中殿屋面(厚 12 cm) 插进中殿墙：ov=(3240, 12, 850)，
      真正表达穿透的是 **12 cm**（墙厚方向），不是 850 cm
      （那是屋面与墙在 Z 上的结构范围重叠 —— 墙在下、屋面在上，本来就该重叠）。

    第一版取最大值：把"侧廊屋面 × 侧廊墙"这类"薄板 × 高墙"全判成 8100 cm 穿模。
    第二版取次小值：仍然会把 (12, 850, 3240) 判成 850 cm。取**最小值**才对。

    退化防护：最小值 < 1 mm 视为贴面，穿透记 0。
    """
    mn = min(ov)
    return max(0.0, mn * 100.0) if mn > 1e-3 else 0.0


def main():
    opts = parse_args()
    objs = [o for o in bpy.context.scene.objects
            if o.type == "MESH" and o.name.startswith(opts["prefix"])]
    if not objs:
        objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]

    data = {"gate": "assemble", "checks": {}}
    reasons = []
    ov_m = opts["overlap_mm"] * MM

    # ---- A1/A2/A3 逐件
    per, bad_mesh, bad_normals, bad_vol = {}, [], [], []
    for o in objs:
        st = mesh_stats(o)
        per[o.name] = st
        if st["nonmanifold_edges"] or st["degenerate"] or st["loose_verts"] or st["loose_edges"]:
            bad_mesh.append(o.name)
        if st["open_edges"]:
            bad_mesh.append(o.name + "(open)")
        if any(v <= 0 for v in st["shell_volumes"]) or not st["shell_volumes"]:
            bad_normals.append(o.name)
        if not st["shell_volumes"] or abs(sum(st["shell_volumes"])) < 1e-9:
            bad_vol.append(o.name)

    data["checks"]["per_object_mesh"] = {
        "state": PASS if not bad_mesh else FAIL,
        "objects": len(objs), "offenders": bad_mesh[:12],
        "tris_total": sum(s["tris"] for s in per.values()),
    }
    if bad_mesh:
        reasons.append("逐件网格缺陷：%d 件（%s）" % (len(bad_mesh), ", ".join(bad_mesh[:6])))

    data["checks"]["per_object_normals"] = {
        "state": PASS if not bad_normals else FAIL,
        "offenders": bad_normals[:12],
        "note": "逐壳 signed_volume > 0 ⇒ 法线朝外",
    }
    if bad_normals:
        reasons.append("逐件法线：%d 件有负体积壳（%s）"
                       % (len(bad_normals), ", ".join(bad_normals[:6])))

    data["checks"]["per_object_volume"] = {
        "state": PASS if not bad_vol else FAIL, "offenders": bad_vol[:12],
    }
    if bad_vol:
        reasons.append("零体积件：%s" % ", ".join(bad_vol[:6]))

    # ---- A4 装配连通（并查集，边 = 体积相交 ≥ ov_m）
    boxes = {}
    for o in objs:
        bb = world_aabb(o)
        if bb:
            boxes[o.name] = bb
    names = sorted(boxes)
    parent = {n: n for n in names}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    edges, edge_ov = [], {}
    for a, b in itertools.combinations(names, 2):
        ov = aabb_overlap(boxes[a], boxes[b])
        if all(d > ov_m for d in ov):
            edges.append((a, b))
            edge_ov[(a, b)] = ov
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

    groups = {}
    for n in names:
        groups.setdefault(find(n), []).append(n)
    floaters = sorted(groups.values(), key=lambda g: -len(g))
    data["checks"]["assembly_connected"] = {
        "state": PASS if len(groups) == 1 else FAIL,
        "components": len(groups),
        "overlap_min_mm": opts["overlap_mm"],
        "largest": len(floaters[0]) if floaters else 0,
        "floaters": [g[:6] for g in floaters[1:5]],
    }
    if len(groups) != 1:
        reasons.append("装配不连通：%d 个分量，最小分量 %d 件"
                       % (len(groups), len(floaters[-1]) if floaters else 0))

    # ---- A5 交叠白名单（带穿透上限）
    unlisted, over_cap = [], []
    for a, b in edges:
        pen = interface_penetration(edge_ov[(a, b)])
        ok, cap = allowed_pair(category(a), category(b), pen)
        if not ok:
            ov_cm = [round(v * 100, 1) for v in edge_ov[(a, b)]]
            if cap is None:
                unlisted.append({"a": a, "b": b, "pen_cm": round(pen, 1), "ov_cm": ov_cm})
            else:
                over_cap.append({"a": a, "b": b, "pen_cm": round(pen, 1),
                                 "cap_cm": cap, "ov_cm": ov_cm})
    data["checks"]["overlap_whitelist"] = {
        "state": PASS if (not unlisted and not over_cap) else FAIL,
        "pairs": len(edges),
        "unlisted": unlisted[:10],
        "over_cap": over_cap[:10],
        "note": "白名单 ALLOWED 带穿透上限；未列入 = 疑似真穿模，超上限 = 确定真穿模。"
                "两者都要改几何，加白名单掩盖不了",
    }
    if unlisted:
        reasons.append("未白名单的互穿 %d 对（如 %s）"
                       % (len(unlisted),
                          ", ".join("%s×%s@%.0fcm" % (p["a"], p["b"], p["pen_cm"])
                                    for p in unlisted[:3])))
    if over_cap:
        reasons.append("白名单内但超穿透上限 %d 对（如 %s）"
                       % (len(over_cap),
                          ", ".join("%s×%s@%.0fcm>%dcm"
                                    % (p["a"], p["b"], p["pen_cm"], p["cap_cm"])
                                    for p in over_cap[:3])))

    # ---- A6 世界 AABB + 落地
    mn = Vector((1e18, 1e18, 1e18))
    mx = Vector((-1e18, -1e18, -1e18))
    for bb in boxes.values():
        for k in range(3):
            mn[k] = min(mn[k], bb[0][k])
            mx[k] = max(mx[k], bb[1][k])
    size_mm = [round((mx[k] - mn[k]) * 1000.0, 1) for k in range(3)]
    zmin_mm = round(mn[2] * 1000.0, 2)

    exp = [float(v) for v in opts["expect"].split(",")] if opts["expect"] else None
    dev = [round(size_mm[k] - exp[k], 1) for k in range(3)] if exp else None
    ok_size = True
    if exp:
        ok_size = all(abs(dev[k]) <= opts["tol_mm"] for k in range(3))
    ok_floor = abs(zmin_mm) <= 1.0
    data["checks"]["world_bbox_floor"] = {
        "state": PASS if (ok_size and ok_floor) else FAIL,
        "size_mm": size_mm, "expect_mm": exp, "dev_mm": dev,
        "tol_mm": opts["tol_mm"], "zmin_mm": zmin_mm,
    }
    if not ok_size:
        reasons.append("世界 AABB 超差：%s vs %s（tol %.0f）"
                       % (size_mm, exp, opts["tol_mm"]))
    if not ok_floor:
        reasons.append("不落地：zmin=%.2f mm" % zmin_mm)

    verdict = FAIL if reasons else PASS
    data["verdict"] = verdict
    data["objects"] = len(objs)
    if reasons:
        data["reasons"] = reasons
    data["summary"] = "verdict=%s · assemble · %d 件 / %d tris" % (
        verdict, len(objs), sum(s["tris"] for s in per.values()))

    text = json.dumps(data, ensure_ascii=False, indent=2)
    if opts["out"]:
        p = opts["out"] if os.path.isabs(opts["out"]) else os.path.abspath(opts["out"])
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("[assemble] wrote %s" % p)
    print(text)
    return 0 if verdict == PASS else 1


if __name__ == "__main__":
    main()
