# -*- coding: utf-8 -*-
"""把参考图的各色区域打成 ASCII，用来读结构（不靠肉眼看大图）。

用法：python scripts/ascii_masks.py [w=110] [h=52]
"""
import sys

import numpy as np
from PIL import Image


def main():
    path = "ref_crawler.png"
    cols = int(sys.argv[1]) if len(sys.argv) > 1 else 110
    rows = int(sys.argv[2]) if len(sys.argv) > 2 else 52
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0
    mask = np.load("refs_out/mask.npy")
    ys, xs = np.nonzero(mask)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    L, H = x1 - x0 + 1, y1 - y0 + 1

    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    sat = a.max(2) - a.min(2)

    orange = mask & (r > b + 0.18) & (r > 0.35) & (g > 0.12)
    blue = mask & (b > r + 0.12) & (b > 0.45)
    bright = orange & (lum > 0.62)
    mid_or = orange & ~bright
    dark_or = orange & (lum <= 0.62) & (lum > 0.30)
    deep_or = orange & (lum <= 0.30)
    deep = mask & ~orange & ~blue & (lum < 0.16)
    dk = mask & ~orange & ~blue & (lum >= 0.16) & (lum < 0.34)
    md = mask & ~orange & ~blue & (lum >= 0.34) & (lum < 0.52)
    lt = mask & ~orange & ~blue & (lum >= 0.52)

    layers = [
        ("subject", mask, "#"),
        ("blue", blue, "B"),
        ("bright-orange", bright, "H"),
        ("mid-orange", mid_or, "O"),
        ("dark-orange", dark_or, "o"),
        ("deep-orange", deep_or, "d"),
        ("grey-light", lt, "L"),
        ("grey-mid", md, "+"),
        ("grey-dark", dk, "-"),
        ("deep-dark", deep, "."),
    ]

    def dump(title, m, ch, extra=None):
        print("\n== %s ==" % title)
        for rr in range(rows):
            y = int(round(y0 + (H - 1) * rr / float(rows - 1)))
            line = []
            for cc in range(cols):
                x = int(round(x0 + (L - 1) * cc / float(cols - 1)))
                if extra is not None:
                    line.append(extra[y, x] if m[y, x] else " ")
                else:
                    line.append(ch if m[y, x] else ".")
            print("  " + "".join(line))

    # 主图：按色相分类
    cls = np.full(mask.shape, " ", dtype="<U1")
    cls[lt] = "L"
    cls[md] = "+"
    cls[dk] = "-"
    cls[deep] = "."
    cls[deep_or] = "d"
    cls[dark_or] = "o"
    cls[mid_or] = "O"
    cls[bright] = "H"
    cls[blue] = "B"
    dump("legend  B=blue H=bright-orange O=orange o=dark-orange d=deep-orange "
         "L/+/-/.=grey light->dark", mask, "#", extra=cls)

    for title, m, ch in layers[1:]:
        dump(title + " (px=%d)" % int(m.sum()), m, ch)


if __name__ == "__main__":
    main()
