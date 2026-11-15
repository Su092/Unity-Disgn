# agents — 智能体工作区注册表

不同宿主（Cursor / Codex / Claude）读不同的配置文件。本目录声明**谁读什么、哪些是副本、哪些禁止复制**，防止同一份口径在多处分叉。

## 宿主矩阵

| 宿主 | 规则 | 技能 | MCP |
|------|------|------|-----|
| Cursor | `.cursor/rules/*.mdc` | `.cursor/skills/` | `.cursor/mcp.json`（bootstrap 生成） |
| Codex | `AGENTS.md` + `.codex/` | `.codex/skills/` | `.codex/config.toml`（bootstrap 生成） |
| Claude | `CLAUDE.md` | `.agents/skills/`（**不再使用**） | — |

## 唯一真源（Single Source of Truth）

| 内容 | 真源 | 副本策略 |
|------|------|----------|
| 架构 / 路径 / 流程 / 禁忌 | `<HUB>/README.md` + `.cursor/rules/multi-project-workspace.mdc` | Codex 侧通过 `AGENTS.md` 引用，不复制正文 |
| `apimart-image` 技能 | `.cursor/skills/apimart-image/` | **禁止复制**（历史副本已删，勿重建） |
| `unity-6000-cli` 技能 | `.cursor/skills/unity-6000-cli/` | 禁止复制 |
| `blender-asset-pipeline` 技能 | `.cursor/skills/blender-asset-pipeline/` | `.codex/skills/blender-asset-pipeline/` 是**派生改写版**（带 `ADAPTATION.md`），内容有意不同，**不要同步** |
| MCP 配置 | `machine/profile.local.json` | `.cursor/mcp.json` 与 `.codex/config.toml` 均由 `machine/bootstrap.ps1` 生成，**不手工编辑** |
| 机器绑定 | `machine/profile.local.json` | 不入库；`profile.example.json` 是模板 |

## 校验

`machine/doctor.ps1` 第 7 项检查越界 `SKILL.md`：除 `.cursor/skills/` 与 `.codex/skills/` 外出现任何 `SKILL.md` 即判 `fail`。

## 新增宿主时

1. 在本文件「宿主矩阵」加一行
2. 规则文件写到对应位置，但**正文不复制**：只写宿主差异 + 指向真源
3. 若该宿主必须有自己的技能副本，在本文件「唯一真源」表里明确标注「派生版，不同步」及原因
4. 更新 `doctor.ps1` 的允许目录列表

## 工程级规则

各 Unity 工程可有自己的 `.cursor/rules/`，但**只允许写本工程特有**的内容（例如 Star Defanse 禁止装 URP、S 的 `Core/` 零 Unity 依赖）。通用口径一律上移到工作区级。
