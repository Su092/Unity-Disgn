# Unity Editor 6000.6 — 经典命令行参数全量

来源：[Unity Editor command line arguments reference · 6000.6](https://docs.unity.com/en-us/engine/6000.6/manual/unity-editor/command-line-arguments/editor)

启动形态（Windows）：

```powershell
& "C:\Program Files\Unity\Hub\Editor\6000.6.XfY\Editor\Unity.exe" <args...>
```

示例：`Unity.exe -batchmode -quit -executeMethod MyClass.MyMethod`

---

## Asset import

| 参数 | 说明 |
|------|------|
| `-refreshImportMode <mode>` | `InProcess` / `OutOfProcessPerQueue` / `OutOfProcess`。未设则读 `UNITY_REFRESH_IMPORT_MODE` |
| `-desiredWorkerCount <n>` | 期望导入 worker 数 |
| `-standbyWorkerCount <n>` | 空闲时保留的最少 worker（默认 2） |
| `-idleWorkerShutdownDelay <ms>` | 空闲多久关闭 worker（毫秒，默认 60000） |

## Configuration

| 参数 | 说明 |
|------|------|
| `-createProject <path>` | 在路径创建空工程 |
| `-cloneFromTemplate <path>` | 与 `-createProject` 联用，从模板归档/目录克隆 |
| `-consistencyCheck` | 启动时做 importer 一致性检查（默认 local） |
| `-consistencyCheckSourceMode <local\|cacheserver>` | 对比源 |
| `-consistencyCheckShaderCacheEnabled` | 检查 shader cache |
| `-consistencyCheckTextureCacheEnabled` | 检查 texture compression cache |
| `-disable-assembly-updater [dll...]` | 忽略指定（或全部）程序集的 API Updater |
| `-disable-gpu-skinning` | 禁用 GPU skinning |
| `-disable-playback-engines <dirs...>` | 禁用构建模块（目录名，大小写敏感） |
| `-executeMethod <Class.Method>` 或 `<Ns.Class.Method>` | 打开工程后执行静态方法；脚本须在 Editor 文件夹 |
| `-job-worker-count <n>` | JobQueue 最大线程数 |
| `-gc-helper-count <n>` | 资源 GC helper 线程数（默认=核数） |
| `-logFile <path\|->` | Editor 日志路径；`-` 输出到控制台 |
| `-noUpm` | 禁用 Package Manager |
| `-openfile <path>` | 从场景/包路径打开工程（或用 `-projectPath`） |
| `-password <pwd>` | 登录表单密码 |
| `-projectPath <path>` | 打开工程（绝对/相对；含空格加引号） |
| `-quit` | 其他命令完成后退出（与异步/`-runTests` 有限制） |
| `-quitTimeout <sec>` | `-quit` 等待异步任务超时（默认 300） |
| `-releaseCodeOptimization` | 本会话强制 release 优化 |
| `-setDefaultPlatformTextureFormat <fmt>` | Android：导入前默认纹理压缩（dxt/atc/etc/etc2/astc） |
| `-overrideMaxTextureSize <px>` | 覆盖导入最大纹理边长 |
| `-overrideTextureCompression` | 覆盖导入压缩设置（加速本地切换平台） |
| `-silent-crashes` | Standalone 崩溃时不弹对话框 |
| `-upmLogFile <path>` | UPM 日志路径（优先于 `-useGlobalLog`） |
| `-useGlobalLog` | 全局 Editor.log（跨工程） |
| `-username <email>` | Unity ID 邮箱 |
| `-vcsMode <mode>` | `"Visible Meta Files"` / `"Hidden Meta Files"` / `Perforce` / `PlasticSCM` |
| `-vcsModeSession <mode>` | 仅本会话的 VCS 模式 |
| `-version` | 打印 Editor 版本后退出（不启动 UI） |
| `-timestamps` | 日志加时间戳与线程 ID |

## Batch mode

| 参数 | 说明 |
|------|------|
| `-accept-apiupdate` | batchmode 下运行 API Updater（省略则可能编译失败） |
| `-batchmode` | 无交互、抑制对话框；异常时退出码 1；同一工程不能与 GUI 并存 |
| `-ignorecompilererrors` | 有编译错误仍继续启动 |
| `-nographics` | 不初始化图形设备（无 GPU CI）；关闭默认日志输出，需 `-logFile`；无法 bake GI |

## Package Manager

| 参数 | 说明 |
|------|------|
| `-exportPackage <folders...> <out.unitypackage>` | 导出 `.unitypackage`（整文件夹）；可加 `-organization-id` + 凭据签名；签名需 `-batchmode` |
| `-importPackage <path>` | 无对话框导入；不可与 `-noUpm` 同用 |
| `-upmPack <pkgFolder> <outPath>` | batchmode 导出并签名 UPM tarball（需 `-username`/`-password`/`-cloudOrganization`） |

## Build

| 参数 | 说明 |
|------|------|
| `-activeBuildProfile <Assets/...asset>` | 激活 Build Profile（相对工程根）；会追加 scripting defines |
| `-build <path>` | 按 active profile 构建到路径（部分平台需平台扩展名） |
| `-buildLinux64Player <path>` | Linux 64 Player |
| `-buildLinuxHeadlessSimulation <path>` | Linux headless simulation |
| `-buildOSXUniversalPlayer <path>` | macOS universal `.app` |
| `-buildTarget <name>` | 启动时活动目标：`android` `cloudrendering` `ios` `linux64` `osxuniversal` `tvos` `visionos` `windowsstoreapps` `webgl` `win` `win64` |
| `-buildWindowsPlayer <path>` | Win32 Player |
| `-buildWindows64Player <path>` | Win64 Player |
| `-standaloneBuildSubtarget <Player\|Server>` | Standalone 子目标 |

构建命令行说明：[Create a build from the command line · 6000.6](https://docs.unity.com/en-us/engine/6000.6/manual/building-and-publishing/build-command-line)

**必填：** `-projectPath`、`-quit`。**推荐：** `-batchmode`、`-logFile`、`-buildTarget` 或 `-activeBuildProfile`。

batchmode 限制：`BuildProfile.SetActiveBuildProfile`、`SwitchActiveBuildTargetAsync` 等不会在同一次脚本执行中生效——每个平台单独起一次进程。

## Unity Accelerator / Cache Server

| 参数 | 说明 |
|------|------|
| `-EnableCacheServer` | 启用（须配合 endpoint） |
| `-cacheServerEndpoint <host:port>` | 默认端口 10080 |
| `-cacheServerNamespacePrefix <name>` | 命名空间前缀 |
| `-cacheServerEnableImportResultCaching` | 启用导入结果缓存（6.5+ 新工程默认关） |
| `-cacheServerEnableDownload true\|false` | 下载开关 |
| `-cacheServerEnableUpload true\|false` | 上传开关 |
| `-cacheServerWaitForConnection <ms>` | 连接等待 |
| `-cacheServerDownloadBatchSize <n>` | 下载批次（默认 128） |
| `-cacheServerUploadExistingImports` | 上传尚未上传的已有导入 |
| `-cacheServerUploadAllRevisions` | 上传所有历史 revision |
| `-cacheServerUploadExistingShaderCache` | 上传已有 shader cache |
| `-disableShaderCacheRemote` / `...Download` / `...Upload` | 禁 shader 远程缓存 |
| `-disableTextureCacheRemote` / `...Download` / `...Upload` | 禁纹理压缩远程缓存 |

## Debugging

| 参数 | 说明 |
|------|------|
| `-disableManagedDebugger` | 关闭托管调试监听 |
| `-diag-debug-shader-compiler` | 单实例 Shader Compiler，超时 1 小时 |
| `-debugCodeOptimization` | 本会话 debug 优化 |
| `-enableCodeCoverage` | 启用 Coverage API |
| `-force-d3d12-debug` / `-force-d3d12-debug-gbv` | DX12 校验 / GPU 校验 |
| `-force-d3d12-nvidia-aftermath` | NVIDIA Aftermath dump |
| `-force-vulkan-layers` | Vulkan validation |
| `-stackTraceLogType <None\|Script Only\|Full>` | 堆栈详细度 |
| `-log-memory-performance-stats` | 退出时写内存/性能报告到日志 |
| `-wait-for-managed-debugger` | 等待托管调试器 |
| `-wait-for-native-debugger` | 等待原生调试器 |

## Graphics API

| 参数 | 说明 |
|------|------|
| `-force-d3d11` / `-force-d3d12` | Windows Direct3D |
| `-force-vulkan` | Vulkan |
| `-force-glcore` / `-force-glcoreXY` | OpenGL core（XY=32..45） |
| `-force-gles` / `-force-glesXY` | OpenGL ES（Windows） |
| `-force-opengl` | Legacy OpenGL |
| `-force-clamped` | 与 `-force-glcoreXY` 联用，限制扩展探测 |
| `-force-device-index <n>` | 指定 GPU 索引 |

## License

| 参数 | 说明 |
|------|------|
| `-createManualActivationFile` | 手动激活步骤 1 |
| `-manualLicenseFile <file>` | 手动激活步骤 3（`.ulf` / `.xml`） |
| `-returnlicense` | 归还当前 serial/named user license（非 floating） |
| `-serial [<key>]` | 激活；**必须**配 `-batchmode`；建议 `-quit` |

## Metal（macOS）

| 参数 | 说明 |
|------|------|
| `-force-metal` | 默认 Metal |
| `-force-low-power-device` | 低功耗 GPU |
| `-enable-metal-capture` | 允许 Metal capture |

## Profiler

| 参数 | 说明 |
|------|------|
| `-deepprofiling` | CPU Deep Profiling |
| `-profiler-enable` | 启动即采集 |
| `-profiler-log-file <path.raw>` | 启动流到 .raw |
| `-profiler-capture-frame-count <n>` | Player 启动捕获帧数 |
| `-profiler-maxusedmemory <bytes>` | Profiler 内存上限（Player 默认 16MB，Editor 256MB） |

详见：[Profiler command line arguments · 6000.6](https://docs.unity.com/en-us/engine/6000.6/manual/analysis/profiler/command-line-arguments)

## Special（慎用）

| 参数 | 说明 |
|------|------|
| `-enableIncompatibleAssetDowngrade` | 降级不兼容资产（高风险） |
| `-giCustomCacheLocation <abs>` | 本会话 GI cache 路径 |
| `-rebuildLibrary` | 删除 Library 全量重导 |

## Hub 相关（旧 Editor；现行默认已集成）

`-useHub` / `-hubIPC` / `-hubSessionId`

---

## Windows 最小可靠模板

```powershell
$UE = "C:\Program Files\Unity\Hub\Editor\6000.6.0f1\Editor\Unity.exe"
$Project = "E:\Unity Development\MyGame"
$Log = "E:\Unity Development\Logs\editor.log"

# 执行方法
& $UE -batchmode -nographics -quit -accept-apiupdate `
  -projectPath $Project -executeMethod MyEditor.DoWork -logFile $Log
$LASTEXITCODE

# Profile 构建
& $UE -batchmode -nographics -quit `
  -projectPath $Project `
  -activeBuildProfile "Assets/Settings/Build Profiles/Windows.asset" `
  -build "E:\Builds\MyGame\MyGame.exe" `
  -logFile $Log
```
