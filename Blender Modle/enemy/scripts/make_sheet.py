# -*- coding: utf-8 -*-
"""Build renders/compare_sheet.png : reference | render | overlay (labels)."""
import os
import numpy as np
from PIL import Image, ImageDraw

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(PROJ, "renders")
ref = Image.open(os.path.join(PROJ, "ref_crawler.png")).convert("RGB")
ren = Image.open(os.path.join(R, "hero.png")).convert("RGB").resize(ref.size, Image.LANCZOS)

# overlay: ref silhouette red, render silhouette cyan, both = source
a = np.asarray(ref).astype(np.int16)
r = np.asarray(ren).astype(np.int16)
bg = np.array([119, 119, 118])
mref = np.linalg.norm(a - bg, axis=2) > 30
mren = np.linalg.norm(r - bg, axis=2) > 30
ov = (a * 0.32).astype(np.uint8)
ov[mref & ~mren] = [230, 40, 40]
ov[mren & ~mref] = [40, 190, 240]
ov[mref & mren] = (a[mref & mren] * 0.85).astype(np.uint8)
ovim = Image.fromarray(ov)

W, H = ref.size
pad = 24
sheet = Image.new("RGB", (W * 3 + pad * 4, H + pad * 2 + 44), (28, 28, 30))
for i, im in enumerate((ref, ren, ovim)):
    sheet.paste(im, (pad + i * (W + pad), pad + 44))
d = ImageDraw.Draw(sheet)
labels = ["REFERENCE", "MODEL (same camera)", "SILHOUETTE OVERLAY  red=ref only  cyan=model only"]
for i, txt in enumerate(labels):
    d.text((pad + i * (W + pad) + 6, pad + 14), txt, fill=(235, 235, 235))
sheet = sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS)
out = os.path.join(R, "compare_sheet.png")
sheet.save(out)
print("WROTE", out, sheet.size)
