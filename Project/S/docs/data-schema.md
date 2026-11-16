# 数据契约 — Cfg/*.tsv

唯一数据源：`unity/Assets/_Game/Res/Cfg/*.tsv`（11 张表，三行表头）
装配器：`Assets/_Game/Core/SCfgLoader.cs`（零 Unity 依赖，dotnet 断言共用同一份）
校验器：`Assets/_Game/Core/SCfgValidator.cs`（跨表引用与规则矛盾，有 Error 就拒绝启动）
人读镜像：`loadout-spec.md`（配件数值）、`gameplay-spec.md`（环境与成长）

> 旧的 `Resources/Data/sdata.json` 已**移出运行时**（留档在 `tools/legacy-sdata.json`）。
> 任何「改 json 就生效」的旧习惯现在会静默失效 —— 运行时只读 TSV。

## 为什么是 TSV，不是 JSON

| | TSV | JSON |
|---|---|---|
| 编辑 | 表格软件直接打开，改一格存盘 | 手工逗号与引号，一个括号错整份失效 |
| 加一件配件 | 加一行，diff 只多一行 | 加一个嵌套对象，diff 看不出改了哪件 |
| 列序 | 第 1 行是字段名，调列序不影响代码 | 键名与值挤在同一行 |
| 数值类型 | 第 3 行声明规则，可被校验 | 无类型约束 |
| 深层嵌套（子弹的 20+ 个数值） | 一列一个 | 缩进与括号占掉半屏 |

## 三行表头（硬约定）

```
字段名        id        name        hp
中文名        编号      名称        生命
类型规则      string    string      float
数据行        e_boss    铸造核心     6000
```

| 行 | 作用 | 谁读 |
|---|---|---|
| 1 | 字段名。代码按它取值，**列序可任意调** | `STsvRow.F/I/Str/B` |
| 2 | 中文名。给人看，避免认错列 | 只有人 |
| 3 | 类型规则：`float` / `int` / `string` / `bool01` / `{A,B}` / `string,unique` | 校验与文档 |

只有两行表头时「这一列填什么」全靠猜，一旦有人手滑删了中文名行，整张表会**静默错位**。

**不支持的写法**：

- `#` 行内注释 —— 数据里的 `#rrggbb` 颜色值会被误伤。需要说明就写在第 2 行，或加一列 `note`。
- 列名重复 —— 加载期直接抛异常（重名列会让取值静默命中后一个）。
- 某行多/少一个 Tab —— 加载期报「第 N 行有 X 列，表头是 Y 列」。

## 通用约定

- 编码 **UTF-8**（可带 BOM，`STsv` 会剥掉）。
- 所有字段**缺省即有默认值**（见 `S.Core/SData.cs` 的 `*Def` 类），但新增配件必须把语义字段写全，否则会静默取 0。
- 数值列**留空 = 用默认值**。这是合法意图（「这列我不关心」），所以不报错；
  必须存在的字段由 `SCfgValidator` 单独断言。
- 枚举按**名字**写（大小写不敏感），也接受数字：

| 枚举 | 取值 |
|------|------|
| `Scope` | `Next` `Prev` `Adj` `N2` `N3` `P2` `All` `P3` `Adj2` `Skip`（见 `loadout-spec.md` §2） |
| `Rarity` | `Common` `Rare` `Epic` `Starter` |
| `BulletKind` | `Proj` `Beam` `Mine` `Field` `Chain` `Saw` `Hole` |
| `TriggerKind` | `None` `Hit` `Timer` `Expire` |
| `EnemyAi` | `Chaser` `Bomber` `Turret` |

## 表清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `Player.tsv` | 1 | 玩家基础属性 + 成长曲线 + 威胁缩放 + 分解收益 |
| `Gun.tsv` | 6 | 枪械 |
| `Bullet.tsv` | 17 | 子弹配件 |
| `Modifier.tsv` | 13 | 子弹向衍生件 |
| `GunModifier.tsv` | 9 | 枪械向衍生件 |
| `RarityWeight.tsv` | 3 | 三选一权重 |
| `Enemy.tsv` | 4 | **敌人（本轮新增）** |
| `Arena.tsv` | 1 | 竞技场地形 |
| `Timeline.tsv` | 6 | 刷怪时间轴（含 Boss 阶段行） |
| `Elite.tsv` | 1 | 精英强化系数与节奏 |
| `Boss.tsv` | 1 | Boss 数值 + 技能节奏 |

