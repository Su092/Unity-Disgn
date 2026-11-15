# Unity 工程联接

本仓库不含 Unity 工程本体（避免 `Library` 与嵌套 Git）。工程根在 `machine/profile.local.json` 的 `games.S.path`。

## 建立联接

不要手敲 `mklink`，跑：

```powershell
powershell -ExecutionPolicy Bypass -File "<HUB>\machine\bootstrap.ps1" -OnlyGame S
```

它做三件事：建 `unity` 联接 → 校验目标 → 报告结果（幂等，可反复跑）。
联接指向错误时加 `-Force` 重建。

## 绑定

| 项 | 值 |
|----|-----|
| 枢纽 | `<HUB>/Project/S/` |
| 工程根 | `<GAME:S>`（`unity/` 为其联接） |
| 工程远端 | `git@github.com:Su092/Project-S.git`（`main`） |
| 编辑器版本 | `unity/ProjectSettings/ProjectVersion.txt` = `6000.6.4f1` |

联接已被 `.gitignore` 的 `Project/*/unity/` 规则忽略，不会把工程内容带进枢纽仓库。
绑定、验证命令与禁忌：见同级 `PROJECT.md`。

## 删除联接（不会删工程本体）

```powershell
cmd /c rmdir "<HUB>\Project\S\unity"
```

## 验收

```powershell
powershell -ExecutionPolicy Bypass -File "<HUB>\machine\doctor.ps1" -OnlyGame S
powershell -ExecutionPolicy Bypass -File "<HUB>\Project\S\unity\scripts\check.ps1" -Task all
```

**换机前置**：`-Task tests` 需要 .NET SDK，且 `tools/loadout-tests/*.csproj` 被工程 `.gitignore` 忽略、
不随仓库分发，需本地重建；否则只有 `setup/assets/build/shots` 可跑。
