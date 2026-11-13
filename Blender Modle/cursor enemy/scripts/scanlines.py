# -*- coding: utf-8 -*-
"""扫描线结构表：逐行列出每个色类的 x 游程（归一化到 bbox t）。

用法：python scripts/scanlines.py [rows] [step]
"""
import sys

import numpy as np
from PIL import Image


def classify(a, mask):
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    orange = mask & (r > b + 0.18) & (r > 0.35) & (g > 0.12)
    blue = mask & (b > r + 0.12) & (b > 0.45)
    cls = np.zeros(mask.shape, np.int8)   # 1..4 grey lum bands, 5 orange, 6 bright orange, 7 blue
    grey = mask & ~orange & ~blue
    cls[grey & (lum < 0.16)] = 1
    cls[grey & (lum >= 0.16) & (lum < 0.28)] = 2
    cls[grey & (lum >= 0.28) & (lum < 0.40)] = 3
    cls[grey & (lum >= 0.40)] = 4
    cls[orange & (lum <= 0.62)] = 5
    cls[orange & (lum > 0.62)] = 6
    cls[blue] = 7
    return cls


NAMES = {0: "-", 1: "K1", 2: "K2", 3: "K3", 4: "K4", 5: "OR", 6: "BR", 7: "BL"}


def runs_of(row, x0, L):
    out = []
    cur = None
    for x in range(len(row)):
        v = int(row[x])
        if cur and cur[0] == v:
            cur[2] = x
        else:
            if cur:
                out.append(cur)
            cur = [v, x, x]
    if cur:
        out.append(cur)
    res = []
    for v, a, b in out:
        if v == 0:
            continue
        if b - a < 2:
            continue
        res.append("%s[%.3f-%.3f]" % (NAMES[v], (a - x0) / float(L), (b - x0) / float(L)))
    return res


def main():
    rows = int(sys.argv[1]) if len(sys.argv) > 1 else 46
    a = np.asarray(Image.open("ref_crawler.png").convert("RGB")).astype(np.float32) / 255.0
    mask = np.load("refs_out/mask.npy")
    ys, xs = np.nonzero(mask)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    L, H = x1 - x0 + 1, y1 - y0 + 1
    cls = classify(a, mask)
    print("bbox x[%d,%d] y[%d,%d]  L=%d H=%d" % (x0, x1, y0, y1, L, H))
    for k in range(rows + 1):
        y = int(round(y0 + (H - 1) * k / float(rows)))
        rr = runs_of(cls[y], x0, L)
        print("t=%.3f y=%4d  %s" % (k / float(rows), y, "  ".join(rr)))


if __name__ == "__main__":
    main()
