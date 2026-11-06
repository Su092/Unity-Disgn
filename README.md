# Unity Development 工作区

多游戏并行开发的总控目录。各游戏在 `Project/<游戏名>/` 下独立维护文档与拆解；Unity 工程本体可落在其它盘符，通过该游戏目录内的 `unity` 联接访问。

## 目录结构

```text
Unity Development/
├── README.md                 # 本文件：工作区总览
├── .cursor/                  # Cursor MCP / rules / skills（工作区级）
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

## 已注册游戏

| 游戏 | 枢纽目录 | Unity 工程 |
|------|----------|------------|
| 云端王国 (Kingdom Of Cloud) | `Project/Kingdom Of Cloud/` | `D:\Kingdom Of Cloud`（联接为 `Project/Kingdom Of Cloud/unity`） |

编辑器目标族：**Unity 6000.6.x**（以各游戏 `PROJECT.md` 为准）。
