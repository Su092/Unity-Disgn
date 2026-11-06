# 2026-09-30 基础控制层与 MCP

## 做了什么

- 生成基础控制脚本与过程说明
- 安装 MCP for Unity，Cursor 连上 **Unity 2022.3.62f3c1** 工程实例
- 约定场景搭建走 MCP；过程文件进工作空间

## 关键路径

| 路径 | 说明 |
|---|---|
| `Assets/_Game/Scripts/Core/*` | Singleton、GameManager |
| `Assets/_Game/Scripts/Player/PlayerController.cs` | 第三人称移动 |
| `Assets/_Game/Scripts/Camera/CameraFollow.cs` | 环绕相机 |
| `Assets/_Game/Editor/McpLocalHttpBootstrap.cs` | MCP HTTP 8765 自动连接 |
| `Packages/com.coplaydev.unity-mcp` | MCP 包 |
| `.cursor/mcp.json` | 项目 MCP：8765 |

## 坑

- 默认 MCP HTTP 8080 与 Steam 冲突 → 改用 8765
- 误用团结引擎打开会触发版本/库损坏对话框；本工程只用 62f3c1
- `McpLog` 为 internal，项目脚本勿直接调用
