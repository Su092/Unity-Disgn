# 当前快照 — 云端王国

更新：2026-11-06

## 关联

- 枢纽：`E:\Unity Development\Project\Kingdom Of Cloud\`
- Unity：`D:\Kingdom Of Cloud`（`unity\` 目录联接）
- 编辑器：Unity **6000.6.4f1**（`D:\Unity\6000.6.4f1`）

## 已定约定

- **关联开发**：文档/拆解/记忆只在枢纽；运行时只在 `unity/Assets/_Game/`
- 场景/预制体：优先本工程 Unity MCP（HTTP 8765）；失败给手动步骤；未要求不写菜单工具
- 输入：旧 Input Manager
- 玩法方向：类《星际拓荒》有限箱庭（见 `docs/concept.md`）
- 渲染底座：URP 17.6.0
- 少写保护性兜底，尽早暴露配置错误

## 当前状态

- 游戏端 `Cursor Work Space/` 已删除（控制/笔记/记忆/日志/vendor 已清；概念原文迁至 `docs/source/`）
- MCP 包：`Packages/com.coplaydev.unity-mcp`
- 基础脚本：`Singleton` / `GameManager` / `PlayerController` / `CameraFollow`
- 拆解入口：`breakdown/01-foundation-status.md`

## 未决 / 注意

- 概念未决：肉鸽、元素矩阵、知识锁与锁合/深潜咬合
- 渲染下一阶段：压力雾 / 体积云 / 锁合材质（需新拆解文件）
- `.gitignore` 构建目录只用根路径 `/[Bb]uild/`，勿用全局 `[Bb]uild/`
