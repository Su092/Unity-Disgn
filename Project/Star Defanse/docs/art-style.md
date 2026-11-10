# 视觉规范 — 深空赛璐璐

> **唯一设计依据**。改素材前先读这里，改完同步更新。
> 本文件已从工程内 `Docs/ART-STYLE.md` 迁入枢纽，工程内不再保留副本。

## 风格定义

**深空赛璐璐（Deep Space Cel）**：日本动画赛璐璐上色 + 星际舰队仪表盘的结合。

与更早版本的差别 —— 旧版是「细霓虹发光线」的赛博朋克（靠 glow 出效果），
现在靠**厚黑描边 + 平涂双色 + 硬边高光**出效果：轮廓先立住，颜色再分块，不用柔光。
这正是 3D 模型（`StarLane/ModelLit` 赛璐璐着色器）的语言，UI 与模型因此统一。

### 四条铁律

1. **厚黑描边**：所有可交互元素都有一圈近黑外描边，宽度约为素材短边的 2–3%。
   描边色 `#07040F`，不是纯黑，带一点冷紫。
2. **平涂双色**：每个面只用两个色阶，交界是**硬边直线**，不做渐变。
   上半部亮 `#1E1A46`，下半部暗 `#12102B`。
3. **硬边高光**：一条锐利的亮色带（`#D8F4FF` 或主色亮部），斜切 45°，不透明度 0.35–0.5。
   **不要**径向柔光、不要外发光。
4. **切角造型**：矩形面板切掉四角（倒角 6–14 px），不用大圆角。
   圆形按钮保留正圆，但同样加厚描边 + 内圈硬边高光弧。

### 调色板

| 用途 | 色值 | 说明 |
|------|------|------|
| 星空底 | `#0A0718` | 场景最暗处 |
| 面板亮 | `#1E1A46` | 面板上半 |
| 面板暗 | `#12102B` | 面板下半 |
| 描边 | `#07040F` | 所有轮廓 |
| 主强调 | `#4FF3FF` | 青，品牌色 |
| 副强调 | `#FF3DAE` | 品红，警示 / 精英 |
| 金色 | `#FFD166` | 货币、稀有 |
| 高光 | `#D8F4FF` | 硬边高光、文字 |
| 次文字 | `#9B93C8` | 说明文字 |

职业色（`classes[].color`）：突击 `#4FF3FF`、狙击 `#A78BFF`、重炮 `#FFAE3A`、拦截 `#5BE39A`。

## 布局（保持不变）

布局沿用既有结构，只换皮肤：

- **主菜单**：标题左上，底部一宽两窄三个按钮。
- **战斗 HUD**：左上三块信息牌（关卡 / 波次 / 金币）竖排；左侧三个圆形按钮（暂停 / 倍速 / 帮助）竖排；
  右上编队头像竖排；左下强化卡；右下召唤大圆钮；底部中央核心耐久条。
- **关卡选择**：竖排关卡卡（缩略图 + 名称 + 难度 + 状态）。
- **编队**：两列干员卡。

## 素材规格

### 九宫格（`Art/UI/`）

> **边距规则**：`spriteBorder = 贴图短边 × 0.22`，由 `STBuild.FixUiBorders`
> 在每次资源校验时自动写入。运行时 `STUi.FitSlice` 再按「素材短边 ↔ 控件短边」等比缩放，
> 所以同一张素材在 968 px 弹窗和 72 px 信息牌上都不会被压扁，切角永远是 45°。
>
> **为什么不做逐边实测**：这批素材有硬边阴影分界，自动判据会把整块内胆误判成装饰
> （实测四个边都顶到 45% 上限）。固定比例 + 运行时等比缩放是唯一稳定的组合。

