<#
.SYNOPSIS
  Blender 交付门：一条命令跑完「门自检 → 数值门 → 导入契约 → 出 manifest」。

.DESCRIPTION
  把 blender-asset-pipeline 技能接成工作区可执行入口。三件必做的事：
    1. 先跑 gate 的 selftest（11/11）；门坏了的时候，任何模型结论都不可信
    2. 数值门跑在 .blend（构建通路）
    3. 契约门 + 数值门再跑一遍**导出的 FBX**（交付通路）—— 换通路复核，见技能铁律 B

  任何一环 degraded 都以退出码 2 结束：degraded 不是通过，必须补查。

.PARAMETER Blend
  源 .blend 路径。

.PARAMETER Fbx
  导出的 FBX 路径（可选，建议给）。

.PARAMETER Objects
  逗号分隔对象名 / 集合名，省略=全部网格。

.PARAMETER MinMm
  壁厚下限（mm）。不给则壁厚门只报数不判定。

.PARAMETER ResolutionMm
  网格测量分辨率（mm）。MinMm 低于它时壁厚门会判 degraded。

.PARAMETER Expect
  期望尺寸 x,y,z（mm），如 "1000,1000,2000"。

.PARAMETER TolMm
  尺寸公差（mm），默认 3。

.PARAMETER MaxTris
  三角面预算，默认 60000。

.PARAMETER NoBone
  该件不需要骨架（道具 / 核心 / 出生门）。

.PARAMETER RequireFloor
  世界最低点必须贴地（z≈0）。

.PARAMETER ContractOnly
  只跑导入契约门，跳过数值门。用于**存量外部制作件**：它们是分件装配体，
  单体水密判据（①–④）本来就不适用，硬跑会得到一堆与本工程无关的 fail。

.PARAMETER Out
  输出目录，默认 <工作区>/tools/_gate。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\blender-gate.ps1 `
      -Blend "E:\work\tower.blend" -Fbx "E:\work\out\Modle_Tower_Assault.fbx" `
      -MinMm 1.2 -Expect "1000,1000,2000" -RequireFloor
#>
param(
    [string]$Blend = "",
    [string]$Fbx = "",
    [string]$Objects = "",
    [double]$MinMm = 0,
    [double]$ResolutionMm = 0,
    [string]$Expect = "",
    [double]$TolMm = 3,
    [int]$MaxTris = 60000,
    [switch]$NoBone,
    [switch]$RequireFloor,
    [switch]$ContractOnly,
    [switch]$UvUnwrap,
    [string]$Out = ""
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------- 路径

$Workspace = Split-Path $PSScriptRoot -Parent
$SkillRoot = Join-Path $Workspace ".cursor\skills\blender-asset-pipeline"
$GatePy = Join-Path $SkillRoot "scripts\blender_gate.py"
$ContractPy = Join-Path $PSScriptRoot "blender_contract.py"
$FbxGatePy = Join-Path $PSScriptRoot "blender_fbx_gate.py"
$BuriedTruePy = Join-Path $PSScriptRoot "blender_buried_true.py"
$UvGatePy = Join-Path $PSScriptRoot "blender_uv_gate.py"

if (-not $Out) { $Out = Join-Path $PSScriptRoot "_gate" }
if (-not (Test-Path $Out)) { New-Item -ItemType Directory -Path $Out -Force | Out-Null }
$Out = (Resolve-Path $Out).Path

# ---------------------------------------------------------------- 找 Blender

$Candidates = @(
    "E:\SteamLibrary\steamapps\common\Blender\blender.exe",
    "E:\toyxyz_RGBMocap\runtime_character\blender.exe",
    (Join-Path $env:ProgramFiles "Blender Foundation\Blender 5.2\blender.exe")
)
$Blender = ""
foreach ($c in $Candidates) {
    if (Test-Path $c) { $Blender = $c; break }
}
if (-not $Blender) {
    $cmd = Get-Command blender -ErrorAction SilentlyContinue
    if ($cmd) { $Blender = $cmd.Source }
}
if (-not $Blender) {
    Write-Host "找不到 blender.exe。显式指定：`$env:BLENDER_EXE = <路径>" -ForegroundColor Red
    if ($env:BLENDER_EXE -and (Test-Path $env:BLENDER_EXE)) { $Blender = $env:BLENDER_EXE }
    else { exit 3 }
}

foreach ($f in @($GatePy, $ContractPy, $FbxGatePy, $BuriedTruePy, $UvGatePy)) {
    if (-not (Test-Path $f)) { Write-Host "缺少脚本：$f" -ForegroundColor Red; exit 3 }
}

function Invoke-Blender([string[]]$BlenderArgs) {
    # Blender 把日志与告警混在 stdout/stderr 两路打印，必须合并再挑 JSON。
    # 合并后 PowerShell 会把 stderr 行包成 NativeCommandError，在 Stop 模式下直接抛异常，
    # 所以这里临时降到 Continue —— 真失败由 JSON verdict 与退出码判定，不靠异常。
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $raw = & $Blender @BlenderArgs 2>&1 | Out-String
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $prev
    }
    return @{ Code = $code; Text = $raw }
}

