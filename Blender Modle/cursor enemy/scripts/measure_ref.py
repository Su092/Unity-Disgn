# -*- coding: utf-8 -*-
"""参考图量测（cursor enemy / ref_crawler.png）。

参考图口径：中性灰背景（luma≈0.467, sat<0.05），主体为深灰/橙/蓝的低模机器人。
分割 = 与背景灰差异足够大的像素 + 从四条边泛洪判背景（吃掉接触阴影里较亮的灰）。

输出（全部为像素口径，无标定不换算毫米）：
  · 整机 bbox、L/H 比、每列上/下轮廓 21 点
  · 关键色块 bbox（橙壳 / 蓝色条 / 发光橙 visor / 腿橙带）
  · ASCII 掩膜 + 色块分类图（O=橙 K=深灰 B=蓝 G=发光橙）

用法：
  python scripts/measure_ref.py ref_crawler.png --ascii --json out.json
"""
import json
import sys

import numpy as np
from PIL import Image

BG_LUMA = 0.467


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def classify(a):
    """返回 (mask, label_map)。label: 0=bg 1=dark 2=orange 3=blue 4=glow"""
    mx = a.max(2)
    mn = a.min(2)
    sat = mx - mn
    lum = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]

    bg_like = (sat < 0.045) & (np.abs(lum - BG_LUMA) < 0.055)
    mask = ~bg_like

    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    # 橙/黄：红显著高于蓝，绿居中
    orange = (r > 0.33) & (r > b + 0.16) & (g > 0.10)
    # 发光橙/琥珀：饱和度极高且亮度高
    glow = orange & (r > 0.72) & (g > 0.30)
    # 蓝：蓝显著高于红
    blue = (b > r + 0.10) & (b > 0.35) & (g > 0.30)
    dark = mask & ~orange & ~blue

    label = np.zeros(a.shape[:2], np.uint8)
    label[dark] = 1
    label[orange] = 2
    label[blue] = 3
    label[glow] = 4
    return mask, label


def bbox_of(mask):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()), int(len(xs))


def largest_runs(col_flags, x0):
    runs, cur = [], None
    for k, v in enumerate(col_flags):
        x = x0 + k
        if v:
            cur = [x, x] if cur is None else [cur[0], x]
        else:
            if cur and cur[1] - cur[0] > 3:
                runs.append(tuple(cur))
            cur = None
    if cur and cur[1] - cur[0] > 3:
        runs.append(tuple(cur))
    return runs


def analyze(path, ascii_dump=False, cols_n=90, rows_n=34):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32) / 255.0
    h, w, _ = a.shape
    mask, label = classify(a)
    out = {"path": path, "size": [w, h]}

    bb = bbox_of(mask)
    x0, x1, y0, y1 = bb[0], bb[1], bb[2], bb[3]
    L, H = x1 - x0 + 1, y1 - y0 + 1
    out["bbox"] = [x0, x1, y0, y1]
    out["L"] = L
    out["H"] = H
    out["H_over_L"] = round(H / L, 4)
    out["fill"] = round(bb[4] / float(w * h), 4)

    print("%s  %dx%d" % (path, w, h))
    print("  bbox x[%d,%d] y[%d,%d]  L=%d H=%d  H/L=%.4f  fill=%.3f"
          % (x0, x1, y0, y1, L, H, H / L, out["fill"]))

    # 每列上下轮廓
    top = np.full(w, -1, np.int32)
    bot = np.full(w, -1, np.int32)
    for x in range(x0, x1 + 1):
        col = np.nonzero(mask[:, x])[0]
        if len(col):
            top[x], bot[x] = col.min(), col.max()
    prof_t, prof_b = [], []
    for k in range(21):
        x = int(round(x0 + (L - 1) * k / 20.0))
        if top[x] >= 0:
            prof_t.append(round(1.0 - (top[x] - y0) / float(H - 1), 4))
            prof_b.append(round((bot[x] - y0) / float(H - 1), 4))
        else:
            prof_t.append(None)
            prof_b.append(None)
    out["top_profile"] = prof_t
    out["bottom_profile"] = prof_b
    print("  top(t=0..1)   : " + " ".join("%.2f" % v if v is not None else "--" for v in prof_t))
    print("  bottom(t=0..1): " + " ".join("%.2f" % v if v is not None else "--" for v in prof_b))

    # 最高点位置
    tz = np.where(top >= 0, top, 10 ** 6)
    hx = int(np.argmin(tz))
    out["highest_t"] = round((hx - x0) / float(L - 1), 4)
    print("  highest point at t=%.3f (x=%d, z=1.0)" % (out["highest_t"], hx))

    # 关键色块
    regions = {}
    for name, lab in (("orange", 2), ("blue", 3), ("glow", 4)):
        m = label == lab
        b = bbox_of(m)
        if b:
            regions[name] = list(b)
            print("  %-7s bbox x[%d,%d] y[%d,%d]  w=%d h=%d  px=%d  cx=%.3f t_cy=%.3f"
                  % (name, b[0], b[1], b[2], b[3], b[1] - b[0], b[3] - b[2], b[4],
                     (b[0] + b[1]) / 2.0 / w, (b[2] + b[3]) / 2.0 / h))
    out["regions"] = regions

    # 蓝色条：拆成独立连通块（简单按列游程）
    bm = label == 3
    if bm.any():
        cols = bm.any(0)
        runs = largest_runs(cols, 0)
        out["blue_runs"] = [list(r) for r in runs]
        print("  blue column runs: %s" % (["%d-%d" % (r[0], r[1]) for r in runs],))

    # 腿橙带：底部 30% 内的橙色块
    leg_mask = np.zeros_like(mask)
    leg_mask[int(y0 + H * 0.60):] = True
    om = (label == 2) & leg_mask
    cols = om.any(0)
    runs = largest_runs(cols, 0)
    out["leg_band_runs"] = [list(r) for r in runs]
    print("  leg band runs (lower 40%%): %s"
          % (["%d-%d (w=%d)" % (r[0], r[1], r[1] - r[0]) for r in runs],))

    if ascii_dump:
        print("  ascii label map (%dx%d)  .=bg k=dark O=orange B=blue *=glow" % (cols_n, rows_n))
        chars = ".kOB*"
        for rr in range(rows_n):
            y = int(round(y0 + (H - 1) * rr / float(rows_n - 1)))
            line = []
            for cc in range(cols_n):
                x = int(round(x0 + (L - 1) * cc / float(cols_n - 1)))
                line.append(chars[label[y, x]])
            print("    " + "".join(line))
    return out


def main():
    args = [a for a in sys.argv[1:]]
    ascii_dump = "--ascii" in args
    if ascii_dump:
        args.remove("--ascii")
    json_out = None
    if "--json" in args:
        i = args.index("--json")
        json_out = args[i + 1]
        args = args[:i] + args[i + 2:]
    result = {}
    for p in args:
        result[p] = analyze(p, ascii_dump=ascii_dump)
    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("[measure] -> %s" % json_out)


if __name__ == "__main__":
    main()
