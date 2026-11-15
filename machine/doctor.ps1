#requires -Version 5.1
<#
.SYNOPSIS
  换机 / 日常开工前的环境自检。三态判决：pass(0) / fail(1) / degraded(2)。

.DESCRIPTION
  检查项：
    1. profile.local.json 存在且可解析
    2. 枢纽真实目录存在；枢纽联接（若配置）指向正确目标
    3. 每个游戏：真实工程存在、ProjectVersion 与 profile 一致、git remote 一致、
       枢纽内 unity 联接存在且指向正确目标
    4. 工具：Unity 编辑器、Blender、uvx、.NET SDK
    5. 凭据：tools/.apimart.key
    6. MCP 配置：.cursor/mcp.json 与 .codex/config.toml 的关键项与 profile 一致
    7. 技能单源：除允许的目录外不得出现 SKILL.md
    8. 脚本编码：含中文的 .ps1 必须有 UTF-8 BOM（PS 5.1 无 BOM 会按 GBK 解码报错）

  三态口径（与 blender 门同源）：
    pass     = 全部检查通过
    degraded = 没有硬错误，但有"没查完 / 可降级"项（缺可选工具、游戏未克隆等）
    fail     = 有硬错误（profile 缺失、路径错误、联接指向错、MCP 不一致）

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File <HUB>\machine\doctor.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File <HUB>\machine\doctor.ps1 -Quiet
#>
[CmdletBinding()]
param(
    [switch]$Quiet,
    [string[]]$OnlyGame
)

$ErrorActionPreference = 'Stop'

$fail = New-Object System.Collections.Generic.List[string]
$degr = New-Object System.Collections.Generic.List[string]

function Pass { param($m) if (-not $Quiet) { Write-Host "  [pass] $m" -ForegroundColor Green } }
function Fail { param($m) $fail.Add($m); Write-Host "  [FAIL] $m" -ForegroundColor Red }
function Degr { param($m) $degr.Add($m); Write-Host "  [degr] $m" -ForegroundColor Yellow }
function Sect { param($m) if (-not $Quiet) { Write-Host "`n== $m ==" -ForegroundColor Cyan } }

# --- 1. profile ---------------------------------------------------------
Sect '1/8 profile'
$profilePs1 = Join-Path $PSScriptRoot 'profile.ps1'
if (-not (Test-Path -LiteralPath $profilePs1)) {
    Write-Host '  [FAIL] machine/profile.ps1 缺失' -ForegroundColor Red
    exit 1
}
. $profilePs1
try {
    $pf = Get-HubProfile
    Pass "profile 可解析（machine = $($pf.machine)）"
} catch {
    Fail "profile 不可用：$($_.Exception.Message)"
    Write-Host "`nRESULT: fail`n"
    exit 1
}

if ($pf.machine -match '^(B|example)$' -or $pf.hub.real -match '^X:') {
    Fail 'profile.local.json 仍是模板内容，请填写本机真实路径'
}

# --- 2. 枢纽 ------------------------------------------------------------
Sect '2/8 枢纽'
$hub = $pf.hub.real
if (Test-Path -LiteralPath $hub) { Pass "枢纽真实目录：$hub" } else { Fail "枢纽真实目录不存在：$hub" }

if ($pf.hub.link) {
    $linkItem = Get-Item -LiteralPath $pf.hub.link -Force -ErrorAction SilentlyContinue
    if (-not $linkItem) {
        Fail "枢纽联接不存在：$($pf.hub.link)（跑 bootstrap.ps1）"
    } elseif (-not ($linkItem.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint))) {
        Fail "枢纽联接位置不是联接：$($pf.hub.link)"
    } else {
        $target = @($linkItem.Target)[0]
        if ($target -and $target.TrimEnd('\') -ieq $hub.TrimEnd('\')) {
            Pass "枢纽联接：$($pf.hub.link) -> $target"
        } else {
            Fail "枢纽联接悬空或指错：$($pf.hub.link) -> $target（应为 $hub）。跑 bootstrap.ps1 -Force"
        }
    }
} else {
    Degr 'profile.hub.link 未配置：所有 <HUB> 记号只能解析为真实路径，文档里的 E:\... 写法会失效'
}

# --- 3. 游戏 ------------------------------------------------------------
Sect '3/8 游戏工程'
$ids = Get-GameIds -Profile $pf
if ($OnlyGame) { $ids = $ids | Where-Object { $OnlyGame -contains $_ } }
if (-not $ids) { Fail 'profile.games 为空' }

