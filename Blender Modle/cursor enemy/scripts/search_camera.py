# -*- coding: utf-8 -*-
"""机位搜索：渲一组低分辨率候选 → 用与参考图**同一套**量测脚本算色块中心，
按色块中心距离打分。IoU 在近方形轮廓上有对称简并，色块位置没有。

用法：
  blender -b crawler.blend --python scripts/search_camera.py -- [--res 560] [--write]
"""
import json
import math
import os
import subprocess
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
REFS = os.path.join(PROJ, "refs_out")
RENDERS = os.path.join(PROJ, "renders")
SEARCH = os.path.join(RENDERS, "search")
os.makedirs(SEARCH, exist_ok=True)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ARGS = dict(t.split("=", 1) for t in argv if "=" in t)
RES = int(ARGS.get("res", 560))
WRITE = "--write" in sys.argv

# 参考图色块中心（归一化到主体 bbox），来自 structures.py / components.py
REF_CUES = {
    "visor": (0.818, 0.516),
    "blue": (0.6775, 0.1925),
    "flank": (0.2875, 0.429),
    "legA": (0.077, 0.634),
    "legB": (0.371, 0.749),
    "legC": (0.917, 0.746),
}
WEIGHTS = {"visor": 1.0, "blue": 1.0, "flank": 1.0, "legA": 0.7, "legB": 0.7, "legC": 0.7}


def place_camera(cam, cfg):
    az, el = math.radians(cfg["az"]), math.radians(cfg["el"])
    target = Vector(cfg["target"])
    d = Vector((-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam.location = target + d * cfg["dist"]
    cam.rotation_euler = (target - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = cfg["lens"]
    cam.data.shift_x = 0.0
    cam.data.shift_y = 0.0
    bpy.context.view_layer.update()


def measure(path):
    """调外部 Python（有 PIL）跑 measure_ref 的 JSON 输出。"""
    out = path + ".json"
    subprocess.run(["python", os.path.join(HERE, "measure_shot.py"), path, out],
                   check=True, capture_output=True)
    with open(out, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main():
    sc = bpy.context.scene
    obj = bpy.data.objects["GEO-Enemy-Crawler"]
    cam = bpy.data.objects["CAM-Hero"]
    sc.render.resolution_x = sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = "RGBA"
    ground = bpy.data.objects.get("ENV-Ground")
    if ground:
        ground.hide_render = True

    pts = np.array([v.co[:] for v in obj.data.vertices])
    target = [float(0.5 * (pts[:, i].min() + pts[:, i].max())) for i in range(3)]
    span = float(max(pts[:, 0].max() - pts[:, 0].min(),
                     pts[:, 1].max() - pts[:, 1].min(),
                     pts[:, 2].max() - pts[:, 2].min()))

    rows = []
    for az in range(30, 96, 6):
        for el in (14, 18, 22, 26, 30):
            cfg = {"az": az, "el": el, "lens": 85.0, "dist": span * 3.4, "target": target}
            place_camera(cam, cfg)
            tag = "az%03d_el%02d" % (az, el)
            path = os.path.join(SEARCH, tag + ".png")
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            try:
                m = measure(path)
            except Exception as exc:                      # noqa: BLE001
                print("  %s measure failed: %s" % (tag, exc))
                continue
            cues = m.get("cues") or {}
            err, hit = 0.0, 0
            detail = []
            for k, (rx, ry) in REF_CUES.items():
                if k not in cues:
                    err += 0.25 * WEIGHTS[k]
                    detail.append("%s:miss" % k)
                    continue
                cx, cy = cues[k]
                d = abs(cx - rx) + abs(cy - ry)
                err += WEIGHTS[k] * d
                hit += 1
                detail.append("%s:%.3f" % (k, d))
            rows.append((err, az, el, hit, " ".join(detail)))
            print("  %s err=%.4f hit=%d  %s" % (tag, err, hit, " ".join(detail)))

    rows.sort(key=lambda r: r[0])
    print("\ntop 8:")
    for err, az, el, hit, detail in rows[:8]:
        print("  err=%.4f az=%3d el=%2d hit=%d  %s" % (err, az, el, hit, detail))

    if WRITE and rows:
        err, az, el, hit, _ = rows[0]
        cfg = {"az": float(az), "el": float(el), "lens": 85.0,
               "dist": round(span * 3.4, 4), "target": [round(v, 4) for v in target],
               "shift_x": 0.0, "shift_y": 0.0}
        with open(os.path.join(REFS, "camera_coarse.json"), "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=2)
        print("[search] coarse camera -> refs_out/camera_coarse.json")


main()
