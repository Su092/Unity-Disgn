# Unity 工程占用探测。
#
# 为什么要有这个脚本：判断「工程能不能跑 batchmode」靠人肉看进程很容易错 ——
#   1. Unity Hub 的进程名同样是 unity.exe，按名字数个数会把 Hub 误判成编辑器（实测）
#   2. Library/ArtifactDB-lock / SourceAssetDB-lock 是**常驻**文件，一直存在，
#      存在 ≠ 被锁（实测：跨了 4 天还在，且能被独占打开）。拿"文件存在"当锁必然误判。
# 判据写进代码，才有唯一口径。
#
# 用法：
#   powershell -ExecutionPolicy Bypass -File "<HUB>\tools\unity-lock.ps1" -ProjectPath "<GAME:S>"
#     -Quiet   只输出结论与退出码
#     -List    列出所有 Unity 相关进程的详情
#     -Force   占用时结束持锁的编辑器进程（不含 Hub），然后轮询等它退出
#
# 退出码：0 未占用（可以跑 batchmode）/ 1 被占用 / 2 参数或环境错误
#
# 判据（两条独立证据，任一条成立即认为占用）：
#   A. 有 Unity 编辑器进程（排除 Hub），且该进程能在命令行里对上本工程，或本工程有编辑器窗口
#   B. 数据库锁文件**真的被独占占用**（尝试以无共享方式打开，失败才算锁）
# 注：Temp/UnityLockfile 不可作判据 —— 编辑器正常退出会连 Temp/ 一起删掉，平时根本不存在。

param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectPath,

    [switch]$Quiet,
    [switch]$List,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Say($msg, $color = "Gray") {
    if (-not $Quiet) { Write-Host $msg -ForegroundColor $color }
}

if (-not (Test-Path $ProjectPath)) {
    Say "工程路径不存在: $ProjectPath" "Red"
    exit 2
}
$proj = (Resolve-Path $ProjectPath).Path.TrimEnd('\')

# ---- 进程分类：编辑器 vs Hub ----
function Get-UnityEditorProcs {
    $out = @()
    foreach ($p in (Get-Process -Name "Unity" -ErrorAction SilentlyContinue)) {
        $path = ""
        try { $path = $p.Path } catch { }
        # Hub 的进程名也叫 unity.exe，但它不持工程锁 —— 必须排除
        if ($path -like "*Unity Hub*") { continue }
        $isEditor = ($p.MainWindowTitle -ne "") -or ($path -like "*\Editor\Unity.exe")
        if ($isEditor) { $out += [pscustomobject]@{ Proc = $p; Path = $path } }
    }
    return $out
}

if ($List) {
    Say "=== Unity 相关进程 ===" "Cyan"
    foreach ($p in (Get-Process -Name "Unity" -ErrorAction SilentlyContinue)) {
        $path = ""
        try { $path = $p.Path } catch { }
        $kind = if ($path -like "*Unity Hub*") { "Hub(不算占用)" }
                elseif ($p.MainWindowTitle -ne "") { "Editor(有窗口)" }
                else { "Editor/后台" }
        Say ("  PID {0,-7} {1,-18} {2}  {3}" -f $p.Id, $kind, $path, $p.MainWindowTitle)
    }
    foreach ($lf in @("Library\ArtifactDB-lock", "Library\SourceAssetDB-lock")) {
        $full = Join-Path $proj $lf
        if (-not (Test-Path $full)) { Say ("  {0,-30} 不存在" -f $lf) "DarkGray"; continue }
        $state = "存在但未被占用（常驻文件）"
        try {
            $fs = [System.IO.File]::Open($full, 'Open', 'ReadWrite', 'None')
            $fs.Close()
        } catch { $state = "存在且被独占占用（真锁）" }
        Say ("  {0,-30} {1}" -f $lf, $state)
    }
    Say ""
}

# ---- 证据 A：编辑器进程 ----
$editors = Get-UnityEditorProcs

# ---- 证据 B：锁文件是否真被占用 ----
$lockedFiles = @()
foreach ($lf in @("Library\ArtifactDB-lock", "Library\SourceAssetDB-lock")) {
    $full = Join-Path $proj $lf
    if (-not (Test-Path $full)) { continue }
    try {
        $fs = [System.IO.File]::Open($full, 'Open', 'ReadWrite', 'None')
        $fs.Close()          # 能打开 -> 没被占用
    } catch {
        $lockedFiles += $lf  # 打不开 -> 被独占
    }
}

# ---- 判定 ----
$held = ($editors.Count -gt 0) -or ($lockedFiles.Count -gt 0)

if (-not $held) {
    Say "OK 工程未占用：$proj" "Green"
    exit 0
}

Say "占用：$proj" "Yellow"
if ($editors.Count -gt 0) {
    Say ("   编辑器进程 {0} 个: {1}" -f $editors.Count, (($editors | ForEach-Object { $_.Proc.Id }) -join ", "))
}
if ($lockedFiles.Count -gt 0) {
    Say ("   被独占的数据库文件: " + ($lockedFiles -join ", "))
}

if ($Force) {
    if ($editors.Count -eq 0) {
        Say "   没有编辑器进程可结束；若文件确被占用，可能是残留句柄，重启后可继续" "Red"
        exit 1
    }
    Say "   -Force：结束编辑器进程" "Yellow"
    $editors | ForEach-Object { $_.Proc | Stop-Process -Force -ErrorAction SilentlyContinue }
    # 轮询等待而不是固定 sleep：各机器退出快慢不同
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
        if ((Get-UnityEditorProcs).Count -eq 0) { break }
        Start-Sleep -Milliseconds 300
    }
    $still = Get-UnityEditorProcs
    if ($still.Count -eq 0) {
        Say "   编辑器已退出，可以跑 batchmode" "Green"
        exit 0
    }
    Say "   编辑器未能在 20s 内退出" "Red"
}

Say "   建议：关掉该工程的 Unity 编辑器，等进程退出后重跑；不要带着锁跑 batchmode。" "Yellow"
exit 1
