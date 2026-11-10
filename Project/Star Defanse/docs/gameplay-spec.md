# 玩法与数值规范 — 星轨防线

> 数值镜像自 `unity/Assets/Resources/Data/sldata.json`。**改数值必须同步改本文**。
> 运行时逻辑在 `unity/Assets/Scripts/Core/RunState.cs`，查询在 `STData.cs`。

## 1. 屏幕与输入

| 项 | 值 |
|----|-----|
| 逻辑分辨率 | 1080×1920（战场坐标 = 像素坐标，y 向下为正） |
| 默认窗口 | 540×960（`Screen.SetResolution`，命令行可覆盖） |
| 朝向 | 竖屏锁定 |
| 战场板范围 | `boardTop = 190`，`boardBottom = 1560`（塔台与车道都在此区间内布局） |
| 输入 | 旧 Input Manager；点击 / 拖拽由 `STInput.cs` 自绘命中，不用 UGUI 事件系统 |

快捷键（桌面调试用）：

| 键 | 作用 |
|----|------|
| `空格` / `Esc` | 暂停菜单（继续 / 重开 / 退出） |
| `1` / `2` / `3` | 1×、2×、3× 速度 |
| `S` / `U` / `M` | 召唤 / 强化 / 静音 |

## 2. 全局调参（`sldata.json` → `tuning`）

| 字段 | 值 | 含义 |
|------|-----|------|
| `coreHp` | 20 | 核心耐久 |
| `startGold` | 40 | 开局金币 |
| `maxTowerLevel` | 4 | 塔等级上限 |
| `initialUnlocked` | 6 | 开局解锁塔台数 |
| `summonsPerUnlock` | 3 | 每召唤几次解锁 1 个新塔台 |
| `levelDmg` | 1.8 | 每级伤害倍率（幂增长） |
| `levelRate` | 1.1 | 每级攻速倍率 |
| `levelRange` | 1.05 | 每级射程倍率 |
| `summonBase` / `summonGrowth` | 10 / 1.28 | 召唤基础价与增长系数 |
| `upgradeBase` / `upgradeGrowth` | 24 / 1.42 | 强化基础价与增长系数 |
| `waveInterval` | 24 s | 波次间隔（也是单波最长时长） |
| `firstWaveDelay` | 4 s | 开局到第一波的等待 |
| `waveBonusBase` / `waveBonusPerWave` | 8 / 3 | 每波结束金币 = base + n×perWave |
| `guardsPerTower` | 2 | 每座拦截塔生成的拦截单位数 |
| `guardGap` | 96 | 相邻拦截单位的里程间隔（像素） |
| `heroDmg` / `heroRate` / `heroRange` / `heroSpeed` | 15 / 1.5 / 235 / 320 | 英雄攻击力、次/秒、射程、移速 |

## 3. 公式

```
召唤价   = round(10 × max(1.02, 1.28 × (1 + summonGrowthMul)) ^ summons)
强化价   = round(24 × 1.42                    ^ upgrades)
解锁塔台 = min(塔台总数, 6 + floor(summons / 3))
塔伤害   = max(1, 职业dmg × 1.8^(等级-1) × (1 + dmgMul + reinforce))
塔射程   = round(职业range × 1.05^(等级-1) × (1 + rangeMul))
塔攻速   = max(0.05, 职业rate × 1.1^(等级-1) × (1 + atkSpeedMul))
爆炸半径 = 职业splash × (1 + splashMul) × 1.05^(等级-1)
拦截HP   = round(职业guardHp × 1.8^(等级-1) × (1 + guardHpMul))
拦截重建 = 职业respawn × (1 + guardRespawnMul)
每波金币 = 8 + 3 × 波次序号
```

`mul` 与干员自带的 `mods` 都直接加进同一个 `mod` 字典（**加法叠加**，不是乘法），
所以 3 条 +18% 攻速 = 1.54×，不是 1.18³。

## 4. 职业（4 种，`classes`）

| id | 名称 | 定位 | dmg | rate(次/s) | range | splash | 转向(s) | 拦截HP/DPS/重建 | 阻挡 |
|----|------|------|-----|-----------|-------|--------|---------|----------------|------|
| `assault` | 突击 | 快速单体 | 9 | 2.6 | 190 | — | 6.5 | — | — |
| `sniper` | 狙击 | 高伤单体 | 46 | 0.62 | 380 | — | 2.8 | — | — |
| `siege` | 重炮 | 范围爆破 | 26 | 0.55 | 265 | 78 | 2.2 | — | — |
| `intercept` | 拦截 | 路径阻挡 | — | — | — | — | 5.0 | 160 / 10 / 7.0 | 2 |

