"""列出对象的壳（连通分量）及其 bbox / 面数，用于定位"没并进去"的细节件。"""
import bpy, bmesh, sys
from collections import defaultdict

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []
path = argv[0] if argv else ""
if path:
    bpy.ops.wm.open_mainfile(filepath=path)

obj = next(o for o in bpy.data.objects if o.type == "MESH")
me = obj.data
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()

seen = set()
shells = []
for v in bm.verts:
    if v.index in seen:
        continue
    stack, comp = [v], []
    seen.add(v.index)
    while stack:
        cur = stack.pop()
        comp.append(cur)
        for e in cur.link_edges:
            o = e.other_vert(cur)
            if o.index not in seen:
                seen.add(o.index)
                stack.append(o)
    xs = [c.co for c in comp]
    mn = [min(c[i] for c in xs) for i in range(3)]
    mx = [max(c[i] for c in xs) for i in range(3)]
    nf = len({f.index for c in comp for f in c.link_faces})
    shells.append((len(comp), nf, mn, mx))

shells.sort(key=lambda s: -s[0])
print("[shells] count =", len(shells))
for i, (nv, nf, mn, mx) in enumerate(shells):
    print("  #%-2d verts=%-5d faces=%-5d  x[%7.1f,%7.1f] y[%7.1f,%7.1f] z[%6.1f,%6.1f]"
          % (i, nv, nf, mn[0] / 0.001, mx[0] / 0.001, mn[1] / 0.001, mx[1] / 0.001,
             mn[2] / 0.001, mx[2] / 0.001))
print("[mats]", [m.name if m else None for m in me.materials])
bm.free()
