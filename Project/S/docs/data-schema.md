# 数据契约 — sdata.json

唯一数据源：`unity/Assets/Resources/Data/sdata.json`
解析器：`Assets/_Game/Core/SData.cs`（字段名必须与此文件一致）
人读镜像：`loadout-spec.md`（配件数值）、`gameplay-spec.md`（环境与成长）

## 通用约定

- 文件是标准 JSON，**允许 `//` 行注释**（`SJson` 支持，便于在数据里写说明）。
- 所有字段**缺省即有默认值**（见 `SData.cs`），但新增配件必须把语义字段写全，否则会静默取 0。
- 枚举按**名字**写（区分大小写不敏感）：

| 枚举 | 取值 |
|------|------|
| `Scope` | `Whole`（全场）`After`（后继）`Gun`（枪械） |
| `Rarity` | `Common` `Rare` `Epic` `Starter` |
| `GunKind` | `Auto` `Grenade` `Single` |
| `ProjectileMode` | `Straight` `Ballistic` |

## 顶层结构

| 键 | 类型 | 说明 |
|----|------|------|
| `meta` | object | 版本与备注，运行时不用 |
| `player` | object | 玩家基础属性 |
| `guns` | array | 枪械（6 把） |
| `bullets` | array | 子弹配件（17 件） |
| `modifiers` | array | 衍生配件（作用于子弹，13 件） |
| `gunModifiers` | array | 枪械向衍生件（9 件，含 2 件 `Next` 多重施放） |
| `rarityWeights` | object | 三选一权重 |
| `arena` | object | 单张竞技场的地形参数（无分区、无门） |
| `timeline` | object | 刷怪时间轴：阶段、并发、间隔、Boss 入场时刻 |
| `elite` | object | 精英强化系数与出现节奏 |
| `boss` | object | Boss 基础属性 |

## `player`

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `hp` | float | 100 | 生命上限 |
| `walk` | float | 5.6 | 行走速度 m/s |
| `sprintSpeed` | float | 9.2 | 冲刺速度 |
| `jumpHeight` | float | 1.15 | 跳跃高度 m |
| `gravity` | float | 22 | 重力 m/s² |
| `iFrames` | float | 0.25 | 受击无敌秒数 |
| `gunSlots` | int | 2 | 可携带枪数 |
| `bagSize` | int | 24 | 背包容量 |
| `healPickup` | float | 35 | 区域补给回血量 |

## `guns[]`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 唯一：`rifle` `smg` `shotgun` `sniper` `beam` `launcher` |
| `name` | string | 显示名 |
| `desc` | string | 一句话定位（菜单卡片用） |
| `slotCount` | int | **槽位数**（一格一件） |
| `magSize` | int | 弹匣容量 |
| `reloadTime` | float | 换弹秒数 |
| `fireInterval` | float | 基础击发间隔（秒） |
| `spreadBase` | float | 基础散射（度），加到每个投射物上 |
| `castCount` | int | **一次射击读取几个子弹**（霰弹枪 = 2） |
| `baseBullet` | string | 开局预置在第 1 槽的子弹 id（玩家永远有一发可用） |
| `color` | string | `#rrggbb`，枪模与 UI 用色 |
| `zoom` | float | 右键瞄准时的视距（越小倍率越高） |

