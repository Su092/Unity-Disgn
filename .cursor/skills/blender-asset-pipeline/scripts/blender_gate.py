# -*- coding: utf-8 -*-
"""blender_gate.py — 独立数值门（零依赖：只用 bpy / bmesh / mathutils，不需要 DSH、MCP、任何 addon）

为什么存在：肉眼验收不可靠。"看着对"不是证据，数字才是。
本脚本把建模/交付前必须过的机械判据做成可重跑的命令，输出三态 verdict。

用法（Windows，Blender 5.x / 4.2+）：

  set BLENDER="E:\\SteamLibrary\\steamapps\\common\\Blender\\blender.exe"

  # 1) 网格健康（开边/非流形/退化面/孤立点/松散边/三角数）
  %BLENDER% -b model.blend --python blender_gate.py -- mesh --objects Chair

  # 2) 法线（★ 逐连通壳判定，不是"总 signed_volume > 0"）
  %BLENDER% -b model.blend --python blender_gate.py -- normals --objects Chair

  # 3) 埋在实体内部的面（Delete Loose 删不掉的那种）
  %BLENDER% -b model.blend --python blender_gate.py -- buried --objects Chair

  # 4) 自交（三角级，BVH）
  %BLENDER% -b model.blend --python blender_gate.py -- selfint --objects Chair

  # 5) 壁厚（内向射线；低于分辨率时结论标 degraded）
  %BLENDER% -b model.blend --python blender_gate.py -- thickness --objects Chair --min-mm 1.2

  # 6) 尺寸（世界 AABB，matrix_world 求，不含旋转误差）
  %BLENDER% -b model.blend --python blender_gate.py -- measure --objects Chair --expect 400,400,800 --tol-mm 3

  # 7) 一把梭 + 落 JSON
  %BLENDER% -b model.blend --python blender_gate.py -- all --objects Chair --out gate.json

  # 8) 自检（构造已知答案的用例，验证门本身没坏）
  %BLENDER% -b --factory-startup --python blender_gate.py -- selftest

三态口径（重要，别读反）：
  pass     = 查完了，且没有缺陷
  fail     = 查完了，确有缺陷（看 counts 里非 0 的字段）
  degraded = 没查完 / 判不出来（跳过了检查、精度不足、法线不可判）
  ** degraded 不是通过，也不是失败 ⇒ 要补查。**

退出码：pass=0，fail=1，degraded=2（便于 CI / 脚本串联）。
"""

import argparse
import json
import math
import os
import sys
import traceback

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

VERSION = "1.0.0"
EPS_AREA = 1e-9
PASS, FAIL, DEGRADED = "pass", "fail", "degraded"


# ---------------------------------------------------------------- 基础设施

def resolve_objects(spec):
    """--objects 支持：逗号分隔名 / 集合名 / '*' 全部网格 / 空=全部网格。"""
    if not spec or spec.strip() in ("", "*"):
        return [o for o in bpy.context.scene.objects if o.type == "MESH"], []

    names = [s.strip() for s in spec.split(",") if s.strip()]
    out, missing = [], []
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj is not None and obj.type == "MESH":
            out.append(obj)
            continue
        coll = bpy.data.collections.get(name)
        if coll is not None:
            out.extend([o for o in coll.all_objects if o.type == "MESH"])
            continue
        missing.append(name)
    # 去重保序
    seen, uniq = set(), []
    for o in out:
        if o.name not in seen:
            seen.add(o.name)
            uniq.append(o)
    return uniq, missing


def bm_from(obj, evaluated=False):
    """取网格。evaluated=True 走求值网格（修改器/布尔算数）。"""
    if evaluated:
        dg = bpy.context.evaluated_depsgraph_get()
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(me)
        ev.to_mesh_clear()
    else:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    return bm


