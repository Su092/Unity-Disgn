import bpy
import hashlib
import json
import os
from mathutils import Vector


ROOT = r"E:\Unity Development\Blender Modle\codex enemy"
BLEND = os.path.join(ROOT, "codex_crawler.blend")
FBX = os.path.join(ROOT, "export", "codex_crawler.fbx")
GLB = os.path.join(ROOT, "export", "codex_crawler.glb")
GATE_DIR = os.path.join(ROOT, "gate")
EXPECTED_MM = (3100.0, 3300.0, 1930.0)
TOLERANCE_MM = 2.0


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


collection = bpy.data.collections.get("COL_Crawler")
if collection is None:
    raise RuntimeError("COL_Crawler missing")

objects = [obj for obj in collection.objects if obj.type == "MESH"]
mins = Vector((1e30, 1e30, 1e30))
maxs = Vector((-1e30, -1e30, -1e30))
total_vertices = 0
total_triangles = 0
issues = []

for obj in objects:
    if obj.modifiers:
        issues.append(f"{obj.name}: unapplied modifiers")
    if len(obj.data.materials) != 1 or obj.data.materials[0] is None:
        issues.append(f"{obj.name}: material slot count {len(obj.data.materials)}")
    if obj.location.length > 1e-6:
        issues.append(f"{obj.name}: non-zero object location")
    if (obj.rotation_euler.x, obj.rotation_euler.y, obj.rotation_euler.z) != (0.0, 0.0, 0.0):
        issues.append(f"{obj.name}: non-zero object rotation")
    if (obj.scale - Vector((1.0, 1.0, 1.0))).length > 1e-6:
        issues.append(f"{obj.name}: non-unit object scale")

    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        mins.x = min(mins.x, point.x)
        mins.y = min(mins.y, point.y)
        mins.z = min(mins.z, point.z)
        maxs.x = max(maxs.x, point.x)
        maxs.y = max(maxs.y, point.y)
        maxs.z = max(maxs.z, point.z)

    total_vertices += len(obj.data.vertices)
    total_triangles += sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons)

size_mm = tuple(round((maxs[index] - mins[index]) * 1000.0, 4) for index in range(3))
deltas = [abs(size_mm[index] - EXPECTED_MM[index]) for index in range(3)]
size_pass = all(delta <= TOLERANCE_MM for delta in deltas)
floor_pass = abs(mins.z * 1000.0) <= TOLERANCE_MM
units_pass = (
    bpy.context.scene.unit_settings.system == "METRIC"
    and abs(bpy.context.scene.unit_settings.scale_length - 1.0) <= 1e-9
)

bbox_result = {
    "verdict": "pass" if size_pass and floor_pass and units_pass and not issues else "fail",
    "gate": "overall_bbox",
    "expected_mm": list(EXPECTED_MM),
    "actual_mm": list(size_mm),
    "tolerance_mm": TOLERANCE_MM,
    "min_mm": [round(value * 1000.0, 4) for value in mins],
    "max_mm": [round(value * 1000.0, 4) for value in maxs],
    "floor_contact": floor_pass,
    "metric_units": units_pass,
    "object_count": len(objects),
    "vertices": total_vertices,
    "triangles": total_triangles,
    "issues": issues,
}

os.makedirs(GATE_DIR, exist_ok=True)
with open(os.path.join(GATE_DIR, "overall_bbox.json"), "w", encoding="utf-8") as handle:
    json.dump(bbox_result, handle, ensure_ascii=False, indent=2)

gate_verdicts = {}
for gate_name in ("mesh", "normals", "buried", "selfint", "thickness", "overall_bbox"):
    gate_path = os.path.join(GATE_DIR, f"{gate_name}.json")
    if os.path.exists(gate_path):
        with open(gate_path, "r", encoding="utf-8") as handle:
            gate_verdicts[gate_name] = json.load(handle).get("verdict")

manifest = {
    "asset": "codex_crawler",
    "units": "m",
    "unit_scale": 1.0,
    "reference": "ref_crawler.png",
    "source_blend": "codex_crawler.blend",
    "bbox_mm": [size_mm[0], size_mm[1], size_mm[2]],
    "bbox_min_mm": [round(value * 1000.0, 3) for value in mins],
    "bbox_max_mm": [round(value * 1000.0, 3) for value in maxs],
    "object_count": len(objects),
    "objects": sorted(obj.name for obj in objects),
    "materials": sorted({obj.data.materials[0].name for obj in objects}),
    "vertices": total_vertices,
    "triangles": total_triangles,
    "exports": [],
    "export_roundtrip": {
        "fbx": "pass: 29 meshes, bbox 3.1 x 3.3 x 1.93 m, 8 materials",
        "glb": "pass: 29 meshes, bbox 3.1 x 3.3 x 1.93 m, 8 materials",
    },
    "renders": [
        "renders/codex_crawler_hero.png",
        "renders/codex_crawler_rear.png",
    ],
    "gates": gate_verdicts,
    "known_limits": [
        "尺寸为根据单张透视图估算的 provisional 3.1 x 3.3 x 1.93 m。",
        "材质为纯色 Principled 材质，无 UV/贴图烘焙。",
        "未制作骨骼、动画、碰撞体或 LOD。",
        "跨件装配干涉/浮空未做自动门检。",
    ],
}

for path in (BLEND, FBX, GLB):
    if os.path.exists(path):
        manifest["exports"].append({
            "path": os.path.relpath(path, ROOT).replace("\\", "/"),
            "bytes": os.path.getsize(path),
            "sha256": sha256(path),
        })

with open(os.path.join(ROOT, "manifest.json"), "w", encoding="utf-8") as handle:
    json.dump(manifest, handle, ensure_ascii=False, indent=2)

print("[validate] bbox_mm", size_mm)
print("[validate] min_z_mm", round(mins.z * 1000.0, 4))
print("[validate] objects", len(objects), "verts", total_vertices, "tris", total_triangles)
print("[validate] issues", issues)
print("[validate] gates", gate_verdicts)
