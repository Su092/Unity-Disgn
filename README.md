# Unity Development 工作区

多游戏并行开发的总控目录（**枢纽**）。各游戏在 `Project/<游戏名>/` 下独立维护文档、拆解与记忆；Unity 工程本体落在其它目录，通过该游戏目录内的 `unity` 联接访问。

## 三层结构

| 层 | 位置 | 是否入库 | 内容 |
|----|------|----------|------|
| L1 枢纽 | `<HUB>` | 本仓库 | 规则、技能、智能体注册、文档、记忆、跨游戏工具链 |
| L2 游戏工程 | `<GAME:id>`（各游戏独立仓库） | 各自仓库 | 代码、资源、场景、工程设置、工程级验证脚本 |
| L3 机器绑定 | `machine/profile.local.json` | **不入库** | 本机真实路径、联接、编辑器与 Blender 位置 |

L3 是跨终端的关键：换机时只改这一份文件，再跑 `bootstrap.ps1` 与 `doctor.ps1`。

## 路径记号（文档与脚本统一口径）

**文档里禁止写裸盘符。** 统一用下列记号，由 `machine/profile.ps1` 的 `Expand-HubToken` 展开：

| 记号 | 含义 |
|------|------|
| `<HUB>` | 枢纽根 |
| `<GAME:id>` | 某游戏的真实 Unity 工程根（id 用 `Project/` 下的目录名，含空格照写） |
| `<UNITY:6000.6.4f1>` | 指定版本编辑器可执行文件 |
| `<BLENDER>` | Blender 可执行文件 |

唯一允许出现绝对路径的地方是 `machine/profile.local.json`（已 gitignore）与 `machine/profile.example.json`（模板）。

## 换机三步

**完整步骤（含克隆、依赖、验收判据、已知坑）见 `docs/跨终端部署.md`。** 以下是速查：

```powershell
# 1. 复制模板并填写本机路径
Copy-Item "<HUB>\machine\profile.example.json" "<HUB>\machine\profile.local.json"

# 2. 装配（幂等，可反复跑；指向错误的联接需加 -Force）
powershell -ExecutionPolicy Bypass -File "<HUB>\machine\bootstrap.ps1"

# 3. 自检：pass(0) / fail(1) / degraded(2)
powershell -ExecutionPolicy Bypass -File "<HUB>\machine\doctor.ps1"
```

判据：`doctor.ps1` 输出 `RESULT: pass`，退出码 0。`degraded` 表示没有硬错误但有缺口（如缺 .NET SDK），必须补查，不许当通过。

## 目录结构

```text
<HUB>/
├── README.md                 # 本文件：总览与口径
├── .cursor/                  # rules / skills / mcp.json（skill 单一源头）
├── .codex/                   # Codex 宿主：config.toml + blender skill 派生版
├── machine/                  # 机器绑定层（profile + bootstrap + doctor）
├── tools/                    # 跨游戏工具链（3D 交付门、生图清单）
├── Blender Modle/            # 建模测试项目（不绑定游戏，用于验收管线）
└── Project/
    ├── README.md             # 游戏注册表与新建规范
    └── <GameName>/           # 单一游戏的开发枢纽（互不共享）
        ├── PROJECT.md        # 绑定、编辑器、状态、入口
        ├── docs/             # 项目文档
        ├── breakdown/        # 开发拆解与任务切片
        ├── control/          # 长期操作规范
        ├── memory/           # 进度快照与阶段记忆
        └── unity/            # 目录联接 → <GAME:GameName>
```

## 工作流（固定顺序）

1. **项目文档** → 写在 `Project/<Game>/docs/`
2. **开发拆解** → 写在 `Project/<Game>/breakdown/`
3. **按文档实现** → 只在该游戏的 `unity/`（真实工程）与本游戏文档目录内改动
4. **更新记忆** → `Project/<Game>/memory/CURRENT.md`

## 隔离原则

- 一次会话只服务一个 `Project/<Game>/`；禁止跨游戏改 Assets / 文档 / 配置。
- 工作区级 `.cursor/skills`、MCP 配置可共用；各游戏的规则与记忆互不覆盖。
- 新游戏只在 `Project/` 下新增同级目录，不改既有游戏目录。
- 文档里写逻辑路径（`<HUB>/...`、`<GAME:id>/...`）；只有排查真实落位时才看 `profile.local.json`。

## 工作区工具

