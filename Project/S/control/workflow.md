# 控制：工程流程与实现路径

## 路径

| 类型 | 逻辑路径 |
|------|----------|
| 工作区根 | `<HUB>\` |
| 本游戏枢纽 | `<HUB>\Project\S\` |
| 工程根 | `<GAME:S>`（即 `unity/`） |

文档一律写上述记号；真实盘符只在 `machine/profile.local.json` 里维护，排查磁盘占用 / 联接失效时才看它。

## 编辑器

- 只用 **Unity 6000.6.4f1**（`<UNITY:6000.6.4f1>`）
- 勿用 2022 LTS / 团结引擎打开
- 渲染管线是 **URP 17.6**（本工程已配 `PC_RPAsset`）
- 输入后端是 **仅新 Input System**（`activeInputHandler = 1`）
  → UI 必须用 `InputSystemUIInputModule`，混用 `StandaloneInputModule` 会让 UI 完全无响应

## 目录归属

| 类型 | 位置 |
|------|------|
| 项目文档 / 拆解 / 控制 / 记忆 | `<HUB>\Project\S\` |
| 代码、资源、场景、设置 | `unity/`（即 `<GAME:S>\`） |
| 验证脚本 | `unity/scripts/check.ps1`（工程内，属于运行基础设施） |
| 结算断言工程 | `unity/tools/loadout-tests/`（dotnet，链接 Core 源码） |

不在 `unity/` 下新建文档目录。文档一律写枢纽。

## 素材落点（硬约束）

**生成素材的中间产物只放本工程的 `_Inbox`，不要落到枢纽根。**

| 阶段 | 位置 |
|------|------|
| APIMart 原图 | `<GAME:S>\_Inbox\ui-ai-raw\` |
| 预处理产物（抠图 + 归一） | `<GAME:S>\_Inbox\ui-ai-src\` |
| 进引擎的成品 | `<GAME:S>\Assets\Resources\UI\` |
| 素材清单（跨游戏共用） | `<HUB>\tools\apimart-assets.json` |

**为什么这条要写死**：`apimart_image.download()` 会把**相对路径**拼到枢纽根（`REPO`）上。
清单里的 `out` 字段是相对路径（`_Inbox/ui-ai-raw/xxx.png`），直接传进去就会写到
`<HUB>\_Inbox`，而不是本工程的 `_Inbox` —— 实测 39 张图标全部跑偏，
工程里 0 张，枢纽根多出一个 `_Inbox` 目录。

所以调用 `download()` 前必须先把 `out` 解析成**工程根的绝对路径**：

```python
out = item["out"]
if not os.path.isabs(out):
    out = os.path.abspath(os.path.join(PROJ, out))   # PROJ = <GAME:S>
api.download(url, out)
```

「判断这张图是否已存在」也要用同一套解析，否则会一直认为缺图并重复生成。

**不要写死盘符**：工具脚本用「向上找含 `.cursor/skills` 的目录」得到枢纽根，
用 `os.path.dirname(HERE)` 得到工程根。写死 `E:\...` 的脚本换机直接 import 失败。


## 一次改动的固定顺序

1. **改规格**：`docs/loadout-spec.md`（配件）或 `docs/gameplay-spec.md`（环境）
2. **改数据**：`unity/Assets/_Game/Res/Cfg/*.tsv`
3. **改逻辑**：`unity/Assets/_Game/Core/`（**保持零 Unity 依赖**）
4. **跑断言**：`dotnet run -c Release`（`tools/loadout-tests`）
5. **改表现**：`unity/Assets/_Game/View/`（只读 Core 结果，不回写规则）
6. **跑全量**：`check.ps1`（tests → setup → assets → build → smoke → shots）
7. **写记忆**：`memory/CURRENT.md` 更新状态与未决项

## 验证命令（唯一入口）

```powershell
$proj = "<HUB>\Project\S\unity"

powershell -ExecutionPolicy Bypass -File "$proj\scripts\check.ps1"              # 全量
powershell -ExecutionPolicy Bypass -File "$proj\scripts\check.ps1" -Task tests  # 只跑断言（1.6 秒）
powershell -ExecutionPolicy Bypass -File "$proj\scripts\check.ps1" -Task shots  # 只跑实机自检
```

**看到所选任务的 RESULT 全部通过才算完成该范围；只有全量任务通过才能声称全量通过**。任一任务失败，脚本退出码为 1。

只跑实机自检：

```powershell
& "<GAME:S>\Build\Windows\S.exe" -scheck -screen-width 1600 -screen-height 900 -screen-fullscreen 0
Get-Content "<GAME:S>\selfcheck.log"
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
| **编辑器占用工程锁** | 编辑器开着时 batchmode 抢不到锁，**静默退出且退出码可能是 0**，日志里才看得出；`build` / `shots` / 资源重导全部不可信 | 直接关编辑器，确认目标编辑器进程退出、数据库锁可独占后再跑（Temp 锁文件可残留）；这一轮独占工作做完再重开。见 `.cursor/rules/unity-editor-lock.mdc` |

## 场景与入口

`Assets/Scenes/Main.unity` 包含 `S` 启动节点（Bootstrap）与 `FoundryArena` 地图预制体实例。

UI 结构在 Assets/_Game/Res/UIPrefabs，由 Editor 工厂或 MCP 修改；运行态通过 *Refs 绑定。世界入口和实例创建由 Bootstrap / GameRoot 管理。

需要重建场景或应用工程设置时：

```powershell
$unity = "<UNITY:6000.6.4f1>"
& $unity -batchmode -quit -projectPath "<GAME:S>" `
  -executeMethod S.EditorTools.SceneBuilder.BatchSetup -logFile "<GAME:S>\Logs\setup.log"
```

或走 `check.ps1 -Task setup`。

## Git

- 枢纽与工程是**两个独立仓库**：枢纽属工作区仓库（真实目录 `<HUB>`），`unity/` 指向的 `<GAME:S>` 属 `Project-S.git`
- 工作区 `.gitignore` 已忽略 `Project/*/unity/`，联接不会把工程内容带进工作区仓库
- 改代码要在 `<GAME:S>` 里单独提交推送；改文档在工作区仓库提交
