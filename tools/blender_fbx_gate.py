# -*- coding: utf-8 -*-
"""把导出的 FBX 重新导入空场景，再跑一次 numeric gate。

为什么存在：`.blend` 是**构建通路**，导出的 FBX 才是**交付物**。
技能铁律 B 要求"一条判据至少一条独立通路"——复核不许沿用构建时的通路。
所以这里清空场景、只导入 FBX，再让同一套门跑一遍。
两边结论不一致时，问题必然落在导出 / 轴转换 / 单位 / 修改器未 apply 上。

用法（由 tools/blender-gate.ps1 -Fbx 调用，也可手跑）：

  blender -b --factory-startup --python tools\\blender_fbx_gate.py --
      <file.fbx> <blender_gate.py> <gate> [gate 参数...]

例：
  blender -b --factory-startup --python tools\\blender_fbx_gate.py --
      out\\Modle_Tower_Assault.fbx .cursor\\skills\\blender-asset-pipeline\\scripts\\blender_gate.py
      measure --expect 1,1,2
"""

import importlib.util
import os
import sys

import bpy


def _load_gate(path):
    spec = importlib.util.spec_from_file_location("blender_gate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    if len(args) < 2:
        print("ERROR: 需要 <file.fbx> <blender_gate.py> [gate 参数...]", file=sys.stderr)
        return 2

    fbx, gate_py = args[0], args[1]
    rest = args[2:]

    if not os.path.isfile(fbx):
        print("ERROR: 找不到 FBX: %s" % fbx, file=sys.stderr)
        return 2
    if not os.path.isfile(gate_py):
        print("ERROR: 找不到 blender_gate.py: %s" % gate_py, file=sys.stderr)
        return 2

    # 清场：只留 FBX 里的东西，别让源 .blend 的对象混进验收
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(
        filepath=fbx,
        use_anim=False,                    # 动画片段另测，几何门只要网格
        automatic_bone_orientation=False,  # 别让导入器"帮我"改骨骼朝向
        ignore_leaf_bones=False,
    )

    meshes = [o.name for o in bpy.context.scene.objects if o.type == "MESH"]
    print("[fbx_gate] imported %s · mesh objects=%d · %s"
          % (os.path.basename(fbx), len(meshes), ", ".join(meshes[:8])))

    mod = _load_gate(gate_py)
    # blender_gate.main() 从 "--" 之后取参数：伪造一份，复用它自己的解析与落盘逻辑
    sys.argv = [gate_py, "--"] + rest
    return mod.main()


if __name__ == "__main__":
    # 不调 sys.exit：--python 脚本里的 SystemExit 由 Blender 吞掉，
    # 退出码由调用方（tools/blender-gate.ps1）读 JSON 的 verdict 决定。
    main()