| 工具 | 入口 | 说明 |
|------|------|------|
| **换机部署** | `docs/跨终端部署.md` | **新机器从零跑起来，按此文件顺序执行即可** |
| 环境自检 | `machine/doctor.ps1` | 八项三态判决；换机与每日开工前先跑 |
| 环境装配 | `machine/bootstrap.ps1` | 幂等建联接、按 profile 生成两份 MCP 配置 |
| APIMart 生图 | skill `apimart-image` → `.cursor/skills/apimart-image/scripts/apimart_image.py` | 只用 Python 标准库；`gpt-image-2`；约定见 `.cursor/rules/apimart-image.mdc` |
| Unity CLI 工作流 | skill `unity-6000-cli` | 6000.6 的 `unity` CLI、batchmode、`-executeMethod` 与 MCP 取舍 |
| Blender 交付门 | `tools/blender-gate.ps1` | 一条命令：门自检 → `.blend` 数值门 → FBX 重新导入复核 + 契约门 → `manifest.json` |
| Blender 数值门（底层） | skill `blender-asset-pipeline` → `.cursor/skills/blender-asset-pipeline/scripts/blender_gate.py` | 纯 bpy（无 addon/MCP）；网格健康/逐壳法线/埋面/自交/壁厚/尺寸六道门 |
| Blender 契约门 | `tools/blender_contract.py` | 导入契约：单位、变换 apply、单根、`GEO-` 命名、三角预算、材质贴图、UV 层、`Yaw` 骨架、落地基准 |
| buried 真判据门 | `tools/blender_buried_true.py` | 复核埋面：闭合单壳按定理判 0，多壳做壳间包含检测 |
| UV 可用性门 | `tools/blender_uv_gate.py` | 岛间重叠 0 / UV 在 [0,1]² / 覆盖率 / texel 密度比 |
| FBX 导出 | `tools/blender_export_unity.py` | 固定 Unity 侧读取的轴（-Z/Y）、单位、Legacy 动画前提 |
| 存量模型体检 | `tools/blender-audit-models.ps1` | 对已有 FBX 批量跑契约门 |
| MCP · blender | `machine` 生成的 `.cursor/mcp.json` → `uvx blender-mcp` | 需 Blender 开启对应插件并监听 9876 |
| MCP · unityMCP | `machine` 生成的 `.cursor/mcp.json` → `http://127.0.0.1:8765/mcp` | 需 Unity 编辑器打开工程并启动 MCP 桥 |

工具路径一律从 `machine/profile.local.json` 读取，不在脚本里写默认盘符。

## 智能体工作区

| 宿主 | 配置位置 | 说明 |
|------|----------|------|
| Cursor | `.cursor/rules/*.mdc`、`.cursor/skills/` | 规则与技能的主要载体 |
| Codex | `.codex/config.toml`、`.codex/skills/` | `blender-asset-pipeline` 是**派生改写版**，带 `ADAPTATION.md`，内容有意不同，**不要同步** |

- **skill 只有单一源头**：`.cursor/skills/`。不要再建 `.agents/skills/` 或根级副本；`doctor.ps1` 会检查越界 `SKILL.md`。
- **MCP 配置两份**：`.cursor/mcp.json` 与 `.codex/config.toml`，均由 `bootstrap.ps1` 按 profile 生成，不手工维护；`doctor.ps1` 校验两者与 profile 一致。

## 3D 建模流程（固定顺序）

```text
① 量参考图 → spec（mm，冻结）      ② blockout → 尺寸门
③ 粗形→精修（每步看数）            ④ 修改器栈：按目标排序，不靠背
⑤ 清理/修法线（recalc + 复检）      ⑥ 装配：交叠量按 spec，白名单化
⑦ 渲染验证（同机位对照 + 逐帧取景）  ⑧ 交付：tools\blender-gate.ps1 全门 pass
```

关键纪律：

- **先 `selftest` 11/11，再看模型**；门坏了时任何"干净"结论都不成立。
- **三态**：`pass / fail / degraded`。`degraded` 是「没查完」，必须补查；脚本退出码 `2` 必须让流程变红。
- **两条通路**：`.blend` 是构建通路，导出的 FBX 必须**重新导入后再跑一遍**，否则等于没验交付。
- 数值门查几何质量，`blender_contract.py` 查导入契约（单位/apply/单根/命名/预算/材质/骨架/落地）。
- **分件装配体不适用单体水密门**：`nonmanifold` / `buried` / `selfint` 对多件拼装天然非 0，那是装配语义不是缺陷。这类件只跑契约门（`-ContractOnly`）。
- **`buried` 是启发式，凹腔件必假阳性**：闭合流形单壳在数学上不可能有内部面，所以这类网格的 `buried>0` 恒是遮挡。判决权交给 `tools/blender_buried_true.py`。
- **贴图节点 ≠ 贴图可用**：有 `TEX_IMAGE` 却没有 UV 层时采样固定在一个纹素上，渲染成一片死色。契约门硬判 UV 层存在且未退化。
- **UV 层存在 ≠ UV 展开可用**：`-UvUnwrap` 启用 `tools/blender_uv_gate.py` 判是否真的可用。
- **Boolean `TRANSFER` 会搬进空材质槽**：apply 后要清槽重建；契约门硬判材质槽无空槽/重复/越界。
- 手改 `tools/*.ps1` 后**必须确认文件是 UTF-8 with BOM**：无 BOM 时 PowerShell 5.1 按 GBK 解码，中文会报 `Unexpected token ')'` 且行号指向无关位置。
- 读图分级：L0 数值每轮都看；L1 轮廓叠合只在阶段门；L2 小裁切仅当 L0 出 FAIL；L3 beauty 只给人看。
- 每轮读图 ≤6 张、每张 ≤800×450。

各游戏的具体口径见该游戏 `docs/model-pipeline.md`。

## 已注册游戏

| 游戏 | 枢纽目录 | 真实工程（profile 键） |
|------|----------|------------------------|
| 云端王国 (Kingdom Of Cloud) | `Project/Kingdom Of Cloud/` | `Kingdom Of Cloud` |
| 星轨防线 (Star Defanse) | `Project/Star Defanse/` | `Star Defanse` |
| S (ProjectS) | `Project/S/` | `S` |

真实工程路径与编辑器位置见 `machine/profile.local.json`。编辑器目标族：**Unity 6000.6.x**（以各游戏 `PROJECT.md` 为准）。
