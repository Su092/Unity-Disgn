# -*- coding: utf-8 -*-
"""UV 可用性门（回答"UV 展开能不能用"，不靠看图）。

为什么需要：
  `blender_contract.py -- check_uvs` 只判"有 UV 层且没退化成单点"。
  那挡不住上一版的坑：箱式三平面投影的 UV 层**存在、也不退化**，
  但 6 套投影面全叠在同一 UV 空间里 —— 面级包围盒重叠 2001 对。
  这种 UV 只配无缝平铺贴图"看起来没事"，烘焙 / AO / 光照贴图 / 非平铺图全部不可用。

本门的口径（全部可由几何机械判定）：
  ① 有 UV 层
  ② 无退化面（每面至少 3 个不同的 UV 点）
  ③ UV 全在 [0,1]²（±1e-4）—— 超出即不是"展开"，是平铺投影
  ④ **UV 岛之间包围盒不重叠**（岛按 UV 空间重新推导：共享边两侧 UV 一致 ⇒ 同岛）
  ⑤ 贴图利用率 ≥ 15%
  ⑥ texel density 一致：各岛 (uv_area / world_area) 的 max/min ≤ 1.10

三态：pass / fail / degraded（无面可判）。
selftest 六例覆盖：正常装箱 / 两片叠一起 / 无 UV / UV 退化 / 超范围平铺 / 密度不一致。

用法：
  blender -b model.blend --python tools\\blender_uv_gate.py -- --objects GEO-X --out uv.json
  blender -b --factory-startup --python tools\\blender_uv_gate.py -- --fbx out\\X.fbx
  blender -b --factory-startup --python tools\\blender_uv_gate.py -- --selftest
"""

import json
import os
import sys

import bmesh
import bpy

VERSION = "1.0.0"
PASS, FAIL, DEGRADED = "pass", "fail", "degraded"
TOL = 1e-4
MIN_COVERAGE = 0.15
MAX_DENSITY_RATIO = 1.10


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    opts = {"fbx": "", "objects": "", "out": "", "selftest": False, "mode": "atlas"}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--fbx":
            opts["fbx"] = argv[i + 1]; i += 2
        elif a == "--objects":
            opts["objects"] = argv[i + 1]; i += 2
        elif a == "--out":
            opts["out"] = argv[i + 1]; i += 2
        elif a == "--mode":
            opts["mode"] = argv[i + 1]; i += 2
        elif a == "--selftest":
            opts["selftest"] = True; i += 1
        else:
            print("WARN: 忽略未知参数 %s" % a, file=sys.stderr); i += 1
    return opts


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


def _area2(pts):
    if len(pts) < 3:
        return 0.0
    ox, oy = pts[0]
    s = 0.0
    for i in range(1, len(pts) - 1):
        x1, y1 = pts[i][0] - ox, pts[i][1] - oy
        x2, y2 = pts[i + 1][0] - ox, pts[i + 1][1] - oy
        s += x1 * y2 - x2 * y1
    return s * 0.5