- **拦截塔**不直接攻击：它在**最近的轨道上**生成 `guardsPerTower` 个拦截单位，
  按里程锚定（`baseD ± guardGap`，且夹在车道内），挡路并持续消耗，死亡后按 `respawn` 重建。
- 所有塔的弹道类型由职业决定：`assault` → bullet，`sniper` → beam，`siege` → shell（落点爆炸）。

## 5. 干员（8 名，`operatives`）

每名干员 = 1 个职业 + 1 条被动 + 2 条专属初始词条池。

| id | 名称 | 称号 | 职业 | 被动（`trait`） | 词条池 |
|----|------|------|------|----------------|--------|
| `ran` | 岚 | 离子先锋 | assault | 攻速 +10% | `a_overclock` `u_supply` |
| `zero` | 零式 | 红瞳双持 | assault | 伤害 +8% | `a_crit` `u_hero` |
| `vega` | 维加 | 深空游隼 | sniper | 射程 +12% | `s_far` `u_shred` |
| `sera` | 赛拉 | 静默之光 | sniper | 伤害 +12% / 攻速 −8% | `s_pierce` `s_exec` |
| `grom` | 格洛姆 | 轨道之锤 | siege | 伤害 +10% / 攻速 −10% | `g_aoe` `g_dmg` |
| `chaos` | 卡俄斯 | 星爆工程师 | siege | 爆炸半径 +8% | `g_burn` `u_frost` |
| `ella` | 艾拉 | 棱镜壁垒 | intercept | 拦截单位生命 +10% | `i_guard` `i_leak` |
| `nova` | 诺娃 | 蜂群母体 | intercept | 重建时间 −10% | `i_fast` `a_killgold` |

**编队规则**：1–4 名（`STMain` 存 `PlayerPrefs` 的 `starlane.formation`）。
编队决定两件事 —— 召唤池（只能抽到编队里的干员）、强化池（编队职业的词条 + 通用词条）。

## 6. 词条（18 条 + 1 条兜底，`affixes`）

抽卡时从**编队职业词条 + 通用词条**中抽 3 张，**已拥有的不再出现**；
不足 3 张时用其余未拥有词条补齐；全部拿完后兜底给 `u_reinforce`（可重复）。

| 家族 | 通用（6） | 突击（3） | 狙击（3） | 重炮（3） | 拦截（3） |
|------|-----------|-----------|-----------|-----------|-----------|
| 词条 | 补给协议 +25 金/波<br>精简流程 召唤涨价 −25%<br>回收协议 合成返还 20 金<br>冻结弹头 25% 减速 45%/2 s<br>英雄特训 英雄伤害 +50% 射程 +20%<br>破甲弹 受击伤害 +6%/层，最多 3 层 | 超频协议 攻速 +18%<br>破绽锁定 暴击率 +18%，暴伤 180%<br>战场掠夺 击杀 +2 金 | 穿甲弹 无视 50% 护甲，狙击伤害 +15%<br>精准处决 生命 <20% 双倍伤害<br>超视距校准 全体射程 +15% | 广域爆裂 爆炸半径 +30%<br>灼烧装药 30% 概率 8/s 灼烧 3 s<br>高爆核心 全体伤害 +20% | 强化拦截 拦截 HP +50%、DPS +30%<br>快速重建 重建 −40%<br>缓冲护盾 核心每击 −1（最低 1） |

`mod` 键（`DefaultMods` 全集）：`dmgMul` `atkSpeedMul` `rangeMul` `critChance` `critMul` `goldPerKill`
`waveBonus` `leakReduce` `pierce` `sniperDmgMul` `execute` `splashMul` `burnChance` `burnDps` `burnDur`
`guardHpMul` `guardDmgMul` `guardRespawnMul` `summonGrowthMul` `mergeRefund` `frostChance` `frostSlow`
`frostDur` `heroDmgMul` `heroRangeMul` `shredPerHit` `shredMax` `reinforce`。
新增词条只能复用这些键，否则要同时改 `RunState.StatsOf` 的读取处。

