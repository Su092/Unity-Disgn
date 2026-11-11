# 当前快照 — 星轨防线

更新：2026-11-10

## 关联

- 枢纽：`E:\Unity Development\Project\Star Defanse\`
- Unity：`E:\Star Defanse`（`unity\` 目录联接，`mklink /J`，已被 `.gitignore` 的 `Project/*/unity/` 忽略）
- 工程远端：`git@github.com:Su092/Star-Defanse.git`，`main` @ `6ac1b07`（工作树干净）
- 编辑器：Unity **6000.6.4f1**（`D:\Unity\6000.6.4f1`）
- 渲染：内置管线 + `StarLane/ModelLit` / `StarLane/Unlit`（**未装 URP**）

## 已定约定

- **关联开发**：文档 / 拆解 / 控制 / 记忆只在枢纽；代码与资源只在 `unity/`
- 数据唯一来源 `Resources/Data/sldata.json`，文档镜像在 `docs/gameplay-spec.md`，两边必须同步改
- `Core/` 零 Unity 依赖，对局可 headless 跑；随机只用 `mulberry32` + 种子
- 场景只有一个入口节点，所有 UI 与战场靠代码构建，不手拖
- 生图统一 APIMart；地形 AI 生成、车道代码绘制
- **3D 模型走 Blender 交付门**：数值门 + 契约门，`degraded` 必须补查
- 验证只认 `check.ps1`（tests / verify / build / shots），看 `RESULT` 行与退出码

## 当前状态

- 玩法闭环完整：4 关 × 10 波、8 干员、18 词条、4 职业、5 敌人、编队 1–4 人
- 上一轮 `verify` 结论：**资源校验通过**（模型 / 动画 / 贴图 / 字体逐项 PASS）
- 上一轮 `build`：`RESULT Succeeded`，`ERRORS 0`，输出 `unity/Build/ST.exe`
- 拼装链路：`Assets/Scenes/Main.unity` 单入口 + `STSceneBuilder` 可重建
- MCP：`com.coplaydev.unity-mcp` v10.0.0，桥在 `http://127.0.0.1:8765/mcp`；
  当前**未打开编辑器**，桥不通（`mcp_bridge_check.py` 会直接失败）
- Blender 侧：Steam 版 **5.2.3 LTS** 可用；blender MCP 插件未起（`get_addon_status` 连接失败）

## 本次（2026-11-10）完成

### P0 清理与搬迁（前一阶段）

- 新建枢纽目录并建立 `unity` 联接
- 文档树落地：`docs/`、`breakdown/`、`control/`、`PROJECT.md`、`unity.path.md`
- 工程根四组过程产物移入 `tools/_archive/`（`canvas/`、`TowerDesigns/`、`UiStyleTests/`、`UiC6/`，约 87 MB）
- 8 份旧日志移入 `tools/_archive/logs/`，`.gitignore` 追加归档与缓存规则

### 3D 管线接入 blender-asset-pipeline skill（本次）

| 资产 | 位置 | 作用 |
|------|------|------|
| skill 本体 | `.cursor/skills/blender-asset-pipeline/`（单一源头） | 方法论 + `blender_gate.py` 六道数值门 |
| 交付门入口 | `E:\Unity Development\tools\blender-gate.ps1` | selftest → `.blend` 数值门 → FBX 重新导入复核 + 契约门 → manifest |
| FBX 复核 | `tools/blender_fbx_gate.py` | 清场只导 FBX 再跑数值门（换通路复核，技能铁律 B） |
| 契约门 | `tools/blender_contract.py` | 单位 / 变换 / 单根 / `GEO-` 命名 / 三角预算 / 材质贴图 / `Yaw` 骨架 / 落地 |
| 导出器 | `tools/blender_export_unity.py` | 固定 -Z/Y 轴、单位、Legacy 动画前提；`Modle_`/`Anim_` 前缀不符拒导 |
| 批量体检 | `tools/blender-audit-models.ps1` | 对存量 FBX 只跑契约门，输出 `audit.csv` |
| 规则 | `.cursor/rules/blender-asset-pipeline.mdc` | 工作区执行口径（三态、两条通路、判据边界） |
| 文档 | `docs/model-pipeline.md` | 本工程的数值 / 导出契约 / 修法速查 / 存量件现状 |

**实测结论**（Blender 5.2.3 LTS，`e13b728c6880`）：

- `blender_gate.py -- selftest` **11 / 11 passed**
- 冒烟件（带骨架塔 + 无骨架道具）走完整链路：`pass→0`、`fail→1`、`degraded→2` 三态均按预期
- 契约门分支验证：未 apply 变换 / 多根 / 缺材质 → `fail`；缺骨架未加 `--no-bone` → `degraded`
- **存量 13 个 `Modle_*` 契约门全部 pass**（三角数 22k–26k / 预算 60000）

### ★ 接入时的关键发现：分件装配体不能用单体水密门

初次把数值门直接套在存量件上，13 件**全部 fail**。逐条查证后确认是**判据不适用**，不是模型缺陷：

| 门 | `Modle_Tower_Assault` 实测 | 实际含义 |
|---|---|---|
| ① 网格健康 | `nonmanifold_edges=70` | 7 个部件贴合共边 |
| ② 法线 | `degraded` / 部分 fail | 开放壳无"整体朝向" |
| ③ 埋面 | `buried_count=1588` | 部件互相插入 |
| ④ 自交 | `pair_count=1081` | 同上 |

但这件在实机完全正常（`verify` 与 `shots` 全绿）。⇒ 数值门只适用**单体件**；
分件装配体只跑契约门，或先 Boolean UNION 成实体。已落进规则与 `docs/model-pipeline.md` §3.3。

同时修正了契约门的两处误判：导入通路的旋转/缩放是轴转换与骨骼传播的合法产物（只硬判负缩放）；
`--no-bone` 只表示"不要求 Yaw 骨骼"，不再对有骨架但不需瞄准的件判 fail。

## 验证（搬迁 + 清理后重跑，全绿）

| 任务 | 结果 |
|------|------|
| `-Task tests` | `RESULT 123/123 passed in 3600 ms` |
| `-Task verify` | `RESULT 资源校验通过`（数据 / 干员 / 关卡 / 精灵 / UI / 模型 / 动画 / 字体逐项 PASS） |
| `-Task build` | `RESULT Succeeded`，`SIZE 271718913`，`ERRORS 0`，`TIME 34.9 s` |
| `-Task shots` | `INPUT 6/6`、`MODEL 4/4`、`FACING 3/3`、`SAVE 2/2`、`FX 2/2`；`UI SLICE` 与 `UI TEXT` 全绿；20 张截图 |

## 未决 / 注意

- **存量 13 个 `Modle_*` 只有契约门结论，没有数值门结论**：它们是分件装配体且无 `.blend` 源，
  单体水密判据不适用（见 `docs/model-pipeline.md` §3.3）。要补数值门结论，得先拿到源文件或 UNION 成实体
- 存量件是已验收的运行中资源，**不要为了过门去改**——改动会让 `verify` 的动画轨道断言失效
- `tools/_gate/` 与 `tools/_gate_*/` 已 gitignore（门的运行产物不入库）；`__pycache__` 亦已忽略
- 归档导致四组工具脚本的相对路径暂时失效：`tower_cut/trim/overview` 写死 `TowerDesigns/`，
  `ui_install/ui_borders/border_measure/ui_c_compare` 写死 `UiStyleTests/`
- 87 MB 位图只是退出跟踪，Git **历史**里仍在；要彻底瘦身需 `filter-repo` 重写历史（未做）
- `Shots/` 里还留着 `_c6-*.png`、`_v1.png`、`_v2.png` 三组旧试验图（已 gitignore）
- 工程 `.gitignore` 原有中文注释是混合编码（部分 GBK 字节），只做 ASCII 追加，未重写旧行
- `Art/Sprites/` 27 张位图已废弃，仅 `STBuild.CheckSprites` 仍在校验
- 数值未做实机校准（星级阈值、`nexus` 车道、召唤/强化涨价曲线、BOSS 波可解性）
- Unity 未打开时 MCP 桥不通；用 `python unity/tools/mcp_bridge_check.py` 定位
- Blender MCP 需在 Blender 里启用插件并监听 9876；当前未起，交互式建模走 `blender-mcp` 前要先开
- `blender-gate.ps1` 尚未接进 `check.ps1`（3D 门与 Unity 资源校验是两条独立链路，暂不强行合并）
