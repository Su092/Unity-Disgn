# -*- coding: utf-8 -*-
"""把参考图里需要建模的几个结构量成数字：橙色侧条骨架、腿的定向盒、visor 四边形、蓝条四边形。

输出 refs_out/structures.json
"""
import json
from collections import deque

import numpy as np
from PIL import Image


def rgb(path="ref_crawler.png"):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0
    return a


def comps(m, minarea=200, conn8=True):
    h, w = m.shape
    vis = np.zeros((h, w), bool)
    out = []
    ys, xs = np.nonzero(m)
    nb = ((1, 0), (-1, 0), (0, 1), (0, -1))
    if conn8:
        nb = nb + ((1, 1), (1, -1), (-1, 1), (-1, -1))
    for sy, sx in zip(ys, xs):
        if vis[sy, sx]:
            continue
        q = deque([(sx, sy)])
        vis[sy, sx] = True
        pts = []
        while q:
            x, y = q.popleft()
            pts.append((x, y))
            for dx, dy in nb:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and m[ny, nx] and not vis[ny, nx]:
                    vis[ny, nx] = True
                    q.append((nx, ny))
        if len(pts) >= minarea:
            out.append(np.array(pts, np.int32))
    out.sort(key=lambda p: -len(p))
    return out


def convex_hull(pts):
    p = sorted(set(map(tuple, pts)))
    if len(p) < 3:
        return p

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for q in p:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], q) <= 0:
            lower.pop()
        lower.append(q)
    upper = []
    for q in reversed(p):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], q) <= 0:
            upper.pop()
        upper.append(q)
    return lower[:-1] + upper[:-1]


def simplify(poly, tol=3.0):
    """Ramer-Douglas-Peucker on a closed-ish polygon."""
    if len(poly) < 4:
        return poly
    pts = [np.array(p, np.float64) for p in poly]

    def rdp(a, b, idx):
        if not idx:
            return []
        x1, y1 = pts[a]
        x2, y2 = pts[b]
        dx, dy = x2 - x1, y2 - y1
        n = max((dx * dx + dy * dy) ** 0.5, 1e-9)
        best, bi = -1.0, -1
        for i in idx:
            d = abs(dy * (pts[i][0] - x1) - dx * (pts[i][1] - y1)) / n
            if d > best:
                best, bi = d, i
        if best <= tol:
            return []
        return rdp(a, bi, [i for i in idx if a < i < bi]) + [bi] + \
            rdp(bi, b, [i for i in idx if bi < i < b])

    keep = rdp(0, len(pts) - 1, list(range(1, len(pts) - 1)))
    out = [poly[0]] + [poly[i] for i in keep] + [poly[-1]]
    return out


