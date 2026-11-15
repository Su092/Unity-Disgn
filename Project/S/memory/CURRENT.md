# 当前快照 — S

更新：2026-11-15（深夜 · 对齐 MODCORE 原型）

## 关联

- 枢纽：`<HUB>\Project\S\`
- Unity：`<GAME:S>`（`unity\` 为其目录联接）
- 编辑器：Unity **6000.6.4f1**（`<UNITY:6000.6.4f1>`）
- 渲染：**URP 17.6**（`PC_RPAsset`）
- 输入：**仅新 Input System**（`activeInputHandler = 1`）
- 工程远端：`git@github.com:Su092/Project-S.git`（`main`，唯一提交 `012dbfb`）

## 已定约定

- 文档 / 拆解 / 控制 / 记忆只在枢纽；代码与资源只在 `unity/`
- 数据唯一来源 `Assets/Resources/Data/sdata.json`，人读镜像在 `docs/loadout-spec.md` 与 `docs/gameplay-spec.md`
- `Core/` 零 Unity 依赖（`SDataLoader.cs` 是唯一桥），结算可在 dotnet 下断言
- 场景只有一个 `S` 节点，所有对象与 UI 由代码构建
- 材质一律走 `SMat`，不用裸 `new Material(Shader.Find(...))`
- 验证只认 `check.ps1`（tests / setup / assets / ui / build / smoke / shots）

## 当前状态

**已对齐 MODCORE Web 原型：读取式链 + 7 种作用域 + 6 把枪 + 39 个配件，全链验证通过。**

> 下表为本机 2026-11-15 深夜实测（Unity 自带 .NET 8 SDK）。
| 项 | 结果 |
|----|------|
| 逻辑断言（dotnet） | **106/106 passed** |
| Unity 编译 | 0 errors |
| 打包 | `build Succeeded (0 errors)` |
| 实机自检 | **94/94 passed**（11 张截图） |
| 配件图标 | **39/39 加载** |
| 材质池 | 基线 5 → 战斗后 5（零增长） |

## 本轮改造：结算引擎重写（MODCORE 对齐）

详见 `../breakdown/11-modcore-alignment.md`。**这是继单图改造之后第二次推翻核心规则。**

| 维度 | 改前（自研链式触发） | 改后（原型读取式扫描） |
|------|----------------------|------------------------|
| 一格内容 | 一条可叠多件的「链」 | **一件** |
| 触发方式 | 按链顺序在时间轴上逐项兑现 | **一次性扫描解析出全部投射物** |
| 作用域 | 3 种 | **7 种**（Next/Prev/Adj/N2/N3/P2/All） |
| 枪械 | 3 把 | **6 把**（槽位 6–12，读取 1–2） |
| 配件 | 25 件 | **39 件**（17 子弹 + 22 衍生） |
| 弹道形态 | 直线 + 抛射 | **7 种**（含 Beam/Mine/Field/Chain/Saw/Hole） |
| 触发弹 | 无 | **命中 / 定时 / 消散** 三种载荷 |
| 分解 | 无 | 普通 3 / 稀有 6 / 史诗 9 经验 |
| 精英 / Boss | 4:00 / 8:00 | **5:00 / 10:00**（原型口径） |

已删：`View/ChainCast.cs`（按时间逐项触发的执行器，新模型不需要）。
新增：`Core/Loadout.cs` 全重写、`View/Projectile.cs` 七形态、`tools/add_modcore_icons.py`。

## 背包详情区（`#inv-detail` 对齐）

`View/ItemDetailPanel.cs`（新）：背包右下角的**常驻详情区**。

| 状态 | 内容 |
|------|------|
| 空态 | 「—」+「把鼠标移到配件上查看详情」 |
| 悬停配件 | 图标（带稀有度色环）+ 名称 + 稀有度/类别 + 作用域色条 + 完整数值 + 用法提示 |
| 拖拽到槽位 | **落点预览**：本次期望 `前 → 后（±）`、耗弹变化、生效目标数 |
| 落点为无目标 | 红字「没有作用目标，效果会全部落空」 |

落点预览在槽位副本上真跑 `ResolveGun` + `ResolveCast`，不是估算 ——
读取式链的产出取决于扫描顺序与作用域吸附，纸面加法算不出来。

