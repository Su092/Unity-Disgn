# -*- coding: utf-8 -*-
"""Compare a render against the reference: silhouette IoU + palette match.

  python compare.py [render.png] [--mask renders/mask.png]

Reference: E:\\Unity Development\\Blender Modle\\enemy\\ref_crawler.png
"""
import sys, os, json
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
REF = os.path.join(PROJ, "ref_crawler.png")

def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32)

def ref_mask(a):
    bg = np.array([119, 119, 118], np.float32)
    m = np.linalg.norm(a - bg, axis=2) > 30
    # drop the ground shadow: neutral, darker than bg, and below the body mass
    lum = a.mean(axis=2)
    mx = a.max(axis=2); mn = a.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1)
    shadow = (lum < 112) & (sat < 0.10)
    # shadow only counts where it touches the border region (bottom band)
    H = a.shape[0]
    yy = np.arange(H)[:, None]
    shadow = shadow & (yy > H * 0.62)
    return m & ~shadow

def mask_from_alpha(a):
    # transparent film -> alpha in 4th channel; re-read with alpha
    return a[:, :, 3] > 0.5 if a.shape[2] > 3 else None

def hue_class(a, m):
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mx = a.max(axis=2); mn = a.min(axis=2); C = mx - mn
    S = np.where(mx > 0, C / np.maximum(mx, 1), 0)
    V = mx / 255.0
    hue = np.zeros_like(mx)
    nz = C > 1e-6
    hue = np.where(nz & (mx == r), ((g - b) / np.maximum(C, 1e-6)) % 6, hue)
    hue = np.where(nz & (mx == g), ((b - r) / np.maximum(C, 1e-6)) + 2, hue)
    hue = np.where(nz & (mx == b), ((r - g) / np.maximum(C, 1e-6)) + 4, hue)
    hue *= 60.0
    out = {}
    out["red"] = m & (hue < 22) & (S > 0.45) & (V > 0.45)
    out["orange"] = m & (hue >= 22) & (hue < 44) & (S > 0.45) & (V > 0.45)
    out["blue"] = m & (hue > 180) & (hue < 235) & (S > 0.30) & (V > 0.40)
    out["grey"] = m & (S < 0.18) & (V > 0.25) & (V < 0.55)
    out["dark"] = m & (V <= 0.25)
    return out

def stats(a, m, tag):
    rows = []
    cls = hue_class(a, m)
    for k, sel in cls.items():
        n = int(sel.sum())
        rgb = np.round(a[sel].mean(axis=0), 0) if n else None
        rows.append((k, n, rgb))
    print("  %s" % tag)
    for k, n, rgb in rows:
        print("    %-7s n=%7d  mean=%s" % (k, n, rgb))
    return cls

def main():
    render = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJ, "renders", "hero.png")
    maskp = os.path.join(PROJ, "renders", "mask.png")
    a_ref = load(REF)
    a_ren = load(render)
    H = a_ref.shape[0]
    if a_ren.shape[0] != H:
        a_ren = np.asarray(Image.fromarray(a_ren.astype(np.uint8)).resize(
            (H, H), Image.LANCZOS)).astype(np.float32)

    m_ref = ref_mask(a_ref)
    if os.path.exists(maskp):
        m_ren = load(maskp)[:, :, 3] > 128 if load(maskp).shape[2] == 4 else \
                (load(maskp).max(axis=2) > 10)
        # mask.png is render size; resample
        if m_ren.shape[0] != H:
            m_ren = np.asarray(Image.fromarray((m_ren * 255).astype(np.uint8))
                               .resize((H, H), Image.NEAREST)) > 128
    else:
        bg = np.array([119, 119, 118], np.float32)
        m_ren = np.linalg.norm(a_ren - bg, axis=2) > 30

    inter = int((m_ref & m_ren).sum())
    union = int((m_ref | m_ren).sum())
    iou = inter / max(union, 1)

    def bbox(m):
        ys, xs = np.nonzero(m)
        return (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()))

    br, bn = bbox(m_ref), bbox(m_ren)
    print("=== silhouette ===")
    print("  ref    area=%7d bbox=%s" % (m_ref.sum(), br))
    print("  render area=%7d bbox=%s" % (m_ren.sum(), bn))
    print("  IoU=%.4f  Dice=%.4f  missing=%d extra=%d" % (
        iou, 2 * inter / max(m_ref.sum() + m_ren.sum(), 1),
        int((m_ref & ~m_ren).sum()), int((m_ren & ~m_ref).sum())))

    print("=== palette ===")
    stats(a_ref, m_ref, "ref")
    stats(a_ren, m_ren, "render")

    out = {"iou": round(iou, 4), "ref_bbox": br, "render_bbox": bn,
           "missing": int((m_ref & ~m_ren).sum()), "extra": int((m_ren & ~m_ref).sum())}
    with open(os.path.join(PROJ, "renders", "compare.json"), "w") as f:
        json.dump(out, f, indent=1)

    # overlay for eyeballing: ref silhouette in red, render in cyan
    ov = (a_ref * 0.35).astype(np.uint8)
    ov[m_ref & ~m_ren] = [255, 40, 40]
    ov[m_ren & ~m_ref] = [40, 200, 255]
    ov[m_ref & m_ren] = (a_ref[m_ref & m_ren] * 0.9).astype(np.uint8)
    Image.fromarray(ov).save(os.path.join(PROJ, "renders", "overlay.png"))
    print("  overlay ->", os.path.join(PROJ, "renders", "overlay.png"))

main()
