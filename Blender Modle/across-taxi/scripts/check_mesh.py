# -*- coding: utf-8 -*-
"""无头体检：退化面 / 零长边 / 开边 / 非流形 / 壳数 / 尺寸 / 轮拱间隙。

对应 plugin audit_mesh 的判据，作为独立第二意见（GUI 被占用时的兜底）。
"""
import bpy
import bmesh
from mathutils import Vector

BLEND = r"E:\Unity Development\Blender Modle\across-taxi\out\taxi.blend"

bpy.ops.wm.open_mainfile(filepath=BLEND)
o = bpy.data.objects["GEO-TaxiAcross"]
me = o.data
bm = bmesh.new()
bm.from_mesh(me)
bm.faces.ensure_lookup_table()

deg = [f for f in bm.faces if f.calc_area() < 1e-9]
short = [e for e in bm.edges if e.calc_length() < 1e-6]
boundary = [e for e in bm.edges if len(e.link_faces) == 1]
nonman = [e for e in bm.edges if len(e.link_faces) > 2]
print("faces=%d verts=%d tris=%d" % (len(bm.faces), len(bm.verts),
                                     sum(len(f.verts) - 2 for f in bm.faces)))
print("degenerate_faces=%d  zero_len_edges=%d  boundary=%d  nonmanifold=%d"
      % (len(deg), len(short), len(boundary), len(nonman)))
for f in deg[:8]:
    c = f.calc_center_median()
    print("  degenerate at (%.0f, %.0f, %.0f) area=%.3e"
          % (c.x * 1000, c.y * 1000, c.z * 1000, f.calc_area()))

# 壳
bm.verts.ensure_lookup_table()
seen, shells = set(), []
for v0 in bm.verts:
    if v0.index in seen:
        continue
    stack, comp = [v0], []
    seen.add(v0.index)
    while stack:
        v = stack.pop()
        comp.append(v)
        for e in v.link_edges:
            w = e.other_vert(v)
            if w.index not in seen:
                seen.add(w.index)
                stack.append(w)
    shells.append(comp)
print("shells=%d" % len(shells))
for i, comp in enumerate(shells):
    xs = [v.co.x for v in comp]
    ys = [v.co.y for v in comp]
    zs = [v.co.z for v in comp]
    print("  shell%d verts=%d x[%.0f,%.0f] y[%.0f,%.0f] z[%.0f,%.0f]"
          % (i, len(comp), min(xs) * 1000, max(xs) * 1000,
             min(ys) * 1000, max(ys) * 1000, min(zs) * 1000, max(zs) * 1000))
bm.free()

xs = [v[0] for v in o.bound_box]
ys = [v[1] for v in o.bound_box]
zs = [v[2] for v in o.bound_box]
print("dims_mm = [%.1f, %.1f, %.1f]" % ((max(xs) - min(xs)) * 1000,
                                        (max(ys) - min(ys)) * 1000,
                                        (max(zs) - min(zs)) * 1000))
print("zmin=%.1f  zmax=%.1f" % (min(zs) * 1000, max(zs) * 1000))
print("materials=%d  uv=%s" % (len(me.materials), [u.name for u in me.uv_layers]))
print("has_texture_node=%s" % any(
    n.type == "TEX_IMAGE" for m in me.materials if m and m.use_nodes
    for n in m.node_tree.nodes))