单行表（Player / Arena / Elite / Boss）**必须恰好 1 行数据**，多行会报错 ——
「取第一行」会让人以为改的第二行生效了。

## `Player.tsv`

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `hp` | float | 100 | 生命上限 |
| `walk` | float | 6.2 | 行走速度 m/s |
| `sprintSpeed` | float | 10.4 | 冲刺速度 |
| `sprintTime` | float | 0.55 | 冲刺持续秒数 |
| `sprintCooldown` | float | 1.4 | 冲刺冷却秒数 |
| `jumpHeight` | float | 1.3 | 跳跃高度 m |
| `gravity` | float | 22 | 重力 m/s² |
| `capsuleRadius` | float | 0.34 | 胶囊半径 m |
| `capsuleHeight` | float | 1.8 | 胶囊高度 m |
| `iFrames` | float | 0.25 | 受击无敌秒数 |
| `gunSlots` | int | 2 | 可携带枪数 |
| `bagSize` | int | 44 | 背包容量 |
| `healPickup` | float | 35 | 补给回血量 |
| `xpSquare` | int | 2 | 升级公式 `A·L²+B·L+C` 的 A |
| `xpLinear` | int | 5 | B |
| `xpFlat` | int | 8 | C |
| `hpScalePerThreat` | float | 0.008 | 威胁每 +1 的敌人生命倍率增量 |
| `dmgScalePerThreat` | float | 0.004 | 威胁每 +1 的敌人伤害倍率增量 |
| `huntAtThreat` | float | 88 | 进入「狩猎模式」的威胁阈值 |
| `salvageCommon` | int | 3 | 分解普通件换经验 |
| `salvageRare` | int | 6 | 分解稀有件 |
| `salvageEpic` | int | 9 | 分解史诗件 |

**升级公式**：`NeedFor(L) = xpSquare·L² + xpLinear·L + xpFlat`。
默认 2/5/8 与原 `2L²+5L+8` 完全一致（L1=15、L2=26、L10=258），由 dotnet 断言锁住。

**威胁缩放**：`HpScale = 1 + hpScalePerThreat × threat`。威胁 100 时血量 ×1.8、伤害 ×1.4。

## `Gun.tsv`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string,unique | `rifle` `smg` `shotgun` `sniper` `beam` `launcher` |
| `name` | string | 显示名 |
| `desc` | string | 一句话定位（菜单卡片用） |
| `slotCount` | int | **槽位数**（一格一件），6–12 |
| `magSize` | int | 弹匣容量 |
| `reloadTime` | float | 换弹秒数 |
| `fireInterval` | float | 基础击发间隔（秒） |
| `spreadBase` | float | 基础散射（度），加到每个投射物上 |
| `castCount` | int | **一次施法读取几个子弹**（霰弹枪 = 2） |
| `baseBullet` | string | 开局预置在第 1 槽的子弹 id |
| `color` | string | `#rrggbb`，枪模与 UI 用色 |
| `zoom` | float | 右键瞄准时的视距（越小倍率越高） |
| `model` | string | 第一人称枪模名（`_Game/Res/Model/<名>`）。原先硬编码在 `PlayerWeapons` 的 switch 里 |
| `starter` | bool01 | 旧起手标记，保留配置兼容；现菜单从全部 GunOrder 选择一把 |

starter 保留原校验约束，但不限制当前菜单可选范围；进入对局只创建选中的一把枪。

## `Bullet.tsv`

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

## `Modifier.tsv` / `GunModifier.tsv`

两者结构相同，只是分组存放（作用于子弹 / 作用于枪械）。
**所有字段都是「每层叠加量」**，`t` = 同名同域在一次结算里的叠加层数。

### 作用域

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `scope` | enum | `Next` | `Next` / `Prev` / `Adj` / `N2` / `N3` / `P2` / `All` / `P3` / `Adj2` / `Skip` |
| `cost` | int | 1 | 每颗实际受影响子弹的耗弹修正；允许负值减耗 |
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
| `multicast` | 本次多读 N 发（解析时**强制归到 `Next`**） |

