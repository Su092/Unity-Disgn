# -*- coding: utf-8 -*-
"""逐件 UNION 探针（带壳尺寸）：发现断壳时直接说清"断开的那块有多大"。

小壳（<200 顶点）通常是新加的零件没咬上；
大壳才可能是车身被切出一块（严重）。
"""
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_sportscar as S  # noqa: E402
import build_taxi as T  # noqa: E402


def shell_sizes(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    seen, out = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        n, stack = 0, [v]
        seen.add(v.index)
        while stack:
            cur = stack.pop()
            n += 1
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        out.append(n)
    bm.free()
    out.sort(reverse=True)
    return out


bpy.ops.wm.read_factory_settings(use_empty=True)
S.setup_scene()
mats = S.build_materials()
body = S.build_body(mats)
parts = S.build_details()
print("[probe] start shells=%s" % shell_sizes(body))
for p in parts:
    name = p.name
    T.bool_op(body, p, "UNION")
    ss = shell_sizes(body)
    flag = "  <<" if len(ss) > 1 else ""
    print("  + %-22s shells=%s%s" % (name, ss, flag))
