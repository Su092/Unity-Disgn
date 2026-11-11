# 蜘蛛侠纵横宇宙风 · 风格化载具（出租车 + 红色复古跑车）

`Blender Modle/` 下的载具测试件：两辆车共用同一套交付门与 lookdev 语言，
同场景并排验收。风格取自《蜘蛛侠：纵横宇宙》。设计取舍见 `report.md` /
`sportscar-spec.md`。

## 交付物

| 文件 | 说明 |
|---|---|
| `out/taxi.blend` | 出租车构建件：`GEO-TaxiSpider` |
| `out/Modle_Vehicle_SpiderTaxi.fbx` + `_basecolor.jpg` | 出租车 Unity 交付 |
| `out/sportscar.blend` | 跑车构建件：`GEO-SportSpider` |
| `out/Modle_Vehicle_SpiderSport.fbx` + `_basecolor.jpg` | 跑车 Unity 交付 |
| `out/duo.blend` | **同场景**：出租车在原点，跑车在 `(−6.5, 0, 0)` |
| `refs/sport-ref-*.png` + `chain-receipt.json` | 跑车链式参考图与生成回执 |
| `renders/sport-*.png` / `sport-silhouette.png` / `duo-*.png` | 单车 lookdev、剪影对拍图、双车场景 |
| `gate/` / `gate-sport/` | 两车各自的交付门回执 |

## 规格速览

| | 出租车 `GEO-TaxiSpider` | 跑车 `GEO-SportSpider` |
|---|---|---|
| 尺寸 mm | **5200 × 1900 × 1720** | **4200 × 1780 × 1215** |
| 三角面 | 11578 | 11672 |
| 壳 | 5（车身 1 + 轮 4） | 5 |
| 主色 | 黄漆 + 棋盘带 | 红漆 + 镀铬 + 敞篷舱 |
| 门回执 | `gate/manifest.json` | `gate-sport/manifest.json` |

跑车是**低趴敞篷**：甲板 758~830、翼子板峰压住轮拱、风挡顶 1215、
真舱口盲腔 + 双座 + 两个头枕鼓包、侧面一条镀铬排气、深色轮盘五辐镀铬轮。

## 先出参考图，再建模

参考图**串行**生成：先出 3/4 主视角，再把它的图片 URL 作为其余视角的 `image_urls` 输入。

```powershell
$B = "E:\SteamLibrary\steamapps\common\Blender\blender.exe"
$P = "e:\Unity Development\Blender Modle\spiderverse-taxi"

# 0) 链式参考图：anchor 先出，其余视角以它为参考
python ".cursor/skills/apimart-image/scripts/apimart_ref_chain.py" --plan "$P\refs\plan-sport.json"

# 0b) 量测（--ascii 直接看掩膜对不对）
& $B -b --factory-startup --python "$P\scripts\measure_ref.py" -- --ascii `
  "$P\refs\sport-ref-side.png"

# 0c) 渲剪影 + 与参考图对拍
& $B -b --factory-startup --python "$P\scripts\silhouette.py" -- `
  "$P\out\sportscar.blend" GEO-SportSpider "$P\renders\sport-silhouette.png" 6.2
& $B -b --factory-startup --python "$P\scripts\ref_compare.py" -- `
  "$P\refs\sport-ref-side.png" "$P\renders\sport-silhouette.png"
```

参考图只硬判 H/L 与最高点位置；逐点轮廓受漫画墨线与地面阴影干扰，只作记录。

## 复现

```powershell
$B = "E:\SteamLibrary\steamapps\common\Blender\blender.exe"
$P = "e:\Unity Development\Blender Modle\spiderverse-taxi"
$X = "E:\Unity Development\tools\blender_export_unity.py"
$G = "E:\Unity Development\tools\blender-gate.ps1"

