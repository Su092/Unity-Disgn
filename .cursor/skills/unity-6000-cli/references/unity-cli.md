# Unity CLI（`unity`）命令目录

来源：[Use the Unity CLI](https://docs.unity.com/en-us/unity-cli/use-unity-cli)、[Unity CLI reference](https://docs.unity.com/en-us/unity-cli/unity-cli-reference)

本机验证：`unity --version`（Windows 安装：`irm https://unity.com/install.ps1 | iex`）。  
权威参数以 `unity <cmd> --help` 为准。搜命令：`unity commands --grep <词> --format json`。

驱动已开 Editor 需要工程装有 `com.unity.pipeline`：`unity pipeline install --project-path <path>`。

---

## 全局标志

| 标志 | 说明 |
|------|------|
| `--format human\|json\|tsv\|ndjson\|github` | 输出格式；也可用 `UNITY_FORMAT` |
| `--json` | `--format json` 简写 |
| `--non-interactive` | CI：禁用提示 |
| `--quiet` / `--verbose` | 少输出 / 完整错误链 |
| `--no-banner` / `--no-pager` | 无品牌头 / 关分页 |
| `--yes` | 确认危险操作（视命令） |
| `--proxy <url>` / `--proxy-disable` | 代理 |

解析输出时**始终**用 `--format json`。

## 关键环境变量

| 变量 | 作用 |
|------|------|
| `UNITY_PROJECT_PATH` | 默认工程路径（`open`/`status`/`command`/`list`/`job`/`mcp` 等） |
| `UNITY_EDITOR_VERSION` | 默认 Editor 版本 |
| `UNITY_FORMAT` / `UNITY_NON_INTERACTIVE` / `UNITY_QUIET` | 对应全局标志 |
| `UNITY_SERVICE_ACCOUNT_ID` / `UNITY_SERVICE_ACCOUNT_SECRET` | CI 服务账号 |
| `UNITY_NO_CLOUD` | 创建工程时不链接 Cloud |
| `UNITY_ACCELERATOR` | Accelerator `host:port` |
| `UNITY_CLI_HOME` | CLI 安装根目录 |

---

## Editors & modules

| 命令 | 别名 | 说明 |
|------|------|------|
| `unity install <ver\|lts\|latest>` | `i` | 安装 Editor，`-m` 加模块 |
| `unity install-modules -e <ver> -m ...` | `im` | 给已装版本加模块 |
| `unity uninstall <ver>` | `u` | 卸载 |
| `unity editors` | `e` | 列表/本地添加/默认/升级/运行中实例 |
| `unity editor ...` | | 单版本操作（如 `module remove`） |
| `unity install-path` | `ip` | 查看/改安装路径 |
| `unity modules list <ver>` | | 可用模块 |
| `unity releases` | | 发布 feed |
| `unity hub install` | | 安装 Hub |

6000.6 示例：

```powershell
unity install 6000.6.0f1 -m windows-il2cpp android webgl --yes --accept-eula
unity editors --installed --format json
unity editors running --format json
```

## Projects / templates / assets

| 命令 | 说明 |
|------|------|
| `unity open <path>` | 打开工程；可 `--until-ready`、`--batchmode`、`--accept-upgrades` |
| `unity close` | 关闭打开该工程的 Editor（不保存） |
| `unity projects` (`p`) | list/create/clone/open/link/pin/size/close |
| `unity templates` (`t`) | 列/检/管模板（`--editor` 需具体 `6000.x.y`，不认 `lts`） |
| `unity assets inspect\|export\|import` | `.unitypackage` |

```powershell
unity projects create MyGame --path E:\Unity Development --editor-version 6000.6.0f1 `
  --template com.unity.template.urp-blank --no-cloud
unity open E:\Unity Development\MyGame --until-ready
```

## Build / run / test / watch

| 命令 | 说明 |
|------|------|
| `unity build` | batch 构建；`--list-targets` / `--list-profiles` / `--create-profile`；`build run` 启动最近构建 |
| `unity run` | batch 跑工程，或 `--command` 跑已注册 Editor 命令后退出 |
| `unity recompile` | 对运行中 Editor 重编译；`--strict` 警告也失败 |
| `unity test` | Edit/Play Mode；NUnit 报告 |
| `unity watch` / `watch test` | 文件变更重跑 |

详见 [build-test.md](build-test.md)。

## Auth / license / cloud

| 命令 | 说明 |
|------|------|
| `unity auth login\|status\|logout` | OAuth 或服务账号 |
| `unity license` / `license status` / `activate` / `return` | 许可证 |
| `unity cloud` | 组织与 Cloud 工程 |

```powershell
unity auth status --format json
unity license status --format json
unity license activate --personal --accept-eula
```

## VCS

`unity vcs setup|status|sync|switch|doctor|merge-setup|conflicts|explain|resolve|diff|blame|summarize|affected|hooks|providers|git|uvcs`

Unity 友好的 Git/GitHub/GitLab/UVCS 工作流；冲突用 Editor 合并工具。

## Connected Editor / agents

| 命令 | 说明 |
|------|------|
| `unity status` | 已连接 Editor：端口、工程、版本、PID、Safe Mode |
| `unity command` / `cmd` | 转发命令到 Editor；无子命令则列出 |
| `unity commands` | 全命令清单（内置+插件+Pipeline） |
| `unity list` | Editor 已注册工具 + 参数 schema |
| `unity pipeline` / `pipe` | 安装/升级 Pipeline；Cloud Build / Automation 查询 |
| `unity mcp` | 启动/配置 MCP server（含 `mcp configure`） |
| `unity job` | 分离式 Editor 任务 |
| `unity skill` | 安装/刷新 agent skill |

```powershell
unity status --until-ready --project-path E:\Unity Development\MyGame --format json
unity command --format json
unity command script eval 'UnityEngine.Debug.Log("hi");' --project-path E:\Unity Development\MyGame
unity mcp configure   # 按客户端配置官方 MCP
```

三种驱动模式：

1. **热交互**：`unity open` → `status ready` → `unity command`
2. **常驻无头**：`unity open --batchmode`（或 Editor `-batchmode` 不加 `-quit`）→ `unity command`
3. **一次性 CI**：`unity run --command ...`（跑完退出）

## Diagnostics / config / lifecycle

| 命令 | 说明 |
|------|------|
| `unity doctor` / `diagnose` | 健康检查 |
| `unity logs` / `env` / `context` / `config` | 日志、环境、命名上下文、设置 |
| `unity analytics` / `cache` / `bug` | 同意、缓存、报 bug |
| `unity shell` | 交互多命令会话；可 `--protocol ndjson` |
| `unity plugin` | 目录插件（如 AI generators） |
| `unity self-update` / `self-uninstall` / `version` | CLI 自身 |

---

## 退出码（摘要）

分支先看进程退出码，再看 JSON `errors[0].code`。

| 码 | 含义（概要） |
|----|----------------|
| 0 | 成功 |
| 2 | 用法错误 |
| 3 | 需登录 / 凭证 |
| 6 | 通用失败（含未 ready） |
| 7 | 编译/Safe Mode 相关 |
| 9 | 安装锁忙 |
| 11–14 | 缺工程 / Editor 未运行 / 未知命令 / 超时 等 |
| 12 | `EDITOR_NOT_RUNNING`（pin 不匹配） |

以 `unity commands --json` 的 `exitCodes` 与当前 CLI `--help` 为准。

## 从 Hub CLI 迁移

旧：`"Unity Hub.exe" -- --headless <cmd>`  
新：`unity <cmd>`（独立二进制，可不装 Hub 桌面端）
