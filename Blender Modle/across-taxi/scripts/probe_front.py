# -*- coding: utf-8 -*-
"""正视图/后视图量测：行带黄漆跨度 + 亮斑（大灯）+ 暗斑（轮胎）。

用法: python probe_front.py <front.png> <W_mm> <out.json> [--rear]
"""
import json
import sys
from collections import deque

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


def comps(mask, min_px):
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    for y in range(h):
        row = np.where(mask[y] & ~seen[y])[0]
        for x in row:
            if seen[y, x]:
                continue
            q = deque([(y, x)])
            seen[y, x] = True
            pts = []
            while q:
                cy, cx = q.popleft()
                pts.append((cy, cx))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if len(pts) >= min_px:
                ys = [p[0] for p in pts]
                xs = [p[1] for p in pts]
                out.append({"n": len(pts), "bbox": [min(xs), min(ys), max(xs), max(ys)]})
    return out


def main():
    path, W_mm, out_path = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0
    H, W, _ = a.shape
    h, s, v = hsv(a)
    yellow = (h > 32) & (h < 72) & (s > 0.45) & (v > 0.28)
    dark = v < 0.24
    glass = (h > 175) & (h < 250) & (s > 0.22) & (v > 0.12)
    chrome = (v > 0.55) & (s < 0.22)
    body = yellow | dark | glass | chrome

    # 主体横带（避开地面阴影）：60%..92% 高度
    band = body[int(H * 0.05):int(H * 0.92)]
    cols = np.where(band.any(axis=0))[0]
    x0, x1 = int(cols.min()), int(cols.max())
    width_px = x1 - x0 + 1
    ppm = width_px / W_mm
    mm = lambda px: round(float(px) / ppm, 1)

    rows = np.where(body.any(axis=1))[0]
    y0, y1 = int(rows.min()), int(rows.max())

    def span(mask, y, lo, hi):
        seg = mask[y, lo:hi + 1]
        idx = np.where(seg)[0]
        if idx.size == 0:
            return None
        return [int(lo + idx.min()), int(lo + idx.max())]

    # 车身宽度随高度的变化（每 5% 高度一条）
    widths = {}
    for f in range(0, 101, 5):
        y = int(y0 + (y1 - y0) * f / 100.0)
        sp = span(body | yellow, y, x0, x1)
        ys = span(yellow, y, x0, x1)
        widths["%d%%" % f] = {"y": y, "body": sp,
                              "body_mm": mm(sp[1] - sp[0]) if sp else None,
                              "yellow": ys,
                              "yellow_mm": mm(ys[1] - ys[0]) if ys else None}

    # 轮胎（暗、下半部、靠左右两侧）
    tire = dark.copy()
    tire[:int(y1 - (y1 - y0) * 0.22)] = False
    tc = comps(tire[::2, ::2], 200)
    tc = sorted(tc, key=lambda c: c["bbox"][0])
    tires = []
    for c in tc:
        bx0, by0, bx1, by1 = [v * 2 for v in c["bbox"]]
        wpx = bx1 - bx0 + 1
        if wpx > W * 0.28 or wpx < 30:
            continue
        tires.append({"bbox_px": [bx0, by0, bx1, by1], "w_px": wpx,
                      "w_mm": mm(wpx), "cx": (bx0 + bx1) / 2.0})

    # 亮斑：大灯（圆、亮、上半部）
    bright = (v > 0.72) & (s < 0.45)
    bright[:int(y0 + (y1 - y0) * 0.25)] = False
    bright[int(y0 + (y1 - y0) * 0.72):] = False
    bc = comps(bright[::2, ::2], 120)
    bcs = []
    for c in bc:
        bx0, by0, bx1, by1 = [v * 2 for v in c["bbox"]]
        wpx, hpx = bx1 - bx0 + 1, by1 - by0 + 1
        if 20 < wpx < W * 0.25 and abs(wpx - hpx) < 0.45 * max(wpx, hpx):
            bcs.append({"bbox_px": [bx0, by0, bx1, by1], "d_px": (wpx + hpx) / 2.0,
                        "d_mm": mm((wpx + hpx) / 2.0), "cx": (bx0 + bx1) / 2.0,
                        "cy": (by0 + by1) / 2.0})
    bcs = sorted(bcs, key=lambda c: -c["d_px"])[:6]

    res = {
        "image": path, "size": [W, H],
        "x_span": [x0, x1], "y_span": [y0, y1],
        "width_px": width_px, "height_px": y1 - y0 + 1,
        "scale": {"W_mm": W_mm, "px_per_mm": round(ppm, 6)},
        "mm": {"width": W_mm, "height": mm(y1 - y0 + 1),
               "w_over_h": round(width_px / float(y1 - y0 + 1), 4)},
        "row_widths": widths,
        "tires": tires,
        "headlights": bcs,
    }
    if len(tires) >= 2:
        left, right = tires[0], tires[-1]
        res["mm"]["tire_w"] = left["w_mm"]
        res["mm"]["track_outer"] = mm(right["bbox_px"][2] - left["bbox_px"][0])
        res["mm"]["track_center"] = mm(right["cx"] - left["cx"])
    if len(bcs) >= 2:
        res["mm"]["headlight_d"] = [b["d_mm"] for b in bcs]
        res["mm"]["headlight_cx"] = [round(b["cx"] - x0, 1) for b in bcs]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
