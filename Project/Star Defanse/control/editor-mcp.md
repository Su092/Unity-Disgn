# 控制：编辑器与 MCP

| 项 | 值 |
|----|-----|
| 唯一编辑器 | Unity **6000.6.4f1** |
| 安装路径 | `D:\Unity\6000.6.4f1\Editor\Unity.exe` |
| 工程版本文件 | `unity/ProjectSettings/ProjectVersion.txt` 须为 `6000.6.4f1` |
| MCP 包 | `com.coplaydev.unity-mcp` **v10.0.0**（`unity/Packages/manifest.json`，Git URL） |
| 传输 | Streamable HTTP：`http://127.0.0.1:8765/mcp` |
| Cursor 侧配置 | 工作区 `.cursor/mcp.json` → `mcpServers.unityMCP` |
| 链路自检 | `python unity/tools/mcp_bridge_check.py`（依次调 `read_console` / `manage_scene` / `find_gameobjects`，通过 ≥2 项算通） |

## 使用前提

1. 工程在 Unity 里**已打开**，且 MCP 桥已起（编辑器菜单里的 MCP 面板可见）。
2. Cursor 已加载工作区 MCP 配置；改过 `.cursor/mcp.json` 必须重载会话才生效。
3. 桥不通时 `python unity/tools/mcp_bridge_check.py` 会直接报连接失败 —— 先用它定位，
   不要靠猜测改端口或换传输方式（stdio 模式发现不到 Unity 实例，这是踩过的坑）。

## 优先顺序

1. **优先 Unity MCP**：读 Console、查 GameObject、改组件字段、进 Play 观察。
2. **MCP 不可用**：给逐步手动步骤（菜单 / 物体名 / Inspector 字段 / 保存路径 / 验收）。
3. **不写 [MenuItem] / EditorWindow 当搭建手段**：只有自检、校验、打包这类批量入口才允许编辑器脚本
   （现有 `Editor/` 全部属于这一类）。

## 批处理入口（无 GUI 也跑得动）

| 方法 | 作用 |
|------|------|
| `StarLane.EditorTools.STSetup.RunSimTests` | 逻辑自检（headless，123 项断言） |
| `StarLane.EditorTools.STBuild.VerifyResources` | 资源校验 + 写九宫格边距 |
| `StarLane.EditorTools.STBuild.BuildPlayer` | 打包 Windows 播放器到 `Build/ST.exe` |
| `StarLane.EditorTools.STSceneBuilder` | 重建 `Main.unity` 与竖屏工程设置 |
| `StarLane.EditorTools.STShaderSetup` | 写入 Always Included Shaders（幂等） |

调用方式：

```powershell
& "D:\Unity\6000.6.4f1\Editor\Unity.exe" -batchmode -quit -nographics `
  -projectPath "E:\Star Defanse" -logFile "E:\Star Defanse\unity_verify.log" `
  -executeMethod StarLane.EditorTools.STBuild.VerifyResources
```

## 失败时的步骤格式

```text
目标：
前置：编辑器版本 / 打开的场景 / 需要的资源
步骤：
1. 菜单或 Hierarchy 操作
2. Inspector 字段 = 具体值
3. 保存路径
验收：进 Play 后应看到什么
```