foreach ($id in $ids) {
    $g = Get-GameProfile -Id $id -Profile $pf
    Write-Host "  -- $id" -ForegroundColor DarkGray

    if (-not (Test-Path -LiteralPath $g.path)) {
        Degr "游戏 '$id' 工程未克隆：$($g.path)"
        continue
    }
    Pass "工程路径：$($g.path)"

    $verFile = Join-Path $g.path 'ProjectSettings\ProjectVersion.txt'
    if (Test-Path -LiteralPath $verFile) {
        $ver = ((Get-Content -LiteralPath $verFile | Select-Object -First 1) -replace '^m_EditorVersion:\s*', '').Trim()
        if ($ver -eq $g.editor) { Pass "编辑器版本 $ver 与 profile 一致" }
        else { Fail "游戏 '$id' 工程版本 $ver ≠ profile.editor $($g.editor)" }
    } else {
        Fail "游戏 '$id' 缺 ProjectSettings\ProjectVersion.txt，不是 Unity 工程根"
    }

    if ($g.remote) {
        Push-Location $g.path
        try {
            $actual = (git remote get-url origin 2>$null)
        } catch { $actual = $null }
        Pop-Location
        if ($actual -and $actual.Trim() -eq $g.remote.Trim()) { Pass "远端：$actual" }
        elseif ($actual) { Fail "游戏 '$id' 远端 $actual ≠ profile $($g.remote)" }
        else { Degr "游戏 '$id' 没有 git 远端（或不是 git 仓库）" }
    }

    $linkPath = Join-Path $hub "Project\$id\unity"
    $linkItem = Get-Item -LiteralPath $linkPath -Force -ErrorAction SilentlyContinue
    if (-not $linkItem) {
        Fail "游戏 '$id' 的 unity 联接缺失：$linkPath（跑 bootstrap.ps1）"
    } elseif (-not ($linkItem.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint))) {
        Fail "游戏 '$id' 的 unity 不是联接：$linkPath"
    } else {
        $target = @($linkItem.Target)[0]
        if ($target -and $target.TrimEnd('\') -ieq $g.path.TrimEnd('\')) {
            Pass "unity 联接：unity -> $target"
        } else {
            Fail "游戏 '$id' 的 unity 联接指错：-> $target（应为 $($g.path)）。跑 bootstrap.ps1 -Force"
        }
    }
}

# --- 4. 工具 ------------------------------------------------------------
Sect '4/8 工具'
if (Test-Path -LiteralPath $pf.tools.blender) { Pass "Blender：$($pf.tools.blender)" }
else { Degr "Blender 不存在：$($pf.tools.blender)（3D 门与建模全不可用）" }

if ($pf.tools.uvx -and (Test-Path -LiteralPath $pf.tools.uvx)) { Pass "uvx：$($pf.tools.uvx)" }
else { Degr "uvx 不存在：$($pf.tools.uvx)（blender MCP 起不来）" }

foreach ($v in ($pf.games.PSObject.Properties | ForEach-Object { $_.Value.editor } | Where-Object { $_ } | Select-Object -Unique)) {
    $exe = Join-Path $pf.tools.unityEditorRoot "$v\Editor\Unity.exe"
    if (Test-Path -LiteralPath $exe) { Pass "Unity $v：$exe" }
    else { Fail "Unity $v 未安装：$exe" }
}

if (Get-Command dotnet -ErrorAction SilentlyContinue) {
    $sdks = @(dotnet --list-sdks 2>$null)
    if ($sdks.Count -gt 0) { Pass ".NET SDK：$($sdks.Count) 个" }
    else { Degr '.NET SDK 缺失：dotnet 只解析到 runtime，dotnet 断言工程跑不了' }
} else {
    Degr 'dotnet 不在 PATH：dotnet 断言工程跑不了'
}

# --- 5. 凭据 ------------------------------------------------------------
Sect '5/8 凭据'
$keyFile = Join-Path $hub 'tools\.apimart.key'
if (Test-Path -LiteralPath $keyFile) { Pass 'tools/.apimart.key 存在' }
else { Degr 'tools/.apimart.key 缺失（生图不可用；不影响其它任务）' }

# --- 6. MCP 一致性 ------------------------------------------------------
Sect '6/8 MCP 配置'
$mcpPath = Join-Path $hub '.cursor\mcp.json'
if (-not (Test-Path -LiteralPath $mcpPath)) {
    Fail '.cursor/mcp.json 缺失（跑 bootstrap.ps1）'
} else {
    try {
        $m = Get-Content -LiteralPath $mcpPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $ok = $true
        if ($m.mcpServers.blender.env.BLENDER_PORT -ne "$($pf.mcp.blenderPort)") {
            Fail ".cursor/mcp.json 的 BLENDER_PORT = $($m.mcpServers.blender.env.BLENDER_PORT) ≠ profile $($pf.mcp.blenderPort)"; $ok = $false
        }
        if ($m.mcpServers.blender.command -ne $pf.tools.uvx) {
            Fail ".cursor/mcp.json 的 blender command ≠ profile.tools.uvx"; $ok = $false
        }
        if ($m.mcpServers.unityMCP.url -ne $pf.mcp.unityBridgeUrl) {
            Fail ".cursor/mcp.json 的 unityMCP.url ≠ profile $($pf.mcp.unityBridgeUrl)"; $ok = $false
        }
        if ($ok) { Pass '.cursor/mcp.json 与 profile 一致' }
    } catch {
        Fail ".cursor/mcp.json 解析失败：$($_.Exception.Message)"
    }
}

