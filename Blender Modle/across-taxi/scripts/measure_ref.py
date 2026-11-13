# -*- coding: utf-8 -*-
"""量测参考图：把"看不清"变成数字（像素口径 + 以选定车长换算的 mm 口径）。

输出：refs/measure-side.json / refs/measure-front.json + 控制台可读表。

纪律：所有 mm 均由「选定车长 L_mm」换算；像素数字全部来自本脚本实测。
"""
import json
import os
import sys
from collections import deque

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, "refs")


def load(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32) / 255.0
    return a, im.size


def bg_color(a):
    h, w, _ = a.shape
    border = np.concatenate([
        a[0:3].reshape(-1, 3), a[h - 3:h].reshape(-1, 3),
        a[:, 0:3].reshape(-1, 3), a[:, w - 3:w].reshape(-1, 3)])
    return np.median(border, axis=0)


def mask_of(a, bg, thr=0.10):
    d = np.sqrt(((a - bg) ** 2).sum(axis=2))
    return d > thr


def bbox(m):
    ys, xs = np.where(m)
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


def profile(m, step=1):
    """每列的 top / bottom（无前景返回 None）。"""
    h, w = m.shape
    cols = {}
    for x in range(0, w, step):
        col = np.where(m[:, x])[0]
        if col.size:
            cols[x] = (int(col.min()), int(col.max()))
    return cols


def components(m, min_px=200):
    """简单 4 连通分量（downsample 后跑，够用）。"""
    h, w = m.shape
    seen = np.zeros_like(m, dtype=bool)
    out = []
    for y in range(h):
        for x in range(w):
            if not m[y, x] or seen[y, x]:
                continue
            q = deque([(y, x)])
            seen[y, x] = True
            pts = []
            while q:
                cy, cx = q.popleft()
                pts.append((cy, cx))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if len(pts) >= min_px:
                ys = [p[0] for p in pts]
                xs = [p[1] for p in pts]
                out.append({"n": len(pts), "bbox": [min(xs), min(ys), max(xs), max(ys)],
                            "cx": sum(xs) / len(xs), "cy": sum(ys) / len(ys)})
    return out


