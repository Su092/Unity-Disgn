# -*- coding: utf-8 -*-
"""整车 AABB / 对象数 / 三角数。"""

import json
import os

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "gate")
os.makedirs(OUT, exist_ok=True)

mn = [1e18] * 3
mx = [-1e18] * 3
tris = 0
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
for o in objs:
    for v in o.data.vertices:
        p = o.matrix_world @ v.co
        for k in range(3):
            mn[k] = min(mn[k], p[k])
            mx[k] = max(mx[k], p[k])
    tris += sum(len(p.vertices) - 2 for p in o.data.polygons)

data = {
    "blend": bpy.data.filepath,
    "objects": len(objs),
    "tris": tris,
    "min_m": [round(v, 4) for v in mn],
    "max_m": [round(v, 4) for v in mx],
    "size_m": [round(mx[k] - mn[k], 4) for k in range(3)],
    "size_mm": [round((mx[k] - mn[k]) * 1000.0, 1) for k in range(3)],
    "floor_mm": round(mn[2] * 1000.0, 3),
}
path = os.path.join(OUT, "aabb.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(json.dumps(data, ensure_ascii=False, indent=2))
