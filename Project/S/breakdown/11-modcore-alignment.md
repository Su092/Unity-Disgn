# 任务：对齐 MODCORE Web 原型（规则 / 配件 / 枪械 / UI / 素材）

- 状态：**完成**（2026-11-15 晚）
- 依据：外部原型 `modcore-prototype`（index.html / style.css / dist/game.js）
- 目标：把原型里的**读取式链 + 7 种作用域 + 6 把枪 + 39 配件**搬进 Unity，
  UI 布局按原型（顶部大计时器 / 左枪械右背包 / 圆形图标三选一），素材缺件用 APIMart 补齐。

## 为什么要推翻旧结算引擎

| 维度 | 旧（自研链式触发） | 新（原型读取式扫描） |
|------|---------------------|----------------------|
| 一格内容 | 一条可叠多件的「链」 | **一件** |
| 触发时机 | 按链顺序在时间轴上逐项兑现 | **一次性扫描解析出全部投射物** |
| 作用域 | 3 种（全场/后继/枪械） | **7 种** |
| 表现力上限 | 「一条链能塞几件」 | 「20 子弹 × 22 件 × 7 作用域 × 6 枪」 |

旧模型把「顺序」做成时间轴，玩家看到的是「这一发慢慢打出几件」；
新模型把「顺序」做成**空间位置**，玩家看到的是「哪张牌影响哪几颗子弹」。
后者才有真正的构筑决策密度。

## 已落地

### Core（重写）

| 改动 | 文件 |
|------|------|
| 数据模型：`BulletKind`(7) / `TriggerKind`(3) / `Scope`(7) / 声明式 `ModifierDef` | `Core/LoadoutTypes.cs` |
| 结算引擎：`ResolveGun` / `ResolveCast` / `TargetsOf` / `NextBulletCell` / `PassivesOn` / `ApplyMod` / `FullSequence` | `Core/Loadout.cs` |
| 运行时：`GunStats`（弹匣/射速/回收/汲能）、指针扫描、`DpsEstimate` | `Core/GunRuntime.cs` |
| 数据解析：`arena` / `timeline` / `elite` + `gunModifiers` 分组 | `Core/SData.cs` |
| 抽取与分解：`Salvage`（3/6/9 经验）、权重 60/30/10 | `Core/RunState.cs` |
| 删除 | `Core/ZoneProgress.cs`（上一轮已删）、`View/ChainCast.cs` |

### View

| 改动 | 文件 |
|------|------|
| 7 种弹道形态（Proj/Beam/Mine/Field/Chain/Saw/Hole）+ 触发载荷 | `View/Projectile.cs` |
| 按 delay 逐发飞出（避免霰弹同帧叠成一团） | `View/PlayerWeapons.cs` |
| 改装台重写：一格一件网格、交换而非覆盖、作用域提示 | `View/InventoryView.cs` |
| 三选一卡片克隆模板（此前取子节点得到 0 张） | `View/InventoryView.cs` |
| 详情卡：7 种作用域说明 + 每层叠加量 | `View/ItemTooltip.cs` |
| HUD：中央大计时器 + 倒计时 + 「下一发 N 发/耗弹/期望」 | `View/HudView.cs` |
| 敌人 4 类改为 Crawler / Brute / Bomber / Turret | `View/Enemy.cs`、`View/GameRoot.cs` |
| 竞技场 100×100 | `View/ArenaBuilder.cs` |

### 数据

| 项 | 内容 |
|----|------|
| 枪械 | 6 把（slotCount 6–12，castCount 1–2） |
| 子弹 | 17 件（含 7 种形态 + 3 种触发） |
| 衍生 | 22 件（13 子弹向 + 9 枪械向） |
| 时间轴 | 5 阶段，5:00 精英、10:00 Boss |

### 素材（APIMart 全量生成）

- **39 个配件图标**（原 25 个旧 id 全部作废）：先出 AI 线稿 glyph，再由
  `gen_ui_assets_ai.py` 用几何画圆底板 + 双层圆环 + 稀有度色环。
- 流水线三段：`preprocess_ui_assets.py`（抠图归一）→ `gen_ui_assets_ai.py`（合成）→ `SUiTextureReimport`。
- `ITEM_IDS` / `ITEM_ICONS` 两处清单必须同步（各 39 项），否则自检会点名缺失。

