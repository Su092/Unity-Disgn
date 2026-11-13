# -*- coding: utf-8 -*-
"""整体比例拟合：搜索 (sx, sy, sz, az, el)，最大化「归一化剪影 IoU + 色类 IoU」。

为什么需要：参考图只有一张 3/4 视角，肉眼无法判断"机体该多长/多宽"。
这里把三个轴向缩放当未知量，用与参考图同口径的剪影与色类证据反解。
反解出的缩放值回填 spec.md，再在构建脚本里改数字（不是运行时缩放）。

用法：
  blender -b crawler.blend --python scripts/fit_shape.py -- [--res 360] [--write]
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
ARGS = dict(t.split("=", 1) for t in argv if "=" in t)
RES = int(ARGS.get("res", 360))
WRITE = "--write" in sys.argv

# 与 classfit.py 同口径的色类
C_ORANGE, C_AMBER, C_BLUE, C_DARK = 1, 2, 3, 4
WEIGHT = {C_ORANGE: 1.0, C_AMBER: 1.0, C_BLUE: 1.0, C_DARK: 0.6}


def ref_classes(size=RES):
    a = np.load(os.path.join(REFS, "ref_rgb.npy")).astype(np.float32) / 255.0
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mx, mn = a.max(2), a.min(2)
    sat = mx - mn
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    bg = (sat < 0.05) & (np.abs(lum - 0.467) < 0.055)
    gr = g / np.maximum(r, 1e-6)
    cls = np.zeros(a.shape[:2], np.int8)
    cls[~bg] = C_DARK
    cls[(~bg) & (r > b + 0.14) & (r > 0.22) & (gr < 0.46)] = C_ORANGE
    cls[(~bg) & (r > b + 0.20) & (r > 0.55) & (gr >= 0.46) & (gr < 0.88) & (b < 0.42)] = C_AMBER
    cls[(~bg) & (b > r + 0.10) & (b > 0.35)] = C_BLUE
    return cls


def norm_crop(arr, size=RES):
    ys, xs = np.nonzero(arr != 0)
    if len(xs) == 0:
        return np.zeros((size, size), np.int8), None
    crop = arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = crop.shape
    yi = (np.arange(size) * h // size).astype(np.int32)
    xi = (np.arange(size) * w // size).astype(np.int32)
    return crop[yi][:, xi], (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()))


def face_classes(obj):
    names = [s.material.name for s in obj.material_slots]
    out = np.zeros(len(obj.data.polygons), np.int8)
    for poly in obj.data.polygons:
        n = names[poly.material_index] if poly.material_index < len(names) else ""
        if "Shell" in n:
            out[poly.index] = C_ORANGE
        elif "Vent" in n or "Blue" in n:
            out[poly.index] = C_BLUE
        elif "Band" in n or "Visor" in n or "Amber" in n:
            out[poly.index] = C_AMBER
        else:
            out[poly.index] = C_DARK
    return out


def raster(obj, fclass, cfg, scale, res=RES):
    """按轴向缩放投影并光栅化色类图（z-buffer）。"""
    verts = [v.co.copy() for v in obj.data.vertices]
    verts = [Vector((v.x * scale[0], v.y * scale[1], v.z * scale[2])) for v in verts]
    az, el = math.radians(cfg["az"]), math.radians(cfg["el"])
    t = Vector((0.0, 0.0, 0.5 * (max(v.z for v in verts))))
    d = Vector((-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    pos = t + d * cfg["dist"]
    fwd = (t - pos).normalized()
    right = fwd.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(fwd).normalized()
    focal = cfg["lens"] / 36.0 * res
    px = np.zeros((len(verts), 2))
    depth = np.zeros(len(verts))
    for i, v in enumerate(verts):
        rel = v - pos
        z = rel.dot(fwd)
        depth[i] = z
        z = max(z, 1e-6)
        px[i, 0] = res * 0.5 + rel.dot(right) / z * focal
        px[i, 1] = res * 0.5 - rel.dot(up) / z * focal
    cls = np.zeros((res, res), np.int8)
    zbuf = np.full((res, res), 1e18)
    for poly in obj.data.polygons:
        idx = list(poly.vertices)
        k = fclass[poly.index]
        for i in range(1, len(idx) - 1):
            tri = [idx[0], idx[i], idx[i + 1]]
            xs, ys, zs = px[tri, 0], px[tri, 1], depth[tri]
            X0 = max(0, int(np.floor(xs.min())))
            X1 = min(res - 1, int(np.ceil(xs.max())))
            Y0 = max(0, int(np.floor(ys.min())))
            Y1 = min(res - 1, int(np.ceil(ys.max())))
            if X1 < X0 or Y1 < Y0:
                continue
            gx, gy = np.meshgrid(np.arange(X0, X1 + 1) + 0.5, np.arange(Y0, Y1 + 1) + 0.5)
            (ax, ay), (bx, by), (cx, cy) = (xs[0], ys[0]), (xs[1], ys[1]), (xs[2], ys[2])
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-12:
                continue
            w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
            w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
            w2 = 1.0 - w0 - w1
            inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
            if not inside.any():
                continue
            z = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
            sub_z = zbuf[Y0:Y1 + 1, X0:X1 + 1]
            upd = inside & (z < sub_z)
            if upd.any():
                sub_z[upd] = z[upd]
                cls[Y0:Y1 + 1, X0:X1 + 1][upd] = k
    return cls


def score(obj, fclass, ref_norm, ref_sil, cfg, scale):
    mc = raster(obj, fclass, cfg, scale)
    m, box = norm_crop(mc)
    if box is None:
        return -1.0, {}
    sil_m = m != 0
    sil = (sil_m & ref_sil).sum() / float((sil_m | ref_sil).sum())
    tot, wsum, detail = 0.0, 0.0, {}
    for k in (C_ORANGE, C_AMBER, C_BLUE, C_DARK):
        mr, rr = (m == k), (ref_norm == k)
        union = (mr | rr).sum()
        if union < 50:
            continue
        iou = (mr & rr).sum() / float(union)
        detail[str(k)] = round(float(iou), 3)
        tot += WEIGHT[k] * iou
        wsum += WEIGHT[k]
    cls_iou = tot / max(wsum, 1e-9)
    detail["sil"] = round(float(sil), 3)
    detail["cls"] = round(float(cls_iou), 3)
    aspect_m = (box[3] - box[2] + 1) / float(box[1] - box[0] + 1)
    detail["aspect"] = round(aspect_m, 3)
    # 总分：色类与剪影各半（色类提供方位证据，剪影提供比例证据）
    return 0.5 * cls_iou + 0.5 * sil, detail


def main():
    obj = bpy.data.objects[OBJ]
    fclass = face_classes(obj)
    ref_cls = ref_classes()
    ref_norm, ref_box = norm_crop(ref_cls)
    ref_sil = ref_norm != 0
    print("[shape] ref aspect=%.4f" % ((ref_box[3] - ref_box[2] + 1) / (ref_box[1] - ref_box[0] + 1)))
    pts = np.array([[v.co.x, v.co.y, v.co.z] for v in obj.data.vertices])
    span = float(max(pts.max(0) - pts.min(0)))
    base = {"az": 30.0, "el": 14.0, "lens": 110.0, "dist": span * 3.6}

    def obj_fn(params):
        az, el, sx, sy, sz = params
        cfg = dict(base, az=az, el=el)
        return score(obj, fclass, ref_norm, ref_sil, cfg, (sx, sy, sz))

    best = (1.0, 1.0, 1.0, 30.0, 14.0)
    best_score = obj_fn([30.0, 14.0, 1.0, 1.0, 1.0])[0]
    print("[shape] start score=%.4f (unit scale)" % best_score)

    # 粗网格：az / sy（长度）/ sz（高度）；sx 与 sy 在投影上高度耦合，先一起扫
    grid = []
    for az in (18, 24, 30, 36, 42, 50):
        for sy in (0.80, 0.90, 1.00, 1.10, 1.20):
            for sz in (0.85, 0.95, 1.05, 1.15):
                s, d = obj_fn([az, 14.0, 1.0, sy, sz])
                grid.append((s, az, sy, sz, d))
    grid.sort(key=lambda r: -r[0])
    print("[shape] coarse top 6:")
    for s, az, sy, sz, d in grid[:6]:
        print("   %.4f az=%3d sy=%.2f sz=%.2f  %s" % (s, az, sy, sz, d))
    s0, az, sy, sz, _ = grid[0]
    best = [az, 14.0, 1.0, sy, sz]
    best_score = s0

    # 坐标下降细化
    steps = {"az": 4.0, "el": 3.0, "sx": 0.06, "sy": 0.06, "sz": 0.05}
    keys = ["az", "el", "sx", "sy", "sz"]
    for _ in range(14):
        improved = False
        for i, key in enumerate(keys):
            for sign in (1, -1):
                trial = list(best)
                trial[i] += sign * steps[key]
                s, _d = obj_fn(trial)
                if s > best_score + 1e-5:
                    best, best_score, improved = trial, s, True
        if not improved:
            steps = {k: v * 0.5 for k, v in steps.items()}
            if max(steps.values()) < 0.004:
                break
    s, d = obj_fn(best)
    print("[shape] refined score=%.4f  az=%.1f el=%.1f sx=%.3f sy=%.3f sz=%.3f  %s"
          % (s, best[0], best[1], best[2], best[3], best[4], d))
    print("[shape] => 建议尺寸（当前 AABB × 各轴缩放）：")
    size = [float(pts[:, i].max() - pts[:, i].min()) for i in range(3)]
    print("   L=%.3f m  W=%.3f m  H=%.3f m" % (size[1] * best[3], size[0] * best[2], size[2] * best[4]))
    if WRITE:
        with open(os.path.join(REFS, "shapefit.json"), "w", encoding="utf-8") as fh:
            json.dump({"score": round(s, 4), "detail": d,
                       "az": round(best[0], 2), "el": round(best[1], 2),
                       "scale": {"x": round(best[2], 4), "y": round(best[3], 4), "z": round(best[4], 4)},
                       "suggest_size_m": {"L": round(size[1] * best[3], 3),
                                          "W": round(size[0] * best[2], 3),
                                          "H": round(size[2] * best[4], 3)}},
                      fh, ensure_ascii=False, indent=2)
        print("[shape] wrote refs_out/shapefit.json")


main()
