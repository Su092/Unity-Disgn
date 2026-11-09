#!/usr/bin/env python
"""APIMart gpt-image-2 生图：提交 → 轮询 → 下载，单文件完成。

只用标准库，无需 pip 安装任何依赖。

用法（仓库根目录执行）：
    python .cursor/skills/apimart-image/scripts/apimart_image.py \
        --prompt "..." --out assets/art/gen/level-map-3.png \
        --size 9:16 --resolution 2k

    # 从 JSON 清单批量跑（结构见 tools/apimart-assets.json）
    python .cursor/skills/apimart-image/scripts/apimart_image.py \
        --manifest tools/apimart-assets.json --only level-map-3

密钥查找顺序：--key 参数 → 环境变量 APIMART_API_KEY → 仓库根 tools/.apimart.key
"""

import argparse
import http.client
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request

BASE = "https://api.apimart.ai/v1"
MODEL = "gpt-image-2"
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
KEY_FILE = os.path.join(REPO, "tools", ".apimart.key")
CACHE_FILE = os.path.join(REPO, "tools", ".apimart-ip.json")
HOST = "api.apimart.ai"


# ---------------------------------------------------------------- DNS 反污染
# 2026-11 实测：本地 DNS 会把 api.apimart.ai 解析到 Facebook 的 IP
# （128.242.250.155 / 2a03:2880:...face:b00c），POST 偶尔蒙对、GET 全部超时。
# 真实地址是 Cloudflare 的三条 A 记录。这里用 DoH（走 HTTPS，不受投毒影响）
# 现取一次并缓存，再用「固定 IP + SNI/Host 头」的方式建连。
DOH_SERVERS = ["https://dns.google/resolve?name={h}&type=A",
               "https://cloudflare-dns.com/dns-query?name={h}&type=A"]

_ip_cache = None


def resolve_real_ips(force=False):
    global _ip_cache
    if _ip_cache and not force:
        return _ip_cache
    if not force and os.path.isfile(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                ips = json.load(f).get("ips") or []
            if ips:
                _ip_cache = ips
                return ips
        except Exception:
            pass

    ips = []
    for tpl in DOH_SERVERS:
        url = tpl.format(h=HOST)
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers={"accept": "application/dns-json"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    j = json.loads(r.read().decode("utf-8"))
                for a in j.get("Answer", []):
                    if a.get("type") == 1 and a.get("data"):
                        ips.append(a["data"])
                if ips:
                    break
            except Exception:
                time.sleep(2)
        if ips:
            break

    if not ips:
        return []          # 交给系统 DNS 兜底

    _ip_cache = ips
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"ips": ips, "at": int(time.time())}, f)
    except Exception:
        pass
    return ips


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """连到固定 IP，但用真实域名做 SNI 与证书校验。"""

    def __init__(self, ip, host, timeout):
        super().__init__(host, 443, timeout=timeout,
                         context=ssl.create_default_context())
        self._ip = ip
        self._host = host

    def connect(self):
        sock = socket.create_connection((self._ip, 443), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self._host)


def request_via(ip, host, method, path, key, payload=None, timeout=120):
    conn = PinnedHTTPSConnection(ip, host, timeout)
    headers = {"Authorization": "Bearer " + key, "Host": host,
               "Accept": "application/json", "Connection": "close"}
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    try:
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8", "replace")
        if resp.status >= 400:
            raise RuntimeError("HTTP %s: %s" % (resp.status, raw[:400]))
        return json.loads(raw)
    finally:
        try:
            conn.close()
        except Exception:
            pass



def find_key(explicit=None):
    if explicit:
        return explicit.strip()
    env = os.environ.get("APIMART_API_KEY")
    if env:
        return env.strip()
    if os.path.isfile(KEY_FILE):
        with open(KEY_FILE, "r", encoding="utf-8") as f:
            v = f.read().strip()
        if v:
            return v
    return None


def http_json(url, key, payload=None, method=None, timeout=180, retries=4):
    """POST/GET 到 APIMart。先试固定 IP（绕过 DNS 投毒），再退回系统 DNS。"""
    path = url[len("https://" + HOST):] if url.startswith("https://" + HOST) else url
    # path 形如 /v1/tasks/xxx；PinnedHTTPSConnection 已经自带域名
    if path.startswith("/v1"):
        pass
    verb = method or ("POST" if payload is not None else "GET")

    ips = resolve_real_ips()
    routes = [("ip", ip) for ip in ips] + [("dns", None)]

    last = None
    for attempt in range(retries):
        for kind, ip in routes:
            try:
                if kind == "ip":
                    j = request_via(ip, HOST, verb, path, key, payload, timeout=min(timeout, 90))
                else:
                    data = None
                    headers = {"Authorization": "Bearer " + key}
                    if payload is not None:
                        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                        headers["Content-Type"] = "application/json"
                    req = urllib.request.Request(url, data=data, headers=headers, method=verb)
                    with urllib.request.urlopen(req, timeout=timeout) as r:
                        j = json.loads(r.read().decode("utf-8"))
                return j
            except RuntimeError as e:
                # 明确的 HTTP 4xx 不必重试
                msg = str(e)
                if msg.startswith("HTTP 4") and not msg.startswith("HTTP 429"):
                    raise
                last = msg
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")
                last = "HTTP %s: %s" % (e.code, body[:400])
                if e.code not in (429, 500, 502, 503, 504):
                    raise RuntimeError(last)
            except Exception as e:
                last = "%s: %s" % (type(e).__name__, e)
        time.sleep(3 * (attempt + 1))
        if attempt == 1:
            resolve_real_ips(force=True)   # 换一组 IP 再试
            routes = [("ip", ip) for ip in (_ip_cache or [])] + [("dns", None)]
    raise RuntimeError(last or "request failed")