**解析期自动纠正两条**（`SCfgLoader`，不报错）：

1. `multicast > 0` 而 `scope != Next` → 强制改成 `Next`（双重施放由物理后一格子弹触发）。
2. 枪械向件（`IsGunOnly`）→ 强制 `scope = All`。

## `Enemy.tsv`（本轮新增）

原先敌人的数值硬编码在 `GameRoot.cs` 的 6 个 `Kind*` switch 里、行为分支硬编码在
`Enemy.Update` 的 `Kind` switch 里。新增一种敌人要改 7 处，漏一处就静默退化成爬行者。
现在**加一种敌人 = 加一行**。

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `id` | string,unique | | 时间轴 `pool` 里引用这个 id |
| `name` | string | | 显示名（Toast / 遥测用） |
| `ai` | enum | `Chaser` | `Chaser` 贴身撞击 / `Bomber` 贴近自爆 / `Turret` 原地远程 |
| `model` | string | | 模型名（`_Game/Res/Model/<名>`）。缺件时回退胶囊占位 |
| `height` | float | 1 | 模型归一到的目标高度（米），碰撞体随之缩放 |
| `hp` | float | 60 | 基础生命（再乘威胁缩放与精英倍率） |
| `dmg` | float | 10 | 接触/远程伤害 |
| `speed` | float | 2 | 移速 m/s |
| `xp` | int | 8 | 击杀经验 |
| `contactRange` | float | 1.4 | 贴身判定距离（0 = 不做接触伤害） |
| `attackRange` | float | 0 | 远程/引爆触发距离（0 = 不用） |
| `attackCooldown` | float | 0 | 重复攻击/引爆冷却（0 = 一次性） |
| `shieldFacing` | float | 0 | 正面盾的朝向点积阈值（0 = 无盾） |
| `shieldMul` | float | 1 | 盾面挡住时（普通弹）的伤害系数 |
| `shieldPierceMul` | float | 1 | 盾面挡住时（穿透弹）的伤害系数 |

**四种敌人**：`Crawler`（基准，55/10/2）、`Brute`（盾卫，220 血带正面盾）、
`Bomber`（自爆，34 伤）、`Turret`（站桩远程，30m 射程）。

**`speed` 为什么是 2 而不是 6**：原设计文档写「6.5 / 3」，代码里已经降过速
（不降速玩家拉不开距离），这里落的是结算值。改之前先读 `gameplay-spec.md`。

## `Arena.tsv`

单张连续场地。**没有分区、没有门**。

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `width` | float | 100 | 场地 X 向尺寸（m） |
| `depth` | float | 100 | 场地 Z 向尺寸（m） |
| `wallHeight` | float | 8 | 四周墙高；墙实心、挡人挡弹 |
| `bossPadRadius` | float | 9 | 中央 Boss 台半径；也是掩体留空的基准 |
| `coverCount` | int | 18 | 掩体数量（固定种子，避开中央与出生点） |
| `highGroundCount` | int | 4 | 高台数量，均布于四边中点，带台阶 |
| `spawnPoints` | int | 16 | 沿外缘的环形刷怪点数 |
| `playerSpawnZ` | float | -38 | 玩家出生点的 Z 坐标（X 恒为 0） |

## `Timeline.tsv`

时间轴是本作**唯一的节奏来源**（`gameplay-spec.md` §2.1）。一行一个阶段，
`boss=1` 的那行是 Boss 阶段（决定 Boss 入场时刻，且**只能有一行**）。

| 字段 | 类型 | 说明 |
|------|------|------|
| `at` | float,ascending | 该阶段开始时刻（秒）。首条必须为 0 |
| `name` | string | UI 显示名（`开局` / `加压` / `混编` / `全谱` / `高压` / `BOSS`） |
| `pool` | `{A,B,C}` | 敌人池，**引用 `Enemy.tsv` 的 id** |
| `concurrency` | int | 场上同时存活上限。**这是可读性保护**，不是性能参数 |
| `interval` | float | 单只刷出间隔（秒） |
| `boss` | bool01 | 是否为 Boss 阶段。与 `Boss.tsv` 的 `bossAt` 冗余，以这里为准 |

