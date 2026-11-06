# 控制：编辑器与 MCP

| 项 | 值 |
|----|-----|
| 唯一编辑器 | Unity **6000.6.4f1** |
| 安装路径 | `D:\Unity\6000.6.4f1\Editor\Unity.exe` |
| 工程版本文件 | `unity/ProjectSettings/ProjectVersion.txt` 须为 `6000.6.4f1` |
| MCP | Cursor → `http://127.0.0.1:8765/mcp` → 上述编辑器中的本工程 |
| 工程 MCP 配置 | `unity/.cursor/mcp.json` |
| 连桥脚本 | `unity/Assets/_Game/Editor/McpLocalHttpBootstrap.cs` |
| 渲染 | URP **17.6.0** |

说明：8765 为固定端口（8080 曾被占用）。若 Unity 启动改写端口，以 Bootstrap 写回的 8765 为准。
