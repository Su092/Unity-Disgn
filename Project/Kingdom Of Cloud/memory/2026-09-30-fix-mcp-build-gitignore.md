# 修复：MCP ManageBuild CS0234（Build 命名空间缺失）

更新：2026-09-30

## 现象

```
Packages\com.coplaydev.unity-mcp\Editor\Tools\ManageBuild.cs(9,32): error CS0234:
The type or namespace name 'Build' does not exist in the namespace 'MCPForUnity.Editor.Tools'
```

## 根因

根目录 `.gitignore` 使用了 `[Bb]uild/`，会匹配**任意路径**下名为 `Build` 的目录。  
`Packages/com.coplaydev.unity-mcp/Editor/Tools/Build/`（`BuildRunner` / `BuildJob` 等）因此被忽略，未进仓库；克隆后只剩空目录 + `ManageBuild.cs` 的 `using`，编译失败。

上游 Coplay 包已用例外规避：`!MCPForUnity/**/Build/`。

## 修复

1. 从 `com.coplaydev.unity-mcp` **v10.2.0** 补回 `Editor/Tools/Build/*.cs`（及 `.meta`）
2. `.gitignore` 改为仅忽略仓库根输出：`/[Bb]uild/`、`/[Bb]uilds/`

## 注意

以后勿把全局 `[Bb]uild/` 写回；需要忽略打包产物时用根路径前缀 `/`。
