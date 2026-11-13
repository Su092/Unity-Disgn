# 控制：工程流程与实现路径

## 编辑器

- 只用 **Unity 6000.6.4f1**（`D:\Unity\6000.6.4f1\Editor\Unity.exe`）
- 勿用 2022 LTS / 团结引擎打开
- 渲染管线是 **URP 17.6**（本工程已配 `PC_RPAsset`）
- 输入后端是 **仅新 Input System**（`activeInputHandler = 1`）
  → UI 必须用 `InputSystemUIInputModule`，混用 `StandaloneInputModule` 会让 UI 完全无响应

## 目录归属

| 类型 | 位置 |
|------|------|
| 项目文档 / 拆解 / 控制 / 记忆 | `E:\Unity Development\Project\S\` |
| 代码、资源、场景、设置 | `unity/`（即 `E:\S\`） |
| 验证脚本 | `unity/scripts/check.ps1`（工程内，属于运行基础设施） |
| 结算断言工程 | `unity/tools/loadout-tests/`（dotnet，链接 Core 源码） |

不在 `unity/` 下新建文档目录。文档一律写枢纽。

## 一次改动的固定顺序

1. **改规格**：`docs/loadout-spec.md`（配件）或 `docs/gameplay-spec.md`（环境）
2. **改数据**：`unity/Assets/Resources/Data/sdata.json`
3. **改逻辑**：`unity/Assets/_Game/Core/`（**保持零 Unity 依赖**）
4. **跑断言**：`dotnet run -c Release`（`tools/loadout-tests`）
5. **改表现**：`unity/Assets/_Game/View/`（只读 Core 结果，不回写规则）
6. **跑全量**：`check.ps1`（tests → setup → build → shots）
7. **写记忆**：`memory/CURRENT.md` 更新状态与未决项

## 验证命令（唯一入口）

```powershell
$proj = "E:\Unity Development\Project\S\unity"

powershell -ExecutionPolicy Bypass -File "$proj\scripts\check.ps1"              # 全量
powershell -ExecutionPolicy Bypass -File "$proj\scripts\check.ps1" -Task tests  # 只跑断言（1.6 秒）
powershell -ExecutionPolicy Bypass -File "$proj\scripts\check.ps1" -Task shots  # 只跑实机自检
```

**看到 `RESULT ALL PASS` 才算跑完**。任一任务失败，脚本退出码为 1。

只跑实机自检：

```powershell
& "E:\S\Build\Windows\S.exe" -scheck -screen-width 1600 -screen-height 900 -screen-fullscreen 0
Get-Content "E:\S\selfcheck.log"
```

## 禁止

- 在 `Core/` 里 `using UnityEngine`（唯一例外 `SDataLoader.cs`；否则 dotnet 断言跑不了）
- 在 `View/` 里改规则（判定必须留在 Core，否则 HUD 预览与实战会对不上）
- 直接 `new Material(Shader.Find(...))`（打包后会被剥离 → 黑屏）；一律走 `SMat`
- 用 `WaitForSeconds` 等待暂停状态（`timeScale=0` 会永久挂起）；用 `WaitUnscaled`
- 手写 `.unity` / `.prefab` YAML 冒充搭建
- 为了「看起来稳」加静默兜底（吞异常、失败给默认值）——本项目刻意尽早暴露配置错误
- 一次任务里跨到其它 `Project/<别的游戏>/`

## 踩过的坑（不要回退）

| 坑 | 症状 | 正确做法 |
|----|------|----------|
| URP 着色器被剥离 | 编辑器正常，播放器黑屏 + `ArgumentNullException: shader` | 跑 `S/写入 Always Included Shaders`；材质走 `SMat` 兜底 |
| `StandaloneInputModule` | UI 完全不响应 | `InputSystemUIInputModule` |
| `CaptureScreenshot` 帧末捕获 | 截图内容与预期状态不符 | 截图后 `yield return null` 两帧 |
| `Application.dataPath` | 播放器里指向 `S_Data` | 向上找含 `Assets` 的工程根 |
| PowerShell 5.1 编码 | 中文乱码 / `Unexpected token ')'` | `check.ps1` 必须存为 **UTF-8 with BOM** |
| **Force Single Instance** | 上一个 `S.exe` 还在运行时，新进程**静默退出、不写日志**，表现为 `RESULT shots FAIL（未生成 selfcheck.log）` | `check.ps1` 已在 shots 前自动 `Stop-Process -Name S`；手动重跑自检前也要先确认没有残留进程 |

## 场景与入口

`Assets/Scenes/Main.unity` 只有一个 `S` 节点（挂 `Bootstrap`）。

**不要在编辑器里手拖 UI 或组件**：运行时全量重建会覆盖。
需要调整结构就改 `Bootstrap` / `HudView` / `InventoryView` 的构建代码。

需要重建场景或应用工程设置时：

```powershell
$unity = "D:\Unity\6000.6.4f1\Editor\Unity.exe"
& $unity -batchmode -quit -projectPath "E:\S" `
  -executeMethod S.EditorTools.SceneBuilder.BatchSetup -logFile "E:\S\Logs\setup.log"
```

或走 `check.ps1 -Task setup`。
