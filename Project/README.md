# Project 注册表

本目录下每个子文件夹是一个**独立游戏**。游戏之间不得共用 `docs` / `breakdown` / `memory` / `unity` 内容。

## 注册列表

| 目录名 = profile 键 | 显示名 | 状态 |
|---------------------|--------|------|
| `Kingdom Of Cloud` | 云端王国 | 已关联 |
| `Star Defanse` | 星轨防线 STARLANE BULWARK | 已关联 |
| `S` | S（配件构筑型 FPS Roguelite） | 已关联，垂直切片可玩 |

真实工程路径、远端与编辑器版本由 `machine/profile.local.json` 的 `games.<目录名>` 定义，不写在本文件。

## 新建游戏（检查清单）

1. 在 `machine/profile.local.json` 的 `games` 下加一项：`path` / `remote` / `editor`
2. 创建 `Project/<GameName>/`，内含：`PROJECT.md`、`docs/`、`breakdown/`、`control/`、`memory/`、`unity.path.md`
3. 跑 `machine/bootstrap.ps1 -OnlyGame <GameName>` 建联接（不要手敲 `mklink`）
4. 填写 `PROJECT.md`（显示名、渲染/输入约定、运行时根目录、验证入口）
5. 更新本文件注册表与 `<HUB>/README.md` 的已注册表
6. 跑 `machine/doctor.ps1` 确认新游戏全绿
7. 如需工程内 Cursor 规则，写在该 Unity 工程的 `.cursor/rules/`，且只描述本工程

## 文档维护规则

- **已有文件**：整文件删除式重写（覆盖），禁止在旧文末追加「另见 / 补充引用」。
- **没有对应主题**：才新增文件或新章节。
- **路径口径**：写 `<HUB>/...` 与 `<GAME:id>/...` 记号，禁止写裸盘符。
- 进度以各游戏 `memory/CURRENT.md` 为快照入口。
