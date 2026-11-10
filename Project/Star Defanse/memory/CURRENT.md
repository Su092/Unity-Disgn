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
- 验证只认 `check.ps1`（tests / verify / build / shots），看 `RESULT` 行与退出码

## 当前状态

- 玩法闭环完整：4 关 × 10 波、8 干员、18 词条、4 职业、5 敌人、编队 1–4 人
- 上一轮 `verify` 结论：**资源校验通过**（模型 / 动画 / 贴图 / 字体逐项 PASS）
- 上一轮 `build`：`RESULT Succeeded`，`ERRORS 0`，输出 `unity/Build/ST.exe`（见下方「验证」）
- 拼装链路：`Assets/Scenes/Main.unity` 单入口 + `STSceneBuilder` 可重建
- MCP：`com.coplaydev.unity-mcp` v10.0.0，桥在 `http://127.0.0.1:8765/mcp`；
  当前**未打开编辑器**，桥不通（`mcp_bridge_check.py` 会直接失败）

## 本次（2026-11-10）完成

- 新建枢纽目录并建立 `unity` 联接（`Project/Star Defanse/unity` → `E:\Star Defanse`）
- 文档树落地：`docs/`（6 篇）、`breakdown/`（盘点）、`control/`（3 篇）、`PROJECT.md`、`unity.path.md`
- 注册到工作区 `README.md`、`Project/README.md`、`.cursor/rules/multi-project-workspace.mdc`
- 工程侧同步改动（**未提交**，在 `Star-Defanse` 仓库工作树里）：
  - `Docs/ART-STYLE.md` 删除，内容迁入枢纽 `docs/art-style.md`
  - `README.md` 改两处：URP 兼容管线 → 内置管线；视觉规范链接改为指向枢纽
  - `tools/make_plate_thin.py` 注释里的文档路径改为枢纽
  - 该仓库 `git status`：`D Docs/ART-STYLE.md`、`M README.md`、`M tools/make_plate_thin.py`、`M .gitignore`、另有 70 个 `D`（见下）

## 清理（P0-3 / P0-4，2026-11-10）

- 工程根四组过程产物移入 `tools/_archive/`：`canvas/`、`TowerDesigns/`(42 文件 37 MB)、
  `UiStyleTests/`(25 文件 48 MB)、`UiC6/`(2 文件 2 MB)，并从 Git 跟踪移除（共 70 个文件，约 87 MB）
- 8 份旧日志移入 `tools/_archive/logs/`
- `.gitignore` 追加：`/tools/_archive/`、`/TowerDesigns/`、`/UiStyleTests/`、`/UiC6/`、`__pycache__/`、`*.pyc`
- 文件**未删除**，仍在磁盘；还原方式与脚本依赖写在 `docs/asset-pipeline.md` 的「关于 tools/_archive/」
- 工程根现在只剩 `.cursor/ Assets/ Build/ Library/ Logs/ Packages/ ProjectSettings/ scripts/ Shots/ tools/ UserSettings/ .gitignore icon.png README.md`

## 验证（2026-11-10 搬迁 + 清理后重跑，全绿）

| 任务 | 结果 |
|------|------|
| `-Task tests` | `RESULT 123/123 passed in 3600 ms` |
| `-Task verify` | `RESULT 资源校验通过`（数据 / 干员 / 关卡 / 精灵 / UI / 模型 / 动画 / 字体逐项 PASS） |
| `-Task build` | `RESULT Succeeded`，`SIZE 271718913`，`ERRORS 0`，`TIME 34.9 s`；OUTPUT = `E:/Unity Development/Project/Star Defanse/unity/Build/ST.exe`（新路径，旧日志的 `E:/omg test` 问题已消除） |
| `-Task shots` | `INPUT 6/6`、`MODEL 4/4`、`FACING 3/3`、`SAVE 2/2`、`FX 2/2`；`UI SLICE` 4/4·6/6·10/10·6/6·6/6·10/10、`UI TEXT` 6/6·25/25·65/65·9/9·10/10·30/30 全绿；20 张截图写入 `Shots/` |

## 未决 / 注意

- 工程侧改动尚未在 `Star-Defanse` 仓库提交（含 70 个删除，提交后仓库体积不再包含这 87 MB 位图）
- 归档导致四组工具脚本的相对路径暂时失效：`tower_cut/trim/overview` 写死 `TowerDesigns/`，
  `ui_install/ui_borders/border_measure/ui_c_compare` 写死 `UiStyleTests/`；要重跑先把目录移回或用清单重新生成
- `Shots/` 里还留着 `_c6-*.png`、`_v1.png`、`_v2.png` 三组旧试验图（已 gitignore，不影响出包）
- `Art/Sprites/` 27 张位图已废弃，仅 `STBuild.CheckSprites` 仍在校验
- 数值未做实机校准（星级阈值、`nexus` 车道、召唤/强化涨价曲线、BOSS 波可解性）
- Unity 未打开时 MCP 桥不通；用 `python unity/tools/mcp_bridge_check.py` 定位
