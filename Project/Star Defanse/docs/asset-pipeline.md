# 素材生产管线 — 星轨防线

> 所有 AI 美术走 APIMart `gpt-image-2`，统一入口
> `unity/.cursor/skills/apimart-image/scripts/apimart_image.py`（工作区 `apimart-image` 同名 skill 同源）。
> 视觉标准见 `art-style.md`；本节只管「怎么产出、怎么落地、怎么校验」。

## 1. 铁律

| 铁律 | 原因 |
|------|------|
| **地形由 AI 生成，车道由代码绘制** | 让 AI「顺手画一条路」必然和 `sldata.json` 的 `path[]` 对不上（环形路口被画成捷径、拐角偏移） |
| **不先跑测试图验证链路** | 除非用户明确要求，或 API 真报错需要定位 |
| **新素材先加清单再执行** | 一次性命令散落会导致「这张图哪来的、怎么重跑」永久丢失 |
| **换图必须清 `.meta` 再重导入** | `AssetPostprocessor` 只在首次导入生效，旧 `.meta` 会让 Unity 沿用旧像素边距 → 九宫格切错 |
| **手写 API 调用必须照抄 DoH 逻辑** | 本机 DNS 把 `api.apimart.ai` 解析到不可达地址，症状是「提交成功但轮询永远超时」 |

## 2. 清单（`unity/tools/`）

| 清单 | 条目 | 用途 |
|------|------|------|
| `ui-redesign.json` | 17 | 主 UI 素材集（面板 / 按钮 / 卡片 / 图标），风格前缀在 `style` |
| `apimart-ui-c6.json` | 12 | 当前在用的 C6 白甲 UI 方案（`panel-a/b`、`panel-gold-a`、按钮与框） |
| `apimart-ui-c-variants.json` | 6 | C 方案变体对比（冷白 / 石墨 / 细金线…） |
| `apimart-ui-styles.json` | 5 | 早期风格探索（白甲 / 装甲框 / 军规） |
| `apimart-assets.json` | 76 | 全量素材（KV / 背景 / 立绘 / 图标 / 地图），`style` 为全局前缀；**已 gitignore** |
| `apimart-towers.json` | 8 | 按干员立绘派生 8 座塔 |
| `maps-terrain.json` | 4 | 纯地形（**不许画路**） |
| `maps-redesign.json` | 4 | 带车道的成品地图（历史版本，现由 `paint_lane.py` 二次生成） |
| `thumbs-redesign.json` | 4 | 关卡缩略图地形 |
| `ui-sprite-borders.json` | — | 九宫格边距记录（校验时写入/比对） |

统一结构：顶层 `style`（全局风格后缀）+ `assets[]`，
每项 `{ id, out, size, resolution?, prompt, no_global_style? }`。

## 3. 标准流程

### 3.1 UI 素材

```powershell
cd "E:\Unity Development\Project\Star Defanse\unity"

python .cursor/skills/apimart-image/scripts/apimart_image.py --manifest tools/apimart-ui-c6.json
python tools/ui_reset_meta.py      # 删 .meta，强制按新图重导入
python tools/ui_shrink.py          # 压到 512 / 256
python tools/make_plate_thin.py    # 生成窄条信息牌 plate-thin

powershell -ExecutionPolicy Bypass -File scripts/check.ps1 -Task verify
```

`ui_install.py` 负责把选定的方案拷进 `Assets/Resources/Art/UI/` 并统一命名；
`ui_style_compare.py` / `ui_c_compare.py` / `ui_c6_style.py` 只用于方案对比出图，不进运行时。

### 3.2 战场地图

```powershell
# 1) 只生成地形（prompt 里必须写清 "NO roads, NO lanes, NO path"）
python .cursor/skills/apimart-image/scripts/apimart_image.py --manifest tools/maps-terrain.json
python .cursor/skills/apimart-image/scripts/apimart_image.py --manifest tools/thumbs-redesign.json

# 2) 按真实 path 绘制车道（与 sldata.json 100% 对齐）
python tools/paint_lane.py     # -> level-map-1/2/3.jpg + map.jpg
python tools/paint_thumb.py    # -> level-starport/belt/nexus/crater.jpg
```

换地貌时只重跑第 1 步，路线永远不用管。车道线宽与颜色在 `paint_lane.py` 顶部常量里。