## 验收

| 项 | 结果 |
|----|------|
| `tests`（dotnet） | **106/106 passed** |
| 编译 | 0 errors |
| `-Task build` | `Succeeded (0 errors)` |
| `-scheck` 实机自检 | **94/94 passed**（含详情区 5 条断言 + 2 张详情截图） |
| 配件图标 | **39/39 加载** |

## 过程中修掉的真实缺陷

| # | 问题 | 现象 | 修法 |
|---|------|------|------|
| 1 | `ChainCast` 依赖 `ChainStep` | 删除后整片编译失败 | 整类删除，HUD 改读 `PeekCast()` |
| 2 | 三选一取「现成子节点」 | `cards=0`，界面空白 | 必须 `Instantiate(CardTemplate)` |
| 3 | 图标生成脚本路径写死 `E:\...` | 39 张图跑到枢纽根 `_Inbox`，工程里 0 张 | 手工移正 + 后续改用相对路径 |
| 4 | `preprocess` / `gen_ui_assets` 清单还是旧 25 个 id | 合成报「缺少预处理素材」 | 两处清单同步为 39 个新 id |
| 5 | 三选一图标与描述重叠 | 描述第一行压在圆环上 | 卡片改「标题/图标/分割线/描述」显式分带 |
| 6 | `ItemCard` 仍是 150×84 横条 | 塞进网格后像一排书签 | 改为 116×100 方形，图标居中、名称底部 |
| 7 | 背包格子 150×44 与卡片尺寸不一致 | 卡片被 `GridLayoutGroup` 拉成细条 | 两边统一 116×100 |
| 8 | 槽位网格写死 5 列 124px | 窄分辨率下溢出到背包面板 | 列宽按 `chainArea.rect.width` 实算 |
| 9 | 刷怪点 y=0.9 | 敌人从半空落下 | 落点 y 改为 0.02（CharacterController 自带 center） |
| 10 | 爆炸伤害未计入期望 | 榴弹 DPS 只有 11.7，基准判成废枪 | `ExpectedDamage` 加入 `ExplodeDmg` |
| 11 | 命中率模拟把抛射物当直线 | 榴弹命中率 0%，差点去改数值 | 跳过 `Gravity > 0` 的投射物 |
| 12 | 基准里改共享 `ModifierDef.Scope` | 第二组用例读到被改坏的作用域 | 复制副本再改 |
| 13 | 卡片名称拼了图标单字 | 窄卡片里「标」被挤成孤行 | 只显示名称 |
| 14 | **清单 `out` 是相对路径，`download()` 拼到枢纽根** | 39 张图标全部落到 `<HUB>\_Inbox`，工程里 0 张 | `out` 先按工程根解析成绝对路径；存在性检查同源；脚本不再写死盘符 |
| 15 | 详情区文字用 `LabelFixed` 传负尺寸 | 提示行与数值被裁掉一截（截图可见「有子弹前面」半句） | 改用 `Label`（offsetMin/offsetMax 拉伸），并给多行文本开 Wrap |
| 16 | `ItemTooltip` 页脚还是旧规则文案 | 显示「链式触发：逐项生效」，而规则早已改成读取式扫描 | 改为按作用域给出正确的用法提示 |

## 素材落点约定（本轮踩出来后写进 `control/workflow.md`）

生成素材的中间产物**只放本工程 `_Inbox`**：

| 阶段 | 位置 |
|------|------|
| APIMart 原图 | `<GAME:S>\_Inbox\ui-ai-raw\` |
| 预处理产物 | `<GAME:S>\_Inbox\ui-ai-src\` |
| 进引擎成品 | `<GAME:S>\Assets\Resources\UI\` |
| 共享清单 | `<HUB>\tools\apimart-assets.json` |

## 明确未做

| 项 | 说明 |
|----|------|
| 宝箱（原型 E 键开箱） | 未实现；经验仍只来自击杀 |
| 沙盒模式 / 测试起点选择 | 原型菜单里的两个调试项，未搬 |
| 画质档位 | 原型有高/中/低，Unity 侧未做 |
| 右键瞄准 | 数据里有 `zoom`，未接线 |
| 精英专属模型 | 仍是「本体 ×1.4 + 自发光轮廓」 |
| 时间轴手感调优 | 并发/间隔是初版值，需真人跑局 |