## `bullets[]`

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `id` `name` `icon` `desc` | string | | `icon` 是卡片角标用的单字 |
| `rarity` | enum | `Common` | `Common` / `Rare` / `Epic` |
| `cost` | int | 1 | **耗弹点**（读到时扣） |
| `delay` | float | 0 | 叠加到击发间隔（负数 = 更快） |
| `kind` | enum | `Proj` | `Proj` / `Beam` / `Mine` / `Field` / `Chain` / `Saw` / `Hole` |
| `damage` | float | 10 | 命中伤害 |
| `count` | int | 1 | 投射物数量 |
| `spread` | float | 0 | 散射（度） |
| `speed` | float | 80 | 初速 m/s |
| `lifetime` | float | 1.5 | 存在时间（秒） |
| `size` | float | 0.12 | 视觉半径 |
| `pierce` | int | 0 | 穿透数（999 = 无限） |
| `bounce` | int | 0 | 反弹次数 |
| `homing` | float | 0 | 追踪强度 |
| `gravity` | float | 0 | 抛射重力（>0 才受重力） |
| `explodeR` | float | 0 | 爆炸半径（0 = 无） |
| `explodeDmg` | float | 0 | **爆炸伤害**（与直伤独立结算） |
| `burn` | float | 0 | 燃烧 dps |
| `slow` | float | 0 | 减速 0..1 |
| `crit` | float | 0.05 | 暴击率 |
| `critMul` | float | 2 | 暴击倍率 |
| `knock` | float | 1 | 击退系数 |
| `chainCount` | int | 0 | 连锁次数（仅 `Chain`） |
| `range` | float | 60 | 射程（仅 Beam / Chain） |
| `radius` | float | 0 | 力场/奇点半径 |
| `duration` | float | 0 | 地雷/力场持续秒数 |
| `trigger` | enum | `None` | `Hit` / `Timer` / `Expire` |
| `color` | string | `#ffd25a` | 投射物颜色 |

## `modifiers[]` / `gunModifiers[]`

两者结构相同，只是分组存放（作用于子弹 / 作用于枪械）。
**所有字段都是「每层叠加量」**，`t` = 同名同域在一次结算里的叠加层数。

### 作用域

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `scope` | enum | `Next` | `Next` / `Prev` / `Adj` / `N2` / `N3` / `P2` / `All` |
| `cost` | int | 1 | 被读取时扣的弹（`Next` 才扣；被动件按吸附计） |
| `delay` | float | 0 | 叠加到击发间隔 |

### 乘法组

| 字段 | 说明 |
|------|------|
| `damageMulAdd` | 伤害 `×(1+add·t)` |
| `sizeMulAdd` | 体积 |
| `speedMulAdd` | 速度 |
| `rangeMulAdd` | 射程 |
| `lifeMulAdd` | 存在时间 |
| `knockMulAdd` | 击退 |
| `countMulAdd` | 投射物数量（取整） |
| `radiusMulAdd` | 范围半径 |

### 加法组

| 字段 | 说明 |
|------|------|
| `piercePer` | 每层穿透（最小 1/层） |
| `bouncePer` | 每层反弹（最小 1/层） |
| `homingPer` | 追踪强度 |
| `burnPer` | 燃烧 dps |
| `slowPer` | 减速（取 max） |
| `critPer` | 暴击率 |
| `spreadPer` | 散射（度） |

### 爆裂

| 字段 | 说明 |
|------|------|
| `explodeRBase` | 无爆裂时的半径 |
| `explodeRAdd` | 已有爆裂时的半径加成比例 |
| `explodeDmgFromDmg` | 爆伤 = 伤害 × 该系数 |
| `explodeDmgFlat` | 爆伤固定加成 |

### 弹药 / 枪械 / 多重施放

| 字段 | 说明 |
|------|------|
| `ammoReduce` | 目标子弹耗弹 −N |
| `gunMagMul` `gunReloadMul` `gunDelayMul` `gunSpreadMul` | 枪属性倍率 |
| `gunRecycleAdd` | 免耗弹概率（叠加按 `1−(1−a)(1−b)`） |
| `gunCastAdd` `gunMagMulIfCast` | 读取 +N（带弹匣惩罚） |
| `gunLeech` | 击杀回血 |
| `multicast` | 本次多读 N 发（自动归到 `Next`） |

**校验**：`IsGunOnly` 为真的件会被强制设为 `scope: All`（解析时自动纠正，不报错）。

## `arena`

单张连续场地。**没有 `zones[]`、没有门、没有分区间隔** —— 这是与初版最大的结构差异。

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `width` | float | 120 | 场地 X 向尺寸（m） |
| `depth` | float | 120 | 场地 Z 向尺寸（m） |
| `wallHeight` | float | 12 | 四周墙高；墙实心、挡人挡弹 |
| `bossPadRadius` | float | 14 | 中央 Boss 台半径；也是掩体的最小留空半径基准 |
| `coverCount` | int | 22 | 掩体数量（固定种子，避开中央与出生点） |
| `highGroundCount` | int | 4 | 高台数量，均布于四边中点，带台阶 |
| `spawnPoints` | int | 16 | 沿外缘的环形刷怪点数 |
| `playerSpawnZ` | float | -45 | 玩家出生点的 Z 坐标（X 恒为 0） |

