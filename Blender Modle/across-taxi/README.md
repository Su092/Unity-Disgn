# across-taxi · 《蜘蛛侠：纵横宇宙》风格出租车

一套"参考图先行 → 量测 → 参数化建模 → 门检 → 风格化渲染 → 导出"的完整链路，产物是一辆
可交付的风格化纽约出租车（1 对象 / 5 壳 / 带 UV 与烘焙贴图）。

```
across-taxi/
├─ refs/            参考图（链式生成，1k）+ 量测原始输出 + 生成回执
├─ scripts/         build_taxi.py（几何）· lookdev.py（风格）· export_asset.py（交付）
│                   measure_ref.py / probe3.py / probe_front.py（量测）
│                   check_mesh.py（无头体检·第二意见）· diag_mesh.py（缺陷定位）
├─ out/             taxi.blend（成品）· taxi_look.blend（含描边/合成/布光）
│                   Modle_Vehicle_AcrossTaxi_basecolor.jpg · manifest.json
├─ renders/         look-*.png（成品图）· qc-*.png（过程自检）· cmp-*.png（同机位对比帧）
├─ export/          FBX / GLB / OBJ + MTL + basecolor + manifest(md5)
├─ qc/              visualreport 回执目录（overlay / sheet / 缺陷 crop）
├─ spec.md          **冻结尺寸**（唯一数值来源）
└─ report.md        验收报告（门回执 + 11 条实测坑 + 已知边界）
```

## 快速开始

```powershell
$blender = "E:\SteamLibrary\steamapps\common\Blender\blender.exe"
$p = "E:\Unity Development\Blender Modle\across-taxi"

# 1) 重建几何（约 22 s，含 5 张 QC 图）
& $blender -b --factory-startup --python "$p\scripts\build_taxi.py"

# 2) 风格化渲染（Freestyle 墨线 + 色散 + 同机位对比帧，约 95 s）
& $blender -b --factory-startup --python "$p\scripts\lookdev.py"

# 3) 导出交付件（FBX/GLB/OBJ + manifest+md5）
& $blender -b --factory-startup --python "$p\scripts\export_asset.py"
```

只想复核几何、不出图：给 `build_taxi.py` 加 `-- --no-render`；
只想要同机位对比帧：给 `lookdev.py` 加 `-- --cmp-only`。

## 关键数字

| 项 | 值 |
|---|---|
| 尺寸 | 5200 × 1950 × 2250 mm（误差 0） |
| 三角面 | 14 902（7 449 顶点 / 5 788 面） |
| 壳 | 5（车身 1 + 车轮 4） |
| 材质 / UV / 贴图 | 9 槽 / 1 层 UVMap / 1024² EMIT 烘焙 |
| 网格门 | `audit_mesh` **pass**（boundary/nonmanifold/degenerate/loose/selfint 全 0） |
| 尺寸门 | `audit_measure` **pass** |
| 同机位侧视 | IoU **0.9318** / Dice 0.9647 / 边界 3.85 px（verdict fail，原因见 report §5） |

## 建模要点（为什么长这样）

- **车头细节跨过车身端面**：车身端面在 ±2560，保险杠/格栅/大灯/车牌跨到 ±2600 ——
  否则细节会被埋在车身里面（UNION 后看不见，也不产生壳）。
- **轮拱内壁 552 mm**：轮胎内沿 575 mm，留 23 mm 间隙。内壁取 620 时轮胎会穿过内壁，
  `audit_mesh` 会报 136 对自交。
- **立柱靠刷漆不靠几何**：A/B/C 柱是把车厢上对应 X 区间的玻璃面刷回车漆；
  外贴镀铬条跟不平收分斜面就会浮空（实测壳数 1→3）。
- **棋盘带是真几何**：30 格、凸出车身 20 mm，布尔并进车身；不是贴图。
- **描边用 Freestyle**：inverted-hull 在 EEVEE Next 下没按预期剔除（实测整车涂黑两次）。

## 已知边界

见 `report.md` §7：车厢内部无几何（玻璃是不透明深色面）、顶灯无"TAXI"字（参考图即空白）、
描边/网点/色散属渲染层不进网格、轮毂无螺栓、门缝是贴面细条。

## 参考图来源

APIMart `gpt-image-2`，链式 5 视角（anchor + 4 视图），1k，回执 `refs/chain-receipt.json`。
