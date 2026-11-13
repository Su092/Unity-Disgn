# -*- coding: utf-8 -*-
"""量测一张渲染（或任意）图，输出与参考图对齐的口径：主体 bbox、色块中心。

用系统 Python + PIL/numpy。输出 JSON 供 Blender 侧脚本 subshell 调用。

  python scripts/measure_shot.py shot.png out.json

色块定义与参考图口径一致（见 spec.md §0）：
  orange  : R 高、B 低的橙红车壳
  amber   : 亮琥珀（侧条 / 腿带）
  visor   : 极亮琥珀核（visor）
  blue    : 蓝条
"""
import json
import sys

import numpy as np
from PIL import Image


def analyze(a, bg_transparent=False):
    h, w, _ = a.shape
    if bg_transparent:
        alpha = a[:, :, 3]
        mask = alpha > 0.5
        rgb = a[:, :, :3]
    else:
        rgb = a[:, :, :3]
        mx, mn = rgb.max(2), rgb.min(2)
        sat = mx - mn
        lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
        bg = (sat < 0.05) & (np.abs(lum - 0.467) < 0.055)
        mask = ~bg

    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    L = x1 - x0 + 1
    H = y1 - y0 + 1

    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    gr = np.divide(g, np.maximum(r, 1e-6))
    # 橙壳 G/R ≈ 0.34；琥珀带 G/R ≈ 0.61；visor 核心 G/R ≈ 0.70（参考图实测）
    orange = mask & (r > b + 0.14) & (r > 0.22) & (gr < 0.46)
    amber = mask & (r > b + 0.20) & (r > 0.55) & (gr >= 0.46) & (gr < 0.88) & (b < 0.42)
    visor = amber & (r > 0.94) & (gr > 0.60)
    blue = mask & (b > r + 0.10) & (b > 0.35)

    def largest(m, min_px):
        """最大 8-连通块（去掉零散噪点，避免 bbox 被拉满）。"""
        if m.sum() < min_px:
            return None
        from collections import deque
        vis = np.zeros_like(m, bool)
        best = []
        yy, xx = np.nonzero(m)
        for sy, sx in zip(yy, xx):
            if vis[sy, sx]:
                continue
            q = deque([(sx, sy)])
            vis[sy, sx] = True
            comp = []
            while q:
                cx, cy = q.popleft()
                comp.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                               (1, 1), (1, -1), (-1, 1), (-1, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and m[ny, nx] and not vis[ny, nx]:
                        vis[ny, nx] = True
                        q.append((nx, ny))
            if len(comp) > len(best):
                best = comp
        if len(best) < min_px:
            return None
        pts = np.array(best, np.int32)
        return pts

    def centre(pts):
        if pts is None:
            return None
        return [round((pts[:, 0].mean() - x0) / float(L), 4),
                round((pts[:, 1].mean() - y0) / float(H), 4)]

    def bbox(pts):
        if pts is None:
            return None
        return [int(pts[:, 0].min()), int(pts[:, 0].max()),
                int(pts[:, 1].min()), int(pts[:, 1].max())]

    out = {
        "size": [w, h],
        "bbox": [x0, x1, y0, y1],
        "L": L, "H": H,
        "H_over_L": round(H / float(L), 4),
        "cues": {},
        "boxes": {},
    }
    for name, m, minpx in (("orange", orange, 400), ("amber", amber, 300),
                           ("visor", visor, 200), ("blue", blue, 150)):
        pts = largest(m, minpx)
        c = centre(pts)
        if c:
            out["cues"][name] = c
            out["boxes"][name] = bbox(pts)

    # 腿带：amber 在主体下半部按列分簇
    lower = np.zeros_like(amber)
    lower[int(y0 + H * 0.58):] = True
    am = amber & lower
    cols = am.any(0)
    runs, cur = [], None
    for x in range(len(cols)):
        if cols[x]:
            cur = [x, x] if cur is None else [cur[0], x]
        else:
            if cur and cur[1] - cur[0] > 4:
                runs.append(cur)
            cur = None
    if cur and cur[1] - cur[0] > 4:
        runs.append(cur)
    legs = []
    for a0, a1 in runs:
        sub = am[:, a0:a1 + 1]
        yy, xx = np.nonzero(sub)
        if len(xx) < 40:
            continue
        legs.append([round((xx.mean() + a0 - x0) / float(L), 4),
                     round((yy.mean() - y0) / float(H), 4)])
    out["leg_bands"] = sorted(legs, key=lambda p: p[0])

    # 侧条：amber 在主体中部、且不属于 visor，取最大块
    upper = np.zeros_like(amber)
    upper[int(y0 + H * 0.22):int(y0 + H * 0.58)] = True
    fl = amber & upper & ~visor
    out["flank"] = centre(largest(fl, 200))
    return out


def main():
    path, out_path = sys.argv[1], sys.argv[2]
    im = Image.open(path)
    arr = np.asarray(im.convert("RGBA"))
    transparent = im.mode in ("RGBA", "LA") and int(arr[:, :, 3].min()) < 10
    a = arr.astype(np.float32) / 255.0
    res = analyze(a, bg_transparent=transparent)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res or {}, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
