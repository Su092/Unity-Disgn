# -*- coding: utf-8 -*-
"""发光/基色标定：渲染一张小图，测各材质在屏幕上的中位色，与参考图同色块比对，
反解 emission_strength。避免"自发光过曝成白"（蓝条/visor 会因此完全消失）。

用法：blender -b --factory-startup --python scripts/calibrate.py -- [--res 500]
"""
import json
import os
import subprocess
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
REFS = os.path.join(PROJ, "refs_out")
RENDERS = os.path.join(PROJ, "renders")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ARGS = dict(t.split("=", 1) for t in argv if "=" in t)
RES = int(ARGS.get("res", 500))

# 参考图各色块的中位色（scripts/palette_probe.py 实测，sRGB 0..1）
REF_TARGET = {
    "blue": (0.372, 0.763, 0.982),     # #5FC3FC 均值
    "visor": (0.996, 0.694, 0.098),    # #FEB119
    "amber": (0.878, 0.537, 0.118),    # #E0891E
    "orange": (0.820, 0.284, 0.155),   # #D1462A 受光面
    "dark": (0.115, 0.122, 0.133),     # #1D1F22 侧面
}


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(PROJ, "crawler.blend"))
    sc = bpy.context.scene
    sc.render.resolution_x = sc.render.resolution_y = RES
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = "RGBA"
    ground = bpy.data.objects.get("ENV-Ground")
    if ground:
        ground.hide_render = True
    out = os.path.join(RENDERS, "calib.png")
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)

    a = np.asarray(bpy.data.images.load(out).pixels[:]).reshape(RES, RES, 4)
    rgb = a[:, :, :3]
    alpha = a[:, :, 3]
    solid = alpha > 0.9

    # 按材质把面片投影到屏幕后取样（用 z-buffer 近似：取每类面片投影区域的像素中位色）
    obj = bpy.data.objects["GEO-Enemy-Crawler"]
    print("[calib] whole-object median (lit): %s" %
          [round(float(np.median(rgb[:, :, i][solid])), 3) for i in range(3)])

    # 直接测"最亮 N% 像素"与"蓝色饱和像素"，验证色相是否还在
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    mx = rgb.max(2)
    mn = rgb.min(2)
    sat = mx - mn
    blue_px = solid & (b > r + 0.10) & (b > 0.30)
    print("[calib] blue-class px=%d  median=%s"
          % (int(blue_px.sum()),
             [round(float(np.median(rgb[:, :, i][blue_px])), 3) for i in range(3)] if blue_px.any() else None))
    hot = solid & (mx > 0.97) & (sat < 0.08)
    print("[calib] white-clipped px=%d (%.1f%%)" % (int(hot.sum()), 100.0 * hot.sum() / max(solid.sum(), 1)))
    amber_px = solid & (r > b + 0.20) & (r > 0.55) & (g > 0.30) & (b < 0.45)
    print("[calib] amber/visor px=%d  median=%s"
          % (int(amber_px.sum()),
             [round(float(np.median(rgb[:, :, i][amber_px])), 3) for i in range(3)] if amber_px.any() else None))
    orange_px = solid & (r > b + 0.14) & (g / np.maximum(r, 1e-6) < 0.46) & (r > 0.25)
    print("[calib] orange px=%d  median=%s"
          % (int(orange_px.sum()),
             [round(float(np.median(rgb[:, :, i][orange_px])), 3) for i in range(3)] if orange_px.any() else None))


main()
