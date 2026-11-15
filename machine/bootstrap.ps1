#requires -Version 5.1
<#
.SYNOPSIS
  一台机器上把枢纽与游戏工程接通：建目录联接、生成 MCP 配置、检查凭据。

.DESCRIPTION
  幂等。可反复运行：
    - 枢纽联接存在且目标正确 → 跳过；目标是旧路径 → 报告并需 -Force 才重建
    - 游戏联接缺失 → 建；已存在 → 跳过
    - .cursor/mcp.json 与 .codex/config.toml 按 profile 重新生成（内容一致则不动）
    - 凭据 tools/.apimart.key 缺失时只提示，不自动创建（不入库）

  不做的事：不克隆仓库、不安装 Unity / Blender、不写 profile.local.json。

.PARAMETER Force
  允许删除并重建指向错误目标的联接。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File <HUB>\machine\bootstrap.ps1
#>
[CmdletBinding()]
param(
    [switch]$Force,
    [string[]]$OnlyGame
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'profile.ps1')

try {
    $profile_ = Get-HubProfile
} catch {
    Write-Host ''
    Write-Host '  [FAIL] 缺少 machine/profile.local.json' -ForegroundColor Red
    Write-Host '  换机第一次运行前必须：'
    Write-Host '    Copy-Item machine\profile.example.json machine\profile.local.json'
    Write-Host '    然后按本机实际路径填写 hub / tools / games 三节。'
    Write-Host "  详情：$($_.Exception.Message)"
    Write-Host ''
    exit 1
}
$hub = $profile_.hub.real
$changed = New-Object System.Collections.Generic.List[string]
$warn = New-Object System.Collections.Generic.List[string]

function Get-LinkTarget {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $item = Get-Item -LiteralPath $Path -Force
    if (-not ($item.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint))) { return $null }
    return @($item.Target)[0]
}

function New-JunctionSafe {
    param([string]$LinkPath, [string]$TargetPath, [string]$Label)

    if (-not (Test-Path -LiteralPath $TargetPath)) {
        $warn.Add("$Label 目标不存在，跳过建联接：$TargetPath")
        return
    }

    $existing = Get-LinkTarget -Path $LinkPath
    if ($existing) {
        if ($existing.TrimEnd('\') -ieq $TargetPath.TrimEnd('\')) {
            Write-Host "  [ok]   $Label 联接已正确：$LinkPath -> $existing"
            return
        }
        if (-not $Force) {
            $warn.Add("$Label 联接指向错误目标：$LinkPath -> $existing（应为 $TargetPath）。加 -Force 重建。")
            return
        }
        cmd /c rmdir "$LinkPath" | Out-Null
        Write-Host "  [fix]  $Label 删除错误联接（原目标 $existing）"
    }
    elseif (Test-Path -LiteralPath $LinkPath) {
        $warn.Add("$Label 路径已存在但不是联接，跳过：$LinkPath")
        return
    }

    $parent = Split-Path -Parent $LinkPath
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    cmd /c mklink /J "$LinkPath" "$TargetPath" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "$Label 建联接失败：$LinkPath -> $TargetPath" }
    $changed.Add("$Label 联接：$LinkPath -> $TargetPath")
    Write-Host "  [new]  $Label 联接：$LinkPath -> $TargetPath"
}

Write-Host "`n== 1/4 枢纽联接 ==" -ForegroundColor Cyan
$hubLink = $profile_.hub.link
if ($hubLink) {
    New-JunctionSafe -LinkPath $hubLink -TargetPath $hub -Label '枢纽'
} else {
    Write-Host "  [--]   profile.hub.link 为空，跳过（只用真实路径 $hub）"
}

Write-Host "`n== 2/4 游戏联接 ==" -ForegroundColor Cyan
$ids = Get-GameIds -Profile $profile_
if ($OnlyGame) { $ids = $ids | Where-Object { $OnlyGame -contains $_ } }
foreach ($id in $ids) {
    $gamePath = Get-GamePath -Id $id -Profile $profile_
    if (-not (Test-Path -LiteralPath $gamePath)) {
        $warn.Add("游戏 '$id' 的工程不存在：$gamePath（先克隆 $((Get-GameProfile -Id $id -Profile $profile_).remote)）")
        continue
    }
    New-JunctionSafe -LinkPath (Join-Path $hub "Project\$id\unity") -TargetPath $gamePath -Label "游戏 $id"
}