def shells_of(bm):
    """按顶点连通性分壳。返回 [[vert_index,...], ...]。"""
    seen = set()
    shells = []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack = [v]
        seen.add(v.index)
        comp = []
        while stack:
            cur = stack.pop()
            comp.append(cur.index)
            for e in cur.link_edges:
                other = e.other_vert(cur)
                if other.index not in seen:
                    seen.add(other.index)
                    stack.append(other)
        shells.append(comp)
    return shells


def shell_signed_volume(bm, vert_indices):
    """该壳的有符号体积（散度定理）。< 0 ⇒ 整体法线朝内。"""
    vset = set(vert_indices)
    vol = 0.0
    for f in bm.faces:
        if f.verts[0].index not in vset:
            continue
        a = f.verts[0].co
        for i in range(1, len(f.verts) - 1):
            b = f.verts[i].co
            c = f.verts[i + 1].co
            vol += a.dot(b.cross(c)) / 6.0
    return vol


def shell_bbox(bm, vert_indices):
    vset = set(vert_indices)
    first = bm.verts[vert_indices[0]].co
    mn = Vector((first.x, first.y, first.z))
    mx = Vector((first.x, first.y, first.z))
    for v in bm.verts:
        if v.index not in vset:
            continue
        for k in range(3):
            mn[k] = min(mn[k], v.co[k])
            mx[k] = max(mx[k], v.co[k])
    return mn, mx


def bbox_inside(inner_mn, inner_mx, outer_mn, outer_mx, tol=1e-6):
    for k in range(3):
        if inner_mn[k] < outer_mn[k] - tol or inner_mx[k] > outer_mx[k] + tol:
            return False
    return True


def world_bbox(obj):
    """世界 AABB。用 matrix_world @ v.co —— 不用 obj.dimensions（后者不含旋转）。"""
    mw = obj.matrix_world
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    if not me.vertices:
        ev.to_mesh_clear()
        return None
    first = mw @ me.vertices[0].co
    mn = Vector((first.x, first.y, first.z))
    mx = Vector((first.x, first.y, first.z))
    for v in me.vertices:
        w = mw @ v.co
        for k in range(3):
            mn[k] = min(mn[k], w[k])
            mx[k] = max(mx[k], w[k])
    ev.to_mesh_clear()
    return mn, mx


def result(verdict, **kw):
    out = {"verdict": verdict}
    out.update(kw)
    return out


def combine(verdicts):
    """fail 优先，其次 degraded，最后 pass。"""
    if FAIL in verdicts:
        return FAIL
    if DEGRADED in verdicts:
        return DEGRADED
    return PASS


# ---------------------------------------------------------------- 门 1：网格健康

def gate_mesh(obj):
    bm = bm_from(obj)
    counts = {
        "verts": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": 0,      # 只属 1 个面 = 开边
        "nonmanifold_edges": 0,   # 属 >2 个面
        "degenerate_faces": 0,    # 面积 ~ 0
        "loose_verts": 0,         # 不属任何面
        "loose_edges": 0,         # 不属任何面
        "wire_edges": 0,
        "tris": 0,
    }

    for e in bm.edges:
        n = len(e.link_faces)
        if n == 0:
            counts["loose_edges"] += 1
        elif n == 1:
            counts["boundary_edges"] += 1
        elif n > 2:
            counts["nonmanifold_edges"] += 1

    for v in bm.verts:
        if not v.link_faces:
            counts["loose_verts"] += 1

    for f in bm.faces:
        if f.calc_area() <= EPS_AREA:
            counts["degenerate_faces"] += 1
        counts["tris"] += len(f.verts) - 2

    closed = counts["boundary_edges"] == 0 and counts["nonmanifold_edges"] == 0
    bm.free()

    defects = []
    for key in ("nonmanifold_edges", "degenerate_faces", "loose_verts", "loose_edges"):
        if counts[key]:
            defects.append("%s=%d" % (key, counts[key]))

    verdict = FAIL if defects else PASS
    return result(verdict, object=obj.name, closed=closed, counts=counts, defects=defects,
                  note="boundary_edges>0 只说明是开放网格；对壳类件才算缺陷")


