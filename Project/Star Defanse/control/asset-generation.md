# 控制：生图与素材操作

> 规范与规格见 `../docs/asset-pipeline.md` 与 `../docs/art-style.md`，本文件只讲**操作纪律**。

## 工作目录

所有命令在 `E:\Unity Development\Project\Star Defanse\unity\`（= 工程根）执行。
脚本内部用 `__file__` 反推仓库根，所以从工作区根执行也能定位 `tools/`。

## 密钥

- 位置：`unity/tools/.apimart.key`（已 gitignore，也忽略 `*.key`）
- 不要重复询问、不要写入仓库、不要在命令里明文传 `--key`
- 换密钥时只改这一个文件

## 调用纪律

| 场景 | 做法 |
|------|------|
| 要新素材 | 先在对应清单 `tools/*.json` 加条目（`id` / `out` / `size` / `prompt`），再用 `--only` 跑单条 |
| 批量重跑 | `--manifest tools/xxx.json`，跑完立刻看 `tools/.apimart-state.json` 是否有失败条目 |
| 只查任务 | `--task-id task_xxx --out <路径>`，不重新提交（避免重复扣费） |
| 用户要求验证链路 | 才允许跑 1k 测试图 |
| API 报错 | 先看是不是 DNS 污染（`SSL: UNEXPECTED_EOF`、GET 全超时）；脚本已内置 DoH + 固定 IP，别自己改传输层 |

- `resolution` 按档位计费，调试用 `1k`，正式素材 `2k`。
- 结果 URL 24 小时过期，脚本会自动下载并校验体积（<10 KB 判失败，防拿到错误页）。

## 落地纪律

1. 产物按 `../docs/asset-pipeline.md` 第 6 节的目录表落位。
2. 覆盖 `Art/UI/` 的九宫格素材后，必须跑 `python tools/ui_reset_meta.py`（删 `.meta` 强制重导入），
   否则 Unity 沿用旧像素边距 → 九宫格切错。
3. 地图类**只生成地形**，车道一律 `tools/paint_lane.py` / `paint_thumb.py` 按 `sldata.json` 的 `path[]` 绘制。
4. 生成后跑 `scripts/check.ps1 -Task verify`，再看 `Shots/` 截图确认实机显示。

## 不要做

- 用浏览器或别的生图通道替代 APIMart
- 把临时 prompt 直接写在命令行却不进清单（下次无法复现）
- 把生图中间产物（`tools/_terrain/`、`tools/_ui_backup/`）提交进仓库
- 手动改 `Art/UI/*.png.meta` 里的 `spriteBorder`（由 `STBuild.FixUiBorders` 统一写入）