# ① 出租车
& $B -b --factory-startup --python "$P\scripts\build_taxi.py"
& $B -b "$P\out\taxi.blend" --python $X -- --objects GEO-TaxiSpider "$P\out\Modle_Vehicle_SpiderTaxi.fbx"
& $G -Blend "$P\out\taxi.blend" -Fbx "$P\out\Modle_Vehicle_SpiderTaxi.fbx" `
  -Objects GEO-TaxiSpider -MinMm 5 -Expect "5200,1900,1720" -TolMm 3 `
  -MaxTris 60000 -NoBone -RequireFloor -UvUnwrap -Out "$P\gate"

# ② 红色复古跑车
& $B -b --factory-startup --python "$P\scripts\build_sportscar.py"
& $B -b "$P\out\sportscar.blend" --python $X -- --objects GEO-SportSpider "$P\out\Modle_Vehicle_SpiderSport.fbx"
& $G -Blend "$P\out\sportscar.blend" -Fbx "$P\out\Modle_Vehicle_SpiderSport.fbx" `
  -Objects GEO-SportSpider -MinMm 5 -Expect "4200,1780,1215" -TolMm 3 `
  -MaxTris 60000 -NoBone -RequireFloor -UvUnwrap -Out "$P\gate-sport"

# ③ 同场景合成 + 双车 lookdev（跑车偏移 −6.5 m X，不写进单车 FBX）
& $B -b --factory-startup --python "$P\scripts\compose_scene.py"
```

## 门回执

```text
出租车  RESULT PASS · blend/gates · uv/blend · fbx/gates · uv/fbx · fbx/contract
跑车    RESULT PASS · blend/gates · uv/blend · fbx/gates · uv/fbx · fbx/contract
```

| 门 | 出租车 | 跑车 |
|---|---|---|
| mesh | 11578 tris，开边/非流形/退化 = 0 | 11672 tris，同上 |
| buried | 启发式 1296 → 真判据 **0** | 启发式 1329 → 真判据 **0** |
| thickness | 最薄 11.99 mm | 最薄 **10.18 mm** |
| measure | 5200×1900×1720，偏 0 | 4200×1780×1215，偏 0 |
| uv | 530 岛 / 密度比 1.006 | 546 岛 / 密度比 1.0055 |
| contract | 10 项全过 | 10 项全过 |

## 目录

```text
spiderverse-taxi/
├── spec.md              # 出租车冻结规格
├── sportscar-spec.md    # 跑车冻结规格（§0b 参考图与量测落点）
├── report.md            # 验收报告（参考图两轮、体块重做、16 条坑）
├── scripts/
│   ├── build_taxi.py / build_sportscar.py
│   ├── measure_ref.py   # 参考图/剪影量测（--ascii 看掩膜）
│   ├── silhouette.py    # 渲纯黑剪影供对拍
│   ├── ref_compare.py   # 参考图 vs 剪影 差值
│   ├── probe_union.py   # 逐件 UNION 探针（带壳尺寸）
│   ├── scan_arch.py     # 轮拱参数 → 最小壁厚 扫描
│   ├── lookdev_taxi.py / compose_scene.py / detail_shots.py
│   └── inspect_*.py / qc_image.py
├── refs/                # 链式参考图 + plan + chain-receipt
├── out/                 # 单车 .blend / FBX / duo.blend
├── renders/             # look / sport / silhouette / duo / detail / qc
├── gate/                # 出租车门
└── gate-sport/          # 跑车门
```

## 已知边界

- 跑车敞篷是"盲腔 + 座垫/靠背/头枕"，没有仪表台与方向盘。
- 排气管避开轮拱切削圆柱；全长侧管会在拱壁留下薄切片。
- 甲板必须高于 `轮心 + 拱径`，否则轮拱会切穿上表面（第一版就踩了这个）。
- 参考图只硬判 H/L 与最高点位置；逐点轮廓受墨线与地面阴影干扰，只记录。
- 同场景偏移只写在 `duo.blend`，单车 FBX 仍在原点。
- 描边 / 网点 / 色散是渲染期对象，不进交付件。