| id | 尺寸 | 边距 | 用途 |
|----|------|------|------|
| `panel` | 542×302 | 66 | 通用面板（弹窗、卡片底） |
| `panel-gold` | 608×428 | 94 | 金色强调面板（结算胜利） |
| `button-primary` | 609×141 | 31 | 主按钮（青色） |
| `button-gold` | 722×198 | 44 | 金按钮（召唤 / 强化） |
| `chip` | 530×138 | 30 | 词条胶囊 |
| `bar` | 540×77 | 17 | 耐久条底槽 |
| `card` | 417×579 | 92 | 干员卡竖幅 |
| `frame-plate` | 554×161 | 35 | 大幅信息牌 |
| `plate-thin` | 512×160 | 32 | 窄条信息牌专用（HUD 左上三块、核心耐久） |
| `frame-round` | 512×503 | — | 圆形按钮外框 |

**`plate-thin` 为什么单独做一张**：`frame-plate` 的装饰带（切角 + 45° 玻璃反光 + 端头凹槽）
实测占短边一半以上。九宫格四角是 1:1 绘制的，塞进 72 px 高的 HUD 信息牌只有两种结局 ——
要么四角之和超过高度被 Unity 强行压缩（整块压扁），要么边距吃掉一半内容区（文字压在花纹上）。
`plate-thin` 把装饰带压到 20%，内容区 448×96 足够放 30 px 字。
生成脚本：`python tools/make_plate_thin.py`。

### 图标（`Art/UI/`，透明背景）

`icon-star` `icon-coin` `icon-crystal` `icon-pause` `icon-speed` `icon-help` `icon-arrow` `icon-book`
—— 统一 128 px 高、正方形画布、居中。

### 背景（`Art/Backgrounds/`）

| id | 尺寸 | 说明 |
|----|------|------|
| `menu-kv` | 1024×1536 | 主菜单主视觉 |
| `battle-backdrop` | 1024×1536 | 战场天空幕（星云 + 行星） |
| `elite-threat` | 660×990 | 精英威胁插画 |
| `boss-threat` | 660×990 | BOSS 威胁插画 |
| `op-*` | 660×990 | 8 名干员立绘 |
| `level-*` | 960×640 | 4 张关卡缩略图（3:2） |
| `level-map-*` | 1080×1920 | 4 张战场地图（全部星球表面：月面 / 冰原高地 / 晶簇盆地 / 火星红壤） |

### 3D 模型（`Art/Models/`，按模型分目录）

`tower_assault` `tower_sniper` `tower_siege` `tower_intercept`（各含 4 个等级形态）、
`enemy_grunt` `enemy_runner` `enemy_tank` `enemy_elite` `enemy_boss`、
`hero` `guard` `core` `spawn`；动画为独立 `Anim_*.fbx`。

### 不再使用

`Art/Sprites/` 下 27 张塔 / 单位图片**已不被运行时使用**（战斗走 3D 模型，
只有 `STBuild.CheckSprites` 还在校验）。文件保留不动，待确认后连同校验一起移除。

## 提示词模板

UI 素材共用风格前缀（清单 `style` 字段）：

```
Japanese cel-shaded anime game UI asset, VERY THICK near-black ink outline
(heavy bold contour, at least 3 percent of the asset width, color #07040F),
flat two-tone hard-edged shading with absolutely NO gradients and NO outer glow,
one crisp 45-degree specular highlight band, chamfered 45-degree corners,
deep space sci-fi, clean vector-like edges, high contrast, bold graphic look,
no text, no letters, no numbers, no watermark, no logo, no soft bloom
```

地图与缩略图**不用**这个前缀（会把 UI 风格带进地形），改为逐条写清地貌与「不要路」。

## 交付检查

- 四条铁律逐条对一遍（描边 / 双色 / 硬边高光 / 切角）。
- 面板类：四边之和 < 最小使用高度；不行就另做一张窄版（参考 `plate-thin`）。
- 图标类：透明背景，128 px 高，边缘不带柔光。
- 换素材后跑 `check.ps1 -Task verify`（重写边距）+ `ST.exe -autoshot`（`UI SLICE` / `UI TEXT` 全绿）。