与浮动提示 `ItemTooltip` 的分工：背包用常驻区（可对比、不挡格子），
HUD 链条与三选一用浮动提示（无常驻区域）。两者数值文案同源。

## 素材：39 个配件图标（APIMart 全量重生成）
旧 25 个 id 全部作废（`b_slug` / `m_dmg_up` 等）。新图标流水线三段：

```
preprocess_ui_assets.py   → 抠图 + 归一化 + 质量门（56/56）
gen_ui_assets_ai.py       → AI 线稿 + 几何圆底 + 双层圆环（62/62）
SUiTextureReimport        → 写进 .meta 的 9-slice 与 sprite 设置
```

`ITEM_IDS`（preprocess）与 `ITEM_ICONS`（gen）两处清单必须同为 39 项，否则自检点名缺件。

## 顺带修掉的真实缺陷（本轮 13 条）

见 `breakdown/11-modcore-alignment.md` 表。最值得记的三条：

1. **爆炸伤害没进期望值** → 榴弹 DPS 显示 11.7 被判成废枪。基准的意义就在这：
   纸面公式漏一项，实机就会「感觉这把枪没用」却查不出原因。
2. **命中率模拟把抛射物当直线** → 榴弹命中率 0%。这是**测量方法**的错，
   差点导致去改一个本来就正常的数值。
3. **三选一取现成子节点** → 永远 0 张卡。预制体只提供 `CardTemplate`，必须克隆。

## 数值校准（首轮，2026-11-12）

> 单图改造后经验预算已重算（见 `docs/calibration-log.md` 末尾），但 **DPS 数值未动**。

`-bench` 基准入口，用**蒙特卡洛弹道模拟**而非纸面公式：

| 项 | 校准前 | 校准后 |
|----|--------|--------|
| 三枪单体极差（裸弹/浅/深） | 2.25× / 2.25× / 2.04× | **1.21× / 1.21× / 1.26×** |
| 经验曲线 | 未实测 | **LV 14，16 次三选一**（落在 12–15 设计区间） |
| 散射代价 | 未验证 | 裸弹 100% → 分裂霰粒 **22.1%** 命中 |

关键改动：榴弹 `damageMul` 2.6→3.9、射速 0.62→0.52；单发 3.6→5.4、0.78→0.62；
`m_blast` 从「+1.6/×1.25」降到「+1.4/×1.00」（否则单发枪群伤反超榴弹枪）。

详情见 `docs/calibration-log.md`。

## 表现层（本轮新增）

- **材质池**：`SMat` 按 (shader,颜色,smoothness) 共享缓存；改色一律走 `MaterialPropertyBlock`
- **程序化音效**：`SfxBank` 合成 14 个 clip、16 音源池、类别限流、音高 ±8% 随机
  - 枪械三轨随配件变化：弹速→音高、存在时间→尾音、分裂→追加副本、溅射→叠低频
- **后处理**：`SPostFx` 代码建 Volume（Bloom / Vignette / 冷阴影暖高光），不做景深

## 美术资产

**3D（12 件低模 ≤1056 面）**
- 5 敌人/Boss + 3 枪械 + 4 场景道具
- 4 张 2k 平铺贴图
- 12 张 1k 参考图（仅建模对照，在 `_Inbox/art-refs/`，**已入库**）
- 管线：`tools/blender_s_build_assets.py`（建模 + 双门）、`tools/blender_s_preview.py`（出图在 `_Inbox/art-preview/`）

**UI（11 张素材）**
- 面板 / 卡框 / 条槽 / 横幅 / 暗角 / 准星 / 键位 + 4 个作用域图标
- 加色材质 `mat_ui_additive` + `S/UiAdditive` shader
- 9-slice 边距由 `Editor/SUiSpriteSetup.cs` 写入并硬校验
- 流水线原料在 `_Inbox/{ui-ai-raw,ui-ai-src}/`（**已入库**），成品落 `Assets/Resources/UI/`

**核心取舍**：素材当边框（质感），代码内部底（对比）。因为素材实测平均亮度仅 0.015–0.03。

## 已完成

### 文档（全量）