$tomlPath = Join-Path $hub '.codex\config.toml'
if (-not (Test-Path -LiteralPath $tomlPath)) {
    Fail '.codex/config.toml 缺失（跑 bootstrap.ps1）'
} else {
    $toml = Get-Content -LiteralPath $tomlPath -Raw -Encoding UTF8
    $ok = $true
    if ($toml -notmatch [regex]::Escape("BLENDER_PORT = `"$($pf.mcp.blenderPort)`"")) {
        Fail ".codex/config.toml 的 BLENDER_PORT 与 profile 不一致"; $ok = $false
    }
    if ($toml -notmatch [regex]::Escape($pf.mcp.unityBridgeUrl)) {
        Fail ".codex/config.toml 的 unityMCP url 与 profile 不一致"; $ok = $false
    }
    if ($ok) { Pass '.codex/config.toml 与 profile 一致' }
}

# --- 7. 技能单源 --------------------------------------------------------
Sect '7/8 技能单源'
$allowedSkillDirs = @(
    (Join-Path $hub '.cursor\skills'),
    (Join-Path $hub '.codex\skills')
)
$stray = @()
if (Test-Path -LiteralPath $hub) {
    $stray = Get-ChildItem -LiteralPath $hub -Filter 'SKILL.md' -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $p = $_.FullName
            -not ($allowedSkillDirs | Where-Object { $p.StartsWith($_, [StringComparison]::OrdinalIgnoreCase) })
        }
}
if ($stray.Count -eq 0) { Pass '没有枢纽与 .codex 之外的 SKILL.md 副本' }
else {
    Fail ("发现 $(@($stray).Count) 处越界 SKILL.md：`n    " + (($stray | ForEach-Object { $_.FullName }) -join "`n    "))
}

# --- 8. 脚本编码 --------------------------------------------------------
# PowerShell 5.1 读无 BOM 的 .ps1 时按 GBK 解码，中文会把引号配对搞乱，
# 报 `Unexpected token ')'` 且行号指向无关位置（仓库已记录此坑，跨机极易复发）。
Sect '8/8 脚本编码'
$ps1Files = @()
if (Test-Path -LiteralPath $hub) {
    $ps1Files = Get-ChildItem -LiteralPath $hub -Filter '*.ps1' -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch '\\Library\\|\\_gate' }
}
$noBom = @()
foreach ($f in $ps1Files) {
    $b = [IO.File]::ReadAllBytes($f.FullName)
    $hasBom = ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)
    if (-not $hasBom) {
        # 纯 ASCII 文件不需要 BOM；只有含非 ASCII 字符时才要求
        $text = [IO.File]::ReadAllText($f.FullName)
        if ($text -match '[^\x00-\x7F]') { $noBom += $f.FullName }
    }
}
if (@($ps1Files).Count -eq 0) { Degr '未找到任何 .ps1（在枢纽根之外运行时属正常）' }
elseif ($noBom.Count -eq 0) { Pass "$(@($ps1Files).Count) 个 .ps1 编码正确（含中文的均有 BOM）" }
else {
    Fail ("发现 $(@($noBom).Count) 个含中文但无 BOM 的 .ps1（PowerShell 5.1 会按 GBK 解码报错）：`n    " + (($noBom) -join "`n    "))
}

# --- 判决 --------------------------------------------------------------
Write-Host ''
if ($fail.Count -gt 0) {
    Write-Host ("RESULT: fail（{0} 硬错误 / {1} 降级）" -f $fail.Count, $degr.Count) -ForegroundColor Red
    foreach ($f in $fail) { Write-Host "  - $f" -ForegroundColor Red }
    exit 1
} elseif ($degr.Count -gt 0) {
    Write-Host ("RESULT: degraded（0 硬错误 / {0} 降级）" -f $degr.Count) -ForegroundColor Yellow
    foreach ($d in $degr) { Write-Host "  - $d" -ForegroundColor Yellow }
    exit 2
} else {
    Write-Host 'RESULT: pass' -ForegroundColor Green
    exit 0
}
