#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""APIMart 链式生图：先出主视角，再用它的图片 URL 参考生成其余视角。

问题：清单式批量（apimart_image.py --manifest）是并行/互不可见的，N 个视角只拿到
同一段文字提示，各自想象一遍，比例、灯形、条纹位置都对不上。
做法：主视角先跑完 → 拿到结果 URL → 把它塞进 `image_urls` 再提交其余视角。

用法（仓库根或任意目录执行）：
    python .cursor/skills/apimart-image/scripts/apimart_ref_chain.py \
        --plan "Blender Modle/spiderverse-taxi/refs/plan-sport.json"
    # 只补跑其中几个视角（anchor 仍会重新生成）
    ... --only side,front
    # 用"上一张"作参考，逐张累积一致性（默认是用 anchor）
    ... --ref-mode prev

plan JSON：
  {
    "anchor": {"id","prompt","size","resolution","out"},
    "views":  [{"id","prompt","size","resolution","out"}, ...]
  }
  · out 相对路径按仓库根解析；也接受绝对路径
  · 每条可选 "image_urls"：额外参考图（公网 URL）
  · 每条可选 "no_global_style"/"nsfw_check"：同 apimart_image.py

产物：各视角图片 + 同目录 chain-receipt.json（task_id / URL / 秒数；URL 约 24h 有效）。
"""

import argparse
import json
import os
import sys
import time

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)

import apimart_image as A  # noqa: E402


def find_root(start):
    d = start
    while True:
        if os.path.isfile(os.path.join(d, "tools", ".apimart.key")) or \
           os.path.isfile(os.path.join(d, "tools", "apimart-assets.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return start
        d = parent


ROOT = find_root(_here)


def resolve(path):
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def run_stage(key, item, ref_urls=None):
    t0 = time.time()
    # 参考图默认 1k（工作区口径：贴图 2k / 参考图 1k）。链式产物都是参考图，
    # 不直接进引擎，1k 足够量测比例；2k 会让下载与计费翻倍。
    tid = A.submit(key, item["prompt"], item.get("size", "16:9"),
                   item.get("resolution", "1k"), ref_urls)
    print("  task_id=%s" % tid)
    url = A.poll(key, tid)
    A.download(url, resolve(item["out"]))
    print("  [%s] %.1fs" % (item["id"], time.time() - t0))
    return {"id": item["id"], "task_id": tid, "url": url,
            "out": resolve(item["out"]), "refs": ref_urls or [],
            "seconds": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True, help="plan JSON 路径")
    ap.add_argument("--key")
    ap.add_argument("--only", help="只跑这些 view id（逗号分隔）；anchor 总会跑")
    ap.add_argument("--ref-mode", choices=["anchor", "prev"], default="anchor",
                    help="anchor=所有视角都以主视角为参考；prev=逐张累积")
    ap.add_argument("--receipt", help="回执路径，默认 plan 同目录 chain-receipt.json")
    args = ap.parse_args()

    plan_path = resolve(args.plan)
    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    key = A.find_key(args.key)
    if not key:
        print("缺少密钥：--key / APIMART_API_KEY / tools/.apimart.key", file=sys.stderr)
        return 2

    receipt = []
    print("[chain] anchor %s" % plan["anchor"]["id"])
    anchor = run_stage(key, plan["anchor"])
    receipt.append(anchor)

    ref_url = anchor["url"]
    only = set(s.strip() for s in (args.only or "").split(",") if s.strip())
    for view in plan["views"]:
        if only and view["id"] not in only:
            continue
        extra = list(view.get("image_urls") or [])
        refs = [ref_url] + extra
        print("[chain] view %s (ref=%s)" % (view["id"], args.ref_mode))
        stage = run_stage(key, view, refs)
        receipt.append(stage)
        if args.ref_mode == "prev":
            ref_url = stage["url"]

    receipt_path = args.receipt or os.path.join(os.path.dirname(plan_path),
                                                "chain-receipt.json")
    with open(resolve(receipt_path), "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
    print("[chain] receipt -> %s" % resolve(receipt_path))
    print("[chain] anchor url (≈24h): %s" % anchor["url"])


if __name__ == "__main__":
    sys.exit(main() or 0)