Write-Host "`n== 3/4 MCP 配置 ==" -ForegroundColor Cyan
function Write-IfChanged {
    param([string]$Path, [string]$Content, [string]$Label)
    if ((Test-Path -LiteralPath $Path) -and ((Get-Content -LiteralPath $Path -Raw) -eq $Content)) {
        Write-Host "  [ok]   $Label 已是最新"
        return
    }
    $dir = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [IO.File]::WriteAllText($Path, $Content, (New-Object Text.UTF8Encoding $false))
    $changed.Add("MCP 配置：$Path")
    Write-Host "  [new]  $Label 已写入"
}

$mcpJson = @"
{
  "mcpServers": {
    "blender": {
      "command": "$($profile_.tools.uvx -replace '\\', '\\')",
      "args": ["--python", "3.11", "blender-mcp"],
      "env": {
        "UV_PYTHON_PREFERENCE": "only-managed",
        "BLENDER_HOST": "$($profile_.mcp.blenderHost)",
        "BLENDER_PORT": "$($profile_.mcp.blenderPort)"
      }
    },
    "unityMCP": {
      "url": "$($profile_.mcp.unityBridgeUrl)",
      "type": "http"
    }
  }
}
"@
Write-IfChanged -Path (Join-Path $hub '.cursor\mcp.json') -Label 'Cursor MCP' -Content $mcpJson

$codex = @"
[mcp_servers.blender]
command = '$($profile_.tools.uvx)'
args = ["--python", "3.11", "blender-mcp"]

[mcp_servers.blender.env]
UV_PYTHON_PREFERENCE = "only-managed"
BLENDER_HOST = "$($profile_.mcp.blenderHost)"
BLENDER_PORT = "$($profile_.mcp.blenderPort)"

[mcp_servers.unityMCP]
url = "$($profile_.mcp.unityBridgeUrl)"
"@
Write-IfChanged -Path (Join-Path $hub '.codex\config.toml') -Label 'Codex MCP' -Content ($codex + "`n")

Write-Host "`n== 4/4 凭据与工具 ==" -ForegroundColor Cyan
$keyFile = Join-Path $hub 'tools\.apimart.key'
if (Test-Path -LiteralPath $keyFile) {
    Write-Host "  [ok]   tools/.apimart.key 存在"
} else {
    $warn.Add('缺少 tools/.apimart.key（不入库，需从另一台机器手工拷贝或重新申请）')
}

if (Test-Path -LiteralPath $profile_.tools.blender) {
    Write-Host "  [ok]   Blender：$($profile_.tools.blender)"
} else {
    $warn.Add("Blender 不存在：$($profile_.tools.blender)")
}

if (Test-Path -LiteralPath $profile_.tools.uvx) {
    Write-Host "  [ok]   uvx：$($profile_.tools.uvx)"
} else {
    $warn.Add("uvx 不存在：$($profile_.tools.uvx)（blender MCP 起不来）")
}

foreach ($v in ($profile_.games.PSObject.Properties | ForEach-Object { $_.Value.editor } | Select-Object -Unique)) {
    $exe = Join-Path $profile_.tools.unityEditorRoot "$v\Editor\Unity.exe"
    if (Test-Path -LiteralPath $exe) { Write-Host "  [ok]   Unity $v" }
    else { $warn.Add("Unity $v 未安装：$exe") }
}

Write-Host "`n== 小结 ==" -ForegroundColor Cyan
Write-Host ("  改动 {0} 项，警告 {1} 项" -f $changed.Count, $warn.Count)
if ($warn.Count -gt 0) {
    foreach ($w in $warn) { Write-Host "  [!] $w" -ForegroundColor Yellow }
}
Write-Host "`n下一步：powershell -ExecutionPolicy Bypass -File `"$PSScriptRoot\doctor.ps1`"`n"

if ($warn.Count -gt 0) { exit 2 } else { exit 0 }