| 文件 | 内容 |
|------|------|
| `docs/00-overview.md` | 索引、书写约定、术语表 |
| `docs/concept.md` | 定位、设计支点、核心循环、四个决策、范围 |
| `docs/loadout-spec.md` | **核心**：链结构、轮转、结算算法、作用域、24 条算例 |
| `docs/gameplay-spec.md` | 玩家、箱庭 6 区域、5 敌人、Boss 三阶段、威胁、经验曲线、HUD |
| `docs/art-style.md` | 低多边形工业科幻：配色、材质、UI、特效、素材规格 |
| `docs/audio-spec.md` | 频段分配、枪械三轨、优先级、音乐分层 |
| `docs/technical-design.md` | 分层、数据流、确定性、性能、约定、技术债、自检 |
| `docs/data-schema.md` | `sdata.json` 全字段契约与校验清单 |

### 代码（`unity/Assets/_Game/`）

| 层 | 文件 |
|----|------|
| Core（12） | `SJson` `LoadoutTypes` `Loadout` `GunRuntime` `RunState` `ZoneProgress` `BossState` `MetaProgress` `MusicMix` `Splash` `SData` `SDataLoader` |
| View（43） | 场景 `GameRoot` `ZoneBuilder` `ZoneGate` `Pillar` `BossView` `SpikeTelegraph`；玩家 `PlayerController` `PlayerWeapons` `Projectile` `Enemy` `EnemyBullet` `ChainCast`；UI `HudView` `HudRefs` `InventoryView` `InvRefs` `MenuView` `MenuRefs` `MenuRowRefs` `GunTabRefs` `ChainRowRefs` `CardRefs` `OfferRefs` `OfferCardRefs` `UiKit` `UiPrefab` `UiAssets` `ItemIconView` `ItemTooltip` `ItemHover` `DraggableItem` `SlotDropTarget` `ButtonHover`；表现 `SMat` `SAssets` `SfxBank` `SPostFx` `AudioMix` `MusicDirector` `RunTelemetry` `InputDeviceGuard` `MetaSave` `AutoPilot` |
| App（5） | `Bootstrap` `SelfCheck` `SmokeTest` `AutoPlay` `MouseDiag` |
| Editor（12） | `SceneBuilder` `BuildPlayer` `ShaderSetup` `SAssetPostprocessor` `SModelContract` `SModelSheet` `SInputFix` `SUiMaterialSetup` `SUiSpriteSetup` `SUiTextureReimport` `SUiPrefabFactory` `MouseDisableRootCause` |

### 工具

- `scripts/check.ps1`（UTF-8 BOM）：tests / setup / assets / ui / build / smoke / shots / all；shots 前自动清理残留 exe
- `tools/loadout-tests/`：dotnet 控制台，直接链接 Core 源码（`-bench` 走 `DpsBench` / `XpBench`）
- `tools/*.py`：UI 素材三段流水线、APIMart 清单登记、Blender 建模与预览

### 工程内布局

| 路径 | 内容 |
|------|------|
| `Assets/Scenes/Main.unity` | 唯一场景，只有 `S` 节点（挂 `Bootstrap`），其余全运行时构建 |
| `Assets/Settings/` | URP 资产：`PC_RPAsset` / `PC_Renderer` / `Mobile_*` / `DefaultVolumeProfile` |
| `Assets/Resources/Data/sdata.json` | 数值唯一来源 |
| `Assets/Resources/Models/` | **12 件** `Modle_*` FBX（5 敌人/Boss + 3 枪 + 4 道具） |
| `Assets/Resources/UI/` | 58 张 PNG + `Prefabs/`（UI 结构来自预制体） |

## 实机修掉的 10 个真实缺陷

见 `breakdown/01-vertical-slice.md` 「过程中修掉的真实缺陷」表。
其中最关键的两个：

1. **URP Lit 在打包时被剥离** → 播放器黑屏。编辑器完全看不出来。
2. **自检假绿**：只断言状态位、且截图在同一帧捕获 → 背包没显示也判 PASS。
   现在断言 `IsBagVisible` + 卡片计数，并让截图等两帧。

## 未决 / 注意

- **数值已首轮校准**：三枪单体极差 1.21×；单图改造后经验预算重算为 LV 15 附近（13–17 区间）
- **时间轴节奏未实机调优**：5 个阶段的并发/间隔是初版值（8→12→14→16→18），
  4:00 与 8:00 的手感需要真人跑局确认
