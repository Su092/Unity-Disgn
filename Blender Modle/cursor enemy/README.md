# cursor enemy · 参考图还原建模

参考图 `ref_crawler.png`（1254×1254，低模四足机械虫）→ Blender 低模资产 → Unity 可导入 FBX/GLB。

## 交付物

| 文件 | 说明 |
|---|---|
| `crawler.blend` | 构建件，单对象 `GEO-Enemy-Crawler` |
| `export/Modle_Enemy_Crawler.fbx` | Unity 交付（Forward −Z / Up Y / FBX All / 不含动画） |
| `export/Modle_Enemy_Crawler_basecolor.jpg` | 1024² 基色图（UV 图集内光栅化，非烘焙） |
| `export/crawler.glb` | 通用交换格式 |
| `spec.json` | **冻结规格**（全部毫米数字；改它再重跑构建） |
| `refs_out/` | 量测产物：掩膜、聚类、结构、机位、拟合回执 |
| `renders/hero.png` · `compare.png` | 同机位渲染与三联对照（参考 / 模型 / 轮廓叠合） |
| `gate/manifest.json` | 交付门回执 |

## 规格速览

| | 值 |
|---|---|
| 尺寸 (W×L×H) | **1474 × 2137 × 1387 mm** |
| 三角面 | **1292** |
| 壳 | **1**（UNION 成单壳，visor/蓝条为切入的凹槽） |
| 材质槽 | 7（orange / dark / grey / amber / blue / visor / cavity） |
| UV | 107 岛 / 0 重叠 / 密度比 1.0007 |
| 门 | `RESULT PASS`（blend+fbx 双通路、含契约门） |

## 复现

```powershell
$B = "E:\SteamLibrary\steamapps\common\Blender\blender.exe"
$P = "E:\Unity Development\Blender Modle\cursor enemy"

# 0) 参考图量测（系统 Python + PIL/numpy）
python "$P\scripts\measure_ref.py" "$P\ref_crawler.png" --ascii --json "$P\refs_out\measure.json"
python "$P\scripts\analyze_ref.py" "$P\ref_crawler.png"
python "$P\scripts\structures.py"

# 1) 建模（读 spec.json；含 UV、贴图、导出）
& $B -b --factory-startup --python "$P\scripts\build_crawler.py" -- stage=build

# 2) 机位定标（真实渲染 + 色相分类，约 1 分钟）
& $B -b "$P\crawler.blend" --python "$P\scripts\calibrate_camera.py" -- --write

# 3) 渲染 + 对拍
& $B -b --factory-startup --python "$P\scripts\build_crawler.py" -- stage=render res=1254
python "$P\scripts\compare.py" "$P\ref_crawler.png" "$P\renders\hero.png" "$P\renders\compare.png" "$P\renders\silhouette.png"

# 4) 交付门
powershell -ExecutionPolicy Bypass -File "E:\Unity Development\tools\blender-gate.ps1" `
  -Blend "$P\crawler.blend" -Fbx "$P\export\Modle_Enemy_Crawler.fbx" `
  -Objects GEO-Enemy-Crawler -MinMm 1.2 -Expect "1474,2137,1387" -TolMm 3 `
  -MaxTris 6000 -NoBone -RequireFloor -UvUnwrap -Out "$P\gate"
