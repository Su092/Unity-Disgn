# -*- coding: utf-8 -*-
"""按色相分层做连通域分析：每个色块的定向包围盒（PCA）+ 角点，给出可建模的像素几何。

输出写入 refs_out/components.json，控制台打印摘要。
"""
import json
from collections import deque

import numpy as np
from PIL import Image

NP_SAVE = "refs_out/mask.npy"


def label_mask(mask):
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    comps = []
    cur = 0
    ys, xs = np.nonzero(mask)
    visited = np.zeros((h, w), bool)
    for sy, sx in zip(ys, xs):
        if visited[sy, sx]:
            continue
        cur += 1
        q = deque([(sx, sy)])
        visited[sy, sx] = True
        pts = []
        while q:
            x, y = q.popleft()
            lab[y, x] = cur
            pts.append((x, y))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    q.append((nx, ny))
        if len(pts) >= 120:
            comps.append({"id": cur, "pts": np.array(pts, np.int32)})
        else:
            for x, y in pts:
                lab[y, x] = 0
    return lab, comps


def orient(pts, x0, y0, L, H):
    p = pts.astype(np.float64)
    c = p.mean(0)
    q = p - c
    cov = q.T @ q / len(p)
    evals, evecs = np.linalg.eigh(cov)
    major = evecs[:, np.argmax(evals)]
    minor = evecs[:, np.argmin(evals)]
    u = q @ major
    v = q @ minor
    return {
        "center_px": [float(c[0]), float(c[1])],
        "center_t": [round((c[0] - x0) / float(L), 4), round((c[1] - y0) / float(H), 4)],
        "major_dir": [round(float(major[0]), 4), round(float(major[1]), 4)],
        "length_px": round(float(u.max() - u.min()), 2),
        "width_px": round(float(v.max() - v.min()), 2),
        "angle_deg": round(float(np.degrees(np.arctan2(major[1], major[0]))), 2),
        "n": int(len(p)),
        "bbox_px": [int(pts[:, 0].min()), int(pts[:, 0].max()),
                    int(pts[:, 1].min()), int(pts[:, 1].max())],
    }


def main():
    a = np.asarray(Image.open("ref_crawler.png").convert("RGB")).astype(np.float32) / 255.0
    mask = np.load(NP_SAVE)
    ys, xs = np.nonzero(mask)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    L, H = x1 - x0 + 1, y1 - y0 + 1
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    sets = {
        "blue": mask & (b > r + 0.12) & (b > 0.45),
        "bright_orange": mask & (r > b + 0.18) & (r > 0.72) & (lum > 0.60),
        "mid_orange": mask & (r > b + 0.18) & (r > 0.45) & (r <= 0.72) & (lum > 0.42),
    }

    out = {}
    for name, m in sets.items():
        lab, comps = label_mask(m)
        comps.sort(key=lambda c: -len(c["pts"]))
        print("\n== %s : %d components ==" % (name, len(comps)))
        recs = []
        for c in comps[:14]:
            o = orient(c["pts"], x0, y0, L, H)
            o["id"] = c["id"]
            recs.append(o)
            print("  #%-3d n=%6d c_t=(%.3f,%.3f) L=%.1f W=%.1f ang=%.1f°  bbox x[%d,%d] y[%d,%d]"
                  % (o["id"], o["n"], o["center_t"][0], o["center_t"][1],
                     o["length_px"], o["width_px"], o["angle_deg"],
                     o["bbox_px"][0], o["bbox_px"][1], o["bbox_px"][2], o["bbox_px"][3]))
        out[name] = recs

    with open("refs_out/components.json", "w", encoding="utf-8") as f:
        json.dump({"bbox": [int(x0), int(x1), int(y0), int(y1)], "L": int(L), "H": int(H),
                   "sets": out}, f, ensure_ascii=False, indent=2)
    print("\n[components] -> refs_out/components.json")


if __name__ == "__main__":
    main()