## 7. 敌人（5 种，`enemies`）

| id | 名称 | HP | 速度 | 护甲 | 攻击 | 奖励 | 漏怪扣血 | 半径 |
|----|------|-----|------|------|------|------|---------|------|
| `grunt` | 残骸机兵 | 78 | 52 | 0 | 7 | 4 | 1 | 32 |
| `runner` | 疾影无人机 | 54 | 86 | 0 | 5 | 4 | 1 | 27 |
| `tank` | 重甲巡洋 | 350 | 37 | 3 | 13 | 8 | 2 | 37 |
| `elite` | 精英 · 破阵者 | 1550 | 34 | 5 | 24 | 30 | 4 | 52 |
| `boss` | 旗舰 · 湮灭级 | 8400 | 27 | 9 | 45 | 90 | 9 | 68 |

`boss` 额外有 `slowResist = 0.5`（减速效果减半）。同车道内按顺序排队，不互相穿模。

## 8. 波次（10 波固定）

| 波 | 编队（类型 ×数量 @延迟 / 间隔） |
|----|------|
| 1 | grunt×4 @0/0.7、grunt×4 @8/0.7 |
| 2 | grunt×6 @0/0.6、runner×3 @7/0.5 |
| 3 | grunt×5 @0/0.6、runner×4 @6/0.5、tank×1 @12/1.0 |
| 4 | grunt×6 @0/0.5、runner×5 @5/0.45、tank×2 @10/2.0 |
| 5 | **elite×1** @0/1.0、grunt×8 @3/0.45、runner×4 @10/0.4 |
| 6 | runner×8 @0/0.35、tank×3 @4/1.6、grunt×6 @9/0.5 |
| 7 | tank×4 @0/1.4、grunt×8 @3/0.45、runner×6 @10/0.35 |
| 8 | **elite×1** @0/1.0、tank×4 @4/1.3、runner×8 @8/0.3 |
| 9 | **elite×2** @0/5.0、runner×10 @3/0.28、tank×4 @9/1.2 |
| 10 | **boss×1** @0/1.0、elite×2 @6/4.0、tank×4 @10/1.0、runner×8 @12/0.3 |

- 上一波清完立即进入下一波；未清完则按 `waveInterval = 24 s` 硬推进。
- 强化（3 选 1）在任何时刻点「强化」按钮触发，不消耗波次。

## 9. 关卡（4 关，`levels`）

| # | id | 名称 | 车道点数 | hp | speed | reward | 缩略图 |
|---|----|------|---------|-----|-------|--------|--------|
| 1 | `starport` | 星港回廊 | 33 | 1.10 | 1.00 | 1.00 | `level-starport` |
| 2 | `belt` | 陨带断层 | 32 | 1.28 | 0.98 | 1.15 | `level-belt` |
| 3 | `nexus` | 虫洞枢纽 | 10 | 2.60 | 1.12 | 1.20 | `level-nexus` |
| 4 | `crater` | 陨石外环 | 46 | 3.40 | 1.15 | 1.35 | `level-crater` |

- 每关 14 个塔台（`platforms`），开局解锁 6 个，全部铺满需召唤 24 次。
- `nexus` 只有 10 个路径点：短而急的折线，靠高倍率 hp 撑难度。
- 战场地图 `level-map-1/2/3` + `map` 与 `path` 严格对齐（车道由 `tools/paint_lane.py` 按 path 绘制）。

## 10. 胜负与存档

- **胜利**：10 波全部清空且核心耐久 > 0 → 结算（星级按核心剩余血量）。
- **失败**：核心耐久 ≤ 0 → 结算（记录到达波次、击杀、漏怪、时长、金币、召唤/强化次数）。
- 通关记录按关卡数存 `PlayerPrefs`（长度随关卡数增长，最后一关可落盘，`SAVE RESULT` 校验）。
- 局内模拟完全确定性：`mulberry32` + `SeedValue`，同种子同操作必得同结果。

## 11. 待定 / 已知偏差

- 结算星级阈值目前按核心剩余比例直算，未做过数值调优。
- `nexus` 的 10 点路径是否过于简单，需实机对局验证（见 `../breakdown/01-baseline-audit.md`）。
- `Resources/Art/Sprites/` 下 27 张战斗图片已不被运行时使用（战斗走 3D 模型），
  仅 `STBuild.CheckSprites` 还在校验，清理与否待定。
