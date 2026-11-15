# Unity Development — 多游戏工作区

跨终端游戏开发枢纽。完整架构与口径见 `README.md`；本文件是同内容的精简版，供不读 `.cursor/rules/` 的宿主使用。

## 三层结构

| 层 | 位置 | 入库 |
|----|------|------|
| L1 枢纽 | `<HUB>`（本仓库） | 是 |
| L2 游戏工程 | `<GAME:id>`（各自独立仓库） | 各自仓库 |
| L3 机器绑定 | `machine/profile.local.json` | **否** |

## 路径记号（强制，禁止写裸盘符）

| 记号 | 含义 |
|------|------|
| `<HUB>` | 枢纽根 |
| `<GAME:id>` | 某游戏真实工程根（id = `Project/` 下目录名） |
| `<UNITY:6000.6.4f1>` | 指定版本编辑器 |
| `<BLENDER>` | Blender 可执行文件 |

真实盘符只在 `machine/profile.local.json`。脚本用 `machine/profile.ps1` 的 `Get-GamePath` / `Get-UnityEditor` / `Get-BlenderPath` / `Expand-HubToken` 取。

## 开工前

```powershell
powershell -ExecutionPolicy Bypass -File "<HUB>\machine\doctor.ps1"
```

`pass(0)` 才动手；`degraded(2)` 必须补查；`fail(1)` 先修。
换机首次运行的完整步骤（克隆 / 依赖 / profile 填写 / 验收判据 / 已知坑）见 `docs/跨终端部署.md`。

## 已注册游戏

| 游戏 | 枢纽 | profile 键 |
|------|------|-----------|
| 云端王国 | `Project/Kingdom Of Cloud/` | `Kingdom Of Cloud` |
| 星轨防线 | `Project/Star Defanse/` | `Star Defanse` |
| S | `Project/S/` | `S` |

## 开发顺序

1. `Project/<Game>/docs/` 写规格
2. `Project/<Game>/breakdown/` 拆任务
3. 在该游戏 `unity/`（真实工程）实现
4. 更新 `Project/<Game>/memory/CURRENT.md`

## 硬约束

- 一次只服务一个 `Project/<Game>/`，禁止跨游戏改文件
- 不把 Unity 工程搬进枢纽（`Library` / 嵌套 Git）
- 不在 `unity/` 下建过程文档目录
- 技能单一源头 `.cursor/skills/`；`.codex/skills/blender-asset-pipeline` 是有意不同的派生版，不要同步
- MCP 配置由 `bootstrap.ps1` 生成，不手工编辑
- 手改 `.ps1` 后确认 UTF-8 **with BOM**（PS 5.1 无 BOM 会按 GBK 解码报 `Unexpected token`）

细则：`.cursor/rules/multi-project-workspace.mdc`、`agents/registry.md`、`machine/README.md`。
