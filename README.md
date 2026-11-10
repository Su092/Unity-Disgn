# Unity Development 工作区

多游戏并行开发的总控目录。各游戏在 `Project/<游戏名>/` 下独立维护文档与拆解；Unity 工程本体可落在其它盘符，通过该游戏目录内的 `unity` 联接访问。

## 目录结构

```text
Unity Development/
├── README.md                 # 本文件：工作区总览
├── .cursor/                  # Cursor MCP / rules / skills（工作区级）
├── .agents/                  # Codex 侧 skills（内容与 .cursor/skills 对应）
├── .codex/                   # Codex MCP 配置
├── tools/                    # APIMart 凭据与素材清单（凭据与 IP 缓存已 gitignore）
├── apimart-image/            # apimart skill 的独立副本（与 .cursor/skills 同内容）
└── Project/
    ├── README.md             # 游戏注册表与新建规范
    └── <GameName>/           # 单一游戏的文档与开发枢纽（互不共享）
        ├── PROJECT.md        # 绑定、编辑器、状态、入口
        ├── docs/             # 项目文档（概念 / 设计 / 规格）
        ├── breakdown/        # 开发内容拆解与任务切片
        ├── control/          # 长期操作规范（MCP、目录约定等）
        ├── memory/           # 进度快照与阶段记忆
        └── unity/            # 目录联接 → 真实 Unity 工程根
```

## 工作流（固定顺序）

1. **项目文档** → 写在 `Project/<Game>/docs/`
2. **开发拆解** → 写在 `Project/<Game>/breakdown/`
3. **按文档实现** → 只在该游戏的 `unity/`（真实工程）与本游戏文档目录内改动

## 隔离原则

- 一次会话只服务一个 `Project/<Game>/`；禁止跨游戏改 Assets / 文档 / 配置。
- 工作区级 `.cursor/skills`、MCP 配置可共用；各游戏的规则与记忆互不覆盖。
- 新游戏只在 `Project/` 下新增同级目录，不改既有游戏目录。

## 工作区工具

| 工具 | 入口 | 说明 |
|------|------|------|
| APIMart 生图 | skill `apimart-image` → `.cursor/skills/apimart-image/scripts/apimart_image.py` | 只用 Python 标准库；`gpt-image-2`；约定见 `.cursor/rules/apimart-image.mdc` |
| Unity CLI 工作流 | skill `unity-6000-cli` | 6000.6 的 `unity` CLI、batchmode、`-executeMethod` 与 MCP 取舍 |
| MCP · blender | `.cursor/mcp.json` → `uvx blender-mcp` | 需 Blender 开启对应插件并监听 9876 |
| MCP · unityMCP | `.cursor/mcp.json` → `http://127.0.0.1:8765/mcp` | 需 Unity 编辑器打开工程并启动 MCP 桥 |

新增/修改 skill 时，`.cursor/skills`、`.agents/skills` 与根 `apimart-image/` 三处副本要一起更新（MCP 配置同理：`.cursor/mcp.json` 与 `.codex/config.toml`）。

## 已注册游戏

| 游戏 | 枢纽目录 | Unity 工程 |
|------|----------|------------|
| 云端王国 (Kingdom Of Cloud) | `Project/Kingdom Of Cloud/` | `D:\Kingdom Of Cloud`（联接为 `Project/Kingdom Of Cloud/unity`） |
| 星轨防线 (Star Defanse) | `Project/Star Defanse/` | `E:\Star Defanse`（联接为 `Project/Star Defanse/unity`） |

编辑器目标族：**Unity 6000.6.x**（以各游戏 `PROJECT.md` 为准）。