def submit(key, prompt, size, resolution, image_urls=None, nsfw_check=False):
    body = {"model": MODEL, "prompt": prompt, "n": 1}
    if size:
        body["size"] = size
    if resolution:
        body["resolution"] = resolution
    if image_urls:
        body["image_urls"] = image_urls
    if nsfw_check:
        body["nsfw_check"] = True

    j = http_json(BASE + "/images/generations", key, body)
    data = j.get("data") or []
    if not data or not data[0].get("task_id"):
        raise RuntimeError("提交失败: " + json.dumps(j, ensure_ascii=False)[:400])
    return data[0]["task_id"]


def poll(key, task_id, timeout_s=600, interval=4):
    """轮询到 completed，返回图片 URL。"""
    deadline = time.time() + timeout_s
    last_status = ""
    while time.time() < deadline:
        time.sleep(interval)
        j = http_json(BASE + "/tasks/" + task_id, key, timeout=90)
        d = j.get("data") or {}
        status = d.get("status", "")
        if status != last_status:
            print("  status=%s progress=%s" % (status, d.get("progress")))
            last_status = status
        if status == "completed":
            try:
                return d["result"]["images"][0]["url"][0]
            except (KeyError, IndexError, TypeError):
                raise RuntimeError("completed 但取不到 url: "
                                   + json.dumps(d, ensure_ascii=False)[:400])
        if status in ("failed", "error"):
            raise RuntimeError("任务失败: " + json.dumps(d, ensure_ascii=False)[:400])
    raise RuntimeError("轮询超时: " + task_id)


def download(url, out_path, min_bytes=10000, retries=4):
    """下载到 out_path，并校验体积（防止拿到错误页/占位图）。"""
    out_path = os.path.join(REPO, out_path) if not os.path.isabs(out_path) else out_path
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "starlane/1.0"})
            with urllib.request.urlopen(req, timeout=300) as r:
                blob = r.read()
            if len(blob) < min_bytes:
                raise RuntimeError("文件过小（%d 字节），可能是错误页" % len(blob))
            with open(out_path, "wb") as f:
                f.write(blob)
            print("  saved %s (%s bytes)" % (out_path, format(len(blob), ",")))
            return out_path
        except Exception as e:
            last = "%s: %s" % (type(e).__name__, e)
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(last or "download failed")


def run_one(key, item, global_style=""):
    prompt = item["prompt"]
    if global_style and not item.get("no_global_style"):
        prompt = prompt + " " + global_style
    print("[%s] submitting (%s / %s)" % (item["id"], item.get("size", "auto"),
                                         item.get("resolution", "1k")))
    tid = submit(key, prompt, item.get("size"), item.get("resolution"),
                 item.get("image_urls"), item.get("nsfw_check", False))
    print("  task_id=%s" % tid)
    url = poll(key, tid)
    return download(url, item["out"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key")
    ap.add_argument("--prompt")
    ap.add_argument("--out")
    ap.add_argument("--size", default="9:16",
                    help="比例（如 9:16）或像素尺寸（如 1080x1920）")
    ap.add_argument("--resolution", default="2k", choices=["1k", "2k", "4k"])
    ap.add_argument("--manifest", help="JSON 清单，含 style 与 assets[]")
    ap.add_argument("--only", help="只跑清单里的这些 id，逗号分隔")
    ap.add_argument("--task-id", help="跳过提交，直接轮询已有任务")
    args = ap.parse_args()

    key = find_key(args.key)
    if not key:
        print("缺少密钥。用 --key、环境变量 APIMART_API_KEY，或写入 tools/.apimart.key",
              file=sys.stderr)
        return 2

    if args.task_id:
        download(poll(key, args.task_id), args.out)
        return 0

    if args.manifest:
        with open(args.manifest, "r", encoding="utf-8") as f:
            m = json.load(f)
        style = m.get("style", "")
        items = m.get("assets", [])
        if args.only:
            want = {s.strip() for s in args.only.split(",") if s.strip()}
            items = [i for i in items if i["id"] in want]
        if not items:
            print("清单里没有匹配的条目", file=sys.stderr)
            return 2
        for it in items:
            run_one(key, it, style)
        return 0

    if not args.prompt or not args.out:
        print("需要 --prompt 与 --out（或改用 --manifest）", file=sys.stderr)
        return 2

    run_one(key, {"id": os.path.basename(args.out), "prompt": args.prompt,
                  "out": args.out, "size": args.size,
                  "resolution": args.resolution, "no_global_style": True})
    return 0


if __name__ == "__main__":
    sys.exit(main())