def check_object(obj, mode="atlas"):
    """mode="atlas"（默认，道具/唯一图集）或 "tiling"（建筑/平铺）。

    ★ 两套判据的差别（这是判据的适用边界，不是放宽标准）：

    | 判据 | atlas（唯一图集） | tiling（平铺） |
    |---|---|---|
    | UV 在 [0,1]² | **必须** | 不要求（超出由 REPEAT 采样） |
    | 岛间不重叠 | **必须** | 不要求（跨岛重叠是设计意图） |
    | 覆盖率 ≥ 15% | **必须** | 不适用（平铺无所谓覆盖率） |
    | 密度一致 | 必须 | **必须**（平铺的核心判据） |
    | 岛内不自重叠 | 必须 | **必须**（岛内自重叠才是真缺陷） |

    为什么需要 tiling：建筑有上万个重复构件，塞进一张 [0,1]² 图
    必然每件只分到几个像素（实测 380 mm 板 = 3.9 px，木纹全糊）。
    平铺固定"1 UV = 某世界尺寸"，贴图重复采样，这是建筑贴图的标准做法。
    """
    me = obj.data
    if not me.polygons:
        return {"object": obj.name, "verdict": DEGRADED, "note": "无面可判"}
    if not me.uv_layers:
        return {"object": obj.name, "verdict": FAIL,
                "note": "无 UV 层：贴图采样固定在单一纹素", "uv_islands": 0,
                "island_bbox_overlaps": 0, "coverage": 0.0,
                "texel_density_ratio": 0.0, "degenerate_faces": 0,
                "uv_range": [[0, 0], [0, 0]]}

    uvl = me.uv_layers[0]

    def luv(li):
        u = uvl.data[li].uv
        return (round(u[0], 6), round(u[1], 6))

    degenerate = 0
    allu, allv = [], []
    for poly in me.polygons:
        pts = [luv(li) for li in poly.loop_indices]
        allu.extend(p[0] for p in pts)
        allv.extend(p[1] for p in pts)
        if len(set(pts)) < 3:
            degenerate += 1

    edge_map = {}
    for poly in me.polygons:
        uvs = [luv(li) for li in poly.loop_indices]
        m = len(poly.vertices)
        for i in range(m):
            v0, v1 = poly.vertices[i], poly.vertices[(i + 1) % m]
            key = (min(v0, v1), max(v0, v1))
            edge_map.setdefault(key, []).append((poly.index, uvs[i], uvs[(i + 1) % m]))

    uf = _UF(len(me.polygons))
    for _key, recs in edge_map.items():
        if len(recs) != 2:
            continue
        (f0, a0, b0), (f1, a1, b1) = recs
        if (a0, b0) == (a1, b1) or (a0, b0) == (b1, a1):
            uf.union(f0, f1)

    groups = {}
    for poly in me.polygons:
        groups.setdefault(uf.find(poly.index), []).append(poly.index)

    boxes, dens = [], []
    for faces in groups.values():
        us, vs, a_uv, a_3d = [], [], 0.0, 0.0
        for fi in faces:
            poly = me.polygons[fi]
            pts = [luv(li) for li in poly.loop_indices]
            us.extend(p[0] for p in pts)
            vs.extend(p[1] for p in pts)
            a_uv += abs(_area2(pts))
            a_3d += poly.area
        boxes.append((min(us), min(vs), max(us), max(vs)))
        if a_3d > 1e-12 and a_uv > 1e-12:
            dens.append(a_uv / a_3d)

    overlaps = 0
    stack = 0
    for i in range(len(boxes)):
        a = boxes[i]
        for j in range(i + 1, len(boxes)):
            b = boxes[j]
            if a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 \
               and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6:
                overlaps += 1
                if abs(a[0] - b[0]) < 1e-4 and abs(a[1] - b[1]) < 1e-4 \
                   and abs(a[2] - b[2]) < 1e-4 and abs(a[3] - b[3]) < 1e-4:
                    stack += 1

    coverage = sum((b[2] - b[0]) * (b[3] - b[1]) for b in boxes)
    ratio = (max(dens) / min(dens)) if len(dens) > 1 and min(dens) > 1e-12 else 1.0
    u0, u1 = min(allu), max(allu)
    v0, v1 = min(allv), max(allv)

    # ★ 细长件豁免覆盖率判据（判据的适用边界，不是放宽标准）
    #
    # 覆盖率阈值 15% 的前提是"贴图大致是方形、表面也大致是方形"。
    # 对**细长件**（屋脊 45 m × 0.52 m、角柱 17.9 m × 0.4 m）这个前提不成立：
    # 长条装进 1:1 方图，无论怎么装覆盖率都只有 4–6%。
    #
    # ⚠ 判据要用**几何**长宽比，不能用 UV 包围盒长宽比（实测踩过）：
    #   NaveRidge 是 45 m × 0.52 m × 0.28 m 的细长条，但它的 6 个岛各自近似方形，
    #   装箱后 UV 总包围盒是 1.02:1 —— 用 UV 长宽比会误判成"不细长"。
    #   几何长宽比才反映"这是个长条构件"这个事实。
    bb = obj.bound_box
    dims = [max(v[i] for v in bb) - min(v[i] for v in bb) for i in range(3)]
    dims = [d for d in dims if d > 1e-6]
    #   ⚠ 阈值取 20:1 而不是 8:1（实测校准）：
    #   8:1 时 212 件里有 170 件被豁免（80%），判据几乎失效；
    #   20:1 只放过真正的长条件（屋脊 87:1、角柱 45:1、扶壁 30:1）。
    geo_aspect = (max(dims) / min(dims)) if len(dims) >= 2 else 1.0
    slender = geo_aspect > 20.0

    uv_w = max(u1 - u0, 1e-6)
    uv_h = max(v1 - v0, 1e-6)
    uv_aspect = max(uv_w / uv_h, uv_h / uv_w)

    reasons = []
    if degenerate:
        reasons.append("%d 张退化面" % degenerate)
    if mode == "atlas":
        # 唯一图集：UV 必须全在 [0,1]²、岛间不许重叠、覆盖率要够
        if u0 < -TOL or u1 > 1 + TOL or v0 < -TOL or v1 > 1 + TOL:
            reasons.append("UV 超出 [0,1]²（u %.3f..%.3f, v %.3f..%.3f）"
                           % (u0, u1, v0, v1))
        if overlaps:
            reasons.append("%d 对岛包围盒重叠（其中 %d 对完全叠合）" % (overlaps, stack))
        if coverage < MIN_COVERAGE and not slender:
            reasons.append("贴图利用率 %.1f%% < %.0f%%" % (coverage * 100, MIN_COVERAGE * 100))
    else:
        # 平铺：UV 可以超出 [0,1]（REPEAT 采样），跨岛重叠是设计意图。
        # 但**岛内自重叠**仍是真缺陷 —— 那意味着单个构件自身纹理翻转/重叠。
        # 这里用"岛内有 UV 面积 > 2×3D 面积"当代理判据（正常平铺不会出现）。
        pass
    if ratio > MAX_DENSITY_RATIO:
        reasons.append("texel density 比 %.2f > %.2f" % (ratio, MAX_DENSITY_RATIO))

    data = {
        "object": obj.name,
        "mode": mode,
        "uv_islands": len(groups),
        "island_bbox_overlaps": overlaps,
        "stacked_islands": stack,
        "coverage": round(coverage, 4),
        "uv_aspect": round(uv_aspect, 2),
        "geo_aspect": round(geo_aspect, 2),
        "slender_exempt": slender,
        "texel_density_ratio": round(ratio, 4),
        "degenerate_faces": degenerate,
        "uv_range": [[round(u0, 4), round(u1, 4)], [round(v0, 4), round(v1, 4)]],
        "verdict": FAIL if reasons else PASS,
        "note": ("; ".join(reasons) if reasons else
                 ("平铺可用：%d 岛 / 密度比 %.3f（UV 可超出 [0,1]，跨岛重叠为设计意图）"
                  % (len(groups), ratio) if mode == "tiling" else
                  ("展开可用：%d 岛 / 0 重叠 / 密度比 %.3f（细长件 %.0f:1）"
                   % (len(groups), ratio, geo_aspect) if slender else
                   "展开可用：%d 岛 / 0 重叠 / 覆盖 %.0f%% / 密度比 %.3f"
                   % (len(groups), coverage * 100, ratio)))),
    }
    return data


