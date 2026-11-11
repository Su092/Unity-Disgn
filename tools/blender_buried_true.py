# -*- coding: utf-8 -*-
"""真·内部面门（buried 的独立复核通路）。

为什么需要：
  `blender_gate.py -- buried` 用的是启发式——"从面中心沿外法线打射线，
  命中别的几何就算埋住"。它把**凹腔与被遮挡的可见面**一并判成 buried：
  底座肩部朝上被柱身挡住、灯座托盘上表面朝上被屋顶挡住、灯笼竖梃内侧朝向
  对面竖梃……这些面都看得见，不是内部面。

  而且数学上：**闭合流形的单壳网格不可能含内部面**——每个面都在体积边界上。
  所以 buried>0 在单壳闭合网格上恒为"遮挡"，不是缺陷。

本门用正交判据：面中心沿法线外移 eps 后，该点**是否落在实体体积内**。
落在体积内 ⇒ 这个面的外面是实心 ⇒ 真内部面（法线朝内或壳体互相埋入）。
判定用射线奇偶（向 3 个不共面方向各打一次，取多数票，避免擦边）。

三态口径与其余门一致：pass / fail / degraded。
selftest 四例证明它真能区分：
  clean cube            → heuristic 0, true 0
  two overlapping cubes → heuristic >0, true >0   （必须 fail）
  closed annulus tube   → heuristic >0, true 0    （必须 pass，这正是假阳性）
  solid inside a bore   → heuristic >0, true 0    （2026-11 加：腔体里的实体，擦边回归）

用法：
  blender -b model.blend --python tools\\blender_buried_true.py -- --objects GEO-X --out b.json
  blender -b --factory-startup --python tools\\blender_buried_true.py -- --fbx out\\X.fbx
  blender -b --factory-startup --python tools\\blender_buried_true.py -- --selftest
"""

import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

VERSION = "1.1.0"
PASS, FAIL, DEGRADED = "pass", "fail", "degraded"
EPS = 3e-4  # 0.3 mm（模型尺度 ~3 m）
EPS_STEP = 2e-4   # 0.2 mm：命中推进步长（擦边去重）
MAX_TRAVEL = 200.0

# 三个不共面、且刻意避开轴对齐的方向，降低"擦边命中"概率
DIRS = [
    Vector((0.9973, 0.0370, 0.0651)).normalized(),
    Vector((-0.3010, 0.9013, 0.3130)).normalized(),
    Vector((0.2201, -0.4102, 0.8850)).normalized(),
]


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    opts = {"fbx": "", "objects": "", "out": "", "selftest": False, "max_report": 12,
            "decide": "", "decided_out": ""}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--fbx":
            opts["fbx"] = argv[i + 1]; i += 2
        elif a == "--objects":
            opts["objects"] = argv[i + 1]; i += 2
        elif a == "--out":
            opts["out"] = argv[i + 1]; i += 2
        elif a == "--max-report":
            opts["max_report"] = int(argv[i + 1]); i += 2
        elif a == "--decide":
            opts["decide"] = argv[i + 1]; i += 2
        elif a == "--decided-out":
            opts["decided_out"] = argv[i + 1]; i += 2
        elif a == "--selftest":
            opts["selftest"] = True; i += 1
        else:
            print("WARN: 忽略未知参数 %s" % a, file=sys.stderr); i += 1
    return opts


def _inside(tree, p, seed=0):
    """奇偶交点法：点为实体内部 ⇔ 与闭合曲面的交点数（单向）为奇数。

    2026-11 修正（实测于 spiderverse-taxi）：原实现每命中一次只把起点推 1e-7 m，
    射线擦着圆柱面走时会反复命中同一张面 —— 实测命中计数打到 5000 的 guard 上限，
    于是"嵌在轮拱里、四周留 15–70 mm 间隙的车轮"整片被误判成内部面（26 张假阳性）。
    两处加固：
      ① 命中距离 ≤ EPS_STEP 视为同一次擦边的重复命中：只推起点，不计数；
      ② 三个固定方向意见不一致时，按 seed 确定性地补投 5 个随机方向复决。
    """
    votes = 0
    for d in DIRS:
        if _ray_hits(tree, p, d) % 2 == 1:
            votes += 1
    if votes == 0:
        return False
    if votes >= 2:
        return True

    rnd = random.Random(seed * 7919 + 13)
    extra = 0
    for _ in range(5):
        v = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        if v.length < 1e-3:
            continue
        if _ray_hits(tree, p, v.normalized()) % 2 == 1:
            extra += 1
    return extra >= 3