**`pool` 里的 id 拼错会怎样**：`SCfgValidator` 在加载期报 Error 并拒绝启动。
（改造前是静默退化成 Crawler —— 数据看起来「生效了」其实是错的。）

## `Elite.tsv`

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `firstAt` | float | 300 | 首只精英的入场时刻（5:00） |
| `interval` | float | 90 | 之后每只的间隔 |
| `hpMul` | float | 4.0 | 生命倍率 |
| `dmgMul` | float | 1.5 | 伤害倍率 |
| `speedMul` | float | 0.9 | 速度倍率（比本体慢，给玩家反应时间） |
| `xpMul` | int | 6 | 经验倍率 |
| `scale` | float | 1.4 | 体积倍率；**碰撞体同步放大**（只改视觉会造成「看得见打不中」） |
| `healOnKill` | float | 15 | 击杀回复玩家生命。单图下这是中期唯一续航来源 |

精英总数由公式推导，不写死（`RunDirector.EliteCount`）：
`1 + ⌊(bossAt − firstAt) / interval⌋` = **4 只**（5:00 / 6:30 / 8:00 / 9:30）。

## `Boss.tsv`

原先是 `BossState` 里的 `const` 与 `BossView` 方法体里的字面量，
改护盾节奏要重新编译并重新打包 —— 而这恰恰是 Boss 手感调优最常动的数。

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `id` `name` | string | | 标识与显示名 |
| `hp` | float | 6000 | 生命上限 |
| `contactDamage` | float | 25 | 贴身伤害 |
| `contactRange` | float | 3.2 | 贴身判定半径 |
| `moveSpeed` | float | 2.5 | 移动速度（P3 ×1.6） |
| `pillars` | int | 4 | 能量柱数 |
| `pillarHp` | float | 800 | 单柱血量 |
| `breachTime` | float | 4 | 破防窗口秒数 |
| `breachDamageMul` | float | 1.5 | 破防期间的受伤倍率 |
| `shieldPeriod` | float | 18 | 护盾周期（开+关） |
| `shieldUpTime` | float | 6 | 周期里护盾开启的秒数 |
| `summonInterval` | float | 12 | 召唤间隔 |
| `summonCount` | int | 2 | 每次召唤数量 |
| `summonEnemy` | string | `Crawler` | 召唤的敌人 id（引用 `Enemy.tsv`） |
| `shockwaveInterval` | float | 20 | 冲击波间隔 |
| `shockwaveDamage` | float | 22 | 冲击波伤害 |
| `volleyInterval` | float | 3 | 扇形弹幕间隔 |
| `volleyCount` | int | 5 | 扇形弹数 |
| `volleySpeed` | float | 14 | 弹幕速度 |
| `volleyDamage` | float | 14 | 弹幕伤害 |
| `trackVolleyInterval` | float | 2.4 | P3 追踪弹幕间隔 |
| `trackVolleySpeed` | float | 16 | 追踪弹速度 |
| `trackVolleyDamage` | float | 16 | 追踪弹伤害 |
| `spikeInterval` | float | 4.5 | P2 地刺间隔 |
| `spikeDamage` | float | 18 | 地刺伤害 |
| `spikeTelegraphTime` | float | 1.2 | 地刺预警时长（**不能改到 0**，否则变成不可躲的随机伤害） |
| `bossAt` | float | 600 | Boss 入场时刻。冗余快照，**以 `Timeline.tsv` 的 `boss=1` 行为准** |
| `threatFullAt` | float | 600 | 威胁值到满的时刻 |

**两条默认值必须与代码一致**：`BossState` 保留一份不读表的默认值
（dotnet 断言走 `new BossState(hp)` 这条路径）。两边不一致会导致
「测试绿、实机是另一套节奏」。`SCfgValidator` + dotnet 断言双层锁住。

## `RarityWeight.tsv`

| `rarity` | `weight` |
|----|--------|
| `Common` | 60 |
| `Rare` | 30 |
| `Epic` | 10 |