### 3.3 塔与模型

```powershell
python .cursor/skills/apimart-image/scripts/apimart_image.py --manifest tools/apimart-towers.json
python tools/tower_cut.py        # 切单个塔的立绘
python tools/tower_trim.py       # 去白边 / 统一画布
python tools/tower_overview.py   # 出 8 塔对照图（人工检查用）
```

3D 模型是外部制作后导入的 FBX（`Assets/Resources/Art/Models/`），不是生图产物。
导入规则与动画轨道剔除见 `technical-design.md` 的「关键实现约定」；
建模侧的数值门、契约门与导出约定见 `model-pipeline.md`。

## 4. 导入规则（`STAssetPostprocessor`）

| 资源 | 规则 |
|------|------|
| `Art/UI/*.png` | Sprite（Single），`spriteBorder = 短边 × 0.22`，不生成 mipmap |
| `Art/Backgrounds/*` | Sprite，压缩按平台默认 |
| `Art/Models/**/*.fbx` | 材质按 `basecolor` 贴图重建，缩放 1.0，不勾 `Apply Transform` |
| `Anim_*.fbx` | 剔除「末段为 `Yaw`」的轨道，保留其余后代轨道 |
| `Fonts/*` | 等线 Regular / Bold，动态字体 |

改动后必须 `check.ps1 -Task verify`：它会重写九宫格边距并逐项校验模型 / 动画 / 贴图 / 字体。

## 5. 验收

1. `check.ps1 -Task verify` → `RESULT 资源校验通过`。
2. `check.ps1 -Task build` → `build.log` 里 `RESULT Succeeded` / `ERRORS 0`。
3. `ST.exe -autoshot` → `INPUT / MODEL / FACING / SAVE / FX` 全 PASS，
   `UI SLICE n/n` 与 `UI TEXT n/n` 全绿。
4. 看 `Shots/01-menu.png` ~ `14-range-drag.png`，确认素材在实机里显示正常（不是错误页、不是空洞）。

## 6. 目录约定

| 用途 | 路径 |
|------|------|
| 运行时 UI 九宫格 / 图标 | `Assets/Resources/Art/UI/` |
| 背景 / 立绘 / 地图 / 缩略图 | `Assets/Resources/Art/Backgrounds/` |
| 3D 模型与动画 | `Assets/Resources/Art/Models/<模型名>/` |
| 已废弃的战斗位图 | `Assets/Resources/Art/Sprites/`（27 张，待清理） |
| 生图中间产物 | `tools/_terrain/`、`tools/_ui_backup/`（已 gitignore） |
| 已归档的旧试验 | `tools/_archive/`（`canvas/`、`TowerDesigns/`、`UiStyleTests/`、`UiC6/`、旧日志），已 gitignore |
| 截图 | `Shots/`（已 gitignore） |

### 关于 `tools/_archive/`

2026-11-10 清理：把工程根的四组过程产物整体移入 `tools/_archive/` 并从 Git 跟踪中移除
（原 87 MB 位图）。**文件都还在磁盘上**，需要时可原位还原：

| 归档项 | 内容 | 还原方式 |
|--------|------|----------|
| `TowerDesigns/` | 8 张四阶段塔设计表 + `Stages/` 32 张单体 + 总览 + 设计说明 | 移回工程根；`tower_cut.py` / `tower_trim.py` / `tower_overview.py` 用的是相对路径 |
| `UiStyleTests/` | 7 张风格对比图 + `gen/` 12 张 C6 素材 | 移回工程根；`ui_install.py`、`ui_borders.py`、`border_measure.py`、`ui_c_compare.py` 都写死 `UiStyleTests/` |
| `UiC6/` | 2 张 C6 试验面板 | 无脚本依赖，可直接查看 |
| `canvas/` | Cursor Canvas 元数据（自动生成） | 不需要还原 |
| `logs/` | 迁移前的 `build/verify/unity_*/ui_*` 日志 | 仅供参考，已过期（OUTPUT 指向旧路径） |

重新生图时这些目录会被清单重新创建（`.gitignore` 已忽略，不会重新入库）。

覆盖同名文件时 `.meta` 保留原 GUID，`Resources.Load<Sprite>("Art/UI/xxx")` 按名字加载不受影响；
但**九宫格边距必须靠 verify 重写**，否则新图会沿用旧边距。
