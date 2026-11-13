# -*- coding: utf-8 -*-
"""机位定标（真实渲染 + 统一色相分类）：在 (az, el) 小网格上渲小图，按色块 L1 选最优。

为什么不用解析投影：色块是"面片在光照下的可见区域"，解析投影拿不到遮挡与可见性；
小图渲染 420px 约 8 s，30 个候选 ≈ 4 分钟，可接受。

判据（与 scripts/compare.py 完全同一套 refclass 分类）：
    visor_core / blue / sideband / legband 的归一化中心 L1 + 宽高比偏差

用法：
  blender -b crawler.blend --python scripts/calibrate_camera.py -- [--write]
"""
import json
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import refclass as RC  # noqa: E402

PROJ = os.path.dirname(HERE)
REFS = os.path.join(PROJ, "refs_out")
RENDERS = os.path.join(PROJ, "renders")
CAL = os.path.join(RENDERS, "calib")
os.makedirs(CAL, exist_ok=True)
OBJ = "GEO-Enemy-Crawler"
RES = 420
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
WRITE = "--write" in sys.argv

KEYS = ("visor_core", "blue", "sideband", "legband")


def analyse_image(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(img)
    rgb = px[:, :, :3]
    alpha = px[:, :, 3]
    cls = RC.classify(rgb, mask=alpha > 0.5)
    box = RC.bbox(cls)
    if box is None:
        return None
    x0, x1, y0, y1 = box
    L, H = x1 - x0 + 1, y1 - y0 + 1
    out = {"H_over_L": H / float(L), "cues": {}}

    def c_of(m, minpx=40):
        yy, xx = np.nonzero(m)
        if len(xx) < minpx:
            return None
        return ((xx.mean() - x0) / L, (yy.mean() - y0) / H)

    for k, name in RC.NAMES.items():
        c = c_of(cls == k, 80)
        if c:
            out["cues"][name] = c
    c = c_of(RC.visor_mask(rgb, cls), 25)
    if c:
        out["cues"]["visor_core"] = c
    amb = cls == RC.AMBER
    upper = np.zeros_like(amb)
    upper[y0:int(y0 + H * 0.62)] = True
    vis = RC.visor_mask(rgb, cls)
    dil = vis.copy()
    for _ in range(2):
        shifted = np.zeros_like(dil)
        shifted[1:, :] |= dil[:-1, :]
        shifted[:-1, :] |= dil[1:, :]
        shifted[:, 1:] |= dil[:, :-1]
        shifted[:, :-1] |= dil[:, 1:]
        dil = shifted | dil
    c = c_of(amb & upper & ~dil, 150)
    if c:
        out["cues"]["sideband"] = c
    c = c_of(amb & ~upper & ~dil, 150)
    if c:
        out["cues"]["legband"] = c
    return out


def reference():
    a = np.load(os.path.join(REFS, "ref_rgb.npy")).astype(np.float32) / 255.0
    cls = RC.classify(a)
    box = RC.bbox(cls)
    x0, x1, y0, y1 = box
    L, H = x1 - x0 + 1, y1 - y0 + 1
    out = {"H_over_L": H / float(L), "cues": {}}

    def c_of(m, minpx=40):
        yy, xx = np.nonzero(m)
        if len(xx) < minpx:
            return None
        return ((xx.mean() - x0) / L, (yy.mean() - y0) / H)

    for k, name in RC.NAMES.items():
        c = c_of(cls == k, 200)
        if c:
            out["cues"][name] = c
    c = c_of(RC.visor_mask(a, cls), 80)
    if c:
        out["cues"]["visor_core"] = c
    amb = cls == RC.AMBER
    upper = np.zeros((a.shape[0], a.shape[1]), bool)
    upper[y0:int(y0 + H * 0.62)] = True
    vis = RC.visor_mask(a, cls)
    dil = vis.copy()
    for _ in range(3):
        shifted = np.zeros_like(dil)
        shifted[1:, :] |= dil[:-1, :]
        shifted[:-1, :] |= dil[1:, :]
        shifted[:, 1:] |= dil[:, :-1]
        shifted[:, :-1] |= dil[:, 1:]
        dil = shifted | dil
    c = c_of(amb & upper & ~dil, 400)
    if c:
        out["cues"]["sideband"] = c
    c = c_of(amb & ~upper & ~dil, 400)
    if c:
        out["cues"]["legband"] = c
    return out


def main():
    sc = bpy.context.scene
    cam = bpy.data.objects["CAM-Hero"]
    obj = bpy.data.objects[OBJ]
    ground = bpy.data.objects.get("ENV-Ground")
    if ground:
        ground.hide_render = True
    sc.render.resolution_x = sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.file_format = "PNG"

    with open(os.path.join(REFS, "camera.json"), "r", encoding="utf-8") as fh:
        base = json.load(fh)
    ref = reference()
    print("[cal] ref aspect=%.4f cues=%s" % (ref["H_over_L"], {k: tuple(round(v, 3) for v in ref["cues"][k])
                                                               for k in KEYS if k in ref["cues"]}))

    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    center = [0.5 * (min(p[i] for p in pts) + max(p[i] for p in pts)) for i in range(3)]
    span = max(max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3))

    rows = []
    for az in (30, 40, 50, 60, 70, 80, 95, 110):
        for el in (12, 18, 24, 30):
            cfg = dict(base)
            cfg.update({"az": float(az), "el": float(el), "target": center,
                        "dist": span * 2.6, "shift_x": 0.0, "shift_y": 0.0})
            place(cam, cfg)
            path = os.path.join(CAL, "az%03d_el%02d.png" % (az, el))
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            got = analyse_image(path)
            if not got:
                continue
            n = 0
            err = 0.0
            parts = []
            for k in KEYS:
                if k in ref["cues"] and k in got["cues"]:
                    d = abs(ref["cues"][k][0] - got["cues"][k][0]) + \
                        abs(ref["cues"][k][1] - got["cues"][k][1])
                    err += d
                    n += 1
                    parts.append("%s=%.3f" % (k, d))
                else:
                    err += 0.35
                    n += 1
                    parts.append("%s=miss" % k)
            asp = 2.0 * abs(got["H_over_L"] - ref["H_over_L"])
            score = err / max(n, 1) + asp
            rows.append((score, az, el, got["H_over_L"], " ".join(parts)))
            print("  az=%3d el=%2d score=%.4f aspect=%.3f  %s"
                  % (az, el, score, got["H_over_L"], " ".join(parts)))
    rows.sort(key=lambda r: r[0])
    print("\n[cal] top 5:")
    for score, az, el, asp, parts in rows[:5]:
        print("  score=%.4f az=%3d el=%2d aspect=%.3f  %s" % (score, az, el, asp, parts))

    if WRITE and rows:
        score, az, el, _asp, _p = rows[0]
        cfg = dict(base)
        cfg.update({"az": float(az), "el": float(el), "target": center})
        with open(os.path.join(REFS, "camera.json"), "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=2)
        print("[cal] wrote camera.json az=%.0f el=%.0f (dist/shift 由 build 的 fit_framing 现解)"
              % (az, el))


def place(cam, cfg):
    az, el = math.radians(cfg["az"]), math.radians(cfg["el"])
    target = __import__("mathutils").Vector(cfg["target"])
    d = __import__("mathutils").Vector((-math.sin(az) * math.cos(el),
                                        -math.cos(az) * math.cos(el), math.sin(el)))
    cam.location = target + d * cfg["dist"]
    cam.rotation_euler = (target - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = cfg.get("lens", 85.0)
    cam.data.shift_x = cfg.get("shift_x", 0.0)
    cam.data.shift_y = cfg.get("shift_y", 0.0)
    bpy.context.view_layer.update()


main()