## 校验清单（改数据后逐条确认）

1. `Gun.baseBullet` 指向的 id 必须能在 `Bullet.tsv` 里找到（否则开局无弹可用）。
2. 每个 `Modifier` / `GunModifier` 至少有**一个**非默认值字段，否则是占位垃圾数据。
3. 枪械向件不应有投射物字段（有也不会生效，属于数据错误）。
4. Next 仅覆盖物理后一格，Prev 仅覆盖物理前一格；空槽不传递，边界不环绕。
5. `Timeline.pool` 与 `Boss.summonEnemy` 里的 id 必须在 `Enemy.tsv` 里存在。
6. `Enemy` 的 `ai` 与配套字段必须自洽（`Bomber` 要有 `attackRange`、
   `Turret` 要有 `attackRange > 0` 且 `attackCooldown > 0`）。
7. 改任何数值后跑：
   ```powershell
   cd "<GAME:S>\tools\loadout-tests"; dotnet run -c Release
   ```
   断言里的期望值写死在测试中，数值被改坏会立刻变红。
8. 同步更新 `loadout-spec.md` / `gameplay-spec.md` 的对应表。
9. 改 `Timeline` / `Elite` 后必须跑 `-bench` 检查经验预算是否仍落在 13–17 级区间。

## 时间轴的契约（最容易改坏的地方）

| 规则 | 为什么 |
|------|--------|
| `Timeline` 首条 `at` 必须为 0 | 否则开局到第一条之间没有任何刷怪规格，`CurrentPhase` 为 null，场上会空着不动 |
| `threatFullAt` 建议等于 `bossAt` | 让「威胁满」与「Boss 入场」同时发生，玩家能感到两件事是一件事 |
| 精英上限由公式算，不写字段 | 写死的话改 `interval` 会忘记同步上限，出现「明明该出 4 只只出了 2 只」 |
| Boss 阶段 `concurrency` 要低于最后一条普通阶段 | Boss 战需要腾出精力应对 Boss，普通刷怪必须降档 |
| `pool` 名字必须与 `Enemy.tsv` 的 id 完全一致 | 拼错会被校验器拦下（不再静默退化成 Crawler） |

## 加载链路与导入

```
Assets/_Game/Res/Cfg/*.tsv
  → STsvImporter 导入为 TextAsset
  → Addressables 分组及标签
  → Bootstrap 等待 SRes.PreloadAll()
  → SDataLoader 的配置源按表名取已加载资源
  → SCfgLoader.Load → SCfgValidator.Validate → SData
```

Core 纯逻辑测试通过文件配置源读取同一套 TSV，不依赖 Unity。运行态不得回到 Resources.Load 旧路径。
.tsv.meta 必须保留 STsvImporter 的 ScriptedImporter 绑定，缺表或校验 Error 必须报错，不能用默认值掩盖。

数据有 6 枪、17 子弹、25 个弹丸修正和 9 个枪械修正。ChainItem.Level 是运行态实例等级，TSV 保存 Lv.1 基础定义；EffectiveBullet / EffectiveMod 由等级派生，不回写表或共享定义。精确升级规则见 loadout-spec.md。

经验拾取半径 1.5 米、无吸附/无到期、枪奖励概率 10% 与攻击前摇目前是代码规则，不应添加不存在的 Player.tsv 字段来描述它们。

## 新增一张表的流程

1. 在 `Assets/_Game/Res/Cfg/` 新建 `<表名>.tsv`（三行表头 + 数据行）
2. `S.Core/SCfgAddresses.cs` 加常量，并加进 `Required`
3. `S.Core/SData.cs` 加 `<X>Def` 类（字段默认值必须与出厂值一致）
4. `S.Core/SCfgLoader.cs` 加 `LoadXxx`，在 `Load()` 里调用
5. `S.Core/SCfgValidator.cs` 加 `CheckXxx`（跨表引用必须在这里断言）
6. 新增 Core 文件检查并更新 tools/loadout-tests/loadout-tests.csproj 的显式 Compile Include；同时登记新表的 Addressables 地址与标签。
7. 分别运行 scripts/check.ps1 -Task tests 和 -Task build；Task 不接受逗号列表。