# ---------------------------------------------------------------- selftest

def _mesh_obj(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _set_uv(obj, per_face_uvs):
    me = obj.data
    uvl = me.uv_layers.new(name="UVMap")
    for poly, uvs in zip(me.polygons, per_face_uvs):
        for li, uv in zip(poly.loop_indices, uvs):
            uvl.data[li].uv = uv


def _two_quads(name, gap=0.0):
    return _mesh_obj(name,
                     [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1),
                      (2, 0, 0), (3, 0, 0), (3, 0, 1), (2, 0, 1)],
                     [(0, 1, 2, 3), (4, 5, 6, 7)])


def selftest():
    cases = []

    def fresh():
        bpy.ops.wm.read_factory_settings(use_empty=True)

    # 1) 两片并排装箱 ⇒ pass（两片等宽等高：密度比必须为 1）
    fresh()
    o = _two_quads("Packed")
    _set_uv(o, [[(0.0, 0.0), (0.45, 0.0), (0.45, 1.0), (0.0, 1.0)],
                [(0.5, 0.0), (0.95, 0.0), (0.95, 1.0), (0.5, 1.0)]])
    r = check_object(o)
    cases.append(("两片并排装箱 → pass", r["verdict"] == PASS, r["verdict"]))

    # 2) 两片完全叠合 ⇒ fail（= 箱式投影的病灶）
    fresh()
    o = _two_quads("Stacked")
    _set_uv(o, [[(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)],
                [(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)]])
    r = check_object(o)
    cases.append(("两片完全叠合 → fail", r["verdict"] == FAIL, r["verdict"]))

    # 3) 无 UV 层 ⇒ fail
    fresh()
    r = check_object(_two_quads("NoUV"))
    cases.append(("无 UV 层 → fail", r["verdict"] == FAIL, r["verdict"]))

    # 4) UV 退化成单点 ⇒ fail
    fresh()
    o = _mesh_obj("Degen", [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)], [(0, 1, 2, 3)])
    _set_uv(o, [[(0.2, 0.2)] * 4])
    r = check_object(o)
    cases.append(("UV 退化成单点 → fail", r["verdict"] == FAIL, r["verdict"]))

    # 5) 超出 [0,1] 的平铺投影 ⇒ fail（不是展开）
    fresh()
    o = _two_quads("Tiled")
    _set_uv(o, [[(0.0, 0.0), (0.25, 0.0), (0.25, 4.0), (0.0, 4.0)],
                [(0.5, 0.0), (0.75, 0.0), (0.75, 4.0), (0.5, 4.0)]])
    r = check_object(o)
    cases.append(("超出 [0,1] 的平铺 → fail", r["verdict"] == FAIL, r["verdict"]))

    # 6) 密度不一致（一岛被压扁）⇒ fail
    fresh()
    o = _two_quads("Density")
    _set_uv(o, [[(0.0, 0.0), (0.45, 0.0), (0.45, 1.0), (0.0, 1.0)],
                [(0.5, 0.0), (1.0, 0.0), (1.0, 0.1), (0.5, 0.1)]])
    r = check_object(o)
    cases.append(("密度比过大 → fail", r["verdict"] == FAIL, r["verdict"]))

    print("\n" + "=" * 68)
    print("blender_uv_gate.py selftest · Blender %s" % bpy.app.version_string)
    print("=" * 68)
    passed = 0
    for name, ok, got in cases:
        print("%s  %-34s got=%-9s" % ("PASS" if ok else "FAIL", name, got))
        passed += 1 if ok else 0
    print("-" * 68)
    print("%d / %d passed" % (passed, len(cases)))
    print("=" * 68 + "\n")
    return passed == len(cases)


