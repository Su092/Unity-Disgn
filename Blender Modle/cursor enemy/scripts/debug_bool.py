# -*- coding: utf-8 -*-
"""布尔调试：逐件 UNION 并打印每次结果的面数/包围盒，定位哪一步把网格弄坏。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import build_crawler as B  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
B.setup_scene()
mats = B.build_materials()

body = B.loft_y("GEO-Body", B.BODY, B.body_seg_mat, B.M_ORANGE, mats)
head = B.loft_y("GEO-Head", B.HEAD, B.head_seg_mat, B.M_GREY, mats)
legs = []
for name, cy in B.LEGS_Y.items():
    for sign, tag in ((1, "R"), (-1, "L")):
        legs.append(B.build_leg("GEO-Leg-%s-%s" % (name, tag), cy, sign, mats))
vents = B.build_vents(body, mats)


def report(tag, obj):
    me = obj.data
    pts = [obj.matrix_world @ v.co for v in me.vertices]
    mn = [min(p[i] for p in pts) for i in range(3)]
    mx = [max(p[i] for p in pts) for i in range(3)]
    print("[dbg] %-22s verts=%4d faces=%4d  bbox=%s..%s"
          % (tag, len(me.vertices), len(me.polygons),
             [round(v, 3) for v in mn], [round(v, 3) for v in mx]))


report("body", body)
report("head", head)
for leg in legs:
    report(leg.name, leg)
for vent in vents:
    report(vent.name, vent)

for i, op in enumerate(legs + [head] + vents):
    tag = op.name
    B.boolean_apply(body, [op], "UNION")
    B.clean(body)
    report("union:%s" % tag, body)
