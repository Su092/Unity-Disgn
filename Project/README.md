# Project 注册表

本目录下每个子文件夹是一个**独立游戏**。游戏之间不得共用 `docs` / `breakdown` / `memory` / `unity` 内容。

## 注册列表

| 目录名 | 显示名 | Unity 工程路径 | 状态 |
|--------|--------|----------------|------|
| `Kingdom Of Cloud` | 云端王国 | `D:\Kingdom Of Cloud` | 已关联 |
| `Star Defanse` | 星轨防线 STARLANE BULWARK | `E:\Star Defanse` | 已关联 |

## 新建游戏（检查清单）

1. 创建 `Project/<GameName>/`，内含：`PROJECT.md`、`docs/`、`breakdown/`、`control/`、`memory/`
2. 用目录联接绑定工程：  
   `mklink /J "E:\Unity Development\Project\<GameName>\unity" "<真实Unity工程根>"`
3. 填写 `PROJECT.md`（编辑器版本、MCP、运行时根目录）
4. 更新本文件注册表与工作区根 `README.md` 的已注册表
5. 如需工程内 Cursor 规则，写在该 Unity 工程的 `.cursor/rules/`，且只描述本工程

## 文档维护规则

- **已有文件**：整文件删除式重写（覆盖），禁止在旧文末追加「另见 / 补充引用」。
- **没有对应主题**：才新增文件或新章节。
- 进度以各游戏 `memory/CURRENT.md` 为快照入口。
