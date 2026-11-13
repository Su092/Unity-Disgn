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
| `guns` | array | 枪械（初版 3） |
| `bullets` | array | 子弹配件（初版 10） |
| `modifiers` | array | 衍生配件（初版 15） |
| `rarityWeights` | object | 三选一权重 |

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
| `id` | string | 唯一，`g_` 前缀 |
| `name` | string | 显示名 |
| `kind` | enum | `Auto` / `Grenade` / `Single` |
| `slotCount` | int | **配件位数**（轮转长度） |
| `fireInterval` | float | 击发间隔（秒） |
| `magSize` | int | 弹匣上限 |
| `reloadTime` | float | 换弹秒数 |
| `spreadBase` | float | 基础散射（度），链结算前并入每个描述符 |
| `muzzleSpeed` | float | 基础弹速 m/s |
| `damageMul` | float | **枪械固有伤害倍率**，链结算**之后**乘 |
| `splashRadius` | float | 基础溅射半径 m（0 = 无）；与子弹自带取大者 |
| `mode` | enum | `Straight`（直射）/ `Ballistic`（抛射，受 `gravity`） |
| `gravity` | float | 抛射重力，仅 `Ballistic` 用 |
| `starterChain` | string[] | 开局装进 1 号位的配件 id |

## `bullets[]`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` `name` `rarity` | | `b_` 前缀；`Starter` 不进抽取池 |
| `damage` | float | 命中伤害 |
| `ammo` | int | 每次施法扣的弹药点 |
| `spreadAdd` | float | 散射加法（度） |
| `lifetime` | float | 存在时间（秒） |
| `crit` | float | 暴击率 0..1 |
| `critDmg` | float | 暴击倍率（≥1） |
| `speedMul` | float | 弹速倍率，默认 1 |
| `pierce` | int | 可穿透敌人数 |
| `bounce` | int | 撞墙反弹次数 |
| `splashRadius` | float | 自带溅射半径 |
| `burnDps` `burnTime` `burnMaxStacks` | float/float/int | 燃烧 |
| `slowPct` `slowTime` | float | 减速 |
| `ignoreArmor` | bool | 无视护甲（盾卫正面减伤只按 30%） |

## `modifiers[]`

**加法项**（先作用）

| 字段 | 类型 | 说明 |
|------|------|------|
| `damageFlat` | float | 伤害 + |
| `critFlat` | float | 暴击率 +（0.12 = +12%） |
| `critDmgFlat` | float | 暴击倍率 + |
| `spreadAddFlat` | float | 散射 +（度） |
| `lifetimeFlat` | float | 存在时间 +（秒） |
| `pierceFlat` | int | 穿透 + |
| `bounceFlat` | int | 反弹 + |
| `ammoFlat` | int | 弹药消耗 +（负数为减） |

**乘法项**（后作用）

| 字段 | 类型 | 默认 |
|------|------|------|
| `damageMul` | float | 1 |
| `critMul` | float | 1 |
| `spreadMul` | float | 1 |
| `lifetimeMul` | float | 1 |
| `speedMul` | float | 1 |

**行为项**

| 字段 | 类型 | 说明 |
|------|------|------|
| `splashAdd` | float | 溅射半径 + |
| `homingRate` | float | 追踪转向角速度（度/秒），0 = 无 |
| `splitCount` | int | >1 时分裂成这么多个 |
| `splitDamageMul` | float | 分裂体伤害倍率 |
| `splitSpreadAdd` | float | 分裂体散射 + |
| `splitLifetimeMul` | float | 分裂体存在时间倍率 |

**枪械项**（仅 `scope: "Gun"` 使用）

| 字段 | 类型 | 说明 |
|------|------|------|
| `gunMagAdd` | int | 弹匣 + |
| `gunFireIntervalMul` | float | 击发间隔倍率（<1 = 更快） |
| `gunSpreadMul` | float | 枪基础散射倍率 |
| `gunReloadMul` | float | 换弹时间倍率 |

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
   cd "E:\S\tools\loadout-tests"; dotnet run -c Release
   ```
   断言里的期望值写死在测试中，数值被改坏会立刻变红。
6. 同步更新 `loadout-spec.md` / `gameplay-spec.md` 的对应表。
