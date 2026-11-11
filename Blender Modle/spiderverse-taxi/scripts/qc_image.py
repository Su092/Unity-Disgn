# -*- coding: utf-8 -*-
"""图片数值 QC（L0 级证据）：不靠"看着对"。

对渲染图：估背景色 → 主体轮廓 bbox（像素/归一化/像素比）→ 与期望取景对拍。
对参考图：找"出租车黄"像素 → 主体 bbox → 长/高比（量参考图用）。

用法：
  blender -b --factory-startup --python scripts/qc_image.py -- <png> [<png> ...]
"""

import sys

import bpy

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []


def load_pixels(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = list(img.pixels[:])          # 行序自下而上
    return px, w, h


def stats(path):
    px, w, h = load_pixels(path)
    n = w * h

    def at(x, y):
        i = (y * w + x) * 4
        return px[i], px[i + 1], px[i + 2]

    # 背景色 = 四角像素均值
    corners = [at(1, 1), at(w - 2, 1), at(1, h - 2), at(w - 2, h - 2)]
    bg = tuple(sum(c[k] for c in corners) / 4.0 for k in range(3))

    def is_subject(c):
        return (abs(c[0] - bg[0]) + abs(c[1] - bg[1]) + abs(c[2] - bg[2])) > 0.06

    def is_yellow(c):
        r, g, b = c
        return r > 0.30 and r > b * 1.6 and g > b * 1.2 and (r - g) < 0.45

    def is_red(c):
        r, g, b = c
        return r > 0.24 and r > g * 1.7 and r > b * 1.7 and (r - g) > 0.14

    xs, ys, subj, yellow, red = [], [], 0, 0, 0
    for y in range(h):
        for x in range(w):
            c = at(x, y)
            if is_subject(c):
                subj += 1
                xs.append(x)
                ys.append(y)
            if is_yellow(c):
                yellow += 1
            if is_red(c):
                red += 1
    if not xs:
        print("%s: 无主体像素（背景 %s）" % (path, [round(v, 3) for v in bg]))
        return
    bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
    wpx, hpx = bx1 - bx0 + 1, by1 - by0 + 1
    mean = [sum(px[i::4]) / n for i in range(3)]
    print("%s" % path)
    print("   size=%dx%d  bg=%s  mean=%.3f/%.3f/%.3f"
          % (w, h, [round(v, 3) for v in bg], mean[0], mean[1], mean[2]))
    print("   subject_bbox_px=[%d,%d,%d,%d]  w=%d h=%d  ratio=%.4f  fill=%.3f"
          % (bx0, bx1, by0, by1, wpx, hpx, wpx / float(hpx), subj / float(n)))
    print("   yellow_px=%.3f  red_px=%.3f  bbox_norm=[%.3f,%.3f,%.3f,%.3f]"
          % (yellow / float(n), red / float(n), bx0 / w, by0 / h, bx1 / w, by1 / h))


for p in argv:
    stats(p)
