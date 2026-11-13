# -*- coding: utf-8 -*-
"""交付导出：从 out/taxi_look.blend 里只取 GEO-TaxiAcross，导 FBX + GLB，
并写 manifest（units / bbox / 对象 / md5 / 材质 / 贴图）。

为什么单独写：lookdev 里加了 Freestyle 线、QC 地面、灯光相机，这些**不该进交付件**。
导出前显式只选 GEO- 对象，并核对 AABB 与 tris。

用法： blender -b --factory-startup --python scripts/export_asset.py
产物： export/Modle_Vehicle_AcrossTaxi.fbx / .glb / .mtl / basecolor.jpg / manifest.json
"""
import hashlib
import json
import os

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "out", "taxi_look.blend")
OUT = os.path.join(ROOT, "export")
STEM = "Modle_Vehicle_AcrossTaxi"
OBJ_NAME = "GEO-TaxiAcross"


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=SRC)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "MILLIMETERS"

    obj = bpy.data.objects[OBJ_NAME]
    # 清掉非交付对象（描边/地面/灯光/相机都不进 FBX 里的 mesh 集合，但删干净更稳）
    for o in list(bpy.data.objects):
        if o.name != OBJ_NAME:
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bbox = obj.bound_box
    xs = [v[0] for v in bbox]
    ys = [v[1] for v in bbox]
    zs = [v[2] for v in bbox]
    dims = [round((max(xs) - min(xs)) * 1000, 1),
            round((max(ys) - min(ys)) * 1000, 1),
            round((max(zs) - min(zs)) * 1000, 1)]
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)

    # 贴图随件：把打包图落盘到 export 目录（不按名字过滤：重载后 name 可能被改写）
    tex_files = []
    for img in bpy.data.images:
        if img.type != "IMAGE" or img.source not in {"FILE", "GENERATED"}:
            continue
        if img.size[0] < 64:
            continue
        dst = os.path.join(OUT, "Modle_Vehicle_AcrossTaxi_basecolor.jpg")
        try:
            img.filepath_raw = dst
            img.file_format = "JPEG"
            img.save()
        except Exception as exc:                 # noqa: BLE001
            print("[export] WARN 贴图落盘失败 %s: %s" % (img.name, exc))
            continue
        if os.path.exists(dst) and os.path.getsize(dst) > 2048:
            tex_files.append(dst)
            print("[export] texture -> %s (%d bytes)" % (dst, os.path.getsize(dst)))
        break

    fbx = os.path.join(OUT, STEM + ".fbx")
    bpy.ops.export_scene.fbx(
        filepath=fbx, use_selection=True, object_types={"MESH"},
        apply_scale_options="FBX_SCALE_NONE", axis_forward="-Y", axis_up="Z",
        bake_space_transform=False, path_mode="COPY", embed_textures=False,
        mesh_smooth_type="FACE", use_mesh_modifiers=True, add_leaf_bones=False,
    )
    print("[export] fbx -> %s" % fbx)

    glb = os.path.join(OUT, STEM + ".glb")
    try:
        bpy.ops.export_scene.gltf(
            filepath=glb, export_format="GLB", use_selection=True,
            export_apply=True, export_yup=True, export_texcoords=True,
            export_normals=True, export_materials="EXPORT",
        )
        print("[export] glb -> %s" % glb)
    except Exception as exc:                     # noqa: BLE001
        print("[export] WARN glb 失败: %s" % exc)
        glb = None

    # 额外导一份 OBJ（文本、便于别人直接看几何）
    obj_path = os.path.join(OUT, STEM + ".obj")
    try:
        bpy.ops.wm.obj_export(filepath=obj_path, export_selected_objects=True,
                              export_materials=True, apply_modifiers=True)
        print("[export] obj -> %s" % obj_path)
    except Exception as exc:                     # noqa: BLE001
        print("[export] WARN obj 失败: %s" % exc)
        obj_path = None

    files = [fbx] + ([glb] if glb else []) + ([obj_path] if obj_path else []) + tex_files
    manifest = {
        "asset": STEM,
        "source_blend": SRC,
        "units": "mm",
        "unit_scale_length": 1.0,
        "forward_axis": "-Y",
        "up_axis": "Z",
        "objects": [OBJ_NAME],
        "dims_mm": dims,
        "bbox_mm": {
            "x": [round(min(xs) * 1000, 1), round(max(xs) * 1000, 1)],
            "y": [round(min(ys) * 1000, 1), round(max(ys) * 1000, 1)],
            "z": [round(min(zs) * 1000, 1), round(max(zs) * 1000, 1)],
        },
        "verts": len(obj.data.vertices),
        "faces": len(obj.data.polygons),
        "tris": tris,
        "materials": [m.name for m in obj.data.materials],
        "uv_layers": [uv.name for uv in obj.data.uv_layers],
        "textures": [os.path.basename(t) for t in tex_files],
        "files": [],
    }
    for p in files:
        if os.path.exists(p):
            manifest["files"].append({"name": os.path.basename(p),
                                      "bytes": os.path.getsize(p),
                                      "md5": md5(p)})
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("[export] manifest ok: %d files, dims=%s tris=%d"
          % (len(manifest["files"]), dims, tris))


if __name__ == "__main__":
    main()
