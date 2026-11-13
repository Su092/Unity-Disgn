# -*- coding: utf-8 -*-
"""色类判据（唯一实现，供 measure_shot.py / classfit.py / fit_shape.py 共用）。

只用 numpy，不依赖 PIL —— Blender 自带 Python 也能 import。

为什么用 **G/R 比** 而不只是亮度：
  参考图实测（spec.md §0）：
    橙壳   #D1462A  G/R = 0.34
    琥珀带 #E0891E  G/R = 0.60   （与橙壳色相不同，不能靠亮度分）
    visor  #FEB119  G/R = 0.70
    蓝条   #5FC3FC  B 显著高于 R
   深灰    #2F3136  R 低，不属于任何暖色
  亮度在自发光下会被 clip 到 1.0，色相（G/R）不会 —— 所以判据用色相。

类别码：0 背景  1 橙壳  2 琥珀  3 蓝  4 深灰
"""
import numpy as np

BG = 0
ORANGE = 1
AMBER = 2
BLUE = 3
DARK = 4

NAMES = {ORANGE: "orange", AMBER: "amber", BLUE: "blue", DARK: "dark"}

# 参考图背景：中性灰，sRGB luma ≈ 0.467，sat < 0.05
BG_LUMA = 0.467


def hue_of(rgb):
    """HSV 色相角（0..360）。对亮度/高光不敏感 —— 白色高光同时抬高 R/G/B，
    色相基本不动，而 G/R 会比被抬高（实测：橙壳高光处 G/R 从 0.33 涨到 0.47，
    会和琥珀带 #E0891E 的 0.60 混在一起）。"""
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    mx = rgb.max(2)
    mn = rgb.min(2)
    delta = np.maximum(mx - mn, 1e-6)
    hue = np.zeros_like(delta)
    is_max_r = (mx == r)
    is_max_g = (mx == g)
    is_max_b = (mx == b)
    hue[is_max_r] = 60.0 * (((g - b) / delta)[is_max_r] % 6.0)
    hue[is_max_g] = 60.0 * (((b - r) / delta)[is_max_g] + 2.0)
    hue[is_max_b] = 60.0 * (((r - g) / delta)[is_max_b] + 4.0)
    return hue, mx, delta


def classify(rgb, mask=None):
    """rgb: HxWx3 float（0..1，sRGB 直接值）。返回 int8 类别图。

    色相分区（参考图实测）：
      橙壳 #D1462A → 10°    琥珀 #E0891E → 33°    visor #FEB119 → 40°
      蓝条 #5FC3FC → 202°   深灰 #2F3136 → 无色相（delta 小）
    """
    hue, mx, delta = hue_of(rgb)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    if mask is None:
        mask = mask_of(rgb)

    warm = mask & (delta > 0.10) & (((hue < 62.0)) | (hue > 330.0))
    cls = np.full(rgb.shape[:2], BG, np.int8)
    cls[mask] = DARK
    cls[warm & (hue < 21.0)] = ORANGE
    cls[warm & (hue >= 21.0)] = AMBER
    blue = mask & (delta > 0.10) & (hue > 165.0) & (hue < 245.0)
    cls[blue] = BLUE
    return cls


def visor_mask(rgb, cls):
    """visor 核心 = 琥珀里色相最高、亮度最高的一小片。"""
    hue, mx, delta = hue_of(rgb)
    return (cls == AMBER) & (hue > 34.0) & (mx > 0.88)


def mask_of(rgb):
    mx = rgb.max(2)
    mn = rgb.min(2)
    sat = mx - mn
    lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    return ~((sat < 0.05) & (np.abs(lum - BG_LUMA) < 0.055))


def bbox(cls, cls_id=None):
    m = (cls != BG) if cls_id is None else (cls == cls_id)
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())


def normalised(cls, box, size):
    """裁到 box 并最近邻缩放到 size×size（类别码保持，不插值）。"""
    x0, x1, y0, y1 = box
    crop = cls[y0:y1 + 1, x0:x1 + 1]
    h, w = crop.shape
    yi = (np.arange(size) * h // size).astype(np.int32)
    xi = (np.arange(size) * w // size).astype(np.int32)
    return crop[yi][:, xi]


def class_iou(a, b):
    """逐类 IoU。a/b 是同尺寸类别图。返回 {name: iou}, 以及剪影 IoU。"""
    out = {}
    sa, sb = a != BG, b != BG
    out["sil"] = float((sa & sb).sum() / max((sa | sb).sum(), 1))
    for k, name in NAMES.items():
        ma, mb = a == k, b == k
        union = int((ma | mb).sum())
        if union < 40:
            continue
        out[name] = float((ma & mb).sum() / union)
    return out