```

## 与参考图的一致性（数字，非目测）

口径：几何用无背景剪影图（避免地面接触阴影被算进主体），颜色用**色相角分类**
（`scripts/refclass.py`，只用 numpy，Blender 内置 Python 也能跑）。

| 判据 | 参考 | 模型 | 偏差 | 门限 |
|---|---|---|---|---|
| 投影宽高比 H/L | 0.7935 | 0.8191 | **0.0256** | ≤0.06 |
| visor 中心 | (0.805, 0.517) | (0.803, 0.442) | **0.078** | ≤0.06 |
| 蓝条中心 | (0.674, 0.198) | (0.667, 0.150) | **0.054** | ≤0.06 |
| 橙壳质心 | (0.461, 0.187) | (0.450, 0.224) | **0.049** | ≤0.06 |
| 侧条跨度 x | [0.026, 0.966] | [0.083, 0.927] | **0.057** | ≤0.06 |
| 腿带中心 | (0.435, 0.717) | (0.589, 0.665) | 0.206 | ≤0.06 ✗ |

腿带是唯一超限项，原因与处置见下节。

## 已知边界（写清楚，不当通过）

1. **腿带位置 0.206 超限**。参考图里腿带的 x 直方图四簇为 `3120/1601/—/5614/2198/—/—/—/1411/2929`，
   最左簇（远侧腿）最重 —— 说明参考图的机位看得到**远侧**腿带，而同一机位下模型的
   远侧腿带被近侧腿遮住。后视角（az 130–160）能让腿带对上，但那时 visor 或蓝条必丢一个
   （实测 az=130：腿带 0.06、visor 0.86）。单张参考图无法同时满足四项，本件按
   「visor + 蓝条 + 侧条 + 比例」优先，腿带位置记录为**已知偏差**。
2. **参考图无尺寸标注**，全部毫米由唯一一处标定（总高 1387 mm，游戏内敌人尺度）推得；
   像素→毫米不是测量，是标定 + 比例换算。
3. **蓝条与 visor 是凹槽不是贴片**。贴片两次尝试都失败并留档：
   内推 30 mm 会被 `buried_true` 判成 57 张真内部面；外贴 5 mm 会剩 2 张下表面落在壳体内。
   凹槽保持单壳，槽底自发光。
4. **贴图是「UV 图集内光栅化基色」**，不是 Cycles 烘焙。原因：本件材质全是纯色，
   烘焙的收益是 0，而烘焙引入的非确定性（采样/降噪）会让复现不稳定。
5. **相机机位是标定产物**（`refs_out/camera.json`，az=30 el=8 lens=85）。
   它同时影响 `build_crawler.py` 的取景解算；改几何后必须重跑 `calibrate_camera.py`。

## 目录

```text
cursor enemy/
├── ref_crawler.png              # 参考图（唯一输入）
├── spec.json                    # 冻结规格（毫米）
├── spec.md                      # 规格说明 + 验收判据
├── scripts/
│   ├── measure_ref.py           # 参考图量测（掩膜/轮廓/色块 bbox）
│   ├── analyze_ref.py           # 调色板聚类 + 空间分布
│   ├── structures.py            # 侧条路径/visor 多边形/腿带位置
│   ├── ascii_masks.py / ascii_body.py / scanlines.py  # 结构读图（文字化）
│   ├── refclass.py              # ★ 色相分类（唯一口径，numpy only）
│   ├── build_crawler.py         # ★ 建模 + UV + 贴图 + 导出 + 渲染
│   ├── calibrate_camera.py      # 机位定标（真实渲染 + 色相判据）
│   ├── calibrate.py             # 发光/基色标定
│   ├── fit_all.py / fit_shape.py / solve_aspect.py  # 比例反解（解析投影）
│   ├── compare.py               # ★ 参考 vs 模型 对拍（出一张三联图）
│   ├── measure_shot.py          # 单图量测（色块中心）
│   ├── probe_bool.py / probe_vent.py / debug_bool.py  # 布尔/贴合探针
│   └── silhouette_fit.py        # 归一化剪影 IoU（诊断用）
├── refs_out/                    # 量测与拟合产物
├── renders/                     # hero / silhouette / 四视角 / compare / calib
├── export/                      # FBX / GLB / basecolor.jpg
└── gate/                        # 门回执
```

## 构建期踩到并修掉的 6 个坑

| # | 坑 | 判据/证据 | 修法 |
|---|---|---|---|
| 1 | Blender 5.2 的 `EXACT` 布尔在共面输入上返回**空网格** | `body∪head` → v=0 | 改 `MANIFOLD`（实测 1 壳 / 0 开边），失败退回 `FLOAT` |
| 2 | 琥珀带在矮截面上把轮廓压出折返 → 端盖扇形三角自交 | `selfint=12` | 带厚按截面高度 clamp，`room<75 mm` 直接并入下裙 |
| 3 | 蓝条跨屋脊棱时单块四边形扎进壳内 | 露出面积 5% | 3×7 网格逐点取贴合点与法线 |
| 4 | 贴片扎进壳 → `buried_true` 报真内部面 | 57 张 | 改凹槽（槽底自发光），保持单壳 |
| 5 | `stage=render` 打开旧 .blend，保存的 1254² 盖掉 `res` | H/L 从 0.760 虚高到 0.894 | 渲染前显式重设分辨率，并加自动取景 |
| 6 | 屋脊棱面过窄 → 前坡交线处 0.23 mm 楔形薄片 | `thickness` min=0.23 mm | 屋脊点 0.30w→0.52w |
