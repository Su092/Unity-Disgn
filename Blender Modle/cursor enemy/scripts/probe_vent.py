# -*- coding: utf-8 -*-
"""探针：打印蓝条四角的贴合点与法线，用于判断薄板是否与外表面共面。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import build_crawler as B  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
B.setup_scene()
mats = B.build_materials()
body = B.loft_y("GEO-Body", B.BODY, B.body_seg_mat, B.M_ORANGE, mats)

x, hw = B.VENT["x"], B.VENT["half_w"]
for sign in (1, -1):
    corners = [(sign * (x - hw), B.VENT["y0"], 3.0), (sign * (x + hw), B.VENT["y0"], 3.0),
               (sign * (x + hw), B.VENT["y1"], 3.0), (sign * (x - hw), B.VENT["y1"], 3.0)]
    hits = B.surface_hits(body, corners, (0.0, 0.0, -1.0), 0.0)
    print("[probe] side=%+d" % sign)
    for c, h in zip(corners, hits):
        print("   corner=(%.3f,%.3f)  hit=(%.3f,%.3f,%.3f)  n=(%.3f,%.3f,%.3f)"
              % (c[0], c[1], h[0].x, h[0].y, h[0].z, h[1].x, h[1].y, h[1].z))