def analyze_side(path, L_mm, out_json):
    a, (W, H) = load(path)
    bg = bg_color(a)
    m = mask_of(a, bg, 0.10)
    # 去掉背景网格 / 墨线的零星像素：只保留最大连通块
    small = m[::2, ::2]
    comps = components(small, min_px=400)
    comps.sort(key=lambda c: -c["n"])
    body = comps[0]
    x0, y0, x1, y1 = [int(v * 2) for v in body["bbox"]]
    # 用连通块重算 mask（去掉背景噪点）
    keep = np.zeros_like(m)
    keep[y0:y1 + 1, x0:x1 + 1] = m[y0:y1 + 1, x0:x1 + 1]

    length_px = x1 - x0 + 1
    height_px = y1 - y0 + 1
    px_per_mm = length_px / float(L_mm)

    def mm(px):
        return round(px / px_per_mm, 1)

    # ---- 轮胎：暗像素（低亮度 / 低饱和）聚成连通域
    lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    sat = a.max(axis=2) - a.min(axis=2)
    tire = keep & (lum < 0.34) & (sat < 0.16)
    tcomps = components(tire[::2, ::2], min_px=300)
    tcomps.sort(key=lambda c: c["cx"])
    wheels = []
    for c in tcomps:
        bx0, by0, bx1, by1 = [v * 2 for v in c["bbox"]]
        wpx, hpx = bx1 - bx0 + 1, by1 - by0 + 1
        # 轮胎是暗环：宽度应明显大于轮毂；粗略取暗域 bbox
        wheels.append({
            "bbox_px": [bx0, by0, bx1, by1],
            "w_px": wpx, "h_px": hpx,
            "cx_px": round((bx0 + bx1) / 2.0, 1),
            "cy_px": round((by0 + by1) / 2.0, 1),
            "r_px": round((wpx + hpx) / 4.0, 1),
        })

    # ---- 关键横向地标：按列统计"车顶高度"，找出车顶/引擎盖
    top_by_x, bot_by_x = {}, {}
    for x in range(x0, x1 + 1, 4):
        col = np.where(keep[:, x])[0]
        if col.size:
            top_by_x[x] = int(col.min())
            bot_by_x[x] = int(col.max())

    xs = sorted(top_by_x)
    roof_y = min(top_by_x[x] for x in xs)               # 灯箱顶
    roof_span = [x for x in xs if top_by_x[x] <= roof_y + 3]

    # 车身顶面（排除灯箱）：取灯箱两侧 40px 外的最低 top
    body_top_y = None
    for x in xs:
        if roof_span[0] - 120 < x < roof_span[-1] + 120:
            continue
        v = top_by_x[x]
        body_top_y = v if body_top_y is None else min(body_top_y, v)

    # 地面线：底部轮廓的最大值（接地）
    ground_y = max(bot_by_x.values())

    # ---- 棋盘带：沿一条竖线找黑白交替（在车身中段）
    def band_rows(x):
        col = a[:, x, :]
        rows = []
        for y in range(y0, y1 + 1):
            c = col[y]
            s = float(c.max() - c.min())
            if s < 0.10 and 0.25 < float(c.max()) < 0.95:
                rows.append(y)
        return rows

    band_x = x0 + int(length_px * 0.55)
    rows = band_rows(band_x)
    # 连续段
    segs = []
    if rows:
        s = rows[0]
        p = rows[0]
        for r in rows[1:]:
            if r - p > 6:
                segs.append((s, p))
                s = r
            p = r
        segs.append((s, p))
    segs = [s for s in segs if s[1] - s[0] > 8]

    # ---- 结果
    res = {
        "image": path,
        "native_px": [W, H],
        "scale": {"L_mm": L_mm, "length_px": length_px, "px_per_mm": round(px_per_mm, 6)},
        "bbox_px": [x0, y0, x1, y1],
        "length_px": length_px,
        "height_px": height_px,
        "h_over_l": round(height_px / length_px, 4),
        "roof_sign_top_y": roof_y,
        "roof_sign_span_px": [int(roof_span[0]), int(roof_span[-1])] if roof_span else None,
        "body_top_y": body_top_y,
        "ground_y": ground_y,
        "mm": {
            "length": L_mm,
            "height_total": mm(height_px),
            "sign_top_above_ground": mm(ground_y - roof_y),
            "body_top_above_ground": mm(ground_y - body_top_y) if body_top_y else None,
            "sign_height": mm(body_top_y - roof_y) if body_top_y else None,
            "sign_x_from_rear": [mm(x1 - roof_span[-1]), mm(x1 - roof_span[0])] if roof_span else None,
            "sign_width": mm(roof_span[-1] - roof_span[0]) if roof_span else None,
        },
        "wheels": wheels,
        "band_segments_y": segs,
        "top_profile_sample": {int(x): int(top_by_x[x]) for x in xs[::max(1, len(xs) // 40)]},
    }
    for w in wheels:
        w["r_mm"] = mm(w["r_px"])
        w["d_mm"] = mm(w["r_px"] * 2)
        w["cx_from_front_mm"] = mm(w["cx_px"] - x0)
        w["cy_above_ground_mm"] = mm(ground_y - w["cy_px"])
    if len(wheels) >= 2:
        res["wheelbase_px"] = round(wheels[-1]["cx_px"] - wheels[0]["cx_px"], 1)
        res["wheelbase_mm"] = mm(wheels[-1]["cx_px"] - wheels[0]["cx_px"])
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    return res


def analyze_front(path, L_mm, out_json):
    a, (W, H) = load(path)
    bg = bg_color(a)
    m = mask_of(a, bg, 0.10)
    comps = components(m[::2, ::2], min_px=400)
    comps.sort(key=lambda c: -c["n"])
    body = comps[0]
    x0, y0, x1, y1 = [int(v * 2) for v in body["bbox"]]
    width_px = x1 - x0 + 1
    height_px = y1 - y0 + 1
    px_per_mm = width_px / float(L_mm)

    def mm(px):
        return round(px / px_per_mm, 1)

    lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    sat = a.max(axis=2) - a.min(axis=2)
    keep = np.zeros_like(m)
    keep[y0:y1 + 1, x0:x1 + 1] = m[y0:y1 + 1, x0:x1 + 1]
    tire = keep & (lum < 0.34) & (sat < 0.16)
    tcomps = components(tire[::2, ::2], min_px=250)
    tcomps.sort(key=lambda c: c["cx"])
    wheels = []
    for c in tcomps:
        bx0, by0, bx1, by1 = [v * 2 for v in c["bbox"]]
        wheels.append({"bbox_px": [bx0, by0, bx1, by1],
                       "w_px": bx1 - bx0 + 1, "h_px": by1 - by0 + 1,
                       "cx_px": round((bx0 + bx1) / 2.0, 1)})
    res = {
        "image": path,
        "native_px": [W, H],
        "scale": {"width_mm": L_mm, "width_px": width_px,
                  "px_per_mm": round(px_per_mm, 6)},
        "bbox_px": [x0, y0, x1, y1],
        "width_px": width_px, "height_px": height_px,
        "w_over_h": round(width_px / height_px, 4),
        "mm": {"width": L_mm, "height": mm(height_px)},
        "wheels": wheels,
    }
    if len(wheels) >= 2:
        res["track_outer_px"] = round(wheels[-1]["bbox_px"][2] - wheels[0]["bbox_px"][0], 1)
        res["track_outer_mm"] = mm(res["track_outer_px"])
        res["track_center_px"] = round(wheels[-1]["cx_px"] - wheels[0]["cx_px"], 1)
        res["track_center_mm"] = mm(res["track_center_px"])
        res["tire_w_mm"] = mm(wheels[0]["w_px"])
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    return res


def main():
    argv = sys.argv[1:]
    L_mm = float(argv[0]) if argv else 5200.0
    out = {}
    s = os.path.join(REFS, "ref-side.png")
    if os.path.exists(s):
        out["side"] = analyze_side(s, L_mm, os.path.join(REFS, "measure-side.json"))
    f = os.path.join(REFS, "ref-front.png")
    if os.path.exists(f):
        out["front"] = analyze_front(f, float(argv[1]) if len(argv) > 1 else 2000.0,
                                     os.path.join(REFS, "measure-front.json"))
    print(json.dumps(out, ensure_ascii=False, indent=2)[:6000])


if __name__ == "__main__":
    main()
