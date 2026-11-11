# -*- coding: utf-8 -*-
"""参考图 vs 渲染的轮廓比例对照（只做 H/L、H/W，不冒充 IoU 全检）。"""

import json
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, "refs")
RENDERS = os.path.join(ROOT, "renders")
GATE = os.path.join(ROOT, "gate")
os.makedirs(GATE, exist_ok=True)


def bbox_of(path, tol=36):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    bg = px[min(5, w - 1), min(5, h - 1)]
    minx, miny, maxx, maxy = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > tol:
                if x < minx:
                    minx = x
                if x > maxx:
                    maxx = x
                if y < miny:
                    miny = y
                if y > maxy:
                    maxy = y
    if maxx < 0:
        return im, (0, 0, w, h)
    return im, (minx, miny, maxx + 1, maxy + 1)


def measure(path):
    im, box = bbox_of(path)
    w = box[2] - box[0]
    h = box[3] - box[1]
    return im, box, w, h


def contact_sheet(ref_path, ren_path, out_path):
    ri, rb, rw, rh = measure(ref_path)
    mi, mb, mw, mh = measure(ren_path)
    target_h = 620
    ri2 = ri.crop(rb).resize((max(1, int(rw * target_h / rh)), target_h), Image.LANCZOS)
    mi2 = mi.crop(mb).resize((max(1, int(mw * target_h / mh)), target_h), Image.LANCZOS)
    gap = 24
    canvas = Image.new("RGB", (ri2.width + gap + mi2.width, target_h), (150, 150, 150))
    canvas.paste(ri2, (0, 0))
    canvas.paste(mi2, (ri2.width + gap, 0))
    canvas.save(out_path)
    print("[compare] %s" % out_path)


def main():
    rows = []
    for name, ref, ren in (
        ("west", "church-ref-west.png", "west.png"),
        ("side", "church-ref-side.png", "side.png"),
    ):
        _, _, rw, rh = measure(os.path.join(REFS, ref))
        _, _, mw, mh = measure(os.path.join(RENDERS, ren))
        rr = rh / float(rw)
        mr = mh / float(mw)
        rows.append({
            "view": name,
            "ref_px": [rw, rh],
            "model_px": [mw, mh],
            "ref_h_over_w": round(rr, 4),
            "model_h_over_w": round(mr, 4),
            "delta": round(mr - rr, 4),
        })
        contact_sheet(os.path.join(REFS, ref), os.path.join(RENDERS, ren),
                      os.path.join(RENDERS, "compare-%s.png" % name))

    data = {
        "note": "AI 参考图不是标定图；这里只比轮廓比例，不作毫米级结论。",
        "views": rows,
    }
    out = os.path.join(GATE, "ref-compare.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
