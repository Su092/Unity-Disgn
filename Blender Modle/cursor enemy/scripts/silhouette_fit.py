# -*- coding: utf-8 -*-
"""剪影拟合：透视投影光栅化 + 与参考图**归一化剪影**比 IoU / 轮廓误差。

为什么归一化：机位（dist/shift）只影响取景，不影响形体。把两边都裁到主体 bbox
再等比缩到同一尺寸，比的就是"形状"，与取景解耦。取景另用 solve_framing() 解。

用法：
  blender -b crawler.blend --python scripts/silhouette_fit.py -- [--grid] [--write]
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
GRID = "--grid" in sys.argv
WRITE = "--write" in sys.argv
RES = 1254        # 参考图分辨率（取景解算用）
NORM = 256        # 归一化剪影分辨率（IoU 用）


# ---------------------------------------------------------------- 参考掩膜
def ref_mask():
    return np.load(os.path.join(REFS, "mask.npy")).astype(bool)


def norm_crop(mask, size=NORM):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return np.zeros((size, size), bool), None
    crop = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    img = np.array([[False]])
    # 最近邻缩放（纯 numpy，避免 PIL 依赖）
    h, w = crop.shape
    yi = (np.arange(size) * h // size).astype(np.int32)
    xi = (np.arange(size) * w // size).astype(np.int32)
    return crop[yi][:, xi], (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()))


# ---------------------------------------------------------------- 相机
def cam_basis(cfg):
    az, el = math.radians(cfg["az"]), math.radians(cfg["el"])
    target = Vector(cfg["target"])
    d = Vector((-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    pos = target + d * cfg["dist"]
    fwd = (target - pos).normalized()
    right = fwd.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(fwd).normalized()
    return pos, fwd, right, up


def project(verts, cfg, res=RES):
    pos, fwd, right, up = cam_basis(cfg)
    focal = cfg["lens"] / 36.0 * res
    cx = res * (0.5 + cfg.get("shift_x", 0.0))
    cy = res * (0.5 + cfg.get("shift_y", 0.0))
    out = np.zeros((len(verts), 2), np.float64)
    depth = np.zeros(len(verts), np.float64)
    for i, v in enumerate(verts):
        rel = v - pos
        z = rel.dot(fwd)
        depth[i] = z
        z = max(z, 1e-6)
        out[i, 0] = cx + rel.dot(right) / z * focal
        out[i, 1] = cy - rel.dot(up) / z * focal
    return out, depth


def rasterize(mesh, cfg, res=RES):
    verts = [v.co.copy() for v in mesh.vertices]
    proj, _depth = project(verts, cfg, res)
    mask = np.zeros((res, res), bool)
    for poly in mesh.polygons:
        idx = list(poly.vertices)
        for i in range(1, len(idx) - 1):
            tri = [idx[0], idx[i], idx[i + 1]]
            xs = proj[tri, 0]
            ys = proj[tri, 1]
            X0 = max(0, int(np.floor(xs.min())))
            X1 = min(res - 1, int(np.ceil(xs.max())))
            Y0 = max(0, int(np.floor(ys.min())))
            Y1 = min(res - 1, int(np.ceil(ys.max())))
            if X1 < X0 or Y1 < Y0 or X1 - X0 > res or Y1 - Y0 > res:
                continue
            gx, gy = np.meshgrid(np.arange(X0, X1 + 1) + 0.5, np.arange(Y0, Y1 + 1) + 0.5)
            (ax, ay), (bx, by), (cx2, cy2) = (xs[0], ys[0]), (xs[1], ys[1]), (xs[2], ys[2])
            den = (by - cy2) * (ax - cx2) + (cx2 - bx) * (ay - cy2)
            if abs(den) < 1e-12:
                continue
            w0 = ((by - cy2) * (gx - cx2) + (cx2 - bx) * (gy - cy2)) / den
            w1 = ((cy2 - ay) * (gx - cx2) + (ax - cx2) * (gy - cy2)) / den
            w2 = 1.0 - w0 - w1
            inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if inside.any():
                mask[Y0:Y1 + 1, X0:X1 + 1] |= inside
    return mask


# ---------------------------------------------------------------- 误差
def profile_errors(A, B, n=21):
    """归一化剪影的上/下轮廓采样误差（A=参考，B=模型）。z 越大越靠上。"""
    ea, eb = [], []
    for k in range(n):
        x = int(round((NORM - 1) * k / (n - 1.0)))
        ca = np.nonzero(A[:, x])[0]
        cb = np.nonzero(B[:, x])[0]
        ta = 1.0 - ca.min() / float(NORM - 1) if len(ca) else 0.0
        tb = 1.0 - cb.min() / float(NORM - 1) if len(cb) else 0.0
        ba = ca.max() / float(NORM - 1) if len(ca) else 1.0
        bb = cb.max() / float(NORM - 1) if len(cb) else 1.0
        ea.append(ta - tb)
        eb.append(ba - bb)
    return np.array(ea), np.array(eb)


def evaluate(mesh, cfg, ref_norm):
    m = rasterize(mesh, cfg)
    b, box = norm_crop(m)
    if box is None:
        return 0.0, 1e9, 1e9, None
    iou = (ref_norm & b).sum() / float((ref_norm | b).sum())
    et, eb = profile_errors(ref_norm, b)
    rms = float(np.sqrt((et ** 2).mean()))
    rmsb = float(np.sqrt((eb ** 2).mean()))
    h_over_l = (box[3] - box[2] + 1) / float(box[1] - box[0] + 1)
    return iou, rms, rmsb, {"bbox": box, "H_over_L": round(h_over_l, 4),
                            "top_err": [round(float(v), 3) for v in et],
                            "bottom_err": [round(float(v), 3) for v in eb]}


def solve_framing(mesh, cfg, ref_box):
    """解 dist + shift，让投影 bbox 与参考 bbox 对齐（取景，不影响形体判定）。"""
    verts = [v.co.copy() for v in mesh.vertices]
    tw = ref_box[1] - ref_box[0]
    th = ref_box[3] - ref_box[2]

    def bbox_at(dist):
        c = dict(cfg)
        c["dist"] = dist
        p, _ = project(verts, c, RES)
        return p[:, 0].min(), p[:, 0].max(), p[:, 1].min(), p[:, 1].max()

    lo, hi = 0.3, 200.0
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
    cfg["shift_x"] = (0.5 * (ref_box[0] + ref_box[1]) - 0.5 * (x0 + x1)) / RES
    cfg["shift_y"] = (0.5 * (ref_box[2] + ref_box[3]) - 0.5 * (y0 + y1)) / RES
    x0, x1, y0, y1 = bbox_at(cfg["dist"])
    print("[frame] projected x[%.0f,%.0f] y[%.0f,%.0f]  ref x[%d,%d] y[%d,%d]"
          % (x0, x1, y0, y1, ref_box[0], ref_box[1], ref_box[2], ref_box[3]))
    return cfg


def main():
    obj = bpy.data.objects[OBJ]
    rm = ref_mask()
    ref_norm, ref_box = norm_crop(rm)
    print("[fit] ref bbox=%s  aspect=%.4f" % (ref_box, (ref_box[3] - ref_box[2]) / (ref_box[1] - ref_box[0])))

    pts = np.array([v.co[:] for v in obj.data.vertices])
    target = [float(0.5 * (pts[:, i].min() + pts[:, i].max())) for i in range(3)]
    span = float(max(pts.max(0) - pts.min(0)))

    def cfg_of(az, el, lens=85.0):
        return {"az": float(az), "el": float(el), "lens": lens,
                "dist": span * (2.0 + lens / 70.0), "target": target,
                "shift_x": 0.0, "shift_y": 0.0}

    if GRID:
        rows = []
        for az in range(-180, 180, 5):
            for el in (8, 12, 16, 20, 24, 28, 34):
                iou, rms, rmsb, info = evaluate(obj.data, cfg_of(az, el), ref_norm)
                rows.append((iou, az, el, rms, rmsb, info))
        rows.sort(key=lambda r: -r[0])
        print("top 10 by normalised silhouette IoU:")
        for iou, az, el, rms, rmsb, info in rows[:10]:
            print("  IoU=%.4f az=%4d el=%2d  topRMS=%.3f botRMS=%.3f  H/L=%.3f"
                  % (iou, az, el, rms, rmsb, info["H_over_L"]))
        if not WRITE:
            return
        iou, az, el, rms, rmsb, info = rows[0]
        cfg = cfg_of(az, el)
    else:
        path = os.path.join(REFS, "camera.json")
        cfg = json.load(open(path, "r", encoding="utf-8")) if os.path.exists(path) else cfg_of(35, 16)
        cfg["target"] = target
        iou, rms, rmsb, info = evaluate(obj.data, cfg, ref_norm)
        print("[fit] IoU=%.4f topRMS=%.3f botRMS=%.3f H/L=%.3f az=%.0f el=%.0f"
              % (iou, rms, rmsb, info["H_over_L"], cfg["az"], cfg["el"]))

    cfg = {"az": cfg["az"], "el": cfg["el"], "lens": cfg.get("lens", 85.0),
           "dist": cfg["dist"], "target": target, "shift_x": 0.0, "shift_y": 0.0}
    cfg = solve_framing(obj.data, cfg, ref_box)
    iou, rms, rmsb, info = evaluate(obj.data, cfg, ref_norm)
    print("[fit] final IoU=%.4f topRMS=%.3f botRMS=%.3f  az=%.1f el=%.1f lens=%.0f dist=%.3f"
          % (iou, rms, rmsb, cfg["az"], cfg["el"], cfg["lens"], cfg["dist"]))
    print("[fit] top_err   : %s" % info["top_err"])
    print("[fit] bottom_err: %s" % info["bottom_err"])

    if WRITE:
        for k in ("az", "el", "dist", "shift_x", "shift_y"):
            cfg[k] = round(float(cfg[k]), 5)
        with open(os.path.join(REFS, "camera.json"), "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=2)
        with open(os.path.join(REFS, "fit_report.json"), "w", encoding="utf-8") as fh:
            json.dump({"IoU": round(iou, 4), "top_rms": round(rms, 4),
                       "bottom_rms": round(rmsb, 4), "camera": cfg,
                       "profile": info}, fh, ensure_ascii=False, indent=2)
        print("[fit] wrote refs_out/camera.json + fit_report.json")


main()
