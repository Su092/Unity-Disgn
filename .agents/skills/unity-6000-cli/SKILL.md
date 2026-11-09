---
name: unity-6000-cli
description: >-
  Runs Unity 6000.6 workflows via the Unity CLI (`unity`) and classic Editor
  command-line arguments (batchmode, build, test, executeMethod). Use when the
  user asks for Unity CLI, batchmode, -executeMethod, Hub-less installs,
  command-line builds/tests, Pipeline live Editor control, or when choosing
  between Unity MCP and CLI automation for Unity 6 / 6000.6.
---

# Unity 6000.6 CLI

面向 **Unity Editor 6000.6** 的命令行全量调用技能。覆盖两套官方入口：

| 入口 | 可执行文件 | 用途 |
|------|------------|------|
| **Unity CLI**（新） | `unity` | 装编辑器、开工程、构建/测试、驱动已开 Editor、MCP 配置 |
| **Editor 经典 CLI** | `Unity.exe` + 参数 | CI batchmode、`-executeMethod`、`-build`、`-runTests` |

官方文档（6000.6）：

- [Command-line interface](https://docs.unity.com/en-us/engine/6000.6/manual/unity-editor/command-line-arguments)
- [Editor arguments reference](https://docs.unity.com/en-us/engine/6000.6/manual/unity-editor/command-line-arguments/editor)
- [Build from command line](https://docs.unity.com/en-us/engine/6000.6/manual/building-and-publishing/build-command-line)
- [Test Framework CLI](https://docs.unity.com/en-us/engine/6000.6/manual/programming-environment/test-framework-introduction/reference-command-line)
- [Unity CLI 用法](https://docs.unity.com/en-us/unity-cli/use-unity-cli) / [Unity CLI 参考](https://docs.unity.com/en-us/unity-cli/unity-cli-reference)

## 先决条件（Windows）

```powershell
unity --version                          # 本机若无: irm https://unity.com/install.ps1 | iex
unity self-update --check --format json  # 保持 CLI 最新
unity editors --installed --format json  # 确认已装 6000.6.x
```

默认 Editor 路径模板：

```text
C:\Program Files\Unity\Hub\Editor\6000.6.XfY\Editor\Unity.exe
```

路径含空格必须加引号；路径末尾不要单反斜杠。

## 决策树：用哪条路径

```
需要改场景/物体/Play 模式/看 Console？
  ├─ 已有 Editor 打开 → 优先 MCP（user-unityMCP）或 unity command（需 Pipeline）
  └─ 无 GUI / CI 无头 → Unity CLI: unity open --batchmode 或经典 -batchmode

需要装/升级 Editor、模块、授权、建工程？
  └─ Unity CLI: unity install / install-modules / license / projects create

需要一次性构建、跑测试、执行 Editor 静态方法？
  ├─ 优先: unity build / unity test / unity run --command
  └─ 兼容: Unity.exe -batchmode -quit -executeMethod / -build / -runTests
```

**规则：**

1. 活着的 Editor 在时，优先驱动它，不要手改 `.unity` / `.prefab` / `.asset` YAML。
2. 机器可读输出一律 `--format json`（或 `--json`）。
3. 搜命令用 `unity commands --grep <词>`，不要 `grep` help。
4. 多 Editor 时始终传 `--project-path <绝对路径>`。

## 快速食谱（6000.6）

### A. 安装 / 确认 6000.6

```powershell
unity releases --stream tech --limit 10 --format json   # 或 --stream lts
unity install 6000.6.0f1 -m windows-il2cpp android webgl --yes --accept-eula
unity editors --installed --format json
unity install-modules -e 6000.6.0f1 -m ios --yes
```

版本号以 `unity releases` / Hub 实际为准；别名 `lts` / `latest` 也可用于 `install`。

### B. 创建并打开工程

```powershell
unity projects create "MyGame" --path "E:\Unity Development" `
  --editor-version 6000.6.0f1 --template com.unity.template.urp-blank --no-cloud
unity pipeline install --project-path "E:\Unity Development\MyGame"
unity open "E:\Unity Development\MyGame" --until-ready
unity status --until-ready --project-path "E:\Unity Development\MyGame" --format json
```

URP 默认模板：`com.unity.template.urp-blank`（3D）、`com.unity.template.universal-2d`（2D）。

### C. 驱动已打开的 Editor（Pipeline）

```powershell
unity status --format json
unity command --format json                                          # 列出可用命令
unity command script eval 'new UnityEngine.GameObject("AgentObj");' --project-path "E:\...\MyGame"
unity recompile --project-path "E:\...\MyGame" --strict
```

Safe Mode（编译错误）时 Pipeline 不会加载：先 `unity status` 看 `safeMode.compileErrors`，修脚本后再继续。

### D. 无头构建（Unity CLI）

```powershell
unity build "E:\Unity Development\MyGame" --target StandaloneWindows64 --format json
unity build "E:\Unity Development\MyGame" --profile "Assets/Settings/Build Profiles/Win.asset"
unity build --list-targets --project-path "E:\Unity Development\MyGame"
```

### E. 无头构建（经典 Editor CLI / CI）

```powershell
$UE = "C:\Program Files\Unity\Hub\Editor\6000.6.0f1\Editor\Unity.exe"
& $UE -batchmode -nographics -quit `
  -projectPath "E:\Unity Development\MyGame" `
  -buildTarget win64 `
  -build "E:\Builds\MyGame\MyGame.exe" `
  -logFile "E:\Builds\MyGame\editor.log"
```

或自定义方法：

```powershell
& $UE -batchmode -nographics -quit `
  -projectPath "E:\Unity Development\MyGame" `
  -buildTarget StandaloneWindows64 `
  -executeMethod BuildScripts.BuildWindows64 `
  -logFile "E:\Builds\MyGame\editor.log"
```

**必填：** `-projectPath`、`-quit`。**推荐：** `-batchmode`、`-logFile`、`-buildTarget` 或 `-activeBuildProfile`。  
batchmode 下不要在同一次进程里切多个平台；每个 target 单独起一次 Unity。

### F. 跑测试

Unity CLI：

```powershell
unity test "E:\Unity Development\MyGame" --editmode --format json
unity test "E:\Unity Development\MyGame" --playmode --filter "MyNamespace"
```

经典 CLI：

```powershell
& $UE -batchmode -nographics -projectPath "E:\Unity Development\MyGame" `
  -runTests -testPlatform EditMode `
  -testResults "E:\Builds\results.xml" `
  -logFile "E:\Builds\test.log"
```

注意：跑测试时不要加 `-quit`（会在测试完成前退出）。

### G. 执行任意 Editor 静态方法

```powershell
& $UE -batchmode -nographics -quit `
  -projectPath "E:\Unity Development\MyGame" `
  -executeMethod Namespace.ClassName.StaticMethod `
  -logFile "E:\Builds\method.log"
```

方法必须是 `static`，脚本放在 `Editor` 文件夹。参数用 `Environment.GetCommandLineArgs` 读取。失败：`throw` 或 `EditorApplication.Exit(非0)`。

### H. 授权（CI）

```powershell
unity auth login                                          # 交互
# CI 服务账号:
$env:UNITY_SERVICE_ACCOUNT_ID = "..."
$env:UNITY_SERVICE_ACCOUNT_SECRET = "..."
unity license status --format json
unity license activate --serial $env:UNITY_LICENSE_SERIAL --yes   # 或 Personal / floating
```

经典：`Unity.exe -batchmode -quit -serial <KEY> -username <email> -password <pwd>`。

## MCP vs CLI（选用指南）

| 场景 | 优先 |
|------|------|
| Codex 里改场景、加组件、读 Console、迭代 Play | **MCP**（`user-unityMCP`） |
| CI 构建/测试、装 Editor、无 GUI 机器 | **CLI** |
| 需要结构化 JSON、退出码、脚本可复现 | **CLI** |
| 需要 Editor API 细粒度实时反馈 | **MCP** 或 `unity command` |
| 官方 `unity mcp` 可配置 Unity 自带 MCP | CLI 配置 + MCP 消费 |

详见 [references/mcp-vs-cli.md](references/mcp-vs-cli.md)。

## 全局约定

```powershell
unity <cmd> --format json --non-interactive --no-banner
$env:UNITY_PROJECT_PATH = "E:\Unity Development\MyGame"   # open/status/command/list/job/mcp 可读
$env:UNITY_NON_INTERACTIVE = "1"
$env:UNITY_FORMAT = "json"
```

搜命令：

```powershell
unity commands --grep build --format json
unity command --query gameobject --format json
```

## 参考（按需再读）

- [references/editor-args.md](references/editor-args.md) — 6000.6 Editor 参数全表
- [references/unity-cli.md](references/unity-cli.md) — `unity` 命令目录与环境变量
- [references/build-test.md](references/build-test.md) — 构建 / 测试 / Profiler 细节
- [references/mcp-vs-cli.md](references/mcp-vs-cli.md) — MCP 与 CLI 对比与组合策略

## 常见坑

- 同一工程不能同时被 GUI Editor 与 `-batchmode` 打开。
- `-quit` + `-runTests`：会提前退出；测完再关。
- `-nographics`：无 GPU 可用，但无法 bake GI；日志需显式 `-logFile`。
- batchmode 默认不跑 API Updater：加 `-accept-apiupdate`。
- `-activeBuildProfile` 路径相对工程根；与 `-executeMethod` 同用时先应用 profile defines 再编译再执行。
- Safe Mode / 沙箱可能让 `unity status` 看不到 Editor：先确认编译错误与权限，不要默默手改场景文件。
