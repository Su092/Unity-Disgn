# Unity MCP vs CLI — 选用与组合

本仓库/会话常见两条自动化链路：

1. **MCP** — Cursor 的 `user-unityMCP`（连上正在跑的 Editor，工具如 `manage_scene`、`manage_gameobject`、`execute_code`、`read_console`…）
2. **CLI** — 官方 `unity` + 经典 `Unity.exe` 参数（装编辑器、CI、无头构建测试、Pipeline `unity command`）

官方 CLI 也可 `unity mcp configure` 拉起/配置 Unity 侧 MCP；与 Cursor 已装的 MCP 插件可并存，但一次对话里应选一条主路径，避免对同一场景双重写入。

---

## MCP 优点

- **低延迟交互**：Editor 已热启动，改物体/组件/材质即时生效，适合迭代关卡与调试。
- **结构化工具**：场景层级、组件属性、资源搜索等有现成 tool schema，Agent 少拼命令行。
- **强反馈环**：`read_console`、Play/Pause、截图/资源类工具便于「改→看→再改」。
- **适合 IDE 内开发**：与 Cursor 会话绑定，权限与审批流清晰。

## MCP 缺点

- **依赖 GUI/已开 Editor**：无 Editor 或 Safe Mode 时大量工具不可用。
- **难进 CI**：构建机通常无桌面会话；MCP 桥不适合作为流水线主入口。
- **多实例路由**：多开 Editor 时要 `set_active_instance`，易指错工程。
- **可复现性弱**：会话状态、域重载、编译中会导致工具瞬时失败，脚本化不如 CLI 稳定。
- **载荷体积**：层级/属性全量查询易爆 token，需分页与 summary-first。

---

## CLI 优点

- **CI/无头一等公民**：`-batchmode -nographics`、退出码、JSON/`--format json`、日志文件齐全。
- **覆盖生命周期**：装 6000.6、加模块、授权、建工程、构建、测试、VCS，一条 `unity` 搞定。
- **可脚本化、可复现**：Shell/PowerShell/YAML 流水线可版本化；退出码可编程分支。
- **Pipeline 可驱动无头 Editor**：`unity command` / `script eval` 在 batch 常驻实例上也能做场景操作。
- **与官方文档一致**：6000.6 Manual + Unity CLI 参考即真源。

## CLI 缺点

- **冷启动贵**：每次 `Unity.exe -batchmode` 导入/编译成本高（可用常驻无头或 `unity open` 缓解）。
- **交互体验弱**：没有 MCP 那种细粒度「点选物体 / 看 Game 视图」的默认工具面（除非自写 `[CliCommand]` 或 eval）。
- **经典参数冗长**：Windows 路径引号、模块名、`-quit` 与测试的坑需严格遵守。
- **Pipeline 额外依赖**：活 Editor 控制要先 `unity pipeline install`；Safe Mode 下连不上。
- **Agent 沙箱**：受限沙箱可能让 `unity status` 看不到真实 Editor。

---

## 推荐组合

| 任务 | 首选 | 备选 |
|------|------|------|
| Cursor 里摆场景、加组件、查 Console | MCP | `unity command` |
| 修编译错误后验证 | MCP `read_console` / `refresh_unity` | `unity recompile` |
| 安装 Unity 6000.6 + 模块 | CLI `unity install` | Hub GUI |
| PR/夜间构建与测试 | CLI `unity build` / `unity test` 或经典 `-build`/`-runTests` | — |
| 无显示器机器跑 Editor 逻辑 | CLI 无头常驻 + `unity command` | 经典 `-executeMethod` |
| 一次性数据烘焙/导表 | `-executeMethod` 或 `unity run --command` | MCP `execute_code`（需已开 Editor） |
| 配置 Agent 用官方 MCP | `unity mcp configure` | 手动改 MCP 配置 |

**反模式：**

- 已开 Editor 时手改 `.unity` YAML。
- CI 里只靠 MCP。
- 同一回合 MCP 与 CLI 同时改同一场景且不协调。
- batchmode 一次进程多平台切换。

**实用原则：** IDE 迭代用 MCP；流水线与工程生命周期用 CLI；需要无头可编程 Editor 时用 CLI + Pipeline。
