# -*- coding: utf-8 -*-
"""高分辨率色类 ASCII：用来读结构分层（车壳 / 黑边 / 黄条 / 蓝条 / visor）。

用法：python scripts/ascii_body.py [x0 x1 y0 y1] [cols] [rows]
默认给整机。
"""
import sys

import numpy as np
from PIL import Image


def main():
    args = sys.argv[1:]
    a = np.asarray(Image.open("ref_crawler.png").convert("RGB")).astype(np.float32) / 255.0
    mask = np.load("refs_out/mask.npy")
    ys, xs = np.nonzero(mask)
    X0, X1, Y0, Y1 = xs.min(), xs.max(), ys.min(), ys.max()
    if len(args) >= 4:
        X0, X1, Y0, Y1 = map(int, args[:4])
        cols = int(args[4]) if len(args) > 4 else 110
        rows = int(args[5]) if len(args) > 5 else 50
    else:
        cols, rows = 110, 50

    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    sat = a.max(2) - a.min(2)

    ch = np.full(mask.shape, " ", dtype="<U1")
    bg = (sat < 0.05) & (np.abs(lum - 0.467) < 0.05)
    ch[~bg] = "?"
    # 橙红车壳：R 高、G 中等、B 低
    red = (r > 0.60) & (g > 0.20) & (g < 0.45) & (b < 0.34)
    ch[red] = "R"
    # 亮橙/琥珀（黄条、visor 外圈）
    amber = (r > 0.78) & (g > 0.45) & (b < 0.30)
    ch[amber] = "Y"
    # 极亮 visor 核心
    core = (r > 0.93) & (g > 0.60) & (b < 0.28)
    ch[core] = "*"
    # 蓝
    blue = (b > r + 0.12) & (b > 0.45)
    ch[blue] = "B"
    # 灰阶
    grey = ~bg & ~red & ~amber & ~blue & ~core
    ch[grey & (lum >= 0.40) & (lum < 0.55)] = "w"
    ch[grey & (lum >= 0.28) & (lum < 0.40)] = "+"
    ch[grey & (lum >= 0.18) & (lum < 0.28)] = "-"
    ch[grey & (lum < 0.18)] = "."

    print("region x[%d,%d] y[%d,%d]  R=orange Y=amber *=core B=blue w/+/-/.=grey" % (X0, X1, Y0, Y1))
    for rr in range(rows + 1):
        y = int(round(Y0 + (Y1 - Y0) * rr / float(rows)))
        line = []
        for cc in range(cols + 1):
            x = int(round(X0 + (X1 - X0) * cc / float(cols)))
            line.append(ch[y, x])
        print("%4d %s" % (y, "".join(line)))


if __name__ == "__main__":
    main()
