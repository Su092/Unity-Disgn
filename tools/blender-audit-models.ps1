<#
.SYNOPSIS
  对存量 FBX 做批量体检（只跑契约门），汇总成一张表。

.DESCRIPTION
  存量 18 个 FBX 是外部制作后导出的**分件装配体**（塔 = Base/Yaw/Head/Barrel/Muzzle
  共 7 个网格）。它们不是为"单体水密"设计的，所以数值门①–④（开边/非流形/埋面/自交）
  对这些件天然 fail —— 那些"缺陷"是装配语义的正常产物，不是本工程要修的东西。

  因此本脚本只跑契约门（单位 / 导入变换 / 单根 / 命名 / 三角预算 / 材质贴图 /
  骨架 / 落地），这些才是"能不能正确进 Unity"的判据。

  新做的件才走完整门：tools\blender-gate.ps1 -Blend <源> -Fbx <导出>。

.PARAMETER ModelRoot
  模型根目录，默认星轨防线的 Art/Models。

.PARAMETER Out
  结果目录，默认 tools/_gate/audit-all。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\blender-audit-models.ps1
#>
param(
    [string]$ModelRoot = "E:\Star Defanse\Assets\Resources\Art\Models",
    [string]$Out = "E:\Unity Development\tools\_gate\audit-all"
)

$ErrorActionPreference = "Continue"
if (-not (Test-Path $Out)) { New-Item -ItemType Directory -Path $Out -Force | Out-Null }

$Workspace = Split-Path $PSScriptRoot -Parent
$ContractPy = Join-Path $PSScriptRoot "blender_contract.py"

$Blender = ""
foreach ($c in @(
    "E:\SteamLibrary\steamapps\common\Blender\blender.exe",
    "E:\toyxyz_RGBMocap\runtime_character\blender.exe"
)) {
    if (Test-Path $c) { $Blender = $c; break }
}
if (-not $Blender) { Write-Host "找不到 blender.exe" -ForegroundColor Red; exit 3 }

$rows = @()

Get-ChildItem $ModelRoot -Recurse -Filter "Modle_*.fbx" | ForEach-Object {
    $name = $_.BaseName
    # 本工程只有塔需要瞄准骨骼（Yaw）；角色/敌人/道具都不需要
    $needsYaw = $name -match 'Tower'

    $cj = Join-Path $Out "$name.contract.json"
    $a = @("-b", "--factory-startup", "--python", $ContractPy, "--", "--fbx", $_.FullName, "--out", $cj)
    if (-not $needsYaw) { $a += "--no-bone" }

    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $Blender @a 2>&1 | Out-Null } finally { $ErrorActionPreference = $prev }

    $cv = "解析失败"; $bad = ""; $tris = ""
    if (Test-Path $cj) {
        try {
            # PowerShell 5.1 默认按 ANSI 读文件，中文会变乱码导致 ConvertFrom-Json 失败
            $o = Get-Content $cj -Raw -Encoding UTF8 | ConvertFrom-Json
            $cv = $o.verdict
            $bad = (($o.checks | Where-Object { $_.state -ne "pass" } | ForEach-Object { $_.name }) -join "; ")
            $tris = ($o.checks | Where-Object { $_.name -eq "三角面预算" }).detail
        } catch { $cv = "解析失败" }
    }

    $rows += [pscustomobject]@{ model = $name; needs_yaw = $needsYaw; contract = $cv; tris = $tris; failed = $bad }
    Write-Host ("{0,-32} yaw={1,-5} contract={2,-9} {3} {4}" -f $name, $needsYaw, $cv, $tris, $bad)
}

$csv = Join-Path $Out "audit.csv"
$rows | Export-Csv -Path $csv -NoTypeInformation -Encoding UTF8
Write-Host "`n$csv"
Write-Host "---- 汇总 ----"
$rows | Group-Object contract | Select-Object Count, Name | Format-Table -AutoSize

$failedCount = ($rows | Where-Object { $_.contract -ne "pass" }).Count
if ($failedCount -gt 0) { exit 1 }
exit 0
