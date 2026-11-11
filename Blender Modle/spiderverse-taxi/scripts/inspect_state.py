# -*- coding: utf-8 -*-
"""摊开 .blend 状态：对象/材质槽/面数分布/UV/包围盒/壳数。诊断用。"""
import sys

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []
names = [a for a in argv if not a.startswith("-")] or ["GEO-TaxiSpider"]

for name in names:
    o = bpy.data.objects.get(name)
    if o is None:
        print("!! 找不到对象", name)
        continue
    me = o.data
    print("== %s  verts=%d faces=%d tris=%d" % (
        name, len(me.vertices), len(me.polygons),
        sum(len(p.vertices) - 2 for p in me.polygons)))
    mats = [m.name if m else "None" for m in me.materials]
    print("   materials:", mats)
    count = {}
    for p in me.polygons:
        key = mats[p.material_index] if p.material_index < len(mats) else "OOB"
        count[key] = count.get(key, 0) + 1
    print("   faces/mat:", count)
    mw = o.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    print("   bbox mm: min=%s max=%s size=%s" % (
        [round(v * 1000, 2) for v in mn], [round(v * 1000, 2) for v in mx],
        [round((mx[i] - mn[i]) * 1000, 2) for i in range(3)]))
    bm = bmesh.new()
    bm.from_mesh(me)
    nonman = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    loose = sum(1 for v in bm.verts if not v.link_edges)
    print("   nonmanifold_edges=%d loose_verts=%d uv_layers=%d"
          % (nonman, loose, len(me.uv_layers)))
    bm.free()
    print("   location=%s rot=%s scale=%s" % (
        tuple(round(v, 4) for v in o.location),
        tuple(round(v, 4) for v in o.rotation_euler),
        tuple(round(v, 4) for v in o.scale)))
