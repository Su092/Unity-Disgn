# -*- coding: utf-8 -*-
"""扫描轮拱参数 → 最小壁厚（只建车身 + 切拱，不渲染）。

用法：
  blender -b --factory-startup --python scripts/scan_arch.py

判据与 blender_gate 的 thickness 一致：隔步取 400 面，内向射线到对侧。
"""
import itertools
import os
import sys

import bmesh
import bpy
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_sportscar as S  # noqa: E402
import build_taxi as T  # noqa: E402


def min_thickness(obj, samples=400):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    faces = list(bm.faces)
    step = max(1, len(faces) // samples)
    vals = []
    for f in faces[::step][:samples]:
        if len(f.verts) < 3:
            continue
        origin = f.calc_center_median() - f.normal * 1e-5
        loc, nor, idx, dist = tree.ray_cast(origin, -f.normal, 1e6)
        if idx is not None and idx != f.index and dist > 1e-9:
            vals.append((dist * 1000.0, f.calc_center_median().copy()))
    bm.free()
    vals.sort(key=lambda v: v[0])
    return vals


def build(sill, arch_r, wheel_z, arch_y_in):
    S.SPEC["sill_z"] = sill
    S.SPEC["arch_r"] = arch_r
    S.SPEC["tire_r"] = wheel_z
    S.SPEC["arch_y_in"] = arch_y_in
    S.WHEEL_Z = wheel_z
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = S.build_materials()
    body = S.build_body(mats)
    for sx in (1.0, -1.0):
        for sy in (1.0, -1.0):
            cut = T.cylinder("GEO-SArch", "Y", (S.SPEC["wheel_x"] * sx, wheel_z),
                             arch_r, arch_y_in * sy, 940.0 * sy, 28, S.TRIM)
            T.bool_op(body, cut, "DIFFERENCE")
    return body


for sill, arch_r, wz, yin in itertools.product((150.0, 170.0), (430.0, 440.0, 450.0),
                                               (350.0, 360.0), (560.0, 620.0)):
    body = build(sill, arch_r, wz, yin)
    vals = min_thickness(body)
    sc = T.shells_count(body)
    print("sill=%.0f arch_r=%.0f wheel_z=%.0f y_in=%.0f  shells=%d  min=%.3f mm at (%.3f,%.3f,%.3f)"
          % (sill, arch_r, wz, yin, sc, vals[0][0],
             vals[0][1].x, vals[0][1].y, vals[0][1].z))
