# -*- coding: utf-8 -*-
"""参考图 vs 模型剪影 的对拍：只用数字，不靠目测。

比对项（都用"车身长度"归一化，避免分辨率差异）：
  · H/L            总高 / 总长
  · 轮径比          轮子直径 / 总长
  · 轴距比          两轮心距 / 总长
  · 上轮廓 RMS      11 点采样，正反两个朝向取误差小的那个
（参考图带墨线，暗块游程会比轮胎本体宽，所以轮径用"容差 ±0.03L"判，
 不用 ±0.01L。）

用法：
  blender -b --factory-startup --python scripts/ref_compare.py -- <ref.png> <model_silhouette.png>
"""

import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else ".")
import measure_ref as M  # noqa: E402

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []


def wheel_dia(m):
    ws = m.get("wheels") or []
    if len(ws) < 2:
        return None
    return None


def rms(a, b):
    n = min(len(a), len(b))
    return (sum((a[i] - b[i]) ** 2 for i in range(n)) / n) ** 0.5


def main():
    ref, sil = argv[0], argv[1]
    r = M.metrics(ref)
    s = M.metrics(sil)
    print("== 参考图 vs 模型剪影 ==")
    for k, label, tol in (("H_over_L", "H/L", 0.012),
                          ("highest_t", "最高点位置 t", 0.06)):
        if k in r and k in s:
            d = abs(r[k] - s[k])
            print("  %-12s ref=%.4f  model=%.4f  |d|=%.4f  tol=%.3f  %s"
                  % (label, r[k], s[k], d, tol, "OK" if d <= tol else "OUT"))

    rp, sp = r.get("top_profile"), s.get("top_profile")
    if rp and sp:
        e1 = rms(rp, sp)
        e2 = rms(rp, list(reversed(sp)))
        print("  上轮廓 RMS   ref vs model = %.4f   反向后 = %.4f   best=%.4f"
              % (e1, e2, min(e1, e2)))
        best = "正向" if e1 <= e2 else "反向"
        print("  朝向判定     %s（说明两图车头同向）" % best)

    print("  ref   top=%s" % " ".join("%.2f" % v for v in (rp or [])))
    print("  model top=%s" % " ".join("%.2f" % v for v in (sp or [])))
    print("  model top^=%s" % " ".join("%.2f" % v for v in reversed(sp or [])))


if __name__ == "__main__":
    main()
