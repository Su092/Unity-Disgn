# -*- coding: utf-8 -*-
"""布尔求解器探针：FLOAT / EXACT / MANIFOLD 在 body∪head、body∪legs∪head 上的结果与耗时。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
import build_crawler as B  # noqa: E402


def stats(obj):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    nm = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    bd = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    shells = 0
    seen = set()
    for v in bm.verts:
        if v.index in seen:
            continue
        shells += 1
        stack = [v]
        seen.add(v.index)
        while stack:
            cur = stack.pop()
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
    bm.free()
    return len(me.vertices), len(me.polygons), nm, bd, shells


def run(label, solver, parts):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    B.setup_scene()
    mats = B.build_materials()
    body = B.loft_y("GEO-Body", B.BODY, B.body_seg_mat, B.M_ORANGE, mats)
    ops = []
    if "head" in parts:
        ops.append(B.loft_y("GEO-Head", B.HEAD, B.head_seg_mat, B.M_GREY, mats))
    if "legs" in parts:
        legs = []
        for name, cy in B.LEGS_Y.items():
            for sign, tag in ((1, "R"), (-1, "L")):
                legs.append(B.build_leg("GEO-Leg-%s-%s" % (name, tag), cy, sign, mats))
        B.select_only(legs)
        bpy.context.view_layer.objects.active = legs[0]
        bpy.ops.object.join()
        joined = bpy.context.object
        joined.name = "GEO-Legs"
        ops.insert(0, joined)
    if "vents" in parts:
        ops += B.build_vents(body, mats)
    t0 = time.time()
    ok = True
    for op in ops:
        md = body.modifiers.new("b", "BOOLEAN")
        md.operation = "UNION"
        md.object = op
        md.solver = solver
        md.material_mode = "TRANSFER"
        B.select_only([body])
        try:
            bpy.ops.object.modifier_apply(modifier=md.name)
        except Exception as exc:                    # noqa: BLE001
            print("[probe] %-22s %-8s APPLY-FAIL %s" % (label, solver, exc))
            ok = False
            break
        bpy.data.objects.remove(op, do_unlink=True)
    dt = time.time() - t0
    if ok:
        B.clean(body)
        v, f, nm, bd, shells = stats(body)
        print("[probe] %-22s %-8s %6.1fs  v=%4d f=%4d  nonmanifold=%d open=%d shells=%d  %s"
              % (label, solver, dt, v, f, nm, bd, shells,
                 "OK" if (v > 100 and nm == 0 and bd == 0) else "BAD"))


for solver in ("FLOAT", "EXACT", "MANIFOLD"):
    run("body+head", solver, ["head"])
for solver in ("FLOAT", "EXACT", "MANIFOLD"):
    run("body+legs+head+vents", solver, ["legs", "head", "vents"])