# ---------------------------------------------------------------- 门 2：法线（逐壳）

def gate_normals(obj):
    bm = bm_from(obj)
    shells = shells_of(bm)

    info = []
    for idx_list in shells:
        vset = set(idx_list)
        # 该壳是否闭合：只看属于本壳的边
        open_edges = 0
        for e in bm.edges:
            if e.verts[0].index in vset and e.verts[1].index in vset:
                if len(e.link_faces) != 2:
                    open_edges += 1
        vol = shell_signed_volume(bm, idx_list)
        mn, mx = shell_bbox(bm, idx_list)
        info.append({
            "verts": len(idx_list),
            "closed": open_edges == 0,
            "open_edges": open_edges,
            "signed_volume": round(vol, 6),
            "bbox_min": [round(x, 3) for x in mn],
            "bbox_max": [round(x, 3) for x in mx],
        })

    # 嵌套判定：闭合且体积为负，但被某个更大的**正向**壳完全包住 ⇒ 合法空腔
    positive_bboxes = []
    for sh in info:
        if sh["closed"] and sh["signed_volume"] > 0:
            positive_bboxes.append((Vector(sh["bbox_min"]), Vector(sh["bbox_max"])))

    states = []
    reasons = []
    for sh in info:
        if not sh["closed"]:
            sh["state"] = "n/a"
            sh["reason"] = "壳未闭合，'整体朝向'无意义"
            states.append("n/a")
            continue
        if sh["signed_volume"] > 0:
            sh["state"] = "pass"
            sh["nested"] = False
            states.append("pass")
            continue
        # 负体积：可能合法嵌套，也可能是真朝内
        nested = False
        for omn, omx in positive_bboxes:
            if bbox_inside(Vector(sh["bbox_min"]), Vector(sh["bbox_max"]), omn, omx):
                nested = True
                break
        sh["nested"] = nested
        if nested:
            sh["state"] = "pass"
            sh["reason"] = "嵌套空腔（被正向壳包住），负体积属合法"
        else:
            sh["state"] = "fail"
            sh["reason"] = "闭合壳 signed_volume < 0 ⇒ 法线朝内"
            states.append("fail")
        if nested:
            states.append("pass")

    bm.free()

    if "fail" in states:
        verdict = FAIL
        reasons.append("至少一个非嵌套壳法线朝内")
    elif all(s == "n/a" for s in states):
        verdict = DEGRADED
        reasons.append("全部壳未闭合 ⇒ 无法判整体朝向（开口件请按口部法线单独核对）")
    elif "n/a" in states:
        verdict = DEGRADED
        reasons.append("部分壳未闭合 ⇒ 那部分判不了，不算通过")
    else:
        verdict = PASS

    return result(verdict, object=obj.name, shell_count=len(shells), shells=info,
                  reasons=reasons,
                  note="★ 逐壳判，不看聚合 signed_volume（大正向壳会抵消小反向壳）")


# ---------------------------------------------------------------- 门 3：埋在内部的面

def gate_buried(obj, max_report=20):
    bm = bm_from(obj)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)

    hits = []
    for f in bm.faces:
        if len(f.verts) < 3:
            continue
        origin = f.calc_center_median() + f.normal * 1e-5
        loc, nor, idx, dist = tree.ray_cast(origin, f.normal, 1e6)
        if idx is not None and idx != f.index:
            hits.append({"face": f.index, "dist": round(dist, 6),
                         "hit_face": idx, "normal": [round(x, 4) for x in f.normal]})

    total_faces = len(bm.faces)
    bm.free()

    verdict = FAIL if hits else PASS
    return result(verdict, object=obj.name, buried_count=len(hits),
                  total_faces=total_faces,
                  buried=hits[:max_report],
                  note="Delete Loose 删不掉这些（它只删孤立点/边）。处置见 references/六条坑.md §坑二")


# ---------------------------------------------------------------- 门 4：自交