## `timeline`

时间轴是本作**唯一的节奏来源**（`gameplay-spec.md` §2.1）。

| 字段 | 类型 | 说明 |
|------|------|------|
| `bossAt` | float | Boss 入场时刻（秒）。8:00 = 480 |
| `threatFullAt` | float | 威胁值达到 100 的时刻（秒）；`threat = 100 × t / threatFullAt` |
| `phases[]` | array | 阶段表，按下表字段定义 |
| `bossPhase` | object | Boss 入场后的降档刷怪规格（同 `phases[]` 结构） |

`phases[]` / `bossPhase` 的字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `at` | float | 该阶段开始时刻（秒）。首条必须为 0 |
| `name` | string | UI 显示名（`开局` / `加压` / `混编` / `全谱` / `高压` / `BOSS`） |
| `pool` | string[] | 敌人池，名字对应 `Enemy.Kind`：`Crawler` `Spitter` `Shield` `Drone` |
| `concurrency` | int | 场上同时存活上限。**这是可读性保护**，不是性能参数 |
| `interval` | float | 单只刷出间隔（秒） |

**校验**：`phases[0].at` 必须为 0；`at` 必须递增；`pool` 里的名字必须是四个合法 Kind 之一
（拼错会静默退化成 Crawler，见 `GameRoot.SpawnFromPool`）。

## `elite`

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `firstAt` | float | 240 | 首只精英的入场时刻（4:00） |
| `interval` | float | 90 | 之后每只的间隔 |
| `hpMul` | float | 3.5 | 生命倍率 |
| `dmgMul` | float | 1.6 | 伤害倍率 |
| `speedMul` | float | 0.85 | 速度倍率（比本体慢，给玩家反应时间） |
| `xpMul` | int | 6 | 经验倍率 |
| `scale` | float | 1.35 | 体积倍率；**碰撞体同步放大**（只改视觉会造成「看得见打不中」） |
| `healOnKill` | float | 15 | 击杀回复玩家生命。单图下这是中期唯一续航来源 |

精英总数由公式推导，不写死：`1 + floor((bossAt - firstAt) / interval)` = 3 只（4:00 / 5:30 / 7:00）。

## `rarityWeights`

| 键 | 初版值 |
|----|--------|
| `Common` | 58 |
| `Rare` | 34 |
| `Epic` | 8 |

## 校验清单（改数据后逐条确认）

1. `guns` 的 `starterChain` 里每个 id 都能在 `bullets` 或 `modifiers` 找到。
2. 每个 `modifiers` 至少有**一个**非默认值字段，否则是占位垃圾数据。
3. `scope: "Gun"` 的件不应有投射物字段（有也不会生效，属于数据错误）。
4. `scope: "After"` 的件在 UI 里必须能被识别为「需要放在子弹前面」，否则玩家必然配错。
5. 改任何数值后跑：
   ```powershell
   cd "<GAME:S>\tools\loadout-tests"; dotnet run -c Release
   ```
   断言里的期望值写死在测试中，数值被改坏会立刻变红。
6. 同步更新 `loadout-spec.md` / `gameplay-spec.md` 的对应表。
7. 改 `timeline` 后必须跑 `-bench` 检查经验预算是否仍落在 13–17 级区间。

## 时间轴的契约（最容易改坏的地方）

| 规则 | 为什么 |
|------|--------|
| `timeline.phases[0].at` 必须为 0 | 否则开局到第一条 `at` 之间没有任何刷怪规格，`CurrentPhase` 为 null，场上会空着不动 |
| `threatFullAt` 建议等于 `bossAt` | 让「威胁满」与「Boss 入场」同时发生，玩家能感到两件事是一件事 |
| 精英上限由公式算，不写字段 | 写死的话改 `interval` 会忘记同步上限，出现「明明该出 3 只只出了 1 只」 |
| `bossPhase.concurrency` 要低于最后一条 `phases` | Boss 战需要腾出精力应对 Boss，普通刷怪必须降档 |