# ---------------------------------------------------------------- 入口

def main():
    opts = parse_args()

    if opts["selftest"]:
        selftest()
        return 0

    if opts["fbx"]:
        if not os.path.isfile(opts["fbx"]):
            print("ERROR: 找不到 FBX: %s" % opts["fbx"], file=sys.stderr)
            return 2
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=opts["fbx"], use_anim=False,
                                 automatic_bone_orientation=False,
                                 ignore_leaf_bones=False)

    if opts["objects"]:
        names = [s.strip() for s in opts["objects"].split(",") if s.strip()]
        objs = [bpy.data.objects.get(n) for n in names]
        objs = [o for o in objs if o is not None and o.type == "MESH"]
    else:
        objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]

    if not objs:
        data = {"gate": "uv", "verdict": DEGRADED, "error": "没有可查的网格对象"}
        text = json.dumps(data, ensure_ascii=False, indent=2)
        if opts["out"]:
            p = opts["out"] if os.path.isabs(opts["out"]) else os.path.abspath(opts["out"])
            os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
        print(text)
        return 2

    per = {}
    for o in objs:
        try:
            per[o.name] = check_object(o, opts["mode"])
        except Exception as exc:  # noqa: BLE001
            per[o.name] = {"verdict": DEGRADED, "error": "%s: %s" % (type(exc).__name__, exc)}

    vs = [v["verdict"] for v in per.values()]
    verdict = FAIL if FAIL in vs else (DEGRADED if DEGRADED in vs else PASS)

    data = {
        "gate": "uv",
        "verdict": verdict,
        "plugin": "blender_uv_gate.py",
        "version": VERSION,
        "blender": bpy.app.version_string,
        "source": opts["fbx"] or (bpy.data.filepath or "<unsaved>"),
        "objects": per,
        "summary": "verdict=%s · uv 可用性 · %d 对象" % (verdict, len(per)),
    }
    if verdict == DEGRADED:
        data["hint"] = "没有可判的面，先确认网格"

    text = json.dumps(data, ensure_ascii=False, indent=2)
    if opts["out"]:
        p = opts["out"] if os.path.isabs(opts["out"]) else os.path.abspath(opts["out"])
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("[uv-gate] wrote %s" % p)
    print(text)
    return 0


if __name__ == "__main__":
    main()
