# machine — 机器绑定层

> 换机部署的完整步骤见 `<HUB>\docs\跨终端部署.md`。本文件只说明这一层本身。

跨终端开发的唯一差异集中在此。**目录里只有 `profile.local.json` 是机器相关且不入库的**，其余文件都是仓库共用的逻辑。

## 文件

| 文件 | 入库 | 作用 |
|------|------|------|
| `profile.example.json` | 是 | 模板。换机时复制为 `profile.local.json` |
| `profile.local.json` | **否**（gitignore） | 本机真实路径、编辑器、Blender、游戏工程位置 |
| `profile.ps1` | 是 | 解析器。被其它脚本 dot-source，提供 `Get-HubProfile` / `Get-GamePath` / `Expand-HubToken` 等 |
| `bootstrap.ps1` | 是 | 幂等装配：建联接 → 按 profile 生成两份 MCP 配置 → 检查凭据与工具 |
| `doctor.ps1` | 是 | 三态自检：`pass(0)` / `fail(1)` / `degraded(2)` |

## profile 字段

```jsonc
{
  "machine": "A",                       // 机器代号，只用于人眼看是哪台
  "hub": {
    "real": "F:\\Unity Development",     // 枢纽真实目录（仓库所在处）
    "link": "E:\\Unity Development"      // 可选：给枢纽建的联接，留空则不建
  },
  "tools": {
    "unityEditorRoot": "F:\\Unity Hub\\Unity",  // 其下按版本分子目录，自动拼 <ver>\Editor\Unity.exe
    "blender": "...\\blender.exe",
    "uvx": "...\\uvx.exe"
  },
  "mcp": {
    "blenderHost": "127.0.0.1",
    "blenderPort": 9876,
    "unityBridgeUrl": "http://127.0.0.1:8765/mcp"
  },
  "games": {
    "<目录名>": { "path": "...", "remote": "...", "editor": "6000.6.4f1" }
  }
}
```

`games` 的键必须与 `Project/` 下的目录名逐字一致（含空格），因为联接路径就是按它拼的。

## 常用命令

```powershell
# 装配（幂等）
powershell -ExecutionPolicy Bypass -File "<HUB>\machine\bootstrap.ps1"

# 只处理一个游戏
powershell -ExecutionPolicy Bypass -File "<HUB>\machine\bootstrap.ps1" -OnlyGame S

# 联接指向了错误目标时重建
powershell -ExecutionPolicy Bypass -File "<HUB>\machine\bootstrap.ps1" -Force

# 自检
powershell -ExecutionPolicy Bypass -File "<HUB>\machine\doctor.ps1"
powershell -ExecutionPolicy Bypass -File "<HUB>\machine\doctor.ps1" -Quiet -OnlyGame S
```

## 在其它脚本里用

```powershell
. (Join-Path $Workspace 'machine\profile.ps1')
$hub   = Get-HubRoot
$star  = Get-GamePath -Id 'Star Defanse'
$unity = Get-UnityEditor -Version '6000.6.4f1'
$bl    = Get-BlenderPath
$p     = Expand-HubToken '<HUB>\Project\S\unity'   # 记号 → 真实路径
```

## 纪律

- **不要在别处写绝对盘符。** 文档写 `<HUB>` / `<GAME:id>` / `<UNITY:ver>` / `<BLENDER>`，脚本从 profile 取。
- `bootstrap.ps1` 只做幂等的"接线"，不克隆仓库、不装 Unity / Blender、不写 `profile.local.json`。
- 手改本目录下的 `.ps1` 后必须确认文件是 **UTF-8 with BOM**，否则 PowerShell 5.1 按 GBK 解码，中文会引发 `Unexpected token` 且报错行号偏移。
- `doctor.ps1` 退出码 2（degraded）必须补查，不许当通过。
