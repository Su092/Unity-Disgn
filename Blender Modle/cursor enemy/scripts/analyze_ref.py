# -*- coding: utf-8 -*-
"""参考图深入分析：调色板聚类 + 每个色簇的空间分布 + 轮廓细节。

用法：python scripts/analyze_ref.py [ref.png]
"""
import json
import sys

import numpy as np
from PIL import Image

MASK_PATH = "refs_out/mask.npy"


def kmeans(points, k, iters=40, seed=7):
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(points), k, replace=False)
    cent = points[idx].copy()
    for _ in range(iters):
        d = ((points[:, None, :] - cent[None, :, :]) ** 2).sum(2)
        lab = d.argmin(1)
        for j in range(k):
            sel = points[lab == j]
            if len(sel):
                cent[j] = sel.mean(0)
    d = ((points[:, None, :] - cent[None, :, :]) ** 2).sum(2)
    lab = d.argmin(1)
    return cent, lab


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "ref_crawler.png"
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32) / 255.0
    h, w, _ = a.shape
    mask = np.load(MASK_PATH)
    ys, xs = np.nonzero(mask)
    print("subject px", len(xs), "bbox x[%d,%d] y[%d,%d]" % (xs.min(), xs.max(), ys.min(), ys.max()))
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    L, H = x1 - x0 + 1, y1 - y0 + 1

    samples = a[mask]
    sub = samples[::7]
    cent, lab = kmeans(sub, 9)
    full_d = ((samples[:, None, :] - cent[None, :, :]) ** 2).sum(2)
    flab = full_d.argmin(1)

    order = np.argsort(-np.bincount(flab, minlength=9))
    info = []
    for ci in order:
        sel = flab == ci
        cnt = int(sel.sum())
        if cnt < 300:
            continue
        px = xs[sel]
        py = ys[sel]
        c = cent[ci]
        rec = {
            "cluster": int(ci),
            "rgb255": [int(round(v * 255)) for v in c],
            "hex": "#%02X%02X%02X" % tuple(int(round(v * 255)) for v in c),
            "count": cnt,
            "frac": round(cnt / float(len(samples)), 4),
            "bbox": [int(px.min()), int(px.max()), int(py.min()), int(py.max())],
            "cx_t": round((px.mean() - x0) / float(L), 3),
            "cy_t": round((py.mean() - y0) / float(H), 3),
            "x_span_t": [round((px.min() - x0) / float(L), 3), round((px.max() - x0) / float(L), 3)],
            "y_span_t": [round((py.min() - y0) / float(H), 3), round((py.max() - y0) / float(H), 3)],
        }
        info.append(rec)
        print("%-7s %6.2f%%  bbox x[%4d,%4d] y[%4d,%4d]  c_t=(%.3f,%.3f) span x%.2f-%.2f y%.2f-%.2f"
              % (rec["hex"], rec["frac"] * 100, rec["bbox"][0], rec["bbox"][1],
                 rec["bbox"][2], rec["bbox"][3], rec["cx_t"], rec["cy_t"],
                 rec["x_span_t"][0], rec["x_span_t"][1], rec["y_span_t"][0], rec["y_span_t"][1]))

    # 逐簇的列方图（找空间分离的结构，如两条蓝带 / 四条腿）
    print("\nper-cluster column histogram (12 bins over t):")
    for rec in info:
        sel = flab == rec["cluster"]
        px = xs[sel]
        hist, _ = np.histogram((px - x0) / float(L), bins=12, range=(0, 1))
        print("  %-7s %s" % (rec["hex"], " ".join("%5d" % v for v in hist)))

    print("\nper-cluster row histogram (12 bins over t):")
    for rec in info:
        sel = flab == rec["cluster"]
        py = ys[sel]
        hist, _ = np.histogram((py - y0) / float(H), bins=12, range=(0, 1))
        print("  %-7s %s" % (rec["hex"], " ".join("%5d" % v for v in hist)))

    # 最亮饱和橙：visor 候选
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    score = r - b
    cand = mask & (r > 0.85) & (g > 0.42) & (g < 0.78) & (b < 0.35)
    print("\nbright amber px:", int(cand.sum()))
    if cand.any():
        ys2, xs2 = np.nonzero(cand)
        print("  bbox x[%d,%d] y[%d,%d]  t x[%.3f,%.3f] y[%.3f,%.3f]  mean=%s"
              % (xs2.min(), xs2.max(), ys2.min(), ys2.max(),
                 (xs2.min() - x0) / L, (xs2.max() - x0) / L,
                 (ys2.min() - y0) / H, (ys2.max() - y0) / H,
                 [round(float(v), 3) for v in a[cand].mean(0)]))

    # 蓝色：细分两簇看是不是两条条带
    blue = mask & (b > r + 0.10) & (b > 0.45)
    print("\nblue px:", int(blue.sum()))
    if blue.any():
        ys3, xs3 = np.nonzero(blue)
        print("  bbox x[%d,%d] y[%d,%d] mean=%s"
              % (xs3.min(), xs3.max(), ys3.min(), ys3.max(),
                 [round(float(v), 3) for v in a[blue].mean(0)]))
        # 用 x 方向直方图找分离
        hist, edges = np.histogram(xs3, bins=40)
        print("  x hist:", " ".join("%d" % v for v in hist))

    with open("refs_out/clusters.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