def gate_selfint(obj, max_report=20):
    bm = bm_from(obj)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)

    pairs = []
    analyzed = True
    try:
        overlaps = tree.overlap(tree)
    except Exception:
        overlaps = []
        analyzed = False

    face_verts = {}
    for f in bm.faces:
        face_verts[f.index] = {v.index for v in f.verts}

    seen = set()
    for a, b in overlaps:
        if a >= b:
            continue
        key = (a, b)
        if key in seen:
            continue
        seen.add(key)
        # 相邻面（共用顶点）不算自交
        if face_verts.get(a, set()) & face_verts.get(b, set()):
            continue
        pairs.append([a, b])

    bm.free()

    if not analyzed:
        return result(DEGRADED, object=obj.name, pair_count=None,
                      note="BVH overlap 不可用，判不了")

    verdict = FAIL if pairs else PASS
    return result(verdict, object=obj.name, pair_count=len(pairs),
                  pairs=pairs[:max_report],
                  note="三角级相交对数；相邻共点面已排除。贴合接触可能给出 1+，需结合装配语义解释")


# ---------------------------------------------------------------- 门 5：壁厚

def gate_thickness(obj, min_mm=None, samples=400, resolution_mm=None):
    bm = bm_from(obj)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)

    faces = list(bm.faces)
    if not faces:
        bm.free()
        return result(DEGRADED, object=obj.name, note="无面可测")

    step = max(1, len(faces) // samples)
    picked = faces[::step][:samples]

    vals = []
    for f in picked:
        if len(f.verts) < 3:
            continue
        origin = f.calc_center_median() - f.normal * 1e-5
        loc, nor, idx, dist = tree.ray_cast(origin, -f.normal, 1e6)
        if idx is not None and idx != f.index and dist > 1e-9:
            vals.append(dist)

    bm.free()

    if not vals:
        return result(DEGRADED, object=obj.name, samples=len(picked),
                      note="没打到对面（开放曲面没有厚度），不是 fail")

    vals.sort()
    min_v = vals[0]
    med_v = vals[len(vals) // 2]
    unit = bpy.context.scene.unit_settings.scale_length or 1.0
    # 1 BU = 1 m 时，dist(BU) * 1000 = mm
    to_mm = 1000.0

    thin = []
    if min_mm is not None:
        thin = [v for v in vals if v * to_mm < min_mm]

    verdict = PASS
    notes = []
    if thin:
        verdict = FAIL
        notes.append("低于 min_mm 的采样 %d / %d" % (len(thin), len(vals)))
    if resolution_mm is not None and min_mm is not None and min_mm < resolution_mm:
        verdict = DEGRADED
        notes.append("min_mm(%s) < 测量分辨率(%s mm)：结论不可信，先加密网格"
                     % (min_mm, resolution_mm))

    return result(verdict, object=obj.name,
                  min_mm=round(min_v * to_mm, 4),
                  median_mm=round(med_v * to_mm, 4),
                  samples=len(vals),
                  samples_below=len(thin),
                  min_mm_threshold=min_mm,
                  notes=notes,
                  note="内向射线近似；曲率大处会低估")


# ---------------------------------------------------------------- 门 6：尺寸

def gate_measure(obj, expect=None, tol_mm=3.0):
    bb = world_bbox(obj)
    if bb is None:
        return result(DEGRADED, object=obj.name, note="无顶点")
    mn, mx = bb
    size = mx - mn
    to_mm = 1000.0
    size_mm = [round(s * to_mm, 3) for s in size]

    data = {
        "min_mm": [round(v * to_mm, 3) for v in mn],
        "max_mm": [round(v * to_mm, 3) for v in mx],
        "size_mm": size_mm,
        "center_mm": [round(((mn[k] + mx[k]) / 2) * to_mm, 3) for k in range(3)],
    }

    if not expect:
        return result(PASS, object=obj.name, **data)

    if len(expect) != 3:
        return result(DEGRADED, object=obj.name, **data,
                      note="--expect 需要 3 个数（x,y,z mm）")

    devs = []
    bad = []
    for k in range(3):
        d = size_mm[k] - expect[k]
        devs.append(round(d, 3))
        if abs(d) > tol_mm:
            bad.append({"axis": "xyz"[k], "expect": expect[k],
                        "actual": size_mm[k], "dev": round(d, 3)})

    verdict = FAIL if bad else PASS
    return result(verdict, object=obj.name, **data,
                  expect_mm=list(expect), dev_mm=devs, tol_mm=tol_mm,
                  out_of_tolerance=bad)


# ---------------------------------------------------------------- 调度

GATES = {
    "mesh": gate_mesh,
    "normals": gate_normals,
    "buried": gate_buried,
    "selfint": gate_selfint,
}


def run(args):
    objs, missing = resolve_objects(args.objects)
    if missing:
        return {"verdict": DEGRADED, "error": "找不到对象/集合: %s" % ", ".join(missing),
                "hint": "用 --objects 传对象名、集合名，或省略取全部网格"}

    if not objs:
        return {"verdict": DEGRADED, "error": "没有可测的网格对象"}

    which = args.gate
    per_obj = {}

    for obj in objs:
        try:
            if which == "mesh":
                per_obj[obj.name] = gate_mesh(obj)
            elif which == "normals":
                per_obj[obj.name] = gate_normals(obj)
            elif which == "buried":
                per_obj[obj.name] = gate_buried(obj)
            elif which == "selfint":
                per_obj[obj.name] = gate_selfint(obj)
            elif which == "thickness":
                per_obj[obj.name] = gate_thickness(obj, args.min_mm, args.samples,
                                                   args.resolution_mm)
            elif which == "measure":
                per_obj[obj.name] = gate_measure(obj, args.expect, args.tol_mm)
            elif which == "all":
                sub = {
                    "mesh": gate_mesh(obj),
                    "normals": gate_normals(obj),
                    "buried": gate_buried(obj),
                    "selfint": gate_selfint(obj),
                    "thickness": gate_thickness(obj, args.min_mm, args.samples,
                                                args.resolution_mm),
                    "measure": gate_measure(obj, args.expect, args.tol_mm),
                }
                per_obj[obj.name] = result(
                    combine([v["verdict"] for v in sub.values()]), gates=sub)
            else:
                return {"verdict": DEGRADED, "error": "未知门: %s" % which,
                        "available": sorted(list(GATES) + ["thickness", "measure", "all"])}
        except Exception as exc:  # noqa: BLE001
            per_obj[obj.name] = result(DEGRADED, object=obj.name,
                                       error="%s: %s" % (type(exc).__name__, exc),
                                       trace=traceback.format_exc(limit=3))

    verdict = combine([v["verdict"] for v in per_obj.values()])
    out = {
        "gate": which,
        "verdict": verdict,
        "plugin": "blender_gate.py",
        "version": VERSION,
        "blender": bpy.app.version_string,
        "objects": per_obj,
        "missing": missing,
        "summary": "verdict=%s · %s · %d 对象" % (verdict, which, len(per_obj)),
    }
    if verdict == FAIL:
        out["hint"] = "fail = 确有缺陷，看各对象里的 counts/defects/buried_count/pair_count"
    elif verdict == DEGRADED:
        out["hint"] = "degraded = 没查完或判不出来 ⇒ 补查，不许当通过"
    return out


# ---------------------------------------------------------------- 自检

def selftest():
    """构造已知答案的用例，验证门本身判得对。

    这一步是必需的：没有 selftest 的门，你无法区分"模型干净"和"门坏了"。
    """
    cases = []

    def new_scene():
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def add_cube(name, size=1.0, loc=(0, 0, 0)):
        bpy.ops.mesh.primitive_cube_add(size=size, location=loc)
        o = bpy.context.object
        o.name = name
        return o

    # 1) 干净立方体：mesh=pass，normals=pass，selfint=pass，buried=pass
    new_scene()
    c = add_cube("Clean")
    r = gate_mesh(c)
    ok = r["verdict"] == PASS and r["counts"]["boundary_edges"] == 0 \
        and r["counts"]["nonmanifold_edges"] == 0 and r["counts"]["tris"] == 12
    cases.append(("clean cube · mesh", ok, r["verdict"], "期望 pass/0开边/12三角"))

    r = gate_normals(c)
    ok = r["verdict"] == PASS and r["shell_count"] == 1
    cases.append(("clean cube · normals", ok, r["verdict"], "期望 pass/1壳"))

    r = gate_selfint(c)
    ok = r["verdict"] == PASS and r["pair_count"] == 0
    cases.append(("clean cube · selfint", ok, r["verdict"], "期望 pass/0对"))

    r = gate_buried(c)
    ok = r["verdict"] == PASS and r["buried_count"] == 0
    cases.append(("clean cube · buried", ok, r["verdict"], "期望 pass/0面"))

    # 2) 翻转法线：normals 必须 fail
    new_scene()
    c = add_cube("Flipped")
    bm = bmesh.new()
    bm.from_mesh(c.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(c.data)
    bm.free()
    r = gate_normals(c)
    ok = r["verdict"] == FAIL
    cases.append(("flipped cube · normals 必须 fail", ok, r["verdict"], "期望 fail"))

    # 3) ★ 关键用例：大正向壳 + 分离的小反向壳
    #    聚合 signed_volume 仍为正 ⇒ 笨办法会漏判；逐壳必须抓到
    new_scene()
    big = add_cube("Big", size=2.0, loc=(0, 0, 0))
    small = add_cube("Small", size=0.5, loc=(5, 0, 0))
    bm = bmesh.new()
    bm.from_mesh(small.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(small.data)
    bm.free()
    # join 成一个对象（多壳）
    bpy.ops.object.select_all(action="DESELECT")
    big.select_set(True)
    small.select_set(True)
    bpy.context.view_layer.objects.active = big
    bpy.ops.object.join()
    merged = bpy.context.object
    merged.name = "MixedShells"
    r = gate_normals(merged)
    ok = r["verdict"] == FAIL and r["shell_count"] == 2
    cases.append(("big+inverted small · normals 逐壳抓到", ok, r["verdict"],
                  "期望 fail/2壳（聚合体积会漏判）"))

    # 4) 自交：两个重叠立方体 join，必须报出相交对
    new_scene()
    a = add_cube("A", size=1.0, loc=(0, 0, 0))
    b = add_cube("B", size=1.0, loc=(0.5, 0, 0))
    bpy.ops.object.select_all(action="DESELECT")
    a.select_set(True)
    b.select_set(True)
    bpy.context.view_layer.objects.active = a
    bpy.ops.object.join()
    ov = bpy.context.object
    ov.name = "Overlap"
    r = gate_selfint(ov)
    ok = r["verdict"] == FAIL and (r["pair_count"] or 0) > 0
    cases.append(("two overlapping cubes · selfint 报相交", ok, r["verdict"],
                  "期望 fail/>0 对"))

    # 5) buried：重叠对里被埋住的面必须被抓到
    r = gate_buried(ov)
    ok = r["verdict"] == FAIL and r["buried_count"] >= 2
    cases.append(("two overlapping cubes · buried 抓到埋面", ok, r["verdict"],
                  "期望 fail/>=2 面"))

    # 6) 孤立点 + 开边 + 零面积面：mesh 必须 fail，且三个计数都要非 0
    new_scene()
    me = bpy.data.meshes.new("DirtyMesh")
    verts = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (9, 9, 9), (2, 2, 2), (3, 2, 2)]
    faces = [
        (0, 1, 2, 3),      # 干净四边形
        (4, 5, 4),         # 退化：重复顶点 ⇒ 零面积
    ]
    me.from_pydata(verts, [], faces)
    me.update(calc_edges=True)
    c = bpy.data.objects.new("Dirty", me)
    bpy.context.scene.collection.objects.link(c)
    r = gate_mesh(c)
    cnt = r["counts"]
    # 实测（Blender 5.2.3）：verts=7 edges=6 faces=2 boundary=5 degenerate=1 loose_verts=1
    # 断言语义而非精确值，避免跨版本脆化。
    ok = (r["verdict"] == FAIL
          and cnt["loose_verts"] >= 1          # (3,2,2) 不属任何面
          and cnt["boundary_edges"] >= 4       # 四边形是开口的
          and cnt["degenerate_faces"] >= 1)    # 退化三角 (4,5,4)
    cases.append(("loose vert+open+degenerate · mesh fail", ok, r["verdict"],
                  "期望 fail/孤立点+开边+退化面均>0"))

    # 7) 尺寸门：1m 立方体 → 1000mm
    new_scene()
    c = add_cube("Meter", size=1.0)
    r = gate_measure(c, expect=(1000, 1000, 1000), tol_mm=3)
    ok = r["verdict"] == PASS and all(abs(v - 1000) < 1 for v in r["size_mm"])
    cases.append(("1m cube · measure=1000mm", ok, r["verdict"],
                  "期望 pass/size_mm≈1000"))

    # 8) 尺寸门：给错期望必须 fail
    r = gate_measure(c, expect=(400, 400, 800), tol_mm=3)
    ok = r["verdict"] == FAIL and len(r["out_of_tolerance"]) >= 1
    cases.append(("wrong expect · measure 必须 fail", ok, r["verdict"], "期望 fail"))

    passed = sum(1 for _, ok, _, _ in cases if ok)
    total = len(cases)
    print("\n" + "=" * 62)
    print("blender_gate.py selftest · Blender %s" % bpy.app.version_string)
    print("=" * 62)
    for name, ok, got, want in cases:
        print("%s  %-42s got=%-9s %s" % ("PASS" if ok else "FAIL", name, got, want))
    print("-" * 62)
    print("%d / %d passed" % (passed, total))
    print("=" * 62 + "\n")

    return passed == total


# ---------------------------------------------------------------- 入口

def build_parser():
    p = argparse.ArgumentParser(
        prog="blender_gate.py",
        description="Blender 独立数值门（三态 verdict）")
    p.add_argument("gate", nargs="?",
                   choices=sorted(list(GATES) + ["thickness", "measure", "all", "selftest"]),
                   default="mesh")
    p.add_argument("--objects", default="",
                   help="逗号分隔对象名 / 集合名；省略=场景内全部网格")
    p.add_argument("--out", default="", help="结果写入 JSON 路径")
    p.add_argument("--min-mm", type=float, default=None, dest="min_mm",
                   help="壁厚下限（mm），仅 thickness / all 用")
    p.add_argument("--samples", type=int, default=400, help="壁厚采样数")
    p.add_argument("--resolution-mm", type=float, default=None, dest="resolution_mm",
                   help="网格测量分辨率（mm）；min_mm 低于它时判 degraded")
    p.add_argument("--expect", default="",
                   help="期望尺寸 x,y,z（mm），仅 measure / all 用")
    p.add_argument("--tol-mm", type=float, default=3.0, dest="tol_mm",
                   help="尺寸公差（mm），默认 3")
    return p


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []

    try:
        args = build_parser().parse_args(argv)
    except SystemExit:
        return 0

    if args.gate == "selftest":
        return 0 if selftest() else 1

    if args.expect:
        try:
            args.expect = [float(x) for x in args.expect.split(",")]
        except ValueError:
            print("ERROR: --expect 要形如 400,400,800", file=sys.stderr)
            return 2
    else:
        args.expect = None

    data = run(args)
    text = json.dumps(data, ensure_ascii=False, indent=2)

    if args.out:
        path = args.out if os.path.isabs(args.out) else os.path.abspath(args.out)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("[blender_gate] wrote %s" % path)
    print(text)

    return {PASS: 0, FAIL: 1}.get(data.get("verdict"), 2)


if __name__ == "__main__":
    sys.exit(main())
