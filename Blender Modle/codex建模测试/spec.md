# 木制哥特式教堂 · 规格与验收

## 1. 来源

- 参考图由 APIMart `gpt-image-2` 生成，链式主视角 + 三视图：
  - `refs/church-ref-hero.png`
  - `refs/church-ref-west.png`
  - `refs/church-ref-side.png`
  - `refs/church-ref-top.png`
- 提示词与任务 ID：`refs/plan-church.json`、`refs/chain-receipt.json`。
- 参考图是**概念图，不是标定图**。本规格的毫米值来自设计输入，不是照片反推。

## 2. 建筑体量（米制，1 BU = 1 m）

| 项 | 尺寸 / 位置 |
|---|---|
| 总长 X | 27.30 m（含台基外沿 -2.10 .. 25.20） |
| 总宽 Y | 15.40 m（含台基 ±7.70） |
| 总高 Z | 24.60 m（含尖顶十字） |
| 西塔 | 6.00 × 6.00，塔身 0.35 .. 15.00 |
| 八角尖塔 | 底半径 3.15，15.35 .. 23.50 |
| 中殿 | X 6.00 .. 20.00，墙外皮 Y ±4.65，檐口 7.20，脊 12.00 |
| 侧廊 | 单侧宽 2.30，墙外皮 Y ±6.95，檐口 4.20，内侧 5.85 |
| 东端半圆室 | 八边形，中心 X=20.00，半径 4.80，墙 0.35 .. 6.50，顶 8.80 |
| 西门廊 | X -1.85 .. 0.20，Y ±2.20，墙 0.35 .. 5.20，山墙顶 6.70 |
| 主门 | 尖券 2.35 宽 × 3.85 高，底 0.35 |
| 玫瑰窗 | 西面中心 Z=9.20，外半径 1.72，内半径 1.44 |
| 侧窗 | 4 开间 × 2 侧；侧廊窗 1.65 × 3.20，高侧窗 1.30 × 1.15 |
| 扶壁 | 每侧 4 道，下段 0.38 → 0.26，上段 0.26 → 0.18 |

整体 AABB：**27300 × 15400 × 24600 mm**，`zmin = 0.000 mm`。

## 3. 构件与材质

- 分件装配，**653 个网格对象 / 9224 tris**。
- 5 个材质槽：
  | 材质 | 用途 |
  |---|---|
  | `M_TimberDark` | 外露框架、扶壁、窗框、尖顶 |
  | `M_PlankPale` | 竖板墙、体量面板、玫瑰窗棂 |
  | `M_Shingle` | 屋面、瓦楞、尖塔 |
  | `M_Glass` | 尖券窗、玫瑰窗（带铅条菱格） |
  | `M_Iron` | 门铰、百叶底板、十字 |
- 纹理为程序化 512×512 JPG，打包进 `.blend`，并复制到 `export/` 供 Unity 按
  `Modle_*_basecolor.jpg` 重建材质。
- UV：全局箱式平铺投影（`world / 2 m`）；板缝、瓦行在整栋上保持同一实际尺度。

## 4. 门结果（本次运行）

| 门 | 结果 | 关键字段 |
|---|---|---|
| mesh | **pass** | 653/653；`nonmanifold_edges=0`、`degenerate_faces=0`、`loose_*=0` |
| normals | **pass** | 653/653；逐壳 `signed_volume > 0` |
| selfint | **pass** | 653/653；`pair_count=0` |
| buried-true | **pass** | 653/653；单壳按定理 0，多壳无真包含 |
| thickness | **pass** | 15/15；最薄 `GEO-NaveRoof_S = 153.1 mm`（阈值 20 mm） |
| measure | **pass** | 6/6；塔身 6000×6000×14650，尖塔 5820×5820×8150 |
| contract · blend | **pass** | 单位 / 变换 / 单根 / 命名 / tris / 材质 / UV 层 / 落地 |
| contract · FBX | **pass** | FBX 重新导入后同上；单根 `GEO-Plinth` |
| uv atlas | **fail（已知限制）** | UV 超出 [0,1]、岛重叠；本资产用平铺木纹，不用于烘焙/光照贴图 |

证据文件：

```text
gate/mesh.json
gate/normals.json
gate/selfint.json
gate/buried-true.json
gate/thickness.json
gate/measure-*.json
gate/aabb.json
gate/contract-blend.json
gate/contract-fbx.json
gate/wrapper/manifest.json
gate/uv.json
gate/ref-compare.json
```

## 5. 形体对照

只比轮廓比例，不冒充毫米级还原：

| 视图 | 参考 H/W | 模型 H/W | 差值 |
|---|---|---|---|
| 西立面 | 1.7704 | 1.5974 | -0.1730 |
| 侧立面 | 0.6285 | 0.9022 | +0.2737 |

结论：**形体是同一套木构哥特语言，但比例不等价**。参考图是长中殿大教堂，
本模型是紧凑单塔教堂；侧视 H/L 偏差 0.274，已列为已知限制，未用拉伸糊过去。

对照图：

- `renders/compare-west.png`
- `renders/compare-side.png`

## 6. 已知限制

1. 参考图为 AI 概念图，无相机标定；毫米值是设计输入。
2. 侧视比例与参考图不一致（见 §5）。
3. UV atlas 门 fail：全局平铺投影，适合无缝木纹/瓦片，不适合烘焙。
4. 653 个独立对象便于逐件验收，不是性能优化后的合并网格。
5. 逐件数值门通过；跨对象装配干涉未单独建门，隐藏交叠按设计保留。
6. 几何脚本不裁定结构强度。

## 7. 复现

```powershell
$b = 'E:\SteamLibrary\steamapps\common\Blender\blender.exe'
$root = 'E:\Unity Development\Blender Modle\codex建模测试'
$g = 'E:\Unity Development\.codex\skills\blender-asset-pipeline\scripts\blender_gate.py'

& $b -b --factory-startup --python (Join-Path $root 'scripts\build_church.py')
& $b -b (Join-Path $root 'out\church.blend') --python $g -- mesh --objects Church
& $b -b (Join-Path $root 'out\church.blend') --python $g -- normals --objects Church
& $b -b (Join-Path $root 'out\church.blend') --python $g -- selfint --objects Church
& $b -b (Join-Path $root 'out\church.blend') --python 'E:\Unity Development\tools\blender_buried_true.py' --
& $b -b (Join-Path $root 'out\church.blend') --python 'E:\Unity Development\tools\blender_contract.py' -- --max-tris 60000 --no-bone --require-floor --require-prefix
```

完整一键入口：

```powershell
powershell -ExecutionPolicy Bypass -File 'E:\Unity Development\tools\blender-gate.ps1' `
  -Blend (Join-Path $root 'out\church.blend') `
  -Fbx (Join-Path $root 'export\Modle_WoodenGothicChurch.fbx') `
  -NoBone -RequireFloor -ContractOnly
```
