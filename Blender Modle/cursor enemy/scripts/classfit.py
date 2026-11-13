# -*- coding: utf-8 -*-
"""机位拟合（色类 IoU 通路）：把模型按**面材质**光栅化成色类图（无光照），
与参考图同口径色类图逐类比 IoU。

为什么不是剪影 IoU：本案轮廓近方形，剪影 IoU 对 az 有对称简并
（实测 az=0/el=34 与 3/4 视角得分几乎相同）。色类里有**不对称证据**
（visor 只在头部、蓝条只在壳前斜面、侧条只在两舷），没有简并。

色类（与 scripts/measure_shot.py 同口径，见 spec.md §0）：
  1 orange 壳   2 amber 带/visor   3 blue 条   4 dark 灰/黑   0 背景

用法：
  blender -b crawler.blend --python scripts/classfit.py -- [--grid] [--write]
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
RES = 480                    # 拟合分辨率（够了：色块都在 100+ px 量级）
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GRID = "--grid" in sys.argv
WRITE = "--write" in sys.argv
REF_RES = 1254

C_ORANGE, C_AMBER, C_BLUE, C_DARK = 1, 2, 3, 4
CLASS_NAMES = {C_ORANGE: "orange", C_AMBER: "amber", C_BLUE: "blue", C_DARK: "dark"}
WEIGHT = {C_ORANGE: 1.0, C_AMBER: 1.0, C_BLUE: 1.0, C_DARK: 0.7}


# ---------------------------------------------------------------- 参考色类图
def ref_classes():
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
    ys, xs = np.nonzero(cls)
    return cls, (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()))


# ---------------------------------------------------------------- 相机
def project(verts, cfg, res):
    az, el = math.radians(cfg["az"]), math.radians(cfg["el"])
    t = Vector(cfg["target"])
    d = Vector((-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    pos = t + d * cfg["dist"]
    fwd = (t - pos).normalized()
    right = fwd.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(fwd).normalized()
    focal = cfg["lens"] / 36.0 * res
    cx = res * 0.5
    cy = res * 0.5
    px = np.zeros((len(verts), 2))
    depth = np.zeros(len(verts))
    for i, v in enumerate(verts):
        rel = v - pos
        z = rel.dot(fwd)
        depth[i] = z
        z = max(z, 1e-6)
        px[i, 0] = cx + rel.dot(right) / z * focal
        px[i, 1] = cy - rel.dot(up) / z * focal
    return px, depth


def raster_classes(mesh, face_class, cfg, res=RES):
    verts = [v.co.copy() for v in mesh.vertices]
    px, depth = project(verts, cfg, res)
    cls = np.zeros((res, res), np.int8)
    zbuf = np.full((res, res), 1e18, np.float64)
    for poly in mesh.polygons:
        idx = list(poly.vertices)
        k = face_class[poly.index]
        for i in range(1, len(idx) - 1):
            tri = [idx[0], idx[i], idx[i + 1]]
            xs = px[tri, 0]
            ys = px[tri, 1]
            zs = depth[tri]
            X0 = max(0, int(np.floor(xs.min())))
            X1 = min(res - 1, int(np.ceil(xs.max())))
            Y0 = max(0, int(np.floor(ys.min())))
            Y1 = min(res - 1, int(np.ceil(ys.max())))
            if X1 < X0 or Y1 < Y0:
                continue
            gx, gy = np.meshgrid(np.arange(X0, X1 + 1) + 0.5, np.arange(Y0, Y1 + 1) + 0.5)
            (ax, ay), (bx, by), (cx2, cy2) = (xs[0], ys[0]), (xs[1], ys[1]), (xs[2], ys[2])
            den = (by - cy2) * (ax - cx2) + (cx2 - bx) * (ay - cy2)
            if abs(den) < 1e-12:
                continue
            w0 = ((by - cy2) * (gx - cx2) + (cx2 - bx) * (gy - cy2)) / den
            w1 = ((cy2 - ay) * (gx - cx2) + (ax - cx2) * (gy - cy2)) / den
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


def norm_crop(arr, is_class, size=RES):
    """裁到非零 bbox 并最近邻缩放到 size×size。"""
    ys, xs = np.nonzero(arr != 0) if is_class else np.nonzero(arr)
    if len(xs) == 0:
        return np.zeros((size, size), np.int8), None
    crop = arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = crop.shape
    yi = (np.arange(size) * h // size).astype(np.int32)
    xi = (np.arange(size) * w // size).astype(np.int32)
    return crop[yi][:, xi], (int(xs.min()), int(ys.max() if False else xs.max()),
                             int(ys.min()), int(ys.max()))


def score_classes(model_cls, ref_cls, ref_box_aspect):
    m, mbox = norm_crop(model_cls, True, RES)
    r, rbox = norm_crop(ref_cls, True, RES)
    ious = {}
    total = 0.0
    wsum = 0.0
    for k, name in CLASS_NAMES.items():
        mr = m == k
        rr = r == k
        union = (mr | rr).sum()
        if union < 40:
            continue
        iou = (mr & rr).sum() / float(union)
        ious[name] = round(float(iou), 4)
        total += WEIGHT[k] * iou
        wsum += WEIGHT[k]
    sil_m = m != 0
    sil_r = r != 0
    sil = (sil_m & sil_r).sum() / float((sil_m | sil_r).sum())
    ious["sil"] = round(float(sil), 4)
    aspect = (mbox[3] - mbox[2] + 1) / float(mbox[1] - mbox[0] + 1)
    return total / max(wsum, 1e-9), ious, aspect


def face_classes(obj):
    names = [s.material.name for s in obj.material_slots]
    out = []
    for poly in obj.data.polygons:
        n = names[poly.material_index] if poly.material_index < len(names) else ""
        if "Shell" in n:
            out.append(C_ORANGE)
        elif "Vent" in n or "Blue" in n:
            out.append(C_BLUE)
        elif "Band" in n or "Visor" in n or "Amber" in n:
            out.append(C_AMBER)
        else:
            out.append(C_DARK)
    return out


def main():
    obj = bpy.data.objects[OBJ]
    ref_cls, ref_box = ref_classes()
    print("[class] ref bbox=%s" % (ref_box,))
    fclass = face_classes(obj)
    counts = {CLASS_NAMES[k]: fclass.count(k) for k in CLASS_NAMES}
    print("[class] model faces per class: %s" % counts)

    pts = np.array([v.co[:] for v in obj.data.vertices])
    target = [float(0.5 * (pts[:, i].min() + pts[:, i].max())) for i in range(3)]
    span = float(max(pts.max(0) - pts.min(0)))
    ref_aspect = (ref_box[3] - ref_box[2] + 1) / float(ref_box[1] - ref_box[0] + 1)

    def cfg_of(az, el, lens):
        return {"az": float(az), "el": float(el), "lens": lens,
                "dist": span * (2.2 + lens / 70.0), "target": target}

    rows = []
    if GRID:
        for lens in (85.0, 110.0):
            for az in range(-80, 121, 5):
                for el in (10, 14, 18, 22, 26, 30, 36):
                    cfg = cfg_of(az, el, lens)
                    mc = raster_classes(obj.data, fclass, cfg)
                    s, ious, aspect = score_classes(mc, ref_cls, ref_aspect)
                    rows.append((s, az, el, lens, ious, aspect))
        rows.sort(key=lambda r: -r[0])
        print("top 12 by colour-class IoU (mean over classes):")
        for s, az, el, lens, ious, aspect in rows[:12]:
            print("  %.4f az=%4d el=%2d lens=%3.0f  aspect=%.3f  %s"
                  % (s, az, el, lens, aspect, ious))
        best = rows[0]
    else:
        path = os.path.join(REFS, "camera.json")
        cfg = json.load(open(path, "r", encoding="utf-8"))
        mc = raster_classes(obj.data, fclass, cfg)
        s, ious, aspect = score_classes(mc, ref_cls, ref_aspect)
        best = (s, cfg["az"], cfg["el"], cfg.get("lens", 85.0), ious, aspect)
        print("[class] saved camera score=%.4f aspect=%.3f %s" % (s, aspect, ious))

    s, az, el, lens, ious, aspect = best
    if WRITE:
        cfg = cfg_of(az, el, lens)
        cfg = solve_framing(obj, fclass, cfg, ref_box)
        mc = raster_classes(obj.data, fclass, cfg)
        s, ious, aspect = score_classes(mc, ref_cls, ref_aspect)
        print("[class] FINAL score=%.4f aspect=%.4f (ref %.4f)  %s"
              % (s, aspect, ref_aspect, ious))
        for k in ("az", "el", "dist", "shift_x", "shift_y"):
            cfg[k] = round(float(cfg[k]), 5)
        with open(os.path.join(REFS, "camera.json"), "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=2)
        with open(os.path.join(REFS, "classfit.json"), "w", encoding="utf-8") as fh:
            json.dump({"score": round(s, 4), "class_iou": ious, "aspect": aspect,
                       "camera": cfg}, fh, ensure_ascii=False, indent=2)
        print("[class] wrote refs_out/camera.json + classfit.json")
        print(json.dumps(cfg, ensure_ascii=False))


def solve_framing(obj, fclass, cfg, ref_box):
    """解 dist + shift，使投影 bbox 与参考 bbox 同位同尺度（只影响取景）。"""
    verts = [v.co.copy() for v in obj.data.vertices]
    tw = ref_box[1] - ref_box[0]
    th = ref_box[3] - ref_box[2]

    def bbox_at(dist):
        c = dict(cfg)
        c["dist"] = dist
        px, _ = project(verts, c, REF_RES)
        return px[:, 0].min(), px[:, 0].max(), px[:, 1].min(), px[:, 1].max()

    lo, hi = 0.3, 300.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        x0, x1, y0, y1 = bbox_at(mid)
        frac = max((x1 - x0) / tw, (y1 - y0) / th)
        if frac > 1.0:
            lo = mid
        else:
            hi = mid
    cfg["dist"] = 0.5 * (lo + hi)
    x0, x1, y0, y1 = bbox_at(cfg["dist"])
    cfg["shift_x"] = (0.5 * (ref_box[0] + ref_box[1]) - 0.5 * (x0 + x1)) / REF_RES
    cfg["shift_y"] = (0.5 * (ref_box[2] + ref_box[3]) - 0.5 * (y0 + y1)) / REF_RES
    x0, x1, y0, y1 = bbox_at(cfg["dist"])
    print("[class] framing: model x[%.0f,%.0f] y[%.0f,%.0f] ref x[%d,%d] y[%d,%d]"
          % (x0, x1, y0, y1, ref_box[0], ref_box[1], ref_box[2], ref_box[3]))
    return cfg


main()
