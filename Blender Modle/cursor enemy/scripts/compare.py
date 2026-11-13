# -*- coding: utf-8 -*-
"""参考图 vs 渲染 的对拍（唯一口径，全部走 scripts/refclass.py 的色相分类）。

输出：
  · 归一化剪影 IoU（几何口径；渲染侧用无背景剪影图，避免接触阴影被当成主体）
  · 四类色块的中心与 bbox（颜色口径，用带光照的渲染图）
  · 三类发光/涂装色块的 L1 中心偏差（visor / blue / amber-sideband）
一张三联对照图：参考 / 模型 / 轮廓叠合。

用法：
  python scripts/compare.py ref_crawler.png renders/hero.png renders/compare.png renders/silhouette.png
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import refclass as RC  # noqa: E402


def load(path):
    im = Image.open(path)
    arr = np.asarray(im.convert("RGBA"))
    transparent = im.mode in ("RGBA", "LA") and int(arr[:, :, 3].min()) < 10
    return arr.astype(np.float32) / 255.0, transparent


def analyse(path):
    a, transparent = load(path)
    rgb = a[:, :, :3]
    if transparent:
        mask = a[:, :, 3] > 0.5
        cls = RC.classify(rgb, mask=mask)
    else:
        cls = RC.classify(rgb)
    box = RC.bbox(cls)
    if box is None:
        return None
    x0, x1, y0, y1 = box
    L, H = x1 - x0 + 1, y1 - y0 + 1
    out = {"path": path, "bbox": box, "L": L, "H": H, "H_over_L": round(H / L, 4), "cues": {}, "boxes": {}}
    for k, name in RC.NAMES.items():
        m = cls == k
        yy, xx = np.nonzero(m)
        if len(xx) < 60:
            continue
        out["cues"][name] = [round((xx.mean() - x0) / L, 4), round((yy.mean() - y0) / H, 4)]
        out["boxes"][name] = [int(xx.min()), int(xx.max()), int(yy.min()), int(yy.max())]
    vis = RC.visor_mask(rgb, cls)
    yy, xx = np.nonzero(vis)
    if len(xx) >= 40:
        out["cues"]["visor_core"] = [round((xx.mean() - x0) / L, 4), round((yy.mean() - y0) / H, 4)]
        out["boxes"]["visor_core"] = [int(xx.min()), int(xx.max()), int(yy.min()), int(yy.max())]
        out["visor_px"] = int(len(xx))
    # 侧条：琥珀里**不属于腿带、也不属于 visor** 的那部分。
    # ⚠ visor 的色相（40°）落在琥珀区间内，不剔掉它会把侧条质心拖到头部
    #   （参考图实测：混入 visor 时 0.512，剔除后 0.29）。
    amb = cls == RC.AMBER
    upper = np.zeros_like(amb)
    upper[y0:int(y0 + H * 0.62)] = True
    vis = RC.visor_mask(rgb, cls)
    dil = vis.copy()
    for _ in range(3):
        shifted = np.zeros_like(dil)
        shifted[1:, :] |= dil[:-1, :]
        shifted[:-1, :] |= dil[1:, :]
        shifted[:, 1:] |= dil[:, :-1]
        shifted[:, :-1] |= dil[:, 1:]
        dil = shifted | dil
    side = amb & upper & ~dil
    yy, xx = np.nonzero(side)
    if len(xx) >= 250:
        # 质心只在"单段连续条"上可比；参考图的侧条被腿部遮挡切成多段，
        # 质心会被拖向遮挡侧。所以这里同时给**跨度**（x 方向 min/max），
        # 判据用跨度（spec.md §5-H 已注明）。
        out["cues"]["sideband"] = [round((xx.mean() - x0) / L, 4), round((yy.mean() - y0) / H, 4)]
        out["sideband_span_x"] = [round((xx.min() - x0) / L, 4), round((xx.max() - x0) / L, 4)]
        out["sideband_px"] = int(len(xx))
    yy, xx = np.nonzero(amb & ~upper & ~dil)
    if len(xx) >= 250:
        out["cues"]["legband"] = [round((xx.mean() - x0) / L, 4), round((yy.mean() - y0) / H, 4)]
    return out


def crop_norm(mask, rgb, size=420):
    ys, xs = np.nonzero(mask)
    pad = 8
    x0, x1 = max(0, ys.min() * 0 - 0 + xs.min() - pad), min(mask.shape[1] - 1, xs.max() + pad)
    y0, y1 = max(0, ys.min() - pad), min(mask.shape[0] - 1, ys.max() + pad)
    img = Image.fromarray((rgb[y0:y1 + 1, x0:x1 + 1] * 255).astype(np.uint8))
    return img.resize((size, size), Image.LANCZOS)


def overlay(ref_mask, shot_mask, size=420):
    def norm(m):
        ys, xs = np.nonzero(m)
        crop = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        return np.asarray(Image.fromarray((crop * 255).astype(np.uint8))
                          .resize((size, size), Image.NEAREST)) > 127
    A, B = norm(ref_mask), norm(shot_mask)
    out = np.zeros((size, size, 3), np.uint8)
    out[A & ~B] = (230, 60, 50)
    out[B & ~A] = (50, 190, 90)
    out[A & B] = (235, 210, 60)
    return Image.fromarray(out)


def main():
    ref_path, shot_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    sil_path = sys.argv[4] if len(sys.argv) > 4 else None

    ra, r_tr = load(ref_path)
    sa, s_tr = load(shot_path)
    ga, g_tr = load(sil_path) if (sil_path and os.path.exists(sil_path)) else (sa, s_tr)

    rmask = (ra[:, :, 3] > 0.5) if r_tr else RC.mask_of(ra[:, :, :3])
    gmask = (ga[:, :, 3] > 0.5) if g_tr else RC.mask_of(ga[:, :, :3])

    ref = analyse(ref_path)
    mod_geo = analyse(sil_path) if sil_path and os.path.exists(sil_path) else analyse(shot_path)
    mod_col = analyse(shot_path)

    print("== 形体（几何口径：%s）==" % ("剪影图" if sil_path else "渲染图"))
    print("  H/L         ref=%.4f  model=%.4f  |d|=%.4f"
          % (ref["H_over_L"], mod_geo["H_over_L"], abs(ref["H_over_L"] - mod_geo["H_over_L"])))
    print("  L,H px      ref=(%d,%d)  model=(%d,%d)" % (ref["L"], ref["H"], mod_geo["L"], mod_geo["H"]))

    print("\n== 色块（颜色口径：渲染图 + 色相分类）==")
    print("  %-10s %-20s %-20s %s" % ("cue", "reference", "model", "L1"))
    worst = 0.0
    for key in ("visor_core", "blue", "legband", "orange", "amber"):
        rc = ref["cues"].get(key)
        mc = mod_col["cues"].get(key)
        if rc and mc:
            d = abs(rc[0] - mc[0]) + abs(rc[1] - mc[1])
            worst = max(worst, d)
            print("  %-10s %-20s %-20s %.4f" % (key, rc, mc, d))
        else:
            print("  %-10s %-20s %-20s n/a" % (key, rc, mc))
    # 侧条单列：判据用**跨度**而不是质心（参考图侧条被腿部遮挡切成多段）
    rs = ref.get("sideband_span_x")
    ms = mod_col.get("sideband_span_x")
    if rs and ms:
        d0 = abs(rs[0] - ms[0])
        d1 = abs(rs[1] - ms[1])
        worst = max(worst, d0, d1)
        print("  %-10s %-20s %-20s %.4f (两端取大)"
              % ("sideband", "x[%.3f,%.3f]" % tuple(rs), "x[%.3f,%.3f]" % tuple(ms), max(d0, d1)))
    print("  worst L1 = %.4f  (判据见 spec.md §5-H：≤0.06 为通过)" % worst)

    canvas = Image.new("RGB", (420 * 3 + 40, 462), (28, 28, 30))
    canvas.paste(crop_norm(rmask, ra[:, :, :3]), (10, 32))
    canvas.paste(crop_norm(gmask, ga[:, :, :3]), (440, 32))
    canvas.paste(overlay(rmask, gmask), (870, 32))
    from PIL import ImageDraw
    d = ImageDraw.Draw(canvas)
    d.text((12, 10), "REFERENCE", fill=(240, 240, 240))
    d.text((442, 10), "MODEL", fill=(240, 240, 240))
    d.text((872, 10), "OVERLAY  red=ref only / green=model only / yellow=both", fill=(240, 240, 240))
    canvas.save(out_path)
    with open(os.path.splitext(out_path)[0] + ".json", "w", encoding="utf-8") as fh:
        json.dump({"reference": ref, "model_geometry": mod_geo, "model_colour": mod_col,
                   "worst_cue_L1": round(worst, 4)}, fh, ensure_ascii=False, indent=2)
    print("\n[compare] %s (+ .json)" % out_path)


if __name__ == "__main__":
    main()
