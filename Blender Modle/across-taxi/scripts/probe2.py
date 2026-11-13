# -*- coding: utf-8 -*-
"""精细量测：用颜色分类（黄漆 / 玻璃 / 铬 / 深色件）把阴影排除在外，
再按行/列扫描拿地标。全部输出像素 + 按选定车长换算的 mm。

用法: python probe2.py <side.png> <L_mm>
"""
import json
import os
import sys

import numpy as np
from PIL import Image


def hsv(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    # 标准 HSV 色相
    idx = m & (mx == r)
    h[idx] = (60.0 * ((g[idx] - b[idx]) / d[idx]) + 360.0) % 360.0
    idx = m & (mx == g)
    h[idx] = 60.0 * ((b[idx] - r[idx]) / d[idx]) + 120.0
    idx = m & (mx == b)
    h[idx] = 60.0 * ((r[idx] - g[idx]) / d[idx]) + 240.0
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    return h, s, mx


def main():
    path = sys.argv[1]
    L_mm = float(sys.argv[2]) if len(sys.argv) > 2 else 5200.0
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0
    H, W, _ = a.shape
    h, s, v = hsv(a)

    yellow = (h > 32) & (h < 72) & (s > 0.45) & (v > 0.30)
    glass = (h > 175) & (h < 250) & (s > 0.25) & (v > 0.15)
    dark = v < 0.20
    chrome = (v > 0.55) & (s < 0.22)
    body = yellow | glass | dark | chrome

    def rng(mask_rows, axis_name, coord, win):
        if axis_name == "row":
            seg = mask_rows[coord, win[0]:win[1] + 1]
            idx = np.where(seg)[0]
            if idx.size == 0:
                return None
            return [int(win[0] + idx.min()), int(win[0] + idx.max())]
        seg = mask_rows[win[0]:win[1] + 1, coord]
        idx = np.where(seg)[0]
        if idx.size == 0:
            return None
        return [int(win[0] + idx.min()), int(win[0] + idx.max())]

    # ---- 总长：黄漆 + 铬 + 深色，在车身带状区域上取并集
    band = body[int(H * 0.30):int(H * 0.80)]
    cols = np.where(band.any(axis=0))[0]
    x0, x1 = int(cols.min()), int(cols.max())
    length_px = x1 - x0 + 1
    px_per_mm = length_px / L_mm
    mm = lambda px: round(float(px) / px_per_mm, 1)

    # ---- 地面：深色件（轮胎）的最下沿
    rows_dark = np.where(dark[:, x0:x1 + 1].any(axis=1))[0]
    ground_y = int(rows_dark.max())

    # ---- 顶灯：黄漆在顶部的连续块
    top_rows = np.where(yellow[:int(H * 0.35)].any(axis=1))[0]
    sign_top = int(top_rows.min())

    # ---- 车顶（排除灯箱横向区间）
    sign_cols = np.where(yellow[sign_top:sign_top + 60].any(axis=0))[0]
    sign_x = [int(sign_cols.min()), int(sign_cols.max())]
    roof_candidates = []
    for y in range(sign_top, int(H * 0.45)):
        row = yellow[y].copy()
        row[sign_x[0] - 15:sign_x[1] + 16] = False
        if row.any():
            roof_candidates.append(y)
            break
    roof_y = int(roof_candidates[0]) if roof_candidates else None

    # ---- 轮心（用玻璃/黄漆包围的深色圆盘中心：先用行扫描找轮毂铬盘）
    # 轮毂：铬色圆盘，直径 ~ 0.1*L
    hub = chrome & ~yellow
    # 找两个最大的圆形铬块：按列密度
    col_density = hub[int(H * 0.55):int(H * 0.85)].sum(axis=0)
    thr = col_density.max() * 0.35
    on = col_density > thr
    segs, start = [], None
    for x in range(W):
        if on[x] and start is None:
            start = x
        elif not on[x] and start is not None:
            if x - start > 40:
                segs.append((start, x - 1))
            start = None
    if start is not None and W - start > 40:
        segs.append((start, W - 1))
    hubs = []
    for (sx, ex) in segs[:4]:
        sub = hub[:, sx:ex + 1]
        ys = np.where(sub.any(axis=1))[0]
        ys = ys[(ys > ground_y - 300) & (ys < ground_y)]
        if ys.size:
            hubs.append({"x": [sx, ex], "cx": (sx + ex) / 2.0,
                         "cy": int((ys.min() + ys.max()) / 2.0),
                         "d_px": ex - sx + 1})

    # ---- 轮胎外径：在轮心高度扫描深色跨度（轮毂是亮的，所以取左右端点）
    tires = []
    for hb in hubs:
        y = int(hb["cy"])
        win = (max(x0, int(hb["cx"]) - 260), min(x1, int(hb["cx"]) + 260))
        seg = dark[y, win[0]:win[1] + 1]
        idx = np.where(seg)[0]
        if idx.size:
            left = win[0] + int(idx.min())
            right = win[0] + int(idx.max())
            tires.append({"cx": hb["cx"], "cy": y, "left": left, "right": right,
                          "d_px": right - left + 1, "d_mm": mm(right - left + 1),
                          "r_mm": mm((right - left + 1) / 2.0)})

    # ---- 竖直扫描：在车头/车中/车尾各取一条竖线，给出黄漆/深色分段
    def col_segments(x, mask):
        col = mask[:, x]
        segs, start = [], None
        for y in range(H):
            if col[y] and start is None:
                start = y
            elif not col[y] and start is not None:
                if y - start >= 3:
                    segs.append([start, y - 1])
                start = None
        if start is not None:
            segs.append([start, H - 1])
        return segs

    probes = {}
    for name, x in (("front", x0 + int(length_px * 0.08)),
                    ("nose", x0 + int(length_px * 0.16)),
                    ("mid", x0 + int(length_px * 0.50)),
                    ("rear", x1 - int(length_px * 0.06))):
        probes[name] = {
            "x": int(x),
            "yellow": col_segments(int(x), yellow),
            "dark": col_segments(int(x), dark),
            "glass": col_segments(int(x), glass),
        }

    # ---- 棋盘带：黄漆区内的深色横条带（在门中部列）
    out = {
        "image": path,
        "size": [W, H],
        "scale": {"L_mm": L_mm, "length_px": length_px,
                  "px_per_mm": round(px_per_mm, 6)},
        "length_px": length_px,
        "x_span": [x0, x1],
        "ground_y": ground_y,
        "sign_top_y": sign_top,
        "sign_x": sign_x,
        "roof_y": roof_y,
        "mm": {
            "length": L_mm,
            "height_sign_top": mm(ground_y - sign_top),
            "height_roof": mm(ground_y - roof_y) if roof_y else None,
            "sign_h": mm(roof_y - sign_top) if roof_y else None,
            "sign_w": mm(sign_x[1] - sign_x[0]),
            "sign_cx_from_front": mm((sign_x[0] + sign_x[1]) / 2.0 - x0),
            "wheel_d": [t["d_mm"] for t in tires],
            "wheelbase": mm(abs(tires[-1]["cx"] - tires[0]["cx"])) if len(tires) >= 2 else None,
            "front_overhang": mm(tires[0]["cx"] - x0) if tires else None,
            "rear_overhang": mm(x1 - tires[-1]["cx"]) if tires else None,
        },
        "hubs": hubs,
        "tires": tires,
        "probes": probes,
    }
    out["ratio"] = {
        "h_over_l": round((ground_y - sign_top) / length_px, 4),
        "roof_over_l": round((ground_y - roof_y) / length_px, 4) if roof_y else None,
        "wheel_d_over_l": round(tires[0]["d_px"] / length_px, 4) if tires else None,
        "wheelbase_over_l": round(abs(tires[-1]["cx"] - tires[0]["cx"]) / length_px, 4) if len(tires) >= 2 else None,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
