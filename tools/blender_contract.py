# -*- coding: utf-8 -*-
"""Blender → Unity 的「导入契约门」：数值门（blender_gate.py）管几何质量，
这里管**交付契约**——单位、变换是否 apply、骨架命名、落地基准、材质、三角预算、根节点数。

为什么单列：这些不是网格缺陷，数值门一条都不管，但它们会让模型在 Unity 里
缩错、躺平、贴图丢失、多个根各转各的。历史踩坑见
`Project/Star Defanse/docs/technical-design.md` §6 与 `docs/asset-pipeline.md` §3.3。

三态口径与数值门一致：pass / fail / degraded（degraded = 没查完，必须补查）。

用法：
  blender -b model.blend            --python tools\\blender_contract.py -- [参数]
  blender -b --factory-startup --python tools\\blender_contract.py -- --fbx out\\X.fbx

参数：
  --fbx PATH            先清场再导入该 FBX 再检查（导出口径）
  --objects NAMES       只查这些对象（逗号分隔），省略=全部网格
  --max-tris N          三角面预算，默认 60000
  --yaw-bone NAME       期望存在的瞄准骨骼名，默认 Yaw（找不到 ⇒ fail）
  --no-bone             该件不需要瞄准骨骼（道具 / 核心 / 出生门）
  --require-floor       世界 AABB 最低点必须贴地（默认只报告不判）
  --floor-tol-mm F      贴地容差，默认 1.0
  --require-prefix      对象名必须以 GEO- 开头（技能 MUST），默认只报告
  --out PATH            结果写入 JSON
"""

import json
import os
import sys

import bpy
from mathutils import Vector

VERSION = "1.0.0"
PASS, FAIL, DEGRADED = "pass", "fail", "degraded"


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []

    opts = {
        "fbx": "",
        "objects": "",
        "max_tris": 60000,
        "yaw_bone": "Yaw",
        "no_bone": False,
        "require_floor": False,
        "floor_tol_mm": 1.0,
        "require_prefix": False,
        "out": "",
    }
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--fbx":
            opts["fbx"] = argv[i + 1]; i += 2
        elif a == "--objects":
            opts["objects"] = argv[i + 1]; i += 2
        elif a == "--max-tris":
            opts["max_tris"] = int(argv[i + 1]); i += 2
        elif a == "--yaw-bone":
            opts["yaw_bone"] = argv[i + 1]; i += 2
        elif a == "--no-bone":
            opts["no_bone"] = True; i += 1
        elif a == "--require-floor":
            opts["require_floor"] = True; i += 1
        elif a == "--floor-tol-mm":
            opts["floor_tol_mm"] = float(argv[i + 1]); i += 2
        elif a == "--require-prefix":
            opts["require_prefix"] = True; i += 1
        elif a == "--out":
            opts["out"] = argv[i + 1]; i += 2
        else:
            print("WARN: 忽略未知参数 %s" % a, file=sys.stderr)
            i += 1
    return opts


