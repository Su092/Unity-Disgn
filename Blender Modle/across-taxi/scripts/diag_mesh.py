# -*- coding: utf-8 -*-
"""诊断：打开 out/taxi.blend，列出非流形/开边位置与所在材质。"""
import bpy
import bmesh
from collections import Counter

BLEND = r"E:\Unity Development\Blender Modle\across-taxi\out\taxi.blend"

bpy.ops.wm.open_mainfile(filepath=BLEND)
obj = bpy.data.objects.get("GEO-TaxiAcross")
print("obj:", obj.name, obj.type)
me = obj.data
bm = bmesh.new()
bm.from_mesh(me)
bad = [e for e in bm.edges if len(e.link_faces) != 2]
print("nonmanifold edges:", len(bad))
print("link_faces histogram:", dict(Counter(len(e.link_faces) for e in bad)))
names = [m.name for m in me.materials]
for e in bad:
    v0, v1 = e.verts
    cx = (v0.co.x + v1.co.x) / 2 * 1000
    cy = (v0.co.y + v1.co.y) / 2 * 1000
    cz = (v0.co.z + v1.co.z) / 2 * 1000
    mats = sorted({names[f.material_index] for f in e.link_faces}) if e.link_faces else []
    print("  edge (%.0f, %.0f, %.0f) faces=%d mats=%s len=%.1fmm" % (
        cx, cy, cz, len(e.link_faces), mats, (v1.co - v0.co).length * 1000))
bm.free()

# 每个连通壳的体积/包围盒，判断有没有退化壳
import mathutils
print("\n-- shells --")
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
seen = set()
for v0 in bm.verts:
    if v0.index in seen:
        continue
    stack = [v0]
    seen.add(v0.index)
    comp = []
    while stack:
        v = stack.pop()
        comp.append(v)
        for e in v.link_edges:
            o = e.other_vert(v)
            if o.index not in seen:
                seen.add(o.index)
                stack.append(o)
    xs = [v.co.x for v in comp]
    ys = [v.co.y for v in comp]
    zs = [v.co.z for v in comp]
    print("  shell verts=%d bbox_mm=(%.0f..%.0f, %.0f..%.0f, %.0f..%.0f)" % (
        len(comp), min(xs) * 1000, max(xs) * 1000, min(ys) * 1000, max(ys) * 1000,
        min(zs) * 1000, max(zs) * 1000))
bm.free()
