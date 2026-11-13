# 当前快照 — S

更新：2026-11-12

## 关联

- 枢纽：`E:\Unity Development\Project\S\`
- Unity：`E:\S`（`unity\` 目录联接，`mklink /J`）
- 编辑器：Unity **6000.6.4f1**（`D:\Unity\6000.6.4f1`）
- 渲染：**URP 17.6**（`PC_RPAsset`）
- 输入：**仅新 Input System**（`activeInputHandler = 1`）
- 工程远端：尚未创建

## 已定约定

- 文档 / 拆解 / 控制 / 记忆只在枢纽；代码与资源只在 `unity/`
- 数据唯一来源 `Assets/Resources/Data/sdata.json`，人读镜像在 `docs/loadout-spec.md` 与 `docs/gameplay-spec.md`
- `Core/` 零 Unity 依赖（`SDataLoader.cs` 是唯一桥），结算可在 dotnet 下断言
- 场景只有一个 `S` 节点，所有对象与 UI 由代码构建
- 材质一律走 `SMat`，不用裸 `new Material(Shader.Find(...))`
- 验证只认 `check.ps1`（tests / setup / build / shots）

## 当前状态

**垂直切片 → 箱庭+Boss → 美术资产 → UI 素材 → 音效/材质池/后处理，全部可玩并通过验证。**

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
- 12 张 1k 参考图（仅建模对照）
- 管线：`tools/blender_s_build_assets.py`（建模 + 双门）、`tools/blender_s_preview.py`

**UI（11 张素材）**
- 面板 / 卡框 / 条槽 / 横幅 / 暗角 / 准星 / 键位 + 4 个作用域图标
- 加色材质 `mat_ui_additive` + `S/UiAdditive` shader
- 9-slice 边距由 `Editor/SUiSpriteSetup.cs` 写入并硬校验

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
| Core | `SJson` `LoadoutTypes` `Loadout` `GunRuntime` `RunState` `ZoneProgress` `BossState` `SData` `SDataLoader` |
| View | `GameRoot` `ZoneBuilder` `ZoneGate` `Pillar` `BossView` `PlayerController` `PlayerWeapons` `Projectile` `Enemy` `EnemyBullet` `HudView` `InventoryView` `SMat` `SAssets` `UiAssets` `SfxBank` `SPostFx` |
| App | `Bootstrap` `SelfCheck` |
| Editor | `SceneBuilder` `BuildPlayer` `ShaderSetup` `SAssetPostprocessor` `SUiMaterialSetup` `SUiSpriteSetup` |

### 工具

- `scripts/check.ps1`（UTF-8 BOM）：tests / setup / build / shots / all；shots 前自动清理残留 exe
- `tools/loadout-tests/`：dotnet 控制台，直接链接 Core 源码

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
- **无音乐层**：探索/战斗/高压分层未做；无音量设置与混音分组
- **`enemy_near` 已合成未接入**
- **作用域图标偏精细**：与「极简」略有张力，未重跑
- **键位提示素材已生成未接入**
- **Boss 技能简化**：只做冲击波 + 召唤
- **无人机高度判定缺失**：`Explode` 仍按水平距离
- **无局外成长存档**：`shard` 与解锁未实装
- **工程未入 Git**：远端尚未创建
- **场景无顶**：仍是开放箱体
- 中文日志在 PowerShell 5.1 控制台显示为乱码（`selfcheck.log` 是正确的 UTF-8，用 `Get-Content -Encoding UTF8` 读）

## 下一步建议

1. **实机节奏校准**：威胁值 / 敌人 HP 手感 / 背包容量三项都需真人跑局
2. **`03` 剩余**：方案存档、配件扩到 40 种（扩件要在校准定稿后做）
3. Boss 技能补全、无人机高度判定、音乐层
