# S — 配件构筑型 FPS Roguelite

| 项 | 值 |
|----|-----|
| 显示名 | S（代号，正式名待定） |
| 枢纽目录 | `E:\Unity Development\Project\S\` |
| Unity 工程 | **尚未创建**（等确定盘符路径后建 `unity\` 联接） |
| 目标编辑器 | **Unity 6000.6.4f1**（`D:\Unity\6000.6.4f1\Editor\Unity.exe`） |
| 渲染 | **URP**（17.x，随 6000.6 配套版本） |
| 输入 | 新 Input System（FPS 键鼠 + 手柄） |
| 运行时根 | `unity/Assets/_Game/`（建工程后生效） |
| 当前阶段 | **文档阶段**：策划文档 + 开发文档 + 拆解，尚无代码 |

## 目录分工

| 路径 | 用途 |
|------|------|
| `docs/` | 概念、玩法、配件系统、美术、音频、技术、数据契约 |
| `breakdown/` | 开发拆解与可执行任务切片 |
| `control/` | 长期操作规范（流程、MCP、目录约定） |
| `memory/` | `CURRENT.md` 与阶段记忆 |
| `unity/` | **暂不存在**；建工程后为联接至真实工程，只在此树下改代码与资源 |

## 开发顺序

1. `docs/` 写清或更新规格
2. `breakdown/` 拆成可执行任务
3. 打开 `unity` 对应工程，按拆解在 `Assets/_Game/` 实现
4. 阶段结束更新 `memory/CURRENT.md`

## 建工程时要做的事

1. Unity Hub 用 6000.6.4f1 新建 **Universal 3D** 模板工程到目标盘符（建议与枢纽同盘 `E:`，便于 Junction）
2. `mklink /J "E:\Unity Development\Project\S\unity" "<工程根>"`
3. 包：Input System、URP、TextMeshPro（随模板）、`com.coplaydev.unity-mcp`
4. 工程本地 `.cursor/mcp.json` → Coplay HTTP `http://127.0.0.1:8765/mcp`
5. 回填本文件「Unity 工程」行、`../README.md` 与工作区 `README.md` 注册表
6. 建 `unity/scripts/check.ps1`（tests / verify / shots 三任务，口径见 `docs/technical-design.md` §9）

## 不要做

- 把 Unity 工程整体搬进枢纽目录（Library / Hub 注册 / 体积）
- 在 `unity/` 下再建过程文档目录（文档只写枢纽）
- 改其它 `Project/<别的游戏>/` 下的任何文件
- 用 2022.3 / 团结引擎打开本工程
- 手改 `.unity` / `.prefab` YAML 当作常规搭建手段
