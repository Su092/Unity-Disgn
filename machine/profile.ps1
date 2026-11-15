# machine/profile.ps1 — 机器绑定解析
# 被 bootstrap.ps1 / doctor.ps1 / tools/*.ps1 dot-source。
#
# 唯一允许出现绝对盘符的地方是 profile.local.json。其余脚本与文档一律用逻辑记号：
#   <HUB>        = 枢纽根
#   <GAME:id>    = 某游戏真实工程根（id 取 profile.games 的键，含空格照写）
#   <UNITY:ver>  = 指定版本编辑器可执行文件
#   <BLENDER>    = Blender 可执行文件

$ErrorActionPreference = 'Stop'

$script:MachineRoot = $PSScriptRoot
$script:ProfilePath = Join-Path $PSScriptRoot 'profile.local.json'

function Get-HubProfile {
    if (-not (Test-Path -LiteralPath $script:ProfilePath)) {
        throw "缺少 profile.local.json。请把 machine/profile.example.json 复制为 machine/profile.local.json 并填写本机路径。"
    }
    return (Get-Content -LiteralPath $script:ProfilePath -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Get-HubRoot {
    param($Profile)
    if (-not $Profile) { $Profile = Get-HubProfile }
    return $Profile.hub.real
}

function Get-HubLink {
    param($Profile)
    if (-not $Profile) { $Profile = Get-HubProfile }
    return $Profile.hub.link
}

function Get-GameProfile {
    param([Parameter(Mandatory)][string]$Id, $Profile)
    if (-not $Profile) { $Profile = Get-HubProfile }
    $prop = $Profile.games.PSObject.Properties[$Id]
    if (-not $prop) {
        $known = ($Profile.games.PSObject.Properties | ForEach-Object { $_.Name }) -join ', '
        throw "profile 里没有游戏 '$Id'。已注册：$known"
    }
    return $prop.Value
}

function Get-GamePath {
    param([Parameter(Mandatory)][string]$Id, $Profile)
    return (Get-GameProfile -Id $Id -Profile $Profile).path
}

function Get-GameIds {
    param($Profile)
    if (-not $Profile) { $Profile = Get-HubProfile }
    return ($Profile.games.PSObject.Properties | ForEach-Object { $_.Name })
}

function Get-UnityEditor {
    param([string]$Version, $Profile)
    if (-not $Profile) { $Profile = Get-HubProfile }
    if (-not $Version) {
        $Version = ($Profile.games.PSObject.Properties | ForEach-Object { $_.Value.editor } |
            Where-Object { $_ } | Select-Object -First 1)
    }
    if (-not $Version) { throw 'profile 里没有任何游戏的 editor 版本，也没有传 -Version。' }
    return (Join-Path $Profile.tools.unityEditorRoot "$Version\Editor\Unity.exe")
}

function Get-BlenderPath {
    param($Profile)
    if (-not $Profile) { $Profile = Get-HubProfile }
    return $Profile.tools.blender
}

# 把逻辑记号展开为真实路径
function Expand-HubToken {
    param([Parameter(Mandatory)][string]$Text, $Profile)
    if (-not $Profile) { $Profile = Get-HubProfile }
    $out = $Text
    $out = $out.Replace('<HUB>', $Profile.hub.real)
    $out = $out.Replace('<BLENDER>', $Profile.tools.blender)
    foreach ($g in $Profile.games.PSObject.Properties) {
        $out = $out.Replace("<GAME:$($g.Name)>", $g.Value.path)
    }
    $root = $Profile.tools.unityEditorRoot
    $out = [regex]::Replace($out, '<UNITY:([0-9A-Za-z\.]+)>', {
            param($m)
            return (Join-Path $root ($m.Groups[1].Value + '\Editor\Unity.exe'))
        })
    return $out
}