def main():
    a = rgb()
    mask = np.load("refs_out/mask.npy")
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    ys, xs = np.nonzero(mask)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    L, H = x1 - x0 + 1, y1 - y0 + 1
    res = {"bbox": [int(x0), int(x1), int(y0), int(y1)], "L": int(L), "H": int(H)}

    orange = mask & (r > b + 0.18) & (r > 0.35) & (g > 0.12)
    blue = mask & (b > r + 0.12) & (b > 0.45)

    # --- 1) 橙色侧条骨架（第 2 大连通块）
    oc = comps(orange, 500)
    band = oc[1]
    cols = {}
    for x, y in band:
        cols.setdefault(x, []).append(y)
    path = []
    for x in sorted(cols):
        yy = sorted(cols[x])
        path.append([int(x), float(np.median(yy))])
    # 抽稀到 ~9 个节点
    step = max(1, len(path) // 9)
    nodes = path[::step]
    if nodes[-1] != path[-1]:
        nodes.append(path[-1])
    res["flank_band"] = {
        "bbox": [int(band[:, 0].min()), int(band[:, 0].max()), int(band[:, 1].min()), int(band[:, 1].max())],
        "path_px": nodes,
        "path_t": [[round((p[0] - x0) / L, 4), round((p[1] - y0) / H, 4)] for p in nodes],
    }
    print("flank band bbox", res["flank_band"]["bbox"])
    print("  path_t:", res["flank_band"]["path_t"])

    # --- 2) visor：最大亮橙连通块，取凸包 + 简化
    bright = orange & (r > 0.72) & (lum > 0.60)
    bc = comps(bright, 1000)
    vis = bc[0]
    hull = simplify(convex_hull(vis), 3.0)
    res["visor"] = {
        "bbox": [int(vis[:, 0].min()), int(vis[:, 0].max()), int(vis[:, 1].min()), int(vis[:, 1].max())],
        "poly_px": [[int(p[0]), int(p[1])] for p in hull],
        "poly_t": [[round((p[0] - x0) / L, 4), round((p[1] - y0) / H, 4)] for p in hull],
        "px": int(len(vis)),
    }
    print("visor bbox", res["visor"]["bbox"], "poly_t", res["visor"]["poly_t"])

    # --- 3) 蓝条：两块，各自取凸包
    bl = comps(blue, 800)
    strips = []
    for c in bl[:2]:
        hull = simplify(convex_hull(c), 2.5)
        strips.append({
            "bbox": [int(c[:, 0].min()), int(c[:, 0].max()), int(c[:, 1].min()), int(c[:, 1].max())],
            "poly_px": [[int(p[0]), int(p[1])] for p in hull],
            "poly_t": [[round((p[0] - x0) / L, 4), round((p[1] - y0) / H, 4)] for p in hull],
            "px": int(len(c)),
        })
        print("blue strip bbox", strips[-1]["bbox"], "poly_t", strips[-1]["poly_t"])
    res["blue_strips"] = strips

    # --- 4) 腿：底部区域的深色连通块（排除主体）
    dark = mask & ~orange & ~blue & (lum < 0.34)
    dark_bottom = np.zeros_like(dark)
    dark_bottom[int(y0 + H * 0.62):] = True
    dc = comps(dark & dark_bottom, 1500)
    legs = []
    for c in dc[:6]:
        p = c.astype(np.float64)
        ctr = p.mean(0)
        q = p - ctr
        cov = q.T @ q / len(p)
        evals, evecs = np.linalg.eigh(cov)
        M = evecs[:, np.argmax(evals)]
        N = evecs[:, np.argmin(evals)]
        u, v = q @ M, q @ N
        rec = {
            "px": int(len(p)),
            "bbox": [int(p[:, 0].min()), int(p[:, 0].max()), int(p[:, 1].min()), int(p[:, 1].max())],
            "center_t": [round((ctr[0] - x0) / L, 4), round((ctr[1] - y0) / H, 4)],
            "len_px": round(float(u.max() - u.min()), 1),
            "wid_px": round(float(v.max() - v.min()), 1),
            "angle_deg": round(float(np.degrees(np.arctan2(M[1], M[0]))), 1),
        }
        legs.append(rec)
        print("leg comp px=%d bbox=%s c_t=(%.3f,%.3f) L=%.1f W=%.1f ang=%.1f"
              % (rec["px"], rec["bbox"], rec["center_t"][0], rec["center_t"][1],
                 rec["len_px"], rec["wid_px"], rec["angle_deg"]))
    res["leg_components"] = legs

    # --- 5) 橙色腿带
    bands = []
    for c in oc[2:]:
        bands.append({
            "bbox": [int(c[:, 0].min()), int(c[:, 0].max()), int(c[:, 1].min()), int(c[:, 1].max())],
            "center_t": [round((c[:, 0].mean() - x0) / L, 4), round((c[:, 1].mean() - y0) / H, 4)],
            "px": int(len(c)),
        })
    res["leg_bands"] = bands
    print("leg bands:", bands)

    with open("refs_out/structures.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("\n[structures] -> refs_out/structures.json")


if __name__ == "__main__":
    main()
