# S — 配件构筑型 FPS Roguelite

第一人称射击 + 局内构筑 roguelite。枪是容器，配件才是武器。

| 项 | 值 |
|----|-----|
| 显示名 | S（代号，正式名待定） |
| 枢纽目录 | `<HUB>/Project/S/` |
| Unity 工程 | `<GAME:S>`（`unity\` 为其目录联接） |
| 工程远端 | `git@github.com:Su092/Project-S.git`（`main`） |
| 编辑器 | **Unity 6000.6.4f1**（`<UNITY:6000.6.4f1>`） |
| 渲染 | URP 17.6（`unity/Assets/Settings/PC_RPAsset`） |
| 输入 | 仅新 Input System（`activeInputHandler = 1`，Input System 1.20.0） |
| 运行时根 | `unity/Assets/_Game/` |
| 数据 | `unity/Assets/Resources/Data/sdata.json` |
| 场景 | `unity/Assets/Scenes/Main.unity`（只有 `S` 节点） |
| 当前阶段 | **对齐 MODCORE 原型**：6 枪 / 39 配件 / 7 作用域，断言 106/106、打包 0 error、自检 89/89 |

## 目录分工

| 路径 | 用途 |
|------|------|
| `docs/` | 概念、玩法、配件系统、美术、音频、技术、数据契约、校准日志（唯一权威） |
| `breakdown/` | 开发拆解与可执行任务切片 |
| `control/` | 长期操作规范（流程、编辑器、验证、踩过的坑） |
| `memory/` | `CURRENT.md` 与阶段记忆 |
| `unity/` | 联接至 `<GAME:S>`：代码、资源、场景、设置只在此树下改 |

## 工程内布局

| 路径 | 内容 |
|------|------|
| `unity/Assets/_Game/Core/` | 规则与结算，**零 Unity 依赖**（`SDataLoader.cs` 是唯一桥） |
| `unity/Assets/_Game/View/` | 运行时构建场景/UI/特效/音效，只读 Core 结果 |
| `unity/Assets/_Game/App/` | `Bootstrap`、`SelfCheck`、`SmokeTest`、`AutoPlay`、`MouseDiag` |
| `unity/Assets/_Game/Editor/` | 场景构建、打包、着色器与贴图设置、模型朝向契约 |
| `unity/Assets/_Game/Art/` | 交付资产：`Models`（FBX）`Textures` `Shaders`；原料不在此处 |
| `unity/Assets/Resources/` | 运行时副本：`Data/` `Models/` `Textures/` `UI/` |
| `unity/scripts/check.ps1` | 唯一验证入口：tests / setup / assets / ui / build / smoke / shots |
| `unity/tools/loadout-tests/` | dotnet 断言工程（直接链接 Core 源码） |

## 开发顺序

1. 在 `docs/` 写清或更新规格（配件看 `loadout-spec.md`，环境与时间轴看 `gameplay-spec.md`）
2. 在 `breakdown/` 拆成可执行任务
3. 打开 `unity` 对应工程，按拆解在 `Assets/_Game/` 实现
4. 阶段结束更新 `memory/CURRENT.md`

## 验证入口

```powershell
powershell -ExecutionPolicy Bypass -File "<HUB>\Project\S\unity\scripts\check.ps1" -Task all
```

判据：输出 `RESULT ALL PASS` 且退出码 0。跑 Unity 相关任务前**必须先关掉编辑器**（工程锁）。

**换机前置**：`-Task tests` 需 .NET SDK，且 `tools/loadout-tests/*.csproj` 被工程 `.gitignore` 忽略、
不随仓库分发，需本地重建。

## MCP（本游戏）

- 桥地址：`http://127.0.0.1:8765/mcp`（工作区 `.cursor/mcp.json` 的 `unityMCP`）
- 工程内**尚未**装 `com.coplaydev.unity-mcp` 包 → 打开本工程开发前要先装包并起桥
- 场景/预制体优先走 MCP；不可用时给逐步手动步骤

## 不要做

- 把 Unity 工程整体搬进枢纽目录（`Library` / Hub 注册 / 体积）
- 在 `unity/` 下再建过程文档目录（文档只写枢纽）
- 用 2022.3 / 团结引擎打开本工程
- 在 `Core/` 里 `using UnityEngine`
- 在 `View/` 里改规则判定
- 手改 `.unity` / `.prefab` YAML 当作常规搭建手段
- 改其它 `Project/<别的游戏>/` 下的任何文件
