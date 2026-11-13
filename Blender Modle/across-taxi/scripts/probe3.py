# -*- coding: utf-8 -*-
"""精细量测 v3：颜色分类排除阴影，轮心/轮径用"铬盘 + 暗环"双条件判定。

输出 JSON（落盘，不截断）+ 控制台摘要。
用法: python probe3.py <side.png> <L_mm> <out.json>
"""
import json
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


def segs_1d(v, min_len=3):
    out, start = [], None
    for i in range(len(v)):
        if v[i] and start is None:
            start = i
        elif not v[i] and start is not None:
            if i - start >= min_len:
                out.append([start, i - 1])
            start = None
    if start is not None and len(v) - start >= min_len:
        out.append([start, len(v) - 1])
    return out


def main():
    path, L_mm, out_path = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0
    H, W, _ = a.shape
    h, s, v = hsv(a)
    yellow = (h > 32) & (h < 72) & (s > 0.45) & (v > 0.30)
    glass = (h > 175) & (h < 250) & (s > 0.25) & (v > 0.15)
    dark = v < 0.22
    chrome = (v > 0.58) & (s < 0.20)

    # 车身横带（排除地面阴影的影响：只取图像 30%..80% 高度）
    band = (yellow | glass | dark | chrome)[int(H * 0.28):int(H * 0.82)]
    cols = np.where(band.any(axis=0))[0]
    x0, x1 = int(cols.min()), int(cols.max())
    length_px = x1 - x0 + 1
    ppm = length_px / L_mm
    mm = lambda px: round(float(px) / ppm, 1)

    # 轮毂：铬盘、直径 70..160 px、上下有暗环
    hub = chrome & ~yellow
    colsum = hub[int(H * 0.50):int(H * 0.95)].sum(axis=0)
    on = colsum > max(6.0, colsum.max() * 0.30)
    xs = segs_1d(on, min_len=40)
    hubs = []
    for sx, ex in xs:
        d = ex - sx + 1
        if not (70 <= d <= 170):
            continue
        cx = (sx + ex) / 2.0
        sub = hub[:, sx:ex + 1]
        ys = np.where(sub.any(axis=1))[0]
        ys = ys[ys > H * 0.45]
        if ys.size < 10:
            continue
        cy = float((ys.min() + ys.max()) / 2.0)
        # 暗环检查：轮心上方 60px 处应为暗（轮胎上缘）
        dark_up = dark[int(cy - d * 0.75):int(cy - d * 0.55), int(cx) - 5:int(cx) + 6].mean() > 0.5
        if not dark_up:
            continue
        hubs.append({"cx": cx, "cy": cy, "hub_d": d})

    hubs.sort(key=lambda x: x["cx"])
    # 只保留两个最靠轮拱的：轮距/轴距比应在 0.5..0.65
    tires = []
    for hb in hubs:
        y = int(hb["cy"])
        win = (max(x0, int(hb["cx"]) - 300), min(x1, int(hb["cx"]) + 300))
        row = dark[y, win[0]:win[1] + 1]
        idx = np.where(row)[0]
        if idx.size == 0:
            continue
        left, right = win[0] + int(idx.min()), win[0] + int(idx.max())
        # 左右可能被阴影连起来，用"离轮心最近的两侧连续段"更稳
        seg = segs_1d(row, min_len=5)
        segs_px = [[win[0] + s, win[0] + e] for s, e in seg]
        cand = [sg for sg in segs_px if sg[0] <= hb["cx"] <= sg[1]]
        if cand:
            left, right = cand[0]
        r = (right - left) / 2.0
        tires.append({
            "cx": round(hb["cx"], 1), "cy": y,
            "tire_left": left, "tire_right": right,
            "d_px": round(right - left, 1), "r_px": round(r, 1),
            "d_mm": mm(right - left), "r_mm": mm(r),
            "ground_y": round(y + r, 1),
            "hub_d_px": hb["hub_d"],
        })

    ground = max((t["ground_y"] for t in tires), default=float(H) - 1)

    # 顶灯 / 车顶
    rows_y = np.where(yellow[:int(H * 0.4)].any(axis=1))[0]
    sign_top = int(rows_y.min())
    sign_cols = np.where(yellow[sign_top:sign_top + 50].any(axis=0))[0]
    sign_x = [int(sign_cols.min()), int(sign_cols.max())]
    roof_y = None
    for y in range(sign_top, int(H * 0.45)):
        row = yellow[y].copy()
        row[max(0, sign_x[0] - 12):sign_x[1] + 13] = False
        if row.sum() > 6:
            roof_y = y
            break

    # 车身关键横线（在门中部列做颜色分段）
    mx = x0 + int(length_px * 0.52)
    col = {"yellow": segs_1d(yellow[:, mx]), "dark": segs_1d(dark[:, mx]),
           "glass": segs_1d(glass[:, mx]), "chrome": segs_1d(chrome[:, mx])}

    res = {
        "image": path, "size": [W, H],
        "scale": {"L_mm": L_mm, "length_px": length_px, "px_per_mm": round(ppm, 6)},
        "x_span": [x0, x1], "length_px": length_px,
        "ground_y": round(ground, 1),
        "sign_top_y": sign_top, "sign_x": sign_x, "roof_y": roof_y,
        "hubs": hubs, "tires": tires,
        "column_at_mid": {"x": int(mx), **col},
        "mm": {},
        "ratio": {},
    }
    M = res["mm"]
    M["length"] = L_mm
    M["height_sign_top"] = mm(ground - sign_top)
    M["height_roof"] = mm(ground - roof_y) if roof_y else None
    M["sign_h"] = mm(roof_y - sign_top) if roof_y else None
    M["sign_w"] = mm(sign_x[1] - sign_x[0])
    M["sign_cx_from_front"] = mm((sign_x[0] + sign_x[1]) / 2.0 - x0)
    if len(tires) >= 2:
        front, rear = tires[0], tires[-1]
        M["wheel_d"] = [t["d_mm"] for t in tires]
        M["wheelbase"] = mm(rear["cx"] - front["cx"])
        M["front_axle_from_front"] = mm(front["cx"] - x0)
        M["rear_axle_from_rear"] = mm(x1 - rear["cx"])
        M["front_overhang"] = mm(front["tire_left"] - x0)
        M["rear_overhang"] = mm(x1 - rear["tire_right"])
        res["ratio"] = {
            "h_over_l": round((ground - sign_top) / length_px, 4),
            "roof_over_l": round((ground - roof_y) / length_px, 4) if roof_y else None,
            "wheel_d_over_l": round(front["d_px"] / length_px, 4),
            "wheelbase_over_l": round((rear["cx"] - front["cx"]) / length_px, 4),
        }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: res[k] for k in ("scale", "x_span", "ground_y", "sign_top_y",
                                          "roof_y", "tires", "mm", "ratio")},
                     ensure_ascii=False, indent=2))
    print("column_at_mid:", json.dumps(col, ensure_ascii=False))


if __name__ == "__main__":
    main()
