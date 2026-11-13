# -*- coding: utf-8 -*-
"""轮径/轮心：从轮毂中心做径向扫描，取"连续暗域"的外缘，用下半圈拟合圆。

输出 refs/wheels.json。用法: python wheels.py <side.png> <L_mm> <out.json>
"""
import json
import math
import sys

import numpy as np
from PIL import Image


def hsv(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(axis=2), a.min(axis=2)
    d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    i = m & (mx == r)
    h[i] = (60.0 * ((g[i] - b[i]) / d[i]) + 360.0) % 360.0
    i = m & (mx == g)
    h[i] = 60.0 * ((b[i] - r[i]) / d[i]) + 120.0
    i = m & (mx == b)
    h[i] = 60.0 * ((r[i] - g[i]) / d[i]) + 240.0
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    return h, s, mx


def main():
    path, L_mm, out_path = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0
    H, W, _ = a.shape
    h, s, v = hsv(a)
    yellow = (h > 32) & (h < 72) & (s > 0.45) & (v > 0.30)
    dark = v < 0.35
    # 背景：四周中位色
    bd = np.concatenate([a[0:4].reshape(-1, 3), a[H - 4:].reshape(-1, 3),
                         a[:, 0:4].reshape(-1, 3), a[:, W - 4:].reshape(-1, 3)])
    bg = np.median(bd, axis=0)
    bgmask = np.sqrt(((a - bg) ** 2).sum(axis=2)) < 0.09

    band = (yellow | dark)[int(H * 0.28):int(H * 0.82)]
    cols = np.where(band.any(axis=0))[0]
    x0, x1 = int(cols.min()), int(cols.max())
    length_px = x1 - x0 + 1
    ppm = length_px / L_mm
    mm = lambda px: round(float(px) / ppm, 1)

    # 轮毂中心：亮铬盘（沿行找"亮盘被暗环包住"）
    bright = (v > 0.52) & (s < 0.25)
    centers = []
    for cx in range(x0, x1, 1):
        col = bright[:, cx]
        for y in range(int(H * 0.55), int(H * 0.90)):
            if col[y] and col[y - 2] and col[y + 2]:
                # 向上 40px 应进入暗域（轮胎上缘），向外 90px 应回到背景/车身
                up = dark[max(0, y - 70):y - 25, cx].mean()
                if up > 0.6:
                    centers.append((cx, y))
    # 聚类（相邻中心合并）
    centers.sort()
    groups = []
    for c in centers:
        if groups and c[0] - groups[-1][-1][0] < 40:
            groups[-1].append(c)
        else:
            groups.append([c])
    cands = []
    for g in groups:
        if len(g) < 8:
            continue
        xs = [p[0] for p in g]
        ys = [p[1] for p in g]
        cands.append((sum(xs) / len(xs), sum(ys) / len(ys), max(xs) - min(xs)))
    # 取"轮距/车长"合理的两个
    cands.sort(key=lambda c: c[0])

    def radial(cx, cy):
        rs = []
        for deg in range(-70, 71, 2):           # 下半圈（0=正下方）
            ang = math.radians(deg)
            dx, dy = math.sin(ang), math.cos(ang)
            r = 20.0
            last_dark = 0.0
            while r < 420:
                x, y = int(round(cx + dx * r)), int(round(cy + dy * r))
                if not (0 <= x < W and 0 <= y < H):
                    break
                if dark[y, x]:
                    last_dark = r
                elif last_dark > 0 and r - last_dark > 6:
                    break
                r += 1.0
            if last_dark > 0:
                rs.append(last_dark)
        return rs

    out_wheels = []
    for (cx, cy, _) in cands:
        rs = radial(cx, cy)
        if len(rs) < 20:
            continue
        median_r = float(np.median(rs))
        # 只用接近中位数的角度重算中心偏移（上下不对称 = 阴影/拱线干扰）
        if median_r < 60 or median_r > 220:
            continue
        out_wheels.append({"cx": round(cx, 1), "cy": round(cy, 1),
                           "r_px_median": round(median_r, 1),
                           "r_samples": len(rs),
                           "r_spread": [round(min(rs), 1), round(max(rs), 1)]})

    # 只保留横向间距占车长 45%..70% 的一对
    pair = None
    for i in range(len(out_wheels)):
        for j in range(i + 1, len(out_wheels)):
            d = out_wheels[j]["cx"] - out_wheels[i]["cx"]
            if 0.40 * length_px < d < 0.72 * length_px:
                if pair is None or abs(d - 0.55 * length_px) < abs(
                        pair[1]["cx"] - pair[0]["cx"] - 0.55 * length_px):
                    pair = (out_wheels[i], out_wheels[j])
    res = {
        "image": path, "size": [W, H],
        "x_span": [x0, x1], "length_px": length_px,
        "scale": {"L_mm": L_mm, "px_per_mm": round(ppm, 6)},
        "candidates": out_wheels,
        "pair": pair,
    }
    if pair:
        f, r = pair
        d_px = (f["r_px_median"] + r["r_px_median"])
        res["wheel_d_mm"] = mm(d_px)
        res["wheelbase_mm"] = mm(r["cx"] - f["cx"])
        res["wheelbase_over_l"] = round((r["cx"] - f["cx"]) / length_px, 4)
        res["wheel_d_over_l"] = round(d_px / length_px, 4)
        ground = max(f["cy"] + f["r_px_median"], r["cy"] + r["r_px_median"])
        res["ground_y"] = round(ground, 1)
        res["height_mm"] = None
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
