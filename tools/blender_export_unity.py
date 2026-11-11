# -*- coding: utf-8 -*-
"""按星轨防线的导入契约导出 FBX，并打印 Unity 侧应设的导入参数。

为什么不能只靠「在 Blender 里手点导出」：
Unity 侧 `STAssetPostprocessor` 假定了一组固定前提（Legacy 动画、
材质由同目录 *_basecolor.jpg 重建、不 bake axis conversion、动画里的
Yaw 轨道会被剔除）。这些前提一旦在导出侧变化，模型在实机里就会躺平、
贴图丢失或炮塔被扭回零位——而这些改动在 Blender 里完全看不出来。

命名约定（由 STAssets / STAssetPostprocessor 读取，不能改）：
  Modle_<名字>.fbx    含网格（+骨架）
  Anim_<名字>.fbx     只含动画，与 Modle_ 同目录同名族

用法：
  blender -b model.blend --python tools\\blender_export_unity.py -- <out.fbx> [选项]

选项：
  --objects NAMES     只导出这些对象（逗号分隔），省略=导出全部 MESH+ARMATURE
  --anim              该文件只含动画（写 Anim_*.fbx，不带网格）
  --no-leaves         跳过叶子骨骼（骨骼末端不额外导出，减少轨道）
  --apply-transform   （默认已开）导出前应用旋转与缩放
  --keep-transform    不应用变换，保留原始矩阵（一般不要用）
"""

import os
import sys

import bpy

# Unity 侧应设的导入参数（打印成回执，人工在 Inspector 里对齐一次）
UNITY_IMPORT_CONTRACT = [
    ("Rig / Animation Type", "Legacy"),
    ("Rig / Avatar Definition", "—（Legacy 不需要）"),
    ("Model / Scale Factor", "1.00"),
    ("Model / Convert Units", "FBX All"),
    ("Model / Bake Axis Conversion", "关闭"),
    ("Model / Import BlendShapes", "关闭"),
    ("Model / Import Cameras / Lights", "关闭"),
    ("Model / Import Normals", "Import"),
    ("Model / Import Tangents", "None"),
    ("Geometry / Mesh Compression", "Off"),
    ("Geometry / Read/Write", "关闭"),
    ("Geometry / Optimize Mesh", "Anim_* 关；Modle_* 开"),
    ("Materials / Material Creation Mode", "None（运行时按 *_basecolor.jpg 重建）"),
    ("Transform / Apply Transform", "不勾"),
    ("Forward / Up", "-Z / Y"),
]


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    opts = {"out": "", "objects": "", "anim": False, "leaves": True, "apply": True}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--objects":
            opts["objects"] = argv[i + 1]; i += 2
        elif a == "--anim":
            opts["anim"] = True; i += 1
        elif a == "--no-leaves":
            opts["leaves"] = False; i += 1
        elif a == "--apply-transform":
            opts["apply"] = True; i += 1
        elif a == "--keep-transform":
            opts["apply"] = False; i += 1
        elif a.startswith("--"):
            print("WARN: 忽略未知参数 %s" % a, file=sys.stderr); i += 1
        else:
            opts["out"] = a; i += 1
    return opts


def select_targets(spec, anim_only):
    types = {"ARMATURE"} if anim_only else {"MESH", "ARMATURE"}
    if spec:
        names = [s.strip() for s in spec.split(",") if s.strip()]
        objs = [bpy.data.objects.get(n) for n in names]
        objs = [o for o in objs if o is not None and o.type in types]
    else:
        objs = [o for o in bpy.context.scene.objects if o.type in types]

    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]
    return objs


def main():
    opts = parse_args()
    if not opts["out"]:
        print("ERROR: 需要输出路径，如 out\\Modle_Tower_Assault.fbx", file=sys.stderr)
        sys.exit(2)

    out = opts["out"]
    if not out.lower().endswith(".fbx"):
        out += ".fbx"
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    base = os.path.splitext(os.path.basename(out))[0]
    must = "Anim_" if opts["anim"] else "Modle_"
    if not base.startswith(must):
        print("ERROR: 文件名必须以 %s 开头（Unity 侧按前缀分流导入规则），当前 %s"
              % (must, base), file=sys.stderr)
        sys.exit(2)

    objs = select_targets(opts["objects"], opts["anim"])
    if not objs:
        print("ERROR: 没有可导出的对象（检查 --objects 与对象类型）", file=sys.stderr)
        sys.exit(2)

    if opts["apply"]:
        # 只对网格应用旋转/缩放；骨架的变换是姿态基准，不能一起 apply
        meshes = [o for o in objs if o.type == "MESH"]
        if meshes:
            bpy.ops.object.select_all(action="DESELECT")
            for o in meshes:
                o.select_set(True)
            bpy.context.view_layer.objects.active = meshes[0]
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            bpy.ops.object.select_all(action="DESELECT")
            for o in objs:
                o.select_set(True)
            bpy.context.view_layer.objects.active = objs[0]

    bpy.ops.export_scene.fbx(
        filepath=out,
        use_selection=True,
        object_types={"ARMATURE"} if opts["anim"] else {"MESH", "ARMATURE"},
        # 轴：Unity 侧按 Forward -Z / Up Y 读，导出侧保持一致，别让两边各转一次
        axis_forward="-Z",
        axis_up="Y",
        # 单位：Unity Scale Factor 1.00 + FBX All，所以这里不额外缩放
        apply_scale_options="FBX_SCALE_ALL",
        apply_unit_scale=True,
        # 动画：只在 --anim 时才烘焙；Modle_ 不要带动作，否则 Unity 里会混入多余片段
        bake_anim=bool(opts["anim"]),
        bake_anim_use_all_bones=bool(opts["anim"]),
        bake_anim_use_nla_strips=bool(opts["anim"]),
        bake_anim_use_all_actions=False,
        bake_anim_simplify_factor=1.0 if opts["anim"] else 0.0,
        # 骨架
        add_leaf_bones=opts["leaves"],
        primary_bone_axis="Y",
        secondary_bone_axis="X",
        # 网格
        mesh_smooth_type="FACE",
        use_mesh_modifiers=True,
        use_tspace=False,
        use_custom_props=False,
        # 贴图：由 Unity 侧按同目录 *_basecolor.jpg 重建，不嵌进 FBX
        path_mode="AUTO",
        embed_textures=False,
    )

    print("\n" + "=" * 62)
    print("导出完成: %s" % out)
    print("对象: %s" % ", ".join(o.name for o in objs))
    print("-" * 62)
    print("Unity 侧导入参数（必须与本表一致，否则 STAssetPostprocessor 的前提不成立）：")
    for k, v in UNITY_IMPORT_CONTRACT:
        print("  %-38s %s" % (k, v))
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
