# 控制：工程流程与实现路径

## 编辑器

- 只用 **Unity 6000.6.4f1**（`D:\Unity\6000.6.4f1\Editor\Unity.exe`）
- 勿用 2022 LTS / 团结引擎打开；勿给工程装 URP（着色器与材质全套按内置管线写死）

## 目录归属

| 类型 | 位置 |
|------|------|
| 项目文档 / 拆解 / 控制 / 记忆 | `E:\Unity Development\Project\Star Defanse\` |
| 代码、资源、场景、设置 | `unity/`（即 `E:\Star Defanse\`） |
| 生图清单与素材加工脚本 | `unity/tools/`（工程自有，不属于文档） |

不在 `unity/` 下新建文档目录。文档一律写枢纽。

## 一次改动的固定顺序

1. **改规格**：`docs/gameplay-spec.md`（数值）或 `docs/technical-design.md`（实现约束）
2. **改数据**：`unity/Assets/Resources/Data/sldata.json`（运行时唯一数据源）
3. **改逻辑**：`unity/Assets/Scripts/Core/RunState.cs`（保持零 Unity 依赖）
4. **改表现**：`unity/Assets/Scripts/View/`（只读状态 + 消费事件，不回写逻辑）
5. **跑验证**：`check.ps1 -Task tests` → `-Task verify` → `-Task build` → `-Task shots`
6. **写记忆**：`memory/CURRENT.md` 更新状态与未决项

## 验证命令（唯一入口）

```powershell
$proj = "E:\Unity Development\Project\Star Defanse\unity"
powershell -ExecutionPolicy Bypass -File "$proj\scripts\check.ps1" -Task tests
powershell -ExecutionPolicy Bypass -File "$proj\scripts\check.ps1" -Task verify
powershell -ExecutionPolicy Bypass -File "$proj\scripts\check.ps1" -Task build
& "$proj\Build\ST.exe" -autoshot -screen-width 1080 -screen-height 1920 -screen-fullscreen 0
```

`check.ps1` 每次会先删旧日志再跑，避免编译失败时读到上次的成功结果。
**看到「RESULT」行才算跑完**，退出码非 0 一律视为失败。

## 禁止

- 手写 `.unity` / `.prefab` YAML 冒充搭建（场景只有一个入口节点，其余全靠代码）
- 在 `Core/` 里引用 `GameObject` / 渲染 / 输入 API（会毁掉 headless 自检）
- 改数值不跑 `tests`（123 项断言里大量是数值边界）
- 为了「看起来稳」加静默兜底（`try/catch` 吞异常、失败给默认值）——本项目刻意尽早暴露配置错误
- 一次任务里跨到其它 `Project/<别的游戏>/`

## Controller 与场景

`Assets/Scenes/Main.unity` 只有一个 App 根节点。**不要在编辑器里手拖 UI 或组件**，
因为运行时重建会全部覆盖；任何结构调整都改 `STUi` / `STScreens` / `STBattleView` 的构建代码。
需要重建场景与工程设置时跑 `StarLane.EditorTools.STSceneBuilder`。
