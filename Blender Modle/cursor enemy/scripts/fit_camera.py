# -*- coding: utf-8 -*-
"""相机拟合：用**解析剪影 IoU**（不渲染）在 (az, el) 网格上找最贴近参考图的机位。

为什么不用渲染：一次 EEVEE 渲染 ~2 s，网格 30×12 就是 6 分钟；解析投影是纯 numpy，
整个网格 3 秒。拟合完再用真实渲染复核（见 qa_compare.py）。

用法：
  blender -b crawler.blend --python scripts/fit_camera.py -- [--write]
    不带 --write 只打印网格；带 --write 把最优机位写 refs_out/camera.json
"""
import json
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
WRITE = "--write" in argv


def ref_mask():
    """参考图主体掩膜（由 scripts/prepare_ref.py 用系统 Python/PIL 预生成并落盘）。

    Blender 自带 Python 没有 PIL，所以掩膜在外部生成：refs_out/mask.npy。
    """
    mask = np.load(os.path.join(REFS, "mask.npy"))
    return mask.astype(bool)


def rasterize(mesh, cam_dir, up, res, box):
    """正交投影 + 相似变换（缩放/平移）把投影 bbox 对齐到 box，三角光栅化。"""
    right = up.cross(cam_dir).normalized()
    up2 = cam_dir.cross(right).normalized()
    pts = np.array([[(v.co - cam_target).dot(right),
                     (v.co - cam_target).dot(up2)] for v in mesh.vertices], np.float64)
    tris = []
    for poly in mesh.polygons:
        idx = list(poly.vertices)
        for i in range(1, len(idx) - 1):
            tris.append((idx[0], idx[i], idx[i + 1]))
    tris = np.array(tris, np.int32)

    x0, x1 = pts[:, 0].min(), pts[:, 0].max()
    y0, y1 = pts[:, 1].min(), pts[:, 1].max()
    bx0, bx1, by0, by1 = box
    sx = (bx1 - bx0) / max(x1 - x0, 1e-9)
    sy = (by1 - by0) / (y1 - y0) and (by1 - by0) / max(y1 - y0, 1e-9)
    s = min(sx, sy)
    ox = bx0 + ((bx1 - bx0) - (x1 - x0) * s) * 0.5
    oy = by0 + ((by1 - by0) - (y1 - y0) * s) * 0.5
    px = ox + (pts[:, 0] - x0) * s
    py = res - 1 - (oy + (pts[:, 1] - y0) * s)

    mask = np.zeros((res, res), bool)
    for tri in tris:
        xs = px[tri]
        ys = py[tri]
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
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if inside.any():
            mask[Y0:Y1 + 1, X0:X1 + 1] |= inside
    return mask


cam_target = Vector((0.0, 0.0, 0.62))


def main():
    global cam_target
    obj = bpy.data.objects[OBJ]
    bpy.context.view_layer.update()
    rm = ref_mask()
    ys, xs = np.nonzero(rm)
    box = (xs.min(), xs.max(), ys.min(), ys.max())
    res = rm.shape[0]
    ref_center = (0.5 * (xs.min() + xs.max()), 0.5 * (ys.min() + ys.max()))
    pts = np.array([v.co[:] for v in obj.data.vertices])
    cam_target = Vector((0.5 * (pts[:, 0].min() + pts[:, 0].max()),
                         0.5 * (pts[:, 1].min() + pts[:, 1].max()),
                         0.5 * (pts[:, 2].min() + pts[:, 2].max())))

    best = None
    rows = []
    for az in range(-180, 180, 6):
        for el in (6, 10, 14, 18, 22, 26, 30):
            a, e = np.radians(az), np.radians(el)
            d = Vector((-np.sin(a) * np.cos(e), -np.cos(a) * np.cos(e), np.sin(e)))
            up = Vector((0, 0, 1))
            m = rasterize(obj.data, d, up, res, box)
            inter = (m & rm).sum()
            union = (m | rm).sum()
            iou = inter / union if union else 0.0
            my, mx2 = np.nonzero(m)
            off = 0.0
            if len(mx2):
                off = abs((0.5 * (mx2.min() + mx2.max()) - ref_center[0]) / res) + \
                      abs((0.5 * (my.min() + my.max()) - ref_center[1]) / res)
            rows.append((iou, az, el, off))
    rows.sort(key=lambda r: -r[0])
    print("top 12 by silhouette IoU (bbox-normalised, ortho):")
    for iou, az, el, off in rows[:12]:
        print("  IoU=%.4f  az=%4d  el=%2d  centre_off=%.4f" % (iou, az, el, off))

    iou, az, el, off = rows[0]
    print("\nbest az=%d el=%d IoU=%.4f" % (az, el, iou))
    if WRITE:
        # 保持 lens 固定，用求解出的 bbox 比例反推透视距离（用真实投影做一次二分）
        cfg = {"az": float(az), "el": float(el), "lens": 85.0,
               "target": [round(v, 4) for v in cam_target], "dist": 6.0,
               "shift_x": 0.0, "shift_y": 0.0}
        cfg = solve_distance(cfg, box, res)
        os.makedirs(REFS, exist_ok=True)
        with open(os.path.join(REFS, "camera.json"), "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=2)
        print("[fit] camera.json -> %s" % os.path.join(REFS, "camera.json"))
        print(json.dumps(cfg, ensure_ascii=False, indent=2))


def solve_distance(cfg, box, res):
    """在真实透视投影下二分相机距离，让投影 bbox 长边占满参考 bbox；再用 shift 对中。"""
    from bpy_extras.object_utils import world_to_camera_view
    obj = bpy.data.objects[OBJ]
    sc = bpy.context.scene
    cam = bpy.data.objects["CAM-Hero"]

    def place(dist):
        a, e = np.radians(cfg["az"]), np.radians(cfg["el"])
        t = Vector(cfg["target"])
        d = Vector((-np.sin(a) * np.cos(e), -np.cos(a) * np.cos(e), np.sin(e)))
        cam.data.lens = cfg["lens"]
        cam.data.shift_x = cfg["shift_x"]
        cam.data.shift_y = cfg["shift_y"]
        cam.location = t + d * dist
        cam.rotation_euler = (t - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()

    def proj():
        xs, ys = [], []
        for v in obj.data.vertices:
            co = world_to_camera_view(sc, cam, v.co)
            xs.append(co.x * res)
            ys.append((1.0 - co.y) * res)
        return min(xs), max(xs), min(ys), max(ys)

    tw = box[1] - box[0]
    th = box[3] - box[2]
    lo, hi = 0.5, 80.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        place(mid)
        b = proj()
        frac = max((b[1] - b[0]) / tw, (b[3] - b[2]) / th)
        if frac > 1.0:
            lo = mid
        else:
            hi = mid
    cfg["dist"] = round(0.5 * (lo + hi), 4)
    place(cfg["dist"])
    b = proj()
    cfg["shift_x"] = round(cfg["shift_x"] + (((b[0] + b[1]) * 0.5 - 0.5 * (box[0] + box[1])) / res), 5)
    cfg["shift_y"] = round(cfg["shift_y"] - (((b[2] + b[3]) * 0.5 - 0.5 * (box[2] + box[3])) / res), 5)
    place(cfg["dist"])
    b = proj()
    print("[fit] projected bbox x[%.0f,%.0f] y[%.0f,%.0f]  ref x[%d,%d] y[%d,%d]"
          % (b[0], b[1], b[2], b[3], box[0], box[1], box[2], box[3]))
    return cfg


main()
