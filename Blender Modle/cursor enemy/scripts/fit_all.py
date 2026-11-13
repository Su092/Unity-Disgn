# -*- coding: utf-8 -*-
"""联合拟合：机位 (az, el, lens) + 轴向缩放 (sx, sy, sz)，最大化色类/剪影一致性。

判据来源见 scripts/refclass.py（G/R 色相分层，与渲染光照无关）。
反解结果写 refs_out/fit.json；缩放比用于回填 spec.json 的截面数字。

用法：
  blender -b crawler.blend --python scripts/fit_all.py -- [--res 320] [--write]
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import refclass as RC  # noqa: E402

PROJ = os.path.dirname(HERE)
REFS = os.path.join(PROJ, "refs_out")
OBJ = "GEO-Enemy-Crawler"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ARGS = dict(t.split("=", 1) for t in argv if "=" in t)
RES = int(ARGS.get("res", 320))
WRITE = "--write" in sys.argv
NORM = 320


def ref_norm():
    rgb = np.load(os.path.join(REFS, "ref_rgb.npy")).astype(np.float32) / 255.0
    cls = RC.classify(rgb)
    box = RC.bbox(cls)
    return RC.normalised(cls, box, NORM), box


def face_class(obj):
    names = [s.material.name for s in obj.material_slots]
    out = np.zeros(len(obj.data.polygons), np.int8)
    for poly in obj.data.polygons:
        n = names[poly.material_index] if poly.material_index < len(names) else ""
        if "Orange" in n:
            out[poly.index] = RC.ORANGE
        elif "Blue" in n:
            out[poly.index] = RC.BLUE
        elif "Amber" in n or "Visor" in n:
            out[poly.index] = RC.AMBER
        else:
            out[poly.index] = RC.DARK
    return out


def raster(obj, fclass, cfg, scale):
    verts = np.array([[v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]]
                      for v in obj.data.vertices], np.float64)
    center = np.array([0.0, 0.5 * (verts[:, 1].min() + verts[:, 1].max()),
                       0.5 * (verts[:, 2].min() + verts[:, 2].max())])
    az, el = math.radians(cfg["az"]), math.radians(cfg["el"])
    d = np.array([-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)])
    pos = center + d * cfg["dist"]
    fwd = (center - pos)
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, np.array([0.0, 0.0, 1.0]))
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    focal = cfg["lens"] / 36.0 * RES
    rel = verts - pos
    z = rel @ fwd
    z = np.maximum(z, 1e-6)
    px = RES * 0.5 + (rel @ right) / z * focal
    py = RES * 0.5 - (rel @ up) / z * focal
    cls = np.zeros((RES, RES), np.int8)
    zbuf = np.full((RES, RES), 1e18)
    for poly in obj.data.polygons:
        idx = poly.vertices
        k = fclass[poly.index]
        for i in range(1, len(idx) - 1):
            tri = [idx[0], idx[i], idx[i + 1]]
            xs, ys, zs = px[tri], py[tri], (rel[tri] @ fwd)
            X0 = max(0, int(np.floor(xs.min())))
            X1 = min(RES - 1, int(np.ceil(xs.max())))
            Y0 = max(0, int(np.floor(ys.min())))
            Y1 = min(RES - 1, int(np.ceil(ys.max())))
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
            zz = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
            sub = zbuf[Y0:Y1 + 1, X0:X1 + 1]
            upd = inside & (zz < sub)
            if upd.any():
                sub[upd] = zz[upd]
                cls[Y0:Y1 + 1, X0:X1 + 1][upd] = k
    return cls


def evaluate(obj, fclass, refn, cfg, scale, aspect_ref):
    mc = raster(obj, fclass, cfg, scale)
    box = RC.bbox(mc)
    if box is None:
        return -1.0, {}, None
    m = RC.normalised(mc, box, NORM)
    ious = RC.class_iou(m, refn)
    # 权重：色块类各 1（蓝条 2：体量小，容易被忽略而失真），深灰 0.5（体量最大、判别力最低）
    w = {"orange": 1.0, "amber": 1.0, "blue": 2.0, "dark": 0.5, "sil": 1.0}
    num = sum(w[k] * v for k, v in ious.items() if k in w)
    den = sum(w[k] for k in ious if k in w)
    cls = num / max(den, 1e-9)
    aspect = (box[3] - box[2] + 1) / float(box[1] - box[0] + 1)
    # 宽高比必须显式进总分：归一化 IoU 把 bbox 拉成同尺，比例信息会整体丢掉
    aspect_pen = 1.5 * abs(aspect - aspect_ref)
    return cls - aspect_pen, ious, aspect


def main():
    obj = bpy.data.objects[OBJ]
    fclass = face_class(obj)
    refn, ref_box = ref_norm()
    print("[fit] ref bbox=%s" % (ref_box,))
    print("[fit] ref class px: %s" % {RC.NAMES[k]: int((refn == k).sum()) for k in RC.NAMES})
    pts = np.array([[v.co.x, v.co.y, v.co.z] for v in obj.data.vertices])
    span = float(max(pts.max(0) - pts.min(0)))
    aspect_ref = (ref_box[3] - ref_box[2] + 1) / float(ref_box[1] - ref_box[0] + 1)

    def run(params):
        az, el, lens, sx, sy, sz = params
        cfg = {"az": az, "el": el, "lens": lens, "dist": span * (1.4 + lens / 60.0)}
        return evaluate(obj, fclass, refn, cfg, (sx, sy, sz), aspect_ref)

    start = [26.0, 16.0, 110.0, 1.0, 1.0, 1.0]
    best = list(start)
    best_score, ious, aspect = run(best)
    print("[fit] start score=%.4f aspect=%.3f(%.3f) %s" % (best_score, aspect, aspect_ref, ious))

    # 粗网格：优先 az/el（方位），缩放用三档
    coarse = []
    for az in (10, 18, 26, 34, 42, 50):
        for el in (10, 14, 18, 24, 30):
            for sy in (0.86, 1.0, 1.14):
                for sz in (0.92, 1.0, 1.08):
                    s, i, a = run([az, el, 110.0, 1.0, sy, sz])
                    coarse.append((s, az, el, sy, sz, i, a))
    coarse.sort(key=lambda r: -r[0])
    print("[fit] coarse top 8:")
    for s, az, el, sy, sz, i, a in coarse[:8]:
        print("   %.4f az=%3d el=%2d sy=%.2f sz=%.2f asp=%.3f %s" % (s, az, el, sy, sz, a, i))
    s, az, el, sy, sz, i, a = coarse[0]
    best = [az, el, 110.0, 1.0, sy, sz]
    best_score = s

    steps = [4.0, 3.0, 20.0, 0.05, 0.05, 0.04]
    for _ in range(18):
        improved = False
        for i2 in range(6):
            for sign in (1, -1):
                trial = list(best)
                trial[i2] += sign * steps[i2]
                if i2 == 2:
                    trial[2] = max(45.0, min(200.0, trial[2]))
                s, i, a = run(trial)
                if s > best_score + 1e-5:
                    best, best_score, improved = trial, s, True
        if not improved:
            steps = [x * 0.5 for x in steps]
            if max(steps[3:]) < 0.004:
                break

    s, i, a = run(best)
    print("[fit] final score=%.4f  az=%.1f el=%.1f lens=%.0f sx=%.3f sy=%.3f sz=%.3f aspect=%.3f"
          % (s, best[0], best[1], best[2], best[3], best[4], best[5], a))
    print("[fit] class IoU: %s" % i)
    size = [float(pts[:, i2].max() - pts[:, i2].min()) for i2 in range(3)]
    print("[fit] AABB → L=%.3f W=%.3f H=%.3f"
          % (size[1] * best[4], size[0] * best[3], size[2] * best[5]))

    if WRITE:
        cfg = {"az": round(best[0], 3), "el": round(best[1], 3), "lens": round(best[2], 1),
               "dist": round(span * (1.4 + best[2] / 60.0), 4),
               "target": [0.0, 0.5 * (pts[:, 1].min() + pts[:, 1].max()),
                          0.5 * (pts[:, 2].min() + pts[:, 2].max())],
               "shift_x": 0.0, "shift_y": 0.0}
        cfg = solve_framing(obj, cfg, best[3:6], ref_box)
        s2, i2_, a2 = run(best)
        out = {"score": round(s, 4), "class_iou": i, "aspect": a,
               "ref_aspect": round(aspect_ref, 4),
               "camera": cfg,
               "axis_scale": {"x": round(best[3], 4), "y": round(best[4], 4), "z": round(best[5], 4)},
               "suggest_size_m": {"L": round(size[1] * best[4], 3),
                                  "W": round(size[0] * best[3], 3),
                                  "H": round(size[2] * best[5], 3)}}
        with open(os.path.join(REFS, "fit.json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        with open(os.path.join(REFS, "camera.json"), "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=2)
        print("[fit] wrote refs_out/fit.json + camera.json")


def solve_framing(obj, cfg, scale, ref_box):
    """解 dist/shift，让按 scale 缩放后的模型投影 bbox 与参考 bbox 重合。"""
    verts = np.array([[v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]]
                      for v in obj.data.vertices])
    tw = ref_box[1] - ref_box[0]
    th = ref_box[3] - ref_box[2]
    res = 1254

    def bbox_at(dist, shift_x=0.0, shift_y=0.0):
        az, el = math.radians(cfg["az"]), math.radians(cfg["el"])
        d = np.array([-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)])
        t = np.array(cfg["target"])
        pos = t + d * dist
        fwd = (t - pos) / np.linalg.norm(t - pos)
        right = np.cross(fwd, np.array([0.0, 0.0, 1.0]))
        right /= np.linalg.norm(right)
        up = np.cross(right, fwd)
        focal = cfg["lens"] / 36.0 * res
        rel = verts - pos
        z = np.maximum(rel @ fwd, 1e-6)
        x = res * (0.5 + shift_x) + (rel @ right) / z * focal
        y = res * (0.5 + shift_y) - (rel @ up) / z * focal
        return x.min(), x.max(), y.min(), y.max()

    lo, hi = 0.2, 400.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        x0, x1, y0, y1 = bbox_at(mid)
        if max((x1 - x0) / tw, (y1 - y0) / th) > 1.0:
            lo = mid
        else:
            hi = mid
    cfg["dist"] = round(0.5 * (lo + hi), 4)
    x0, x1, y0, y1 = bbox_at(cfg["dist"])
    cfg["shift_x"] = round((0.5 * (ref_box[0] + ref_box[1]) - 0.5 * (x0 + x1)) / res, 5)
    cfg["shift_y"] = round((0.5 * (ref_box[2] + ref_box[3]) - 0.5 * (y0 + y1)) / res, 5)
    x0, x1, y0, y1 = bbox_at(cfg["dist"], cfg["shift_x"], cfg["shift_y"])
    print("[fit] framing x[%.0f,%.0f] y[%.0f,%.0f] vs ref x[%d,%d] y[%d,%d]"
          % (x0, x1, y0, y1, ref_box[0], ref_box[1], ref_box[2], ref_box[3]))
    return cfg


main()
