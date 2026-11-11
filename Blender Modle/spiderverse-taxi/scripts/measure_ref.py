# -*- coding: utf-8 -*-
"""参考图量测：从侧视/正视 PNG 抽轮廓，输出可写进 spec 的比例数字。

分割口径（对"中性底 + 高饱和车身 + 黑墨线"的参考图有效）：
  1) 候选背景 = 低饱和(≈中性灰) 且 亮度在中灰区间 → 从四条边泛洪连通
  2) 主体 = 非背景连通域（车身、墨线、轮胎、白胎壁都留得住）
  3) 列轮廓做 5 列中值平滑，去掉网点噪点造成的毛刺

输出：bbox 长高比、上/下轮廓 11 点、车轮游程、主色、座舱/引擎盖关键高度。

用法：
  blender -b --factory-startup --python scripts/measure_ref.py -- <side.png> [front.png]
"""

import sys
from collections import deque

import bpy

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []


def load(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    return list(img.pixels[:]), w, h


def segment(path):
    px, w, h = load(path)

    def rgb(x, y):
        i = (y * w + x) * 4
        return px[i], px[i + 1], px[i + 2]

    # 背景亮度带：取四边像素的中位数 ± 0.18
    edge = []
    for x in range(0, w, 3):
        edge.append(rgb(x, 0))
        edge.append(rgb(x, h - 1))
    for y in range(0, h, 3):
        edge.append(rgb(0, y))
        edge.append(rgb(w - 1, y))
    lums = sorted(0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] for c in edge)
    med = lums[len(lums) // 2]

    bg = bytearray(w * h)
    q = deque()

    def cand(x, y):
        # 只把"低饱和且不太暗"的像素当背景。
        # 好处：地面阴影是中性灰（sat≈0、luma 0.5~0.7）也会被吃掉，
        # 不再把 H 撑大；车身红漆 sat 高、轮胎/墨线 luma 低，都会挡住泛洪。
        r, g, b = rgb(x, y)
        s = max(r, g, b) - min(r, g, b)
        l = 0.299 * r + 0.587 * g + 0.114 * b
        return s < 0.12 and l > 0.32

    for x in range(w):
        for y in (0, h - 1):
            if cand(x, y) and not bg[y * w + x]:
                bg[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if cand(x, y) and not bg[y * w + x]:
                bg[y * w + x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not bg[ny * w + nx] and cand(nx, ny):
                bg[ny * w + nx] = 1
                q.append((nx, ny))

    mask = bytearray(1 - v for v in bg)
    return px, w, h, mask, med


def col_profile(mask, w, h):
    top, bot = [None] * w, [None] * w
    for x in range(w):
        for y in range(h - 1, -1, -1):
            if mask[y * w + x]:
                top[x] = y
                break
        for y in range(h):
            if mask[y * w + x]:
                bot[x] = y
                break

    def smooth(arr):
        out = list(arr)
        for x in range(2, w - 2):
            win = [arr[x + d] for d in (-2, -1, 0, 1, 2) if arr[x + d] is not None]
            if win:
                win.sort()
                out[x] = win[len(win) // 2]
        return out

    return smooth(top), smooth(bot)


def measure(path, ascii_dump=False):
    px, w, h, mask, bgmed = segment(path)
    top, bot = col_profile(mask, w, h)
    cols = [x for x in range(w) if top[x] is not None]
    if not cols:
        print("%s: 分割失败" % path)
        return
    x0, x1 = cols[0], cols[-1]
    ytop = max(top[x] for x in cols)
    ybot = min(bot[x] for x in cols)
    L, H = x1 - x0 + 1, ytop - ybot + 1
    print("%s" % path)
    print("  size=%dx%d  bg_luma=%.3f  subject_fill=%.3f"
          % (w, h, bgmed, sum(mask) / float(w * h)))
    print("  bbox px x[%d,%d] y[%d,%d]  L=%d H=%d  H/L=%.4f"
          % (x0, x1, ybot, ytop, L, H, H / float(L)))

    def prof(fn):
        out = []
        for k in range(11):
            x = int(x0 + (L - 1) * k / 10.0)
            out.append("%.2f" % fn(x) if top[x] is not None else "--")
        return "  ".join(out)

    print("  top profile  : " + prof(lambda x: 1.0 - (top[x] - ybot) / float(H)))
    print("  bottom profile: " + prof(lambda x: (bot[x] - ybot) / float(H)))

    # 车轮：地面带内"暗像素"占比高的列 → 圆轮
    band = ybot + int(H * 0.22)
    thr = max(3, int(H * 0.04))
    dark = []
    for x in range(x0, x1 + 1):
        nm = 0
        for y in range(ybot, min(band, h)):
            if mask[y * w + x]:
                i = (y * w + x) * 4
                if 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2] < 0.32:
                    nm += 1
        dark.append(nm)
    runs, cur = [], None
    for k, nm in enumerate(dark):
        x = x0 + k
        if nm >= thr:
            cur = [x, x] if cur is None else [cur[0], x]
        else:
            if cur and cur[1] - cur[0] > L * 0.05:
                runs.append(tuple(cur))
            cur = None
    if cur and cur[1] - cur[0] > L * 0.05:
        runs.append(tuple(cur))
    print("  wheel runs px: %s" % (["%d-%d" % r for r in runs],))
    for (a, b) in runs:
        print("    cx=%.3fL  dia=%.3fL  dia=%.3fH"
              % (((a + b) / 2.0 - x0) / float(L), (b - a) / float(L), (b - a) / float(H)))

    # 最高点位置（座舱/风挡顶）与 0.3/0.5/0.7 处高度
    zx = max(cols, key=lambda x: top[x])
    print("  highest point at t=%.3fL (z=1.00)"
          % ((zx - x0) / float(L)))
    for t in (0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95):
        x = int(x0 + (L - 1) * t)
        if top[x] is not None:
            print("    t=%.2f  top_z=%.3f  bottom_z=%.3f"
                  % (t, 1.0 - (top[x] - ybot) / float(H), (bot[x] - ybot) / float(H)))

    if ascii_dump:
        # 粗网格剪影：直接看掩膜对不对（阴影有没有被吃掉、座舱开口在不在）
        cols_n, rows_n = 76, 22
        print("  ascii mask (%dx%d, '#'=subject, '.'=bg):" % (cols_n, rows_n))
        for r in range(rows_n):
            y = int(ybot + (H - 1) * (1.0 - r / float(rows_n - 1)))
            line = []
            for c in range(cols_n):
                x = int(x0 + (L - 1) * c / float(cols_n - 1))
                line.append("#" if mask[y * w + x] else ".")
            print("    " + "".join(line))


def metrics(path):
    """把 measure() 的关键数字收成 dict，供 ref_compare 对拍。"""
    import io
    import json
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        measure(path)
    txt = buf.getvalue()
    out = {"path": path}
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith("bbox px"):
            # bbox px x[36,2017] y[263,836]  L=1982 H=574  H/L=0.2896
            out["L"] = float(s.split("L=")[1].split()[0])
            out["H"] = float(s.split("H=")[1].split()[0])
            out["H_over_L"] = float(s.split("H/L=")[1])
        elif s.startswith("top profile"):
            out["top_profile"] = [float(v) for v in s.split(":", 1)[1].split()]
        elif s.startswith("highest point"):
            out["highest_t"] = float(s.split("t=")[1].split("L")[0])
        elif s.startswith("cx="):
            out.setdefault("wheels", []).append(
                float(s.split("cx=")[1].split("L")[0]))
    return out


def main():
    args = list(argv)
    json_out = None
    ascii_dump = "--ascii" in args
    if ascii_dump:
        args.remove("--ascii")
    if "--json" in args:
        i = args.index("--json")
        json_out = args[i + 1]
        args = args[:i] + args[i + 2:]
    result = {}
    for p in args:
        measure(p, ascii_dump=ascii_dump)
        result[p] = metrics(p)
    if json_out:
        import json
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("[measure] json -> %s" % json_out)


if __name__ == "__main__":
    main()
