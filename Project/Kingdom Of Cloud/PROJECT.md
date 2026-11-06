# 云端王国 — Kingdom Of Cloud

| 项 | 值 |
|----|-----|
| 显示名 | 云端王国 |
| 枢纽目录 | `E:\Unity Development\Project\Kingdom Of Cloud\` |
| Unity 工程 | `D:\Kingdom Of Cloud` |
| 本目录联接 | `unity\` → `D:\Kingdom Of Cloud` |
| 编辑器 | **Unity 6000.6.4f1**（`D:\Unity\6000.6.4f1\Editor\Unity.exe`） |
| 渲染 | URP 17.6.0 |
| 输入 | 旧 Input Manager（未迁新 Input System） |
| 运行时根 | `unity/Assets/_Game/` |

## 目录分工

| 路径 | 用途 |
|------|------|
| `docs/` | 概念、设计、规格；原始素材在 `docs/source/` |
| `breakdown/` | 开发内容拆解与任务切片 |
| `control/` | 长期操作规范（场景/MCP/目录） |
| `memory/` | `CURRENT.md` 与阶段记忆 |
| `unity/` | 联接至真实工程：只在此树下改代码与资源 |

## 开发顺序

1. 在 `docs/` 写清或更新规格  
2. 在 `breakdown/` 拆成可执行任务  
3. 打开 `unity` 对应工程，按拆解在 `Assets/_Game/` 实现  
4. 阶段结束更新 `memory/CURRENT.md`

## MCP（本游戏）

- 工程本地 Cursor 配置：`unity/.cursor/mcp.json` → Coplay HTTP `http://127.0.0.1:8765/mcp`
- 包：`unity/Packages/com.coplaydev.unity-mcp`
- 场景/预制体优先走 Unity MCP；失败再给逐步手动步骤
- 工作区根另有官方 `unity` CLI MCP，**打开本游戏工程开发时以本工程 Coplay 桥为准**

## 不要做

- 把 Unity 工程整体搬进枢纽目录（Library / Hub 路径会乱）  
- 在 `unity/` 下再建过程文档目录（文档只写枢纽）  
- 用 2022.3 / 团结引擎打开本工程做开发或 MCP  
- 改其它 `Project/<别的游戏>/` 下的文件  
- 把手改 `.unity` / `.prefab` YAML 当作常规搭建手段  
