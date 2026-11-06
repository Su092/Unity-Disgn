# 构建、测试、Profiler（Unity 6000.6）

## 构建策略（官方 4 种）

来源：[Create a build from the command line · 6000.6](https://docs.unity.com/en-us/engine/6000.6/manual/building-and-publishing/build-command-line)

| 方式 | 关键参数 |
|------|----------|
| 按 build target | `-buildTarget` + `-build` |
| 按 build profile | `-activeBuildProfile` + `-build` |
| 自定义脚本 + target | `-executeMethod` + `-buildTarget` |
| 自定义脚本 + profile | `-executeMethod` + `-activeBuildProfile` |

无自定义脚本时用 `-build`；有脚本时用 `-executeMethod`（方法内再 `BuildPipeline.BuildPlayer`）。

### Unity CLI（推荐日常/CI 封装）

```powershell
unity build "E:\Unity Development\MyGame" --target StandaloneWindows64 --format json
unity build "E:\Unity Development\MyGame" --list-targets --format json
unity build "E:\Unity Development\MyGame" --list-profiles --format json
unity build "E:\Unity Development\MyGame" --profile "Assets/Settings/Build Profiles/Win.asset" --format json
unity build run --project-path "E:\Unity Development\MyGame"   # 启动最近一次记录的构建
```

Accelerator：命令后跟 `--accelerator host:port`，或 `UNITY_ACCELERATOR` / `unity config accelerator`。

### 经典 Editor CLI

```powershell
$UE = "C:\Program Files\Unity\Hub\Editor\6000.6.0f1\Editor\Unity.exe"

# A) -build + target
& $UE -batchmode -nographics -quit `
  -projectPath "E:\Unity Development\MyGame" `
  -buildTarget win64 `
  -build "E:\Builds\MyGame\MyGame.exe" `
  -logFile "E:\Builds\MyGame\build.log"

# B) -build + profile
& $UE -batchmode -nographics -quit `
  -projectPath "E:\Unity Development\MyGame" `
  -activeBuildProfile "Assets/Settings/Build Profiles/Windows.asset" `
  -build "E:\Builds\MyGame\MyGame.exe" `
  -logFile "E:\Builds\MyGame\build.log"

# C) executeMethod
& $UE -batchmode -nographics -quit -accept-apiupdate `
  -projectPath "E:\Unity Development\MyGame" `
  -buildTarget StandaloneWindows64 `
  -executeMethod BuildScripts.BuildWindows64 `
  -logFile "E:\Builds\MyGame\build.log"
```

### 自定义构建脚本骨架

放在 `Assets/Editor/BuildScripts.cs`：

```csharp
using UnityEditor;
using UnityEditor.Build.Reporting;

public static class BuildScripts
{
    public static void BuildWindows64()
    {
        var opts = new BuildPlayerOptions
        {
            scenes = new[] { "Assets/Scenes/SampleScene.unity" },
            locationPathName = "Builds/Win64/MyGame.exe",
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.None
        };
        var report = BuildPipeline.BuildPlayer(opts);
        EditorApplication.Exit(report.summary.result == BuildResult.Succeeded ? 0 : 1);
    }
}
```

### 硬性限制

- 一次命令行调用只构建**一个**目标；多平台 = 多次启动。
- batchmode 中切换平台的部分 API 无效（程序集会重载，当前脚本跑不完）。
- 始终在命令行显式传 `-buildTarget` 或 `-activeBuildProfile`。

---

## 测试（Test Framework CLI）

来源：[Command-line reference · Testing · 6000.6](https://docs.unity.com/en-us/engine/6000.6/manual/programming-environment/test-framework-introduction/reference-command-line)

### Unity CLI

```powershell
unity test "E:\Unity Development\MyGame" --editmode --format json
unity test "E:\Unity Development\MyGame" --playmode --format json
unity test "E:\Unity Development\MyGame" --filter "MyNamespace.MyTests" --format json
unity watch test --project-path "E:\Unity Development\MyGame"   # 变更后重跑受影响测试
```

### 经典参数

| 参数 | 说明 |
|------|------|
| `-runTests` | 运行测试 |
| `-testPlatform` | `EditMode` / `PlayMode` / `BuildTarget` 枚举值 |
| `-testResults <xml>` | NUnit XML 输出路径 |
| `-testFilter` / `-testfilter` | 名称或正则；`;` 分隔；`!` 否定 |
| `-testCategory` | 类别过滤；可与 filter 同时（取交集） |
| `-assemblyNames` | 程序集列表 `"A;B"` |
| `-orderedTestListFile <txt>` | 按文件顺序跑全名测试 |
| `-repeat <n>` / `-retry <n>` | 成功重复 / 失败重试 |
| `-randomOrderSeed <n>` | 随机顺序种子 |
| `-runSynchronously` | 仅 EditMode 单帧同步（过滤多帧测试） |
| `-playerHeartbeatTimeout <sec>` | Player 心跳超时（默认 600） |
| `-testSettingsFile <json>` | TestSettings.json |
| `-forgetProjectPath` | 不写入 Hub 历史 |

**不要**在跑测试时加 `-quit`。

```powershell
& $UE -batchmode -nographics `
  -projectPath "E:\Unity Development\MyGame" `
  -runTests -testPlatform EditMode `
  -testResults "E:\Builds\EditMode.xml" `
  -logFile "E:\Builds\test.log"
```

### TestSettings.json 常用键

`scriptingBackend`（`"Mono2x"` / `"IL2CPP"`）、`apiProfile`、`architecture`、`playerGraphicsAPI`、`androidBuildAppBundle`、`webGLClientBrowserType`/`Path`、`featureFlags`（如 `requiresSplashScreen`、`fileCleanUpCheck`）。

---

## Profiler 启动参数

| 参数 | 说明 |
|------|------|
| `-profiler-enable` | 启动即 Profile |
| `-profiler-log-file <file.raw>` | 流到文件 |
| `-profiler-capture-frame-count <n>` | 仅 Player |
| `-profiler-maxusedmemory <bytes>` | 内存上限 |
| `-deepprofiling` | Deep Profiling |
| `-connection-id <name>` | Player 显示名 |

Editor 与 Player 均可使用；与自动化结合时配合 `-batchmode` / 独立 Player 启动。

---

## `unity run` 模式对照

| 模式 | 命令 | 生命周期 |
|------|------|----------|
| 常驻无头 | `unity open --batchmode` 后 `unity command` | Editor 保持 |
| 热 GUI | `unity open` → `status ready` → `command` | Editor 保持 |
| 一次性 | `unity run --command <name> -- ...` | 启动→执行→退出 |
| 经典 | `Unity.exe -batchmode -quit -executeMethod ...` | 同上 |

```powershell
unity run "E:\Unity Development\MyGame" --command <RegisteredCliCommand> -- --arg value
unity run "E:\Unity Development\MyGame" -- -executeMethod MyEditor.DoWork   # 转发经典参数（以本机 CLI --help 为准）
```