function Get-JsonBlock([string]$text) {
    # 从混合输出里取最后一个 '{' 到最后一个 '}' —— gate 会把 JSON 打印到末尾
    $i = $text.IndexOf("{")
    $j = $text.LastIndexOf("}")
    if ($i -lt 0 -or $j -le $i) { return $null }
    try { return ($text.Substring($i, $j - $i + 1) | ConvertFrom-Json) } catch { return $null }
}

function Read-JsonFile([string]$path) {
    # BuriedTrue 一次会打印两块 JSON（自身回执 + decide 回执），Get-JsonBlock 会拼坏，
    # 所以判决一律从落盘文件读；必须带 -Encoding UTF8，否则 5.1 按 ANSI 读坏中文。
    if (-not (Test-Path $path)) { return $null }
    try { return (Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { return $null }
}

function Invoke-UvGate([string]$Source, [string]$Tag) {
    # UV 可用性：契约门只查"有 UV 层且不退化"，挡不住"多套投影叠在一起"。
    # 这里跑展开质量门（岛间不重叠 / 在 [0,1] / 密度一致 / 覆盖率）。
    $uj = Join-Path $Out "uv-$Tag.json"
    $u = @("-b")
    if ($Source -like "*.fbx") {
        $u += @("--factory-startup", "--python", $UvGatePy, "--", "--fbx", (Resolve-Path $Source).Path)
    }
    else {
        $u += @((Resolve-Path $Source).Path, "--python", $UvGatePy, "--")
    }
    $u += @("--out", $uj)
    if ($Objects) { $u += @("--objects", $Objects) }

    $ru = Invoke-Blender $u
    if ($ru.Code -ne 0 -and $ru.Code -ne 1) { Write-Host $ru.Text }
    $j = Read-JsonFile $uj
    if ($null -eq $j) {
        Write-Host "    uv/$Tag : 跑失败（脚本异常）" -ForegroundColor Red
        $script:ExitCode = 2
        return
    }
    if ($j.objects) {
        foreach ($p in $j.objects.PSObject.Properties) {
            $o = $p.Value
            Write-Host ("    uv/$Tag {0} : {1}（{2} 岛 / 重叠 {3} / 覆盖 {4:P0} / 密度比 {5}）" -f `
                    $p.Name, $o.verdict, $o.uv_islands, $o.island_bbox_overlaps,
                [double]$o.coverage, $o.texel_density_ratio) `
                -ForegroundColor $(switch ($o.verdict) { "pass" { "Green" } "fail" { "Red" } default { "Yellow" } })
            if ($o.verdict -ne "pass") { Write-Host "      $($o.note)" -ForegroundColor DarkYellow }
        }
    }
    Add-Verdict "uv/$Tag" $j $uj
}

function Invoke-BuriedTrue([string]$Source, [string]$GateJson, [string]$Tag) {
    # buried 启发式在凹腔/遮挡网格上系统性假阳性（见 tools/blender_buried_true.py 文件头）。
    # 这里用奇偶交点法复算，并把 buried 一项替换进数值门的总判决。
    $btJson = Join-Path $Out "buried-true-$Tag.json"
    $decJson = Join-Path $Out "decided-$Tag.json"
    $b = @("-b")
    if ($Source -like "*.fbx") {
        $b += @("--factory-startup", "--python", $BuriedTruePy, "--", "--fbx", (Resolve-Path $Source).Path)
    }
    else {
        $b += @((Resolve-Path $Source).Path, "--python", $BuriedTruePy, "--")
    }
    $b += @("--out", $btJson, "--decide", $GateJson, "--decided-out", $decJson)
    if ($Objects) { $b += @("--objects", $Objects) }

    $rb = Invoke-Blender $b
    if ($rb.Code -ne 0 -and $rb.Code -ne 1) { Write-Host $rb.Text }

    $bt = Read-JsonFile $btJson
    $dec = Read-JsonFile $decJson
    if ($null -eq $bt -or $null -eq $dec) {
        Write-Host "    buried-true/$Tag : 跑失败（脚本异常）" -ForegroundColor Red
        $script:ExitCode = 2
        return $null
    }
    if ($bt.objects) {
        foreach ($p in $bt.objects.PSObject.Properties) {
            $o = $p.Value
            Write-Host ("    buried-true/$Tag {0} : {1}（真内部 {2} 张 / 启发式 {3} 张）" -f `
                    $p.Name, $o.verdict, $o.true_buried, $o.heuristic_buried) `
                -ForegroundColor $(switch ($o.verdict) { "pass" { "Green" } "fail" { "Red" } default { "Yellow" } })
        }
    }
    return $dec
}

Write-Host "Blender : $Blender"
Write-Host "输出    : $Out"

# ---------------------------------------------------------------- 0) 门自检

Write-Host "`n==> [0/3] 门自检 selftest" -ForegroundColor Cyan
$st = Invoke-Blender @("-b", "--factory-startup", "--python", $GatePy, "--", "selftest")
$line = ($st.Text -split "`n" | Select-String -Pattern "\d+\s*/\s*\d+ passed" | Select-Object -Last 1)
if (-not $line) {
    Write-Host $st.Text
    Write-Host "selftest 没输出通过行 ⇒ 门本身有问题，停止" -ForegroundColor Red
    exit 2
}
Write-Host "    $($line.Line.Trim())"
$nums = [regex]::Match($line.Line, "(\d+)\s*/\s*(\d+)")
if ($nums.Groups[1].Value -ne $nums.Groups[2].Value) {
    Write-Host "selftest 未全通过 ⇒ 先修门，别看模型" -ForegroundColor Red
    exit 2
}

# buried 真判据门的自检：三例必须全过（clean / 重叠 / 凹腔），否则它的裁定不可信
$stp = Invoke-Blender @("-b", "--factory-startup", "--python", $BuriedTruePy, "--", "--selftest")
$line2 = ($stp.Text -split "`n" | Select-String -Pattern "\d+\s*/\s*\d+ passed" | Select-Object -Last 1)
if (-not $line2) {
    Write-Host $stp.Text
    Write-Host "buried-true selftest 没输出通过行 ⇒ 停止" -ForegroundColor Red
    exit 2
}
Write-Host "    buried-true $($line2.Line.Trim())"
$n2 = [regex]::Match($line2.Line, "(\d+)\s*/\s*(\d+)")
if ($n2.Groups[1].Value -ne $n2.Groups[2].Value) {
    Write-Host "buried-true selftest 未全通过 ⇒ 别用它的裁定" -ForegroundColor Red
    exit 2
}

# UV 可用性门的自检：六例必须全过，否则"UV 能不能用"没有机器结论
$stu = Invoke-Blender @("-b", "--factory-startup", "--python", $UvGatePy, "--", "--selftest")
$line3 = ($stu.Text -split "`n" | Select-String -Pattern "\d+\s*/\s*\d+ passed" | Select-Object -Last 1)
if (-not $line3) {
    Write-Host $stu.Text
    Write-Host "uv-gate selftest 没输出通过行 ⇒ 停止" -ForegroundColor Red
    exit 2
}
Write-Host "    uv-gate $($line3.Line.Trim())"
$n3 = [regex]::Match($line3.Line, "(\d+)\s*/\s*(\d+)")
if ($n3.Groups[1].Value -ne $n3.Groups[2].Value) {
    Write-Host "uv-gate selftest 未全通过 ⇒ UV 结论不可信" -ForegroundColor Red
    exit 2
}

$Results = @()
$ExitCode = 0

function Add-Verdict([string]$Label, $Json, [string]$File) {
    if ($null -eq $Json) {
        Write-Host "    $Label : 解析失败" -ForegroundColor Red
        $script:ExitCode = 2
        return
    }
    $v = $Json.verdict
    $color = switch ($v) { "pass" { "Green" } "fail" { "Red" } default { "Yellow" } }
    Write-Host "    $Label : $v" -ForegroundColor $color
    $script:Results += [pscustomobject]@{ label = $Label; verdict = $v; file = $File; json = $Json }
    if ($v -eq "fail" -and $script:ExitCode -lt 1) { $script:ExitCode = 1 }
    if ($v -eq "degraded") { $script:ExitCode = 2 }   # degraded 优先于 fail：都要补查
}

# ---------------------------------------------------------------- 1) .blend 数值门

if ($Blend -and -not $ContractOnly) {
    if (-not (Test-Path $Blend)) { Write-Host "找不到 .blend：$Blend" -ForegroundColor Red; exit 3 }
    Write-Host "`n==> [1/3] 数值门 · 构建通路（.blend）" -ForegroundColor Cyan

    $outJson = Join-Path $Out "gate-blend.json"
    $a = @("-b", $Blend, "--python", $GatePy, "--", "all", "--out", $outJson)
    if ($Objects)       { $a += @("--objects", $Objects) }
    if ($MinMm -gt 0)   { $a += @("--min-mm", "$MinMm") }
    if ($ResolutionMm -gt 0) { $a += @("--resolution-mm", "$ResolutionMm") }
    if ($Expect)        { $a += @("--expect", $Expect) }
    $a += @("--tol-mm", "$TolMm")

    $r = Invoke-Blender $a
    $gateJson = Get-JsonBlock $r.Text
    if ($null -eq $gateJson) {
        Add-Verdict "blend/gates" $null $outJson
    }
    else {
        $dec = Invoke-BuriedTrue $Blend $outJson "blend"
        Add-Verdict "blend/gates" $dec (Join-Path $Out "decided-blend.json")
        if ($UvUnwrap) { Invoke-UvGate $Blend "blend" }
    }
}
elseif ($ContractOnly) {
    Write-Host "`n==> [1/3] 跳过数值门（-ContractOnly）" -ForegroundColor DarkGray
}
else {
    Write-Host "`n==> [1/3] 跳过：未给 -Blend" -ForegroundColor DarkGray
}

# ---------------------------------------------------------------- 2) FBX 交付通路

if ($Fbx) {
    if (-not (Test-Path $Fbx)) { Write-Host "找不到 FBX：$Fbx" -ForegroundColor Red; exit 3 }
    Write-Host "`n==> [2/3] 交付通路（FBX 重新导入，换通路复核）" -ForegroundColor Cyan

    $outGate = Join-Path $Out "gate-fbx.json"
    if (-not $ContractOnly) {
        $a = @("-b", "--factory-startup", "--python", $FbxGatePy, "--", (Resolve-Path $Fbx).Path, $GatePy, "all", "--out", $outGate)
        if ($MinMm -gt 0)   { $a += @("--min-mm", "$MinMm") }
        if ($ResolutionMm -gt 0) { $a += @("--resolution-mm", "$ResolutionMm") }
        if ($Expect)        { $a += @("--expect", $Expect) }
        $a += @("--tol-mm", "$TolMm")
        $r = Invoke-Blender $a
        $gJson = Get-JsonBlock $r.Text
        if ($null -eq $gJson) {
            Add-Verdict "fbx/gates" $null $outGate
        }
        else {
            $dec = Invoke-BuriedTrue $Fbx $outGate "fbx"
            Add-Verdict "fbx/gates" $dec (Join-Path $Out "decided-fbx.json")
            if ($UvUnwrap) { Invoke-UvGate $Fbx "fbx" }
        }
    }
    else {
        Write-Host "    fbx/gates : 跳过（-ContractOnly）" -ForegroundColor DarkGray
    }

    $outContract = Join-Path $Out "contract-fbx.json"
    $c = @("-b", "--factory-startup", "--python", $ContractPy, "--", "--fbx", (Resolve-Path $Fbx).Path,
           "--max-tris", "$MaxTris", "--out", $outContract)
    if ($NoBone)       { $c += "--no-bone" }
    if ($RequireFloor) { $c += "--require-floor" }
    $r = Invoke-Blender $c
    Add-Verdict "fbx/contract" (Get-JsonBlock $r.Text) $outContract
}
else {
    Write-Host "`n==> [2/3] 跳过：未给 -Fbx（交付前建议补上，否则没有第二通路）" -ForegroundColor DarkGray
}

# ---------------------------------------------------------------- 3) manifest

Write-Host "`n==> [3/3] manifest" -ForegroundColor Cyan

function Get-Md5([string]$path) {
    if (-not $path -or -not (Test-Path $path)) { return "" }
    return (Get-FileHash $path -Algorithm MD5).Hash.ToLower()
}

# hash 字面量里不能出现赋值语句（会被当成变量值做 key），先算好再拼
$verdicts = @($Results | ForEach-Object {
    [ordered]@{ label = $_.label; verdict = $_.verdict; file = $_.file }
})

$manifest = [ordered]@{
    tool          = "blender-gate.ps1"
    created       = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    blender       = (& $Blender --version | Select-Object -First 1)
    skill_version = (Select-String -Path $GatePy -Pattern '^VERSION' | Select-Object -First 1).Line
    inputs        = [ordered]@{
        blend = if ($Blend) { (Resolve-Path $Blend).Path } else { "" }
        fbx   = if ($Fbx)   { (Resolve-Path $Fbx).Path }   else { "" }
        md5   = [ordered]@{ blend = (Get-Md5 $Blend); fbx = (Get-Md5 $Fbx) }
    }
    params        = [ordered]@{
        objects = $Objects; min_mm = $MinMm; resolution_mm = $ResolutionMm
        expect = $Expect; tol_mm = $TolMm; max_tris = $MaxTris
        no_bone = [bool]$NoBone; require_floor = [bool]$RequireFloor
        contract_only = [bool]$ContractOnly
    }
    verdicts      = $verdicts
    exit_code     = $ExitCode
}

$manifestPath = Join-Path $Out "manifest.json"
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Path $manifestPath -Encoding UTF8
Write-Host "    $manifestPath"

$verdictText = ($Results | ForEach-Object { "$($_.label)=$($_.verdict)" }) -join " · "
if (-not $verdictText) { $verdictText = "无门结果" }

switch ($ExitCode) {
    0 { Write-Host "`nRESULT PASS · $verdictText" -ForegroundColor Green }
    1 { Write-Host "`nRESULT FAIL · $verdictText（确有缺陷，看 $Out 下的 JSON）" -ForegroundColor Red }
    default { Write-Host "`nRESULT DEGRADED · $verdictText（没查完，补查后重跑，不许当通过）" -ForegroundColor Yellow }
}

exit $ExitCode
