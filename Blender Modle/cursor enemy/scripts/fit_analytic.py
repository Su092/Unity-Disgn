# -*- coding: utf-8 -*-
"""解析机位拟合 v2：用**逐材质可见面片**的屏幕质心与参考图色块比对。

判据（全部与光照无关）：
  · visor 面片质心  vs 参考 visor 中心
  · 蓝条面片质心    vs 参考蓝条中心
  · 琥珀侧条（z>0.5）质心 vs 参考侧条中心
  · 四条腿带（z<0.5）逐腿质心 vs 参考三条可见腿带（取最近匹配）
  · 屏幕整体 H/L 与最高点归一化 x

可见性用背面剔除近似：只统计 normal·(cam→face) < 0 的面，按投影面积加权。

用法：blender -b crawler.blend --python scripts/fit_analytic.py -- [--write]
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
REFS = os.path.join(PROJ, "refs_out")
OBJ = "GEO-Enemy-Crawler"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
WRITE = "--write" in sys.argv

# 参考图（measure_shot.py 输出，见 refs_out/ref_measure.json）
REF = {
    "visor": (0.8164, 0.5174),
    "blue": (0.6396, 0.1977),
    "flank": (0.2928, 0.4093),
    "legs": [(0.0774, 0.6329), (0.3713, 0.7478), (0.9157, 0.7449)],
    "aspect": 0.7935,
    "highest_t": 0.484,
}
W = {"visor": 2.2, "blue": 1.6, "flank": 1.3, "legs": 1.0, "aspect": 5.0, "highest": 1.5}


def load_regions():
    obj = bpy.data.objects[OBJ]
    me = obj.data
    mw = obj.matrix_world
    name_of = [s.material.name for s in obj.material_slots]
    groups = {}
    for poly in me.polygons:
        mat = name_of[poly.material_index] if poly.material_index < len(name_of) else ""
        centre = mw @ poly.center
        normal = (mw.to_3x3() @ poly.normal).normalized()
        if "Visor" in mat:
            key = "visor"
        elif "Vent" in mat or "Blue" in mat:
            key = "blue"
        elif "Band" in mat or "Amber" in mat:
            key = "flank" if centre.z > 0.50 else "leg"
        else:
            key = "body"
        groups.setdefault(key, []).append((centre, normal, poly.area,
                                           [mw @ me.vertices[i].co for i in poly.vertices]))
    return groups, [mw @ v.co for v in me.vertices]


def cam_basis(cfg):
    az, el = math.radians(cfg["az"]), math.radians(cfg["el"])
    target = Vector(cfg["target"])
    d = Vector((-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    pos = target + d * cfg["dist"]
    fwd = (target - pos).normalized()
    right = fwd.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(fwd).normalized()
    return pos, fwd, right, up


def project_point(p, cfg, res):
    pos, fwd, right, up = cam_basis(cfg)
    v = p - pos
    z = v.dot(fwd)
    if z <= 1e-6:
        return None
    focal = cfg["lens"] / 36.0 * res
    return (res * (0.5 + cfg.get("shift_x", 0.0)) + v.dot(right) / z * focal,
            res * (0.5 + cfg.get("shift_y", 0.0)) - v.dot(up) / z * focal)


def screen_bbox(pts, cfg, res):
    proj = [project_point(p, cfg, res) for p in pts]
    proj = [p for p in proj if p]
    if not proj:
        return None
    xs = [p[0] for p in proj]
    ys = [p[1] for p in proj]
    return min(xs), max(xs), min(ys), max(ys)


def region_centroid(faces, cfg, res, pos):
    """可见面片按投影面积加权的屏幕质心（归一化到整机 bbox）。"""
    acc_x = acc_y = acc_w = 0.0
    for centre, normal, area, _verts in faces:
        to_cam = (pos - centre).normalized()
        facing = normal.dot(to_cam)
        if facing <= 0.02:            # 背面剔除（近似可见性）
            continue
        p = project_point(centre, cfg, res)
        if not p:
            continue
        w = area * facing
        acc_x += p[0] * w
        acc_y += p[1] * w
        acc_w += w
    if acc_w <= 1e-9:
        return None
    return acc_x / acc_w, acc_y / acc_w


def score(cfg, groups, verts, res=1254):
    box = screen_bbox(verts, cfg, res)
    if not box:
        return 1e9, {}
    x0, x1, y0, y1 = box
    L, H = x1 - x0, y1 - y0
    if L <= 1e-6 or H <= 1e-6:
        return 1e9, {}
    pos = cam_basis(cfg)[0]

    def norm(p):
        return ((p[0] - x0) / L, (p[1] - y0) / H)

    total, info = 0.0, {}
    for key in ("visor", "blue", "flank"):
        c = region_centroid(groups.get(key, []), cfg, res, pos)
        if c is None:
            total += 1.0 * W[key]
            info[key] = None
            continue
        cx, cy = norm(c)
        d = abs(cx - REF[key][0]) + abs(cy - REF[key][1])
        total += W[key] * d
        info[key] = round(d, 4)

    # 腿带：逐腿簇（按世界坐标 x/y 分组），与参考三条可见带最近匹配
    legs = groups.get("leg", [])
    clusters = {}
    for centre, normal, area, _v in legs:
        key = (round(centre.x / 0.5), round(centre.y / 0.5))
        clusters.setdefault(key, []).append((centre, normal, area, _v))
    cand = []
    for key, faces in clusters.items():
        c = region_centroid(faces, cfg, res, pos)
        if c:
            cand.append(norm(c))
    if cand and REF["legs"]:
        errs = []
        for rx, ry in REF["legs"]:
            errs.append(min(abs(cx - rx) + abs(cy - ry) for cx, cy in cand))
        miss = max(0, len(REF["legs"]) - len(cand)) * 0.10
        legs_err = sum(errs) / len(errs) + miss
        total += W["legs"] * legs_err
        info["legs"] = round(legs_err, 4)
        info["leg_n"] = len(cand)
    else:
        total += W["legs"]
        info["legs"] = None

    aspect = H / L
    total += W["aspect"] * abs(aspect - REF["aspect"])
    info["aspect"] = round(aspect, 4)

    top = max(verts, key=lambda p: p.z)
    tp = project_point(top, cfg, res)
    if tp:
        t = (tp[0] - x0) / L
        total += W["highest"] * abs(t - REF["highest_t"])
        info["highest_t"] = round(t, 4)
    return total, info


def refine(cfg, groups, verts):
    best = score(cfg, groups, verts)[0]
    steps = {"az": 4.0, "el": 3.0, "dist": 0.5, "shift_x": 0.02, "shift_y": 0.02}
    for _ in range(16):
        improved = False
        for key, step in list(steps.items()):
            for sign in (1, -1):
                trial = dict(cfg)
                trial[key] = cfg[key] + sign * step
                s = score(trial, groups, verts)[0]
                if s < best - 1e-6:
                    best, cfg, improved = s, trial, True
        if not improved:
            steps = {k: v * 0.5 for k, v in steps.items()}
            if max(steps.values()) < 5e-3:
                break
    return cfg, best


def main():
    groups, verts = load_regions()
    pts = np.array([p[:] for p in verts])
    target = [float(0.5 * (pts[:, i].min() + pts[:, i].max())) for i in range(3)]
    span = float(max(pts.max(0) - pts.min(0)))
    print("[fit] regions: %s" % {k: len(v) for k, v in groups.items()})

    rows = []
    for lens in (70.0, 90.0, 110.0, 135.0):
        for az in range(-180, 180, 3):
            for el in (6, 10, 14, 18, 22, 26, 30, 35, 40):
                cfg = {"az": float(az), "el": float(el), "lens": lens,
                       "dist": span * (2.0 + lens / 70.0), "target": target,
                       "shift_x": 0.0, "shift_y": 0.0}
                s, info = score(cfg, groups, verts)
                rows.append((s, cfg, info))
    rows.sort(key=lambda r: r[0])
    print("top 8:")
    for s, cfg, info in rows[:8]:
        print("  %.4f az=%4.0f el=%2.0f lens=%3.0f  %s"
              % (s, cfg["az"], cfg["el"], cfg["lens"], info))

    if WRITE and rows:
        best_cfg, best_s, best_info = None, 1e9, None
        for s, cfg, _info in rows[:5]:
            c2, s2 = refine(dict(cfg), groups, verts)
            if s2 < best_s:
                best_cfg, best_s = c2, s2
        _, info = score(best_cfg, groups, verts)
        best_cfg["dist"] = round(best_cfg["dist"], 4)
        best_cfg["az"] = round(best_cfg["az"], 3)
        best_cfg["el"] = round(best_cfg["el"], 3)
        best_cfg["shift_x"] = round(best_cfg["shift_x"], 5)
        best_cfg["shift_y"] = round(best_cfg["shift_y"], 5)
        with open(os.path.join(REFS, "camera.json"), "w", encoding="utf-8") as fh:
            json.dump(best_cfg, fh, ensure_ascii=False, indent=2)
        print("[fit] best score=%.4f  %s" % (best_s, info))
        print(json.dumps(best_cfg, ensure_ascii=False, indent=2))


main()
