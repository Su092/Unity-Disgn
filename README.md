# Unity Development 工作区

多游戏并行开发的总控目录。各游戏在 `Project/<游戏名>/` 下独立维护文档与拆解；Unity 工程本体可落在其它盘符，通过该游戏目录内的 `unity` 联接访问。

## 目录结构

```text
Unity Development/
├── README.md                 # 本文件：工作区总览
├── .cursor/                  # Cursor MCP / rules / skills（工作区级，skill 单一源头）
├── .codex/                   # Codex MCP 配置 + Codex 宿主的 blender skill 派生版
├── tools/                    # APIMart 凭据与素材清单（凭据与 IP 缓存已 gitignore）
├── Blender Modle/            # 建模测试项目（不绑定游戏，用于验收管线）
│   ├── medieval-street-lamp/ # 中世纪铸铁路灯：单体件，六道数值门
│   └── spiderverse-taxi/     # 纵横宇宙风：出租车 + 红色复古跑车（同场景 duo）
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
| Blender 交付门 | `tools/blender-gate.ps1` | 一条命令：门自检 → `.blend` 数值门 → FBX 重新导入复核 + 契约门 → `manifest.json`；约定见 `.cursor/rules/blender-asset-pipeline.mdc` |
| Blender 数值门（底层） | skill `blender-asset-pipeline` → `.cursor/skills/blender-asset-pipeline/scripts/blender_gate.py` | 纯 bpy（无 addon/MCP）；网格健康/逐壳法线/埋面/自交/壁厚/尺寸六道门，三态 verdict；先跑 `-- selftest`（11/11） |
| Blender 契约门 | `tools/blender_contract.py` | 数值门管不到的导入契约：单位、变换 apply、单根、`GEO-` 命名、三角预算、材质贴图、**UV 层可用**、`Yaw` 骨架、落地基准 |
| buried 真判据门 | `tools/blender_buried_true.py` | 复核埋面：闭合单壳按定理判 0，多壳做壳间包含检测；自带 3 例 selftest。`blender-gate.ps1` 已把 `buried` 一项改由它裁定 |
| UV 可用性门 | `tools/blender_uv_gate.py` | 回答"UV 展开能不能用"：岛间重叠 0 / UV 在 [0,1]² / 覆盖率 / texel 密度比；自带 6 例 selftest。`blender-gate.ps1 -UvUnwrap` 启用 |
| FBX 导出 | `tools/blender_export_unity.py` | 固定 Unity 侧读取的轴（-Z/Y）、单位、Legacy 动画前提；前缀不符拒导 |
| 存量模型体检 | `tools/blender-audit-models.ps1` | 对已有 FBX 批量跑契约门（分件装配体不适用单体水密门） |
| MCP · blender | `.cursor/mcp.json` → `uvx blender-mcp` | 需 Blender 开启对应插件并监听 9876 |
| MCP · unityMCP | `.cursor/mcp.json` → `http://127.0.0.1:8765/mcp` | 需 Unity 编辑器打开工程并启动 MCP 桥 |

skill 只有**单一源头** `.cursor/skills/`（2026-11 已删除 `.agents/skills` 与根 `apimart-image/` 两处副本，不要再建）。`.codex/skills/blender-asset-pipeline/` 是 Codex 宿主的**派生改写版**，带 `ADAPTATION.md`，内容有意不同，**不要同步**。MCP 配置仍是两份：`.cursor/mcp.json` 与 `.codex/config.toml`，改一处要同步另一处。

Blender 版本速查：Steam 版 `E:\SteamLibrary\steamapps\common\Blender\blender.exe`（**5.2.3 LTS**）；另有便携版 `E:\toyxyz_RGBMocap\runtime_character\blender.exe`（4.5.0）。`blender-asset-pipeline` 在 5.2.3 上实测校准，`blender-gate.ps1` 优先用 5.2.3 并自动探测。

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
- **分件装配体不适用单体水密门**：`nonmanifold` / `buried` / `selfint` 对多件拼装天然非 0，
  那是装配语义不是缺陷。这类件只跑契约门（`-ContractOnly`）；数值门留给单体件。
- **`buried` 是启发式，凹腔件必假阳性**：它的口径是"沿外法线打射线命中别的面"，把"屋顶挡住托盘顶面"
  也算埋住。**闭合流形单壳在数学上不可能有内部面**，所以这类网格的 `buried>0` 恒是遮挡。
  判决权交给 `tools/blender_buried_true.py`（已接进门自检与判决）。
- **贴图节点 ≠ 贴图可用**：有 `TEX_IMAGE` 却没有 UV 层时，采样固定在一个纹素上，渲染成一片死色。
  契约门现在硬判 UV 层存在且未退化。
- **UV 层存在 ≠ UV 展开可用**：箱式三平面投影的 UV 层存在、不退化，但 6 套投影叠在同一 UV 空间，
  只能配无缝平铺贴图"看着没事"，烘焙 / AO / 光照贴图全废。`-UvUnwrap` 启用 `tools/blender_uv_gate.py`
  判是否真的可用（岛间不重叠、在 [0,1]²、密度一致）。
- **Boolean `TRANSFER` 会搬进空材质槽**：apply 后网格出现 `None` 槽，Unity 多出 submesh。
  建模侧 apply 完要清槽重建；契约门硬判"材质槽无空槽/重复/越界"。
- 手改 `tools/*.ps1` 后**必须确认文件是 UTF-8 with BOM**：无 BOM 时 PowerShell 5.1 按 GBK 解码，
  中文字符串会把引号对齐搞乱，报 `Unexpected token ')'` 且行号指向无关位置。
- 读图分级：L0 数值每轮都看；L1 轮廓叠合只在阶段门；L2 小裁切仅当 L0 出 FAIL；L3 beauty 只给人看。
- 每轮读图 ≤6 张、每张 ≤800×450（一张 1600×900 ≈ 25 张 240×240 的成本）。

各游戏的具体口径见该游戏 `docs/model-pipeline.md`。

## 已注册游戏

| 游戏 | 枢纽目录 | Unity 工程 |
|------|----------|------------|
| 云端王国 (Kingdom Of Cloud) | `Project/Kingdom Of Cloud/` | `D:\Kingdom Of Cloud`（联接为 `Project/Kingdom Of Cloud/unity`） |
| 星轨防线 (Star Defanse) | `Project/Star Defanse/` | `E:\Star Defanse`（联接为 `Project/Star Defanse/unity`） |

编辑器目标族：**Unity 6000.6.x**（以各游戏 `PROJECT.md` 为准）。