def world_aabb(obj):
    """世界 AABB，走 matrix_world @ v.co（不是 obj.dimensions，后者不含旋转）。"""
    mw = obj.matrix_world
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    pts = [mw @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    if not pts:
        return None
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def tris_of(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    ev.to_mesh_clear()
    return n


def is_identity_rotation(mat, tol=1e-4):
    """只看旋转块；允许任意平移。"""
    for r in range(3):
        for c in range(3):
            want = 1.0 if r == c else 0.0
            got = mat[r][c]
            if abs(got - want) > tol:
                return False
    return True


def mesh_objects(spec):
    if not spec:
        return [o for o in bpy.context.scene.objects if o.type == "MESH"]
    names = [s.strip() for s in spec.split(",") if s.strip()]
    out = []
    for n in names:
        o = bpy.data.objects.get(n)
        if o is not None and o.type == "MESH":
            out.append(o)
    return out


def check_units():
    us = bpy.context.scene.unit_settings
    scale = us.scale_length
    ok = us.system == "METRIC" and abs(scale - 1.0) < 1e-6
    detail = "system=%s scale_length=%s" % (us.system, scale)
    return {
        "name": "单位 1 BU = 1 m",
        "state": PASS if ok else FAIL,
        "detail": detail,
        "fix": "" if ok else "scene.unit_settings.scale_length 必须 = 1.0（Unity 侧按 1 单位 = 1 m 读）",
    }


def check_object_transforms(objs, imported=False):
    """变换已 apply 只对**构建通路**（源 .blend）是硬判据。

    FBX 重新导入时，轴转换（Z-up → Y-up）会合法地烘焙成对象旋转，
    本工程 Unity 侧 `Bake Axis Conversion` 是关闭的，靠的就是这条烘焙结果
    （见 docs/technical-design.md §6）。所以在导入通路里这条只报数不判定，
    否则每个正常 FBX 都会被误判成"未 apply"。
    """
    fails, notes = [], []
    for o in objs:
        mw = o.matrix_world
        rot_ok = is_identity_rotation(mw)
        sc = mw.to_scale()
        scale_ok = all(abs(abs(s) - 1.0) < 1e-4 for s in sc)
        negative = any(s < 0 for s in sc)
        issues = []
        if not rot_ok:
            issues.append("旋转未应用")
        if not scale_ok:
            issues.append("缩放=%s 未应用" % [round(s, 4) for s in sc])
        if negative:
            issues.append("负缩放（镜像未 apply）")
        if issues:
            fails.append({"object": o.name, "issues": issues})
        elif o.hide_render or not o.visible_get():
            notes.append("%s 不可见（hide_render / 隐藏）" % o.name)

    if imported:
        # 导入方向：旋转来自 Z-up→Y-up 轴转换、缩放来自骨骼层级传播，两者都是合法产物
        # （Unity 侧 Bake Axis Conversion 关闭，靠的就是这条烘焙结果，见 technical-design.md §6）。
        # 唯一仍硬判的是负缩放：镜像没 apply 会真的把几何翻面。
        negative_objs = [f for f in fails if any("负缩放" in i for i in f["issues"])]
        state = FAIL if negative_objs else PASS
        return {
            "name": "对象变换（导入通路：只硬判负缩放）",
            "state": state,
            "detail": "带非单位变换 %d 个（轴转换/骨骼传播，合法）；负缩放 %d 个"
                      % (len(fails), len(negative_objs)),
            "offenders": fails,
            "notes": notes + ["导入通路的旋转与缩放仅作报告；构建通路（源 .blend）才硬判 rot=0 / scale=1"],
            "fix": "" if state == PASS else "负缩放意味着镜像未 apply：导出前 Object → Apply → Scale",
        }

    state = FAIL if fails else PASS
    detail = "全部 %d 个网格变换已应用" % len(objs) if not fails else "%d 个网格未 apply" % len(fails)
    return {
        "name": "对象变换已 apply（rot=0 / scale=1 / 无负缩放）",
        "state": state,
        "detail": detail,
        "offenders": fails,
        "notes": notes,
        "fix": "" if not fails else "Object → Apply → Rotation & Scale；镜像件用 Mirror 修改器后 apply",
    }


def check_roots(objs):
    roots = [o for o in objs if o.parent is None]
    state = PASS if len(roots) <= 1 else FAIL
    if len(roots) == 0:
        detail = "root_count=0（全部网格都挂在骨架/父级下，正常）"
    else:
        detail = "root_count=%d（%s）" % (len(roots), ", ".join(o.name for o in roots[:6]))
    return {
        "name": "单一网格根（≤1）",
        "state": state,
        "detail": detail,
        "fix": "" if state == PASS else "多根会让 Unity 侧落地/缩放各按各的算；用空物体或 join 收敛到 1 个根",
    }


def check_naming(objs, require):
    bad = [o.name for o in objs if not o.name.startswith("GEO-")]
    state = PASS if (not require or not bad) else FAIL
    if require and bad:
        return {"name": "对象命名 GEO- 前缀", "state": state,
                "detail": "%d 个未加前缀：%s" % (len(bad), ", ".join(bad[:6])),
                "fix": "对象一建就命名 GEO-<部件>，blockout 与成品分开"}
    return {"name": "对象命名 GEO- 前缀", "state": PASS,
            "detail": "已加前缀" if not bad else "仅报告（未加 --require-prefix）：%s" % ", ".join(bad[:6]),
            "fix": ""}


def check_tris(objs, budget):
    per = {o.name: tris_of(o) for o in objs}
    total = sum(per.values())
    state = PASS if total <= budget else FAIL
    return {
        "name": "三角面预算",
        "state": state,
        "detail": "tris=%d / 预算 %d" % (total, budget),
        "per_object": per,
        "fix": "" if state == PASS else "先减细分层级/倒角段数，别先删结构",
    }


def check_materials(objs, imported=False):
    """材质 + 贴图随件。

    ★ 两条通路判据不同（结构性限制，不是放宽标准）：

    构建通路（.blend）：必须验**贴图节点**。没有 TEX_IMAGE 节点，
      Blender 里渲染就是死色，作者也看不到最终效果 —— 这是真缺陷。

    交付通路（FBX）：**FBX 格式不携带 Blender 节点树**。导入后
      材质只有名字与基础参数，`textures=0` 是格式的正常结果
      （实测：4 个材质槽全在，但每个都是 textures=0）。
      本工程 Unity 侧的导入契约写明 `Material Creation Mode: None`
      + 运行时按同目录 `*_basecolor.jpg` 重建材质，所以 FBX 里
      没有贴图节点是**设计如此**。
      交付通路改为只验"有材质槽、槽非空"。

    证据：`report.md` §9「Unity 侧导入参数」表。
    """
    missing, no_tex = [], []
    for o in objs:
        if not o.material_slots or all(s.material is None for s in o.material_slots):
            missing.append(o.name)
            continue
        if imported:
            # FBX 通路：只要求槽非空（贴图在 Unity 侧按同名族重建）
            continue
        has_img = False
        for s in o.material_slots:
            m = s.material
            if m is None or not m.use_nodes:
                continue
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image is not None:
                    has_img = True
                    break
            if has_img:
                break
        if not has_img:
            no_tex.append(o.name)

    state = FAIL if (missing or no_tex) else PASS
    return {
        "name": "材质 + 贴图随件",
        "state": state,
        "detail": ("缺材质=%s 缺贴图节点=%s" % (missing or "无", no_tex or "无")
                   if not imported else
                   "缺材质=%s（FBX 通路不验贴图节点：FBX 不携带节点树，"
                   "Unity 侧按 *_basecolor.jpg 重建）" % (missing or "无")),
        "fix": "" if state == PASS else "Unity 侧按同目录 *_basecolor.jpg 重建材质，Blender 里也要有图可对照",
    }


def check_uvs(objs):
    """贴图有图还得有 UV：只有 TEX_IMAGE 节点、没有 UV 层的话，
    采样会落在同一个纹素上 —— 渲染成一片死色，Unity 里也一样。"""
    missing, degenerate = [], []
    for o in objs:
        me = o.data
        if not me.uv_layers:
            missing.append(o.name)
            continue
        uvl = me.uv_layers[0]
        us = [d.uv[0] for d in uvl.data]
        vs = [d.uv[1] for d in uvl.data]
        if not us:
            missing.append(o.name)
        elif (max(us) - min(us)) < 1e-4 and (max(vs) - min(vs)) < 1e-4:
            degenerate.append(o.name)

    state = FAIL if (missing or degenerate) else PASS
    return {
        "name": "UV 层可用（贴图不被压成死色）",
        "state": state,
        "detail": "缺 UV=%s 退化为单点=%s" % (missing or "无", degenerate or "无"),
        "fix": "" if state == PASS else "给网格建 UV 层（回转件可用柱面/箱式投影，data API 即可）",
    }


def check_material_slots(objs):
    """材质槽本身要干净：空槽 / 重复引用 / 索引越界都会让 Unity 多出 submesh。

    实测来源：Boolean 修改器 apply 默认 `material_mode='TRANSFER'`，
    会把操作数的空材质槽搬进目标网格，产出 [None, M_xxx] 这种槽位。
    """
    empty, dup, oob = [], [], []
    for o in objs:
        mats = [s.material for s in o.material_slots]
        if not mats:
            continue
        if any(m is None for m in mats):
            empty.append(o.name)
        names = [m.name for m in mats if m is not None]
        if len(names) != len(set(names)):
            dup.append("%s(%s)" % (o.name, ",".join(names)))
        used = {p.material_index for p in o.data.polygons}
        if used and max(used) >= len(mats):
            oob.append("%s(idx %d >= %d)" % (o.name, max(used), len(mats)))

    state = FAIL if (empty or dup or oob) else PASS
    return {
        "name": "材质槽无空槽/重复/越界",
        "state": state,
        "detail": "空槽=%s 重复=%s 索引越界=%s"
                  % (empty or "无", dup or "无", oob or "无"),
        "fix": "" if state == PASS else "清空材质槽后重新赋单一材质，并把面 material_index 归 0",
    }


def check_bones(objs, bone_name, no_bone):
    """骨架契约分两类：
      - `--no-bone`（道具/不需瞄准）：场景里**有没有骨架都算 pass**，只报告实际骨骼；
      - 默认（塔/需要瞄准）：必须有骨架，且骨骼里必须有 `<bone_name>`。
    """
    armatures = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]

    names = []
    for a in armatures:
        names.extend(b.name for b in a.data.bones)

    if no_bone:
        return {"name": "骨架契约", "state": PASS,
                "detail": "该件不要求瞄准骨骼；实际骨骼 %d 根%s"
                          % (len(names), ("（%s）" % ", ".join(names[:6])) if names else "（无骨架）"),
                "bones": names,
                "fix": ""}

    if not armatures:
        # 需要瞄准骨骼却没有骨架 ⇒ 判不了朝向契约，不能算通过
        return {"name": "骨架契约", "state": DEGRADED,
                "detail": "场景内无 ARMATURE；若该件需要 Yaw/Muzzle 骨骼请补，若不需要请传 --no-bone",
                "fix": "无需骨架的件加 --no-bone；塔/需要瞄准的件必须有 Yaw 骨骼"}

    has_yaw = bone_name in names
    # FBX 导入器会给叶子骨补 <bone>_end，那是导入产物不是设计骨骼，别计入
    muzzles = sorted(n for n in names
                     if n.lower().startswith("muzzle") and not n.lower().endswith("_end"))
    missing_yaw = not has_yaw

    state = FAIL if missing_yaw else PASS
    return {
        "name": "骨架契约（%s + Muzzle*）" % bone_name,
        "state": state,
        "detail": "bones=%d · %s=%s · muzzles=%s"
                  % (len(names), bone_name, "有" if has_yaw else "缺", muzzles or "无"),
        "bones": names,
        "fix": "" if state == PASS else
        "瞄准靠 %s 骨骼：STAssetPostprocessor 只剔除**路径末段恰好是 %s** 的轨道，"
        "所以骨骼必须直接叫 %s（别叫 Yaw_L / AimYaw）" % (bone_name, bone_name, bone_name),
    }


def check_floor(objs, require, tol_mm):
    boxes = [world_aabb(o) for o in objs]
    boxes = [b for b in boxes if b is not None]
    if not boxes:
        return {"name": "落地基准", "state": DEGRADED, "detail": "无顶点", "fix": ""}
    zmin = min(b[0].z for b in boxes)     # Blender Z 向上
    gap_mm = zmin * 1000.0
    ok = abs(gap_mm) <= tol_mm
    if not require:
        state = PASS
    else:
        state = PASS if ok else FAIL
    return {
        "name": "落地基准（世界最低点 z≈0）",
        "state": state,
        "detail": "floor_gap_mm=%s · %s" % (round(gap_mm, 3),
                                          "已判" if require else "仅报告（未加 --require-floor）"),
        "fix": "" if state == PASS else "把模型最低点移到 z=0；Unity 侧 STGroundSnap 会再压一次，但基准不对会先陷地",
    }


def combine(states):
    if FAIL in states:
        return FAIL
    if DEGRADED in states:
        return DEGRADED
    return PASS


def main():
    opts = parse_args()

    if opts["fbx"]:
        if not os.path.isfile(opts["fbx"]):
            print("ERROR: 找不到 FBX: %s" % opts["fbx"], file=sys.stderr)
            return 2
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=opts["fbx"], use_anim=False,
                                 automatic_bone_orientation=False, ignore_leaf_bones=False)
        print("[contract] imported %s" % opts["fbx"])

    objs = mesh_objects(opts["objects"])
    if not objs:
        data = {"verdict": DEGRADED, "error": "没有可查的网格对象",
                "hint": "--objects 传名字，或省略取全部网格；FBX 模式先确认文件里有网格"}
        text = json.dumps(data, ensure_ascii=False, indent=2)
        if opts["out"]:
            path = opts["out"] if os.path.isabs(opts["out"]) else os.path.abspath(opts["out"])
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        print(text)
        return 2

    checks = [
        check_units(),
        check_object_transforms(objs, imported=bool(opts["fbx"])),
        check_roots(objs),
        check_naming(objs, opts["require_prefix"]),
        check_tris(objs, opts["max_tris"]),
        check_materials(objs, imported=bool(opts["fbx"])),
        check_material_slots(objs),
        check_uvs(objs),
        check_bones(objs, opts["yaw_bone"], opts["no_bone"]),
        check_floor(objs, opts["require_floor"], opts["floor_tol_mm"]),
    ]

    verdict = combine([c["state"] for c in checks])
    data = {
        "gate": "contract",
        "verdict": verdict,
        "plugin": "blender_contract.py",
        "version": VERSION,
        "blender": bpy.app.version_string,
        "source": opts["fbx"] or (bpy.data.filepath or "<unsaved>"),
        "objects": [o.name for o in objs],
        "checks": checks,
        "summary": "verdict=%s · contract · %d 网格" % (verdict, len(objs)),
    }
    if verdict == FAIL:
        data["hint"] = "看 checks 里 state=fail 的项，按 fix 字段改"
    elif verdict == DEGRADED:
        data["hint"] = "degraded = 没查完（如缺骨架），补查后再决定，不许当通过"

    text = json.dumps(data, ensure_ascii=False, indent=2)
    if opts["out"]:
        path = opts["out"] if os.path.isabs(opts["out"]) else os.path.abspath(opts["out"])
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("[contract] wrote %s" % path)
    print(text)
    return 0


if __name__ == "__main__":
    main()
