# -*- coding: utf-8 -*-
"""参考图 vs 模型剪影的比例对照（H/L、W/H），并出并排对照图。"""

import json
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(ROOT, "refs")
RENDERS = os.path.join(ROOT, "renders")
GATE = os.path.join(ROOT, "gate")
os.makedirs(GATE, exist_ok=True)


def bbox_ref(path, tol=30):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    bg = px[5, 5]
    mnx, mny, mxx, mxy = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > tol:
                mnx = min(mnx, x); mxx = max(mxx, x)
                mny = min(mny, y); mxy = max(mxy, y)
    return im, (mnx, mny, mxx + 1, mxy + 1)


def bbox_alpha(path):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    a = im.getchannel("A")
    box = a.point(lambda v: 255 if v > 8 else 0).getbbox()
    return im, box or (0, 0, w, h)


def contact(ref_path, model_path, out_path, model_alpha=True):
    ri, rb = bbox_ref(ref_path)
    mi, mb = (bbox_alpha(model_path) if model_alpha else bbox_ref(model_path))
    rw, rh = rb[2] - rb[0], rb[3] - rb[1]
    mw, mh = mb[2] - mb[0], mb[3] - mb[1]
    th = 560
    ri2 = ri.crop(rb).resize((max(1, int(rw * th / rh)), th), Image.LANCZOS)
    mi2 = mi.crop(mb).resize((max(1, int(mw * th / mh)), th), Image.LANCZOS)
    if mi2.mode == "RGBA":
        bg = Image.new("RGB", mi2.size, (150, 150, 150))
        bg.paste(mi2, mask=mi2.getchannel("A"))
        mi2 = bg
    canvas = Image.new("RGB", (ri2.width + 24 + mi2.width, th), (150, 150, 150))
    canvas.paste(ri2, (0, 0))
    canvas.paste(mi2, (ri2.width + 24, 0))
    canvas.save(out_path)


def main():
    rows = []
    for view, ref, model in (
        ("side", "sport-ref-side.png", "side-cut.png"),
        ("front", "sport-ref-front.png", "front-cut.png"),
    ):
        _, rb = bbox_ref(os.path.join(REFS, ref))
        _, mb = bbox_alpha(os.path.join(RENDERS, model))
        rw, rh = rb[2] - rb[0], rb[3] - rb[1]
        mw, mh = mb[2] - mb[0], mb[3] - mb[1]
        rows.append({
            "view": view,
            "ref_px": [rw, rh],
            "model_px": [mw, mh],
            "ref_ratio": round(rw / float(rh), 4),
            "model_ratio": round(mw / float(mh), 4),
            "delta": round(mw / float(mh) - rw / float(rh), 4),
        })
        contact(os.path.join(REFS, ref), os.path.join(RENDERS, model),
                os.path.join(RENDERS, "compare-%s.png" % view))

    data = {"note": "参考图为手绘/概念图，比例只作形体对照，不作毫米级结论。", "views": rows}
    with open(os.path.join(GATE, "ref-compare.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