def _ray_hits(tree, p, d):
    """沿 d 打射线，返回有效交点数（擦边重复命中只算一次）。"""
    cnt, origin, travel = 0, p.copy(), 0.0
    while travel < MAX_TRAVEL:
        loc, nor, idx, dist = tree.ray_cast(origin, d, 1e6)
        if idx is None:
            break
        if dist > EPS_STEP:
            cnt += 1
            travel += dist
            origin = loc + d * EPS_STEP
        else:
            travel += EPS_STEP
            origin = origin + d * EPS_STEP
    return cnt


def _bm_of(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    return bm


def _tree_from_faces(faces):
    """只用给定面造 BVH（顶点打散成汤，面用索引）。"""
    verts, polys = [], []
    for f in faces:
        base = len(verts)
        verts.extend(v.co.copy() for v in f.verts)
        polys.append(list(range(base, base + len(f.verts))))
    return BVHTree.FromPolygons(verts, polys)


def _shells(bm):
    """返回 (壳数, 每个顶点所属壳 id)。按顶点-边连通。"""
    bm.verts.ensure_lookup_table()
    shell_of, count = {}, 0
    for v in bm.verts:
        if v.index in shell_of:
            continue
        stack = [v]
        shell_of[v.index] = count
        while stack:
            cur = stack.pop()
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in shell_of:
                    shell_of[o.index] = count
                    stack.append(o)
        count += 1
    return count, shell_of


def check_object(obj, max_report=12):
    """判据（按严谨度从高到低，先看定理再看射线）：

    1. 闭合流形单壳 ⇒ **定理上不可能有内部面**（每个面都在体积边界上），
       不需要、也不该拿射线去猜。启发式 buried 在这种网格上恒为"遮挡"。
    2. 多壳 ⇒ 逐壳做壳间包含检测：A 的面中心若落在 B 的实体体积内，
       才是真内部面（这就是"join 两个重叠立方体"的成因）。
       射线只打**别的壳**，不打自己 —— 避开"面正下方 0.3mm 近切向命中"的数值坑。
    3. 网格未闭合 ⇒ 判不了，degraded。
    """
    bm = _bm_of(obj)
    nshell, shell_of = _shells(bm)
    total = len(bm.faces)
    open_edges = sum(1 for e in bm.edges if len(e.link_faces) != 2)

    # 启发式计数（照抄门的口径，仅作对照，不参与判决）
    full = BVHTree.FromBMesh(bm)
    heuristic = 0
    for f in bm.faces:
        loc, nor, idx, dist = full.ray_cast(f.calc_center_median() + f.normal * 1e-5,
                                            f.normal, 1e6)
        if idx is not None and idx != f.index:
            heuristic += 1
    bm.faces.ensure_lookup_table()

    data = {
        "object": obj.name,
        "faces": total,
        "shells": nshell,
        "open_edges": open_edges,
        "heuristic_buried": heuristic,
        "true_buried": 0,
        "true_buried_sample": [],
    }

    if open_edges:
        data["verdict"] = DEGRADED
        data["note"] = "网格未闭合（open_edges=%d），壳间包含判据不成立 ⇒ 判不了" % open_edges
        bm.free()
        return data

    if nshell == 1:
        data["verdict"] = PASS
        data["note"] = ("闭合流形单壳：数学上不存在内部面；启发式报的 %d 张是凹腔/遮挡的可见面"
                        % heuristic if heuristic else "闭合流形单壳：不存在内部面")
        bm.free()
        return data

    by_shell = {}
    for f in bm.faces:
        by_shell.setdefault(shell_of[f.verts[0].index], []).append(f)

    buried = []
    for sid, faces in by_shell.items():
        others = [f for s2, fs in by_shell.items() if s2 != sid for f in fs]
        if not others:
            continue
        tree = _tree_from_faces(others)
        for f in faces:
            c = f.calc_center_median()
            if _inside(tree, c, f.index):
                buried.append({"face": f.index, "shell": sid,
                               "center": [round(v, 4) for v in c]})

    data["true_buried"] = len(buried)
    data["true_buried_sample"] = buried[:max_report]
    if buried:
        data["verdict"] = FAIL
        data["note"] = "%d 张面落在别的壳体积内 ⇒ 壳互相埋入（join 未 UNION）" % len(buried)
    else:
        data["verdict"] = PASS
        data["note"] = "%d 个壳闭合且互不包含 ⇒ 无内部面" % nshell

    bm.free()
    return data


# ---------------------------------------------------------------- selftest

def _new_obj(name, mesh):
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _cube(name, size=1.0, loc=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=size)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    obj = _new_obj(name, me)
    obj.location = loc
    return obj


def _annulus_tube(name, r_in=0.10, r_out=0.14, z0=0.0, z1=0.20, seg=24):
    """闭合流形的环形筒：内侧壁朝向对面内侧壁 ⇒ 启发式会误报，真判据应为 0。"""
    bm = bmesh.new()
    rings = []
    for r, z in ((r_out, z0), (r_out, z1), (r_in, z1), (r_in, z0)):
        ring = []
        for s in range(seg):
            a = 2.0 * math.pi * s / seg
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for i in range(4):
        a, b = rings[i], rings[(i + 1) % 4]
        for s in range(seg):
            t = (s + 1) % seg
            bm.faces.new((a[s], a[t], b[t], b[s]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    return _new_obj(name, me)


def _solid_cyl(name, r=0.24, z0=-0.02, z1=0.42, seg=32):
    """闭合实心圆柱（轴 Z），用于"腔体里塞一个实体"的用例。"""
    bm = bmesh.new()
    rings = []
    for z in (z0, z1):
        ring = []
        for s in range(seg):
            a = 2.0 * math.pi * s / seg
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for s in range(seg):
        t = (s + 1) % seg
        bm.faces.new((rings[0][s], rings[0][t], rings[1][t], rings[1][s]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    return _new_obj(name, me)


def _join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    bpy.context.view_layer.update()
    return obj


def selftest():
    cases = []

    bpy.ops.wm.read_factory_settings(use_empty=True)
    r = check_object(_cube("Clean"))
    cases.append(("clean cube → true 0", r["verdict"] == PASS and r["true_buried"] == 0,
                  r["verdict"], "true=0"))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    a = _cube("A", 1.0, (0, 0, 0))
    b = _cube("B", 1.0, (0.5, 0, 0))
    ov = _join([a, b], "Overlap")
    r = check_object(ov)
    cases.append(("two overlapping cubes → true >0", r["verdict"] == FAIL and r["true_buried"] > 0,
                  r["verdict"], "true>0"))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    r = check_object(_annulus_tube("Tube"))
    # 这一例是本门存在的理由：启发式必然 >0，真判据必须 0
    ok = (r["verdict"] == PASS and r["true_buried"] == 0 and r["heuristic_buried"] > 0)
    cases.append(("closed annulus tube → heuristic>0 但 true 0", ok,
                  r["verdict"], "heuristic>0 / true=0"))

    # 2026-11 新增：腔体里的实体（车轮嵌在轮拱里）。两壳互不接触、留间隙，
    # 真判据必须 0；这条用例正是修掉"擦边重复命中"的回归测试。
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bore = _annulus_tube("Bore", r_in=0.30, r_out=0.36, z0=0.0, z1=0.40, seg=32)
    core = _solid_cyl("Core", r=0.24, z0=-0.02, z1=0.42, seg=32)
    w = _join([bore, core], "SolidInBore")
    r = check_object(w)
    cases.append(("solid inside a bore with clearance → true 0", r["verdict"] == PASS
                  and r["true_buried"] == 0, r["verdict"], "true=0"))

    print("\n" + "=" * 68)
    print("blender_buried_true.py selftest · Blender %s" % bpy.app.version_string)
    print("=" * 68)
    passed = 0
    for name, ok, got, want in cases:
        print("%s  %-46s got=%-9s %s" % ("PASS" if ok else "FAIL", name, got, want))
        passed += 1 if ok else 0
    print("-" * 68)
    print("%d / %d passed" % (passed, len(cases)))
    print("=" * 68 + "\n")
    return passed == len(cases)


# ---------------------------------------------------------------- 判决（替换 buried）

RANK = {PASS: 0, DEGRADED: 1, FAIL: 2}


def decide(gate_json_path, mine, out_path):
    """把数值门结果里的 `buried` 换成真判据结论，重算总判决。

    只替换 buried 一项：其余五道门沿用数值门原判（它们是可靠的）。
    替换的理由见文件头——启发式在凹腔网格上系统性假阳性。
    """
    with open(gate_json_path, "r", encoding="utf-8") as fh:
        gate = json.load(fh)

    kept = ["mesh", "normals", "selfint", "thickness", "measure"]
    per, overall = {}, PASS

    for name, o in (gate.get("objects") or {}).items():
        gates = o.get("gates") or {}
        states = {}
        for k in kept:
            if k in gates:
                states[k] = gates[k].get("verdict", DEGRADED)
        states["buried_heuristic"] = (gates.get("buried") or {}).get("verdict", DEGRADED)
        states["buried_true"] = (mine.get("objects", {}).get(name) or {}).get("verdict", DEGRADED)

        decided = PASS
        for k in kept + ["buried_true"]:
            if RANK.get(states.get(k, DEGRADED), 1) > RANK[decided]:
                decided = states[k]

        per[name] = {
            "verdict": decided,
            "gates_used": {k: states.get(k, DEGRADED) for k in kept + ["buried_true"]},
            "buried_note": "启发式 buried=%s，真判据 buried_true=%s"
                           % (states["buried_heuristic"], states["buried_true"]),
        }
        if RANK[decided] > RANK[overall]:
            overall = decided

    data = {
        "gate": "decided",
        "verdict": overall,
        "buried_source": "blender_buried_true.py（奇偶交点法）",
        "from": gate_json_path,
        "objects": per,
        "summary": "verdict=%s · decided（buried 由真判据裁定）· %d 对象" % (overall, len(per)),
    }
    if overall == DEGRADED:
        data["hint"] = "degraded = 没查完（常见于未闭合网格），补查后重跑"
    elif overall == FAIL:
        data["hint"] = "看 gates_used 里非 pass 的项；buried_note 说明启发式与真判据的差异"

    text = json.dumps(data, ensure_ascii=False, indent=2)
    if out_path:
        p = out_path if os.path.isabs(out_path) else os.path.abspath(out_path)
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("[buried-true] decided -> %s" % p)
    print(text)
    return overall


# ---------------------------------------------------------------- 入口

def main():
    opts = parse_args()

    if opts["selftest"]:
        # 不调 sys.exit：--python 脚本里的 SystemExit 会被 Blender 吞掉。
        # 通过打印 "3 / 3 passed" 给调用方判读。
        selftest()
        return 0

    if opts["fbx"]:
        if not os.path.isfile(opts["fbx"]):
            print("ERROR: 找不到 FBX: %s" % opts["fbx"], file=sys.stderr)
            return 2
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=opts["fbx"], use_anim=False,
                                 automatic_bone_orientation=False, ignore_leaf_bones=False)

    if opts["objects"]:
        names = [s.strip() for s in opts["objects"].split(",") if s.strip()]
        objs = [bpy.data.objects.get(n) for n in names]
        objs = [o for o in objs if o is not None and o.type == "MESH"]
    else:
        objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]

    if not objs:
        data = {"verdict": DEGRADED, "error": "没有可查的网格对象"}
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
            per[o.name] = check_object(o, opts["max_report"])
        except Exception as exc:  # noqa: BLE001
            per[o.name] = {"verdict": DEGRADED, "error": "%s: %s" % (type(exc).__name__, exc)}

    verdicts = [v["verdict"] for v in per.values()]
    verdict = FAIL if FAIL in verdicts else (DEGRADED if DEGRADED in verdicts else PASS)

    data = {
        "gate": "buried-true",
        "verdict": verdict,
        "plugin": "blender_buried_true.py",
        "version": VERSION,
        "blender": bpy.app.version_string,
        "source": opts["fbx"] or (bpy.data.filepath or "<unsaved>"),
        "objects": per,
        "summary": "verdict=%s · buried-true · %d 对象" % (verdict, len(per)),
    }
    if verdict == DEGRADED:
        data["hint"] = "网格未闭合 ⇒ 奇偶判据不成立，先闭合再判"

    text = json.dumps(data, ensure_ascii=False, indent=2)
    if opts["out"]:
        p = opts["out"] if os.path.isabs(opts["out"]) else os.path.abspath(opts["out"])
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("[buried-true] wrote %s" % p)
    print(text)

    if opts["decide"]:
        decide(opts["decide"], data, opts["decided_out"])
    return 0


if __name__ == "__main__":
    main()
