import bpy
import sys
from mathutils import Vector


args = sys.argv[sys.argv.index("--") + 1:]
format_name = args[0]
path = args[1]

bpy.ops.wm.read_factory_settings(use_empty=True)
if format_name == "fbx":
    bpy.ops.import_scene.fbx(filepath=path)
elif format_name == "glb":
    bpy.ops.import_scene.gltf(filepath=path)
else:
    raise ValueError(format_name)

objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
mins = Vector((1e30, 1e30, 1e30))
maxs = Vector((-1e30, -1e30, -1e30))
for obj in objects:
    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        mins.x = min(mins.x, point.x)
        mins.y = min(mins.y, point.y)
        mins.z = min(mins.z, point.z)
        maxs.x = max(maxs.x, point.x)
        maxs.y = max(maxs.y, point.y)
        maxs.z = max(maxs.z, point.z)

size = maxs - mins
print("[export-check]", format_name, "objects", len(objects))
print("[export-check] bbox_min_m", tuple(round(value, 4) for value in mins))
print("[export-check] bbox_size_m", tuple(round(value, 4) for value in size))
print("[export-check] materials", len({mat.name for obj in objects for mat in obj.data.materials if mat}))