- **敌人 HP 与 DPS 匹配未验**：爬行者 60 HP 应 1–2 发打死，未实机确认
- **背包容量 24 未验**：是否会频繁「背包满」打断节奏
- **榴弹近距离自伤风险未验**：溅射 2.8m 在单图掩体间是否过强
- **模型已上，但无骨骼无动画**
- **音效为合成音**：节奏与限流已验证，音色待换真实素材
- **音乐已接线但未验听感**：`GameRoot.Update` 每帧调 `UpdateMix`，五层音量曲线未实机听过
- **音量设置已可用**：`AudioMix`（Master/SFX/Music/UI，PlayerPrefs 持久化）+ `MenuView` 四个滑条已接
- **`enemy_near` 已合成未接入**：`SfxBank.PlayEnemyNear()` 全工程无调用点
- **作用域图标偏精细**：与「极简」略有张力，未重跑
- **键位提示素材已生成未接入**：`UiAssets.Keycap` 只在自检里被断言存在，玩法 UI 未使用
- **Boss 技能简化**：只做冲击波 + 召唤
- **无人机高度判定缺失**：`GameRoot.Explode` 仍按 `Vector3.Distance`（含水平 + 垂直）判定
- **精英无专属模型**：现为「本体 ×1.35 + 自发光轮廓子物体」
- **局外成长已实装**：`Core/MetaProgress`（shard / 解锁 / 图鉴）+ `View/MetaSave`（`persistentDataPath/meta.txt`）
  已接进 `MenuView`；`Win()` 现在会真的发 `shard`
- **`03` 方案存档未开始**：`PresetStore` 不存在，`PresetCases.cs` 已被排除在编译之外
- **`check.ps1` 的路径引号 bug**：本机路径含空格时 `-Task build/shots/tests` 直接失败
  （`Start-Process -ArgumentList` 里的 `-projectPath` 未加引号）。本轮用等价命令绕过，脚本未修
- **工程已入 Git**：`git@github.com:Su092/Project-S.git`（`main`，工程根 `<GAME:S>`）
- **`*.csproj` 被 gitignore 吞掉**：`tools/loadout-tests/` 的 `.csproj` 不入库，克隆到新机后需本地重建
- **场景无顶**：仍是开放箱体（无天花板）
- 中文日志在 PowerShell 5.1 控制台显示为乱码（`selfcheck.log` 是正确的 UTF-8，用 `Get-Content -Encoding UTF8` 读）

## 环境缺口（2026-11-15 晚复核）

| 缺口 | 现状 | 影响 |
|------|------|------|
| 系统 .NET SDK | `dotnet --list-sdks` 输出为空 | `check.ps1 -Task tests` 走 PATH 的 dotnet 会失败 |
| **替代方案** | Unity 自带 **.NET 8.0.318**：`<UNITY:6000.6.4f1>/Data/DotNetSdk/dotnet.exe` | 本轮 795 条断言就用它跑，可用 |
| `loadout-tests/*.csproj` | 已被 `.gitignore` 的 `*.csproj` 规则忽略 | 已在本机重建（含 `RunDirector` 链接、`PresetCases` 排除） |
| Coplay MCP 包 | `Packages/manifest.json` 无 `com.coplaydev.unity-mcp` | 打开工程时 Unity MCP 工具为空 |

已核实可用：Unity 6000.6.4f1 @ `<UNITY:6000.6.4f1>`、Blender @ `<BLENDER>`、Unity 内置 .NET 8 SDK。

## 下一步建议

1. **修 `check.ps1` 的引号 bug**：把 `-projectPath` 等参数写成带引号的字符串，
   否则本机路径含空格时脚本每个任务都跑不起来（这是当前最大的工具链阻塞）
2. **时间轴实机调优**：4:00 / 8:00 的手感、5 个阶段的并发与间隔都需真人跑局
3. **`03` 剩余**：实现 `PresetStore` 让方案存档落地，之后再把 `PresetCases.cs` 纳入编译
4. Boss 技能补全、无人机高度判定
5. 装 `com.coplaydev.unity-mcp` 以便场景/预制体走 MCP 而非手改
