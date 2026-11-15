# 当前快照 — S

更新：2026-11-15

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

**垂直切片 → 箱庭+Boss → 美术资产 → UI 素材 → 音效/材质池/后处理，全部可玩并通过验证。**

> 下表数字来自 2026-11-12 的开发机。**2026-11-15 换机克隆后尚未复跑**
> （本机缺 .NET SDK，见文末「环境缺口」），不要当成本地已验证。
| 项 | 结果 |
|----|------|
| 逻辑断言（dotnet） | **213/213 passed** |
| Unity 编译 | 0 errors |
| 打包 | `build Succeeded (0 errors)` |
| 实机自检 | **73/73 passed** |
| 模型构建 | **12/12**（尺寸门 + 装配门） |
| 契约门 | **12/12 pass** |
| 材质池 | 基线 5 → 战斗后 **5**（零增长） |
| **DPS 均衡（单体）** | 极差 **1.21×**（判据 ≤1.30×） |

## 数值校准（本轮新增）

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
- 12 张 1k 参考图（仅建模对照，在 `_Inbox/art-refs/`，**不入库**）
- 管线：`tools/blender_s_build_assets.py`（建模 + 双门）、`tools/blender_s_preview.py`（出图在 `_Inbox/art-preview/`）

**UI（11 张素材）**
- 面板 / 卡框 / 条槽 / 横幅 / 暗角 / 准星 / 键位 + 4 个作用域图标
- 加色材质 `mat_ui_additive` + `S/UiAdditive` shader
- 9-slice 边距由 `Editor/SUiSpriteSetup.cs` 写入并硬校验
- 流水线原料在 `_Inbox/{ui-ai-raw,ui-ai-src}/`（**不入库**），成品落 `Assets/Resources/UI/`

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

- **数值已首轮校准**：三枪单体极差 1.21×，经验曲线实测 LV 14
- **威胁值节奏未实测**：需跑完整局记录开背包时的威胁值
- **敌人 HP 与 DPS 匹配未验**：爬行者 60 HP 应 1–2 发打死，未实机确认
- **背包容量 24 未验**：是否会频繁「背包满」打断节奏
- **榴弹近距离自伤风险未验**：溅射 2.8m 在狭窄区是否过强
- **模型已上，但无骨骼无动画**
- **音效为合成音**：节奏与限流已验证，音色待换真实素材
- **音乐层写了但没接线**：`MusicDirector` 已由 `GameRoot` 创建（`GameRoot.cs:137`），
  但 `UpdateMix(...)` **全工程无调用点**，五个层音量恒为 0 —— 实机听不到音乐。
  接线时要传 `Run.Threat` / `_bossFightActive` / `InventoryOpen` / `dt`。
- **音量设置已可用**：`AudioMix`（Master/SFX/Music/UI，PlayerPrefs 持久化）+ `MenuView` 四个滑条已接
- **`enemy_near` 已合成未接入**：`SfxBank.PlayEnemyNear()` 全工程无调用点
- **作用域图标偏精细**：与「极简」略有张力，未重跑
- **键位提示素材已生成未接入**：`UiAssets.Keycap` 只在自检里被断言存在，玩法 UI 未使用
- **Boss 技能简化**：只做冲击波 + 召唤
- **无人机高度判定缺失**：`GameRoot.Explode` 仍按 `Vector3.Distance`（含水平 + 垂直）判定
- **局外成长已实装**：`Core/MetaProgress`（shard / 解锁 / 图鉴）+ `View/MetaSave`（`persistentDataPath/meta.txt`）
  已接进 `MenuView`；解锁项偏少，内容待扩
- **`03` 方案存档未开始**：全工程无 Preset/Scheme 相关代码，配件方案保存仍未做
- **工程已入 Git**：`git@github.com:Su092/Project-S.git`（`main`，工程根 `<GAME:S>`）
- **`*.csproj` 被 gitignore 吞掉**：`tools/loadout-tests/` 的 `.csproj` 不入库，
  克隆到新机后 `dotnet run` 找不到工程；且本机当前**无 .NET SDK**（`dotnet --list-sdks` 为空），
  `check.ps1 -Task tests` 会 FAIL。补齐方式见下「环境缺口」。
- **场景无顶**：仍是开放箱体
- 中文日志在 PowerShell 5.1 控制台显示为乱码（`selfcheck.log` 是正确的 UTF-8，用 `Get-Content -Encoding UTF8` 读）

## 环境缺口（2026-11-15 复核）

| 缺口 | 现状 | 影响 |
|------|------|------|
| .NET SDK | 本机只有 runtime 解析器，`dotnet --list-sdks` 输出为空 | `check.ps1 -Task tests` 直接失败 |
| `loadout-tests/*.csproj` | 工程文件不存在且被 `.gitignore` 的 `*.csproj` 规则忽略 | 即便装了 SDK 也构建不了 |
| Coplay MCP 包 | `Packages/manifest.json` 无 `com.coplaydev.unity-mcp` | 打开工程时 Unity MCP 工具为空 |

已核实可用：Unity 6000.6.4f1 @ `<UNITY:6000.6.4f1>`、Blender @ `<BLENDER>`。

## 下一步建议

1. **补齐环境缺口**（否则任何验证都跑不了）：装 .NET 8 SDK → 重建 `loadout-tests` 的 `.csproj`
   → 工程装 `com.coplaydev.unity-mcp` → 修 Blender 路径
2. **音乐接线**：`GameRoot.Update` 里调 `_music.UpdateMix(Run.Threat, _bossFightActive, InventoryOpen, dt)`，
   这是「写了但听不到」的直接原因，改一行就能验
3. **实机节奏校准**：威胁值 / 敌人 HP 手感 / 背包容量三项都需真人跑局
4. **`03` 剩余**：方案存档、配件扩到 40 种（扩件要在校准定稿后做）
5. Boss 技能补全、无人机高度判定
