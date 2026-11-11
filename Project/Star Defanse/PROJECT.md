# 星轨防线 — STARLANE BULWARK

竖屏单屏星域塔防：开局编队，局内花金币**随机召唤**编队里的塔，**同级拖拽合成**升阶，
**抽 3 选 1 编队词条**滚雪球，同时操纵一名可自由移动的英雄补火力。
每关固定 10 波（第 5 波精英、第 10 波 BOSS）。

| 项 | 值 |
|----|-----|
| 显示名 | 星轨防线 / STARLANE BULWARK |
| 枢纽目录 | `E:\Unity Development\Project\Star Defanse\` |
| Unity 工程 | `E:\Star Defanse` |
| 本目录联接 | `unity\` → `E:\Star Defanse` |
| 工程远端 | `git@github.com:Su092/Star-Defanse.git`（`main`） |
| 编辑器 | **Unity 6000.6.4f1**（`D:\Unity\6000.6.4f1\Editor\Unity.exe`） |
| 渲染 | 内置管线 + 自定义赛璐璐着色器（`StarLane/ModelLit`、`StarLane/Unlit`），**未装 URP** |
| 输入 | 旧 Input Manager（`activeInputHandler: 0`），指针事件自绘 |
| 分辨率 | 竖屏，逻辑 1080×1920，窗口 540×960（`Check.ps1 -Task shots` 用 1080×1920） |
| 产品名 | `星轨防线 STARLANE BULWARK`，公司 `StarLane Studio`，版本 `1.0.0` |
| 运行时根 | `unity/Assets/Scripts/`（无 `_Game/` 分层） |

## 目录分工

| 路径 | 用途 |
|------|------|
| `docs/` | 概念、玩法数值、技术设计、美术规范、素材管线、3D 模型管线（唯一权威） |
| `breakdown/` | 开发拆解与任务切片 |
| `control/` | 长期操作规范（工程流程、编辑器/MCP、生图与 3D 落地） |
| `memory/` | `CURRENT.md` 与阶段记忆 |
| `unity/` | 联接至真实工程：只在此树下改代码与资源 |

## 工程内布局

| 路径 | 内容 |
|------|------|
| `unity/Assets/Scenes/Main.unity` | 唯一场景，只有一个入口物体，其余全由代码运行时构建 |
| `unity/Assets/Scripts/Core/` | `STData.cs`（反序列化 + 纯查询）、`RunState.cs`（无 Unity 依赖的对局模拟） |
| `unity/Assets/Scripts/View/` | 3D 战场、UI 构建、特效、单位 FSM |
| `unity/Assets/Scripts/App/` | 流程与输入、自动截图自检 |
| `unity/Assets/Scripts/Editor/` | 导入规则、资源校验、打包、逻辑自检、场景构建 |
| `unity/Assets/Resources/` | `Art/`（UI / Backgrounds / Sprites / Models）、`Data/sldata.json`、`Fonts/`、`Shaders/` |
| `unity/scripts/check.ps1` | tests / verify / build / shots 统一入口 |
| `unity/tools/` | APIMart 清单与素材加工脚本（`*.py`、`*.json`） |
| `unity/tools/_archive/` | 已归档的旧试验与旧日志（`TowerDesigns/`、`UiStyleTests/`、`UiC6/`、`canvas/`、`logs/`），已 gitignore |

## 3D 模型入口（工作区级）

| 路径 | 用途 |
|------|------|
| `E:\Unity Development\tools\blender-gate.ps1` | 门自检 → `.blend` 数值门 → FBX 交付通路 → manifest |
| `E:\Unity Development\tools\blender_export_unity.py` | 按 Unity 导入契约导出 `Modle_*` / `Anim_*` FBX |
| `E:\Unity Development\tools\blender_contract.py` | 导入契约门（单位/变换/根/命名/三角/材质/骨架/落地） |

口径见 `docs/model-pipeline.md`。**`degraded`（退出码 2）必须补查，不许当通过。**

## 开发顺序

1. 在 `docs/` 写清或更新规格（改数值先改 `docs/gameplay-spec.md`）
2. 在 `breakdown/` 拆成可执行任务
3. 按拆解在 `unity/Assets/` 实现，改完跑 `check.ps1`
4. 阶段结束更新 `memory/CURRENT.md`

## 验证入口

```powershell
powershell -ExecutionPolicy Bypass -File "E:\Unity Development\Project\Star Defanse\unity\scripts\check.ps1" -Task all
```

逻辑自检（123 项断言，headless）→ 资源校验 → 打包 → 实机自检 + 截图。四项全绿才算完成。

## MCP（本游戏）

- 工程包：`com.coplaydev.unity-mcp` v10.0.0（`Packages/manifest.json`）
- 桥地址：`http://127.0.0.1:8765/mcp`（工作区 `.cursor/mcp.json` 的 `unityMCP`）
- 用前必须先打开本工程并让编辑器起桥，否则 Cursor 里工具为空
- 场景/Prefab 修改优先走 MCP；MCP 不可用时给逐步手动步骤

## 不要做

- 把 Unity 工程整体搬进枢纽目录（`Library` 与嵌套 Git 会出问题）
- 在 `unity/` 下新建过程文档目录（文档只写枢纽；工程内 `Docs/` 已迁空）
- 改 `Resources/Data/sldata.json` 却不更新 `docs/gameplay-spec.md`
- 用 2022.3 / 团结引擎打开本工程，或给工程装 URP
- 改其它 `Project/<别的游戏>/` 下的文件
- 手写 `.unity` / `.prefab` YAML 当搭建手段
