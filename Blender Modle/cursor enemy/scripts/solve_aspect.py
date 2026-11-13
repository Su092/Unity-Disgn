# -*- coding: utf-8 -*-
"""按给定机位解"让投影宽高比命中参考 H/L"的轴缩放（解析，不渲染）。

为什么单独做：fit_all 的色类拟合会因为归一化而丢掉比例信息、并对 az 有对称简并；
这里只解一个明确方程：
    在固定机位 (az, el) 下，模型投影 bbox 的 H/L → 参考的 0.7935
未知量是 (length 缩放 sy, height 缩放 sz)，宽度 sx 固定（由左右腿外沿锁定）。
用二分 + 解析投影，秒级。

用法：blender -b crawler.blend --python scripts/solve_aspect.py -- az=52 el=20
"""
import json
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
REFS = os.path.join(PROJ, "refs_out")
OBJ = "GEO-Enemy-Crawler"
TARGET = 0.7935                       # 参考图 H/L（measure_ref.py）

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ARGS = dict(t.split("=", 1) for t in argv if "=" in t)
AZ = float(ARGS.get("az", 52.0))
EL = float(ARGS.get("el", 20.0))


def projected_aspect(verts, az, el):
    a, e = math.radians(az), math.radians(el)
    d = np.array([-math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])
    fwd = -d
    right = np.cross(fwd, np.array([0.0, 0.0, 1.0]))
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    x = verts @ right
    y = verts @ up
    return (y.max() - y.min()) / (x.max() - x.min())


def main():
    obj = bpy.data.objects[OBJ]
    base = np.array([[v.co.x, v.co.y, v.co.z] for v in obj.data.vertices])
    # 基准：z 归一化到 0（底在 0）
    print("[aspect] base (1,1,1) -> %.4f  target %.4f" % (projected_aspect(base, AZ, EL), TARGET))

    # 只调 sy（长度）来命中原比例：sy↑ → 投影更宽 → H/L 下降
    lo, hi = 0.5, 2.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        v = base.copy()
        v[:, 1] *= mid
        if projected_aspect(v, AZ, EL) > TARGET:
            lo = mid
        else:
            hi = mid
    sy = 0.5 * (lo + hi)
    v = base.copy()
    v[:, 1] *= sy
    print("[aspect] solved sy=%.4f -> H/L=%.4f" % (sy, projected_aspect(v, AZ, EL)))

    # 同步给出最终 3D 尺寸
    size = v.max(0) - v.min(0)
    print("[aspect] new AABB  W=%.3f  L=%.3f  H=%.3f  (mm: %d, %d, %d)"
          % (size[0], size[1], size[2], round(size[0] * 1000), round(size[1] * 1000), round(size[2] * 1000)))
    with open(os.path.join(REFS, "aspect_solution.json"), "w", encoding="utf-8") as fh:
        json.dump({"az": AZ, "el": EL, "target_H_over_L": TARGET,
                   "solved_sy": round(float(sy), 5),
                   "achieved_H_over_L": round(float(projected_aspect(v, AZ, EL)), 4),
                   "size_m": {"W": round(float(size[0]), 4), "L": round(float(size[1]), 4),
                              "H": round(float(size[2]), 4)}}, fh, ensure_ascii=False, indent=2)
    print("[aspect] wrote refs_out/aspect_solution.json")


main()
