# 红色经典敞篷跑车 · 规格与验收

## 1. 来源

只使用 `refs/` 下的跑车参考图，不读取 `spiderverse-taxi` 的脚本、规格或已有模型。

- `refs/sport-ref-anchor.png`：3/4 主视角
- `refs/sport-ref-side.png`：正侧视
- `refs/sport-ref-front.png`：正前视
- `refs/sport-ref-rear34.png`：后 3/4

参考车特征：红色双座敞篷、长车头短车尾、圆头灯、椭圆格栅、镀铬前后保险杠、
五辐轮毂、侧排气管、黑色内饰、银色中央条纹、四个圆形尾灯。

## 2. 体量（米制，1 BU = 1 m）

| 项 | 数值 |
|---|---|
| 总长 X | 4.48 m（含前后保险杠） |
| 总宽 Y | 2.02 m（含轮胎） |
| 总高 Z | 1.13 m（风挡顶） |
| 车身主体 | 4.25 × 1.72 × 0.55 m |
| 轴距 | 2.40 m（前轴 +1.25，后轴 -1.15） |
| 轮胎 | 外径 0.68 m，宽 0.19 m，轮心 z=0.34 |
| 风挡 | 0.18 × 1.10 × 0.26 m |
| 格栅 | 椭圆 0.84 × 0.26 m |

整车 AABB：**4480 × 2020 × 1130 mm**，`zmin = 0.000 mm`。

## 3. 构件

- **135 个网格对象 / 12996 tris**，单根 `GEO-Body`。
- 车身：20 边 loft 闭合壳；四个翼子板鼓包；车门/机盖/尾盖分缝。
- 车轮：轮胎 torus + 轮辋圆柱 + 镀铬轮唇 + 5 根深色辐条 + 轮毂，四轮独立。
- 前脸：椭圆镀铬格栅环 + 黑底 + 5 根镀铬横条、两只圆头灯（镀铬环 + 玻璃）、
  小灯、镀铬前杠 + 防撞柱。
- 侧面：侧排气管 + 打孔隔热罩、侧通风口、门把手、银色中央条纹。
- 座舱：深色开口、红色围边、两张桶座 + 头枕、仪表台、方向盘、透明风挡 + 镀铬框、
  后视镜、折叠软顶。
- 尾部：四个圆形尾灯（镀铬环 + 红透镜）、镀铬后杠、双出排气、油箱盖、尾盖拉手。

## 4. 材质

| 材质 | 用途 |
|---|---|
| `M_PaintRed` | 红色车漆 |
| `M_Chrome` | 保险杠、灯圈、格栅、把手、轮唇 |
| `M_Rubber` | 轮胎 |
| `M_Interior` | 座椅、仪表台、软顶 |
| `M_Glass` | 风挡、灯罩（alpha 0.32） |
| `M_Silver` | 车身中央条纹 |
| `M_RedLens` | 尾灯透镜 |
| `M_DarkGrille` | 格栅底、轮辐、分缝 |
| `M_Perf` | 侧排气管隔热罩 |

纹理为程序化 256×256 JPG，打包进 `.blend`，并复制到 `export/` 供 Unity
按 `Modle_*_basecolor.jpg` 重建。

## 5. 门结果

| 门 | 结果 | 关键字段 |
|---|---|---|
| mesh | **pass** | 135/135；非流形/开边/退化/孤立点全 0 |
| normals | **pass** | 135/135；逐壳朝外 |
| selfint | **pass** | 135/135；`pair_count=0` |
| buried-true | **pass** | 135/135；单壳定理 + 多壳包含 |
| thickness | **pass** | 7/7；最薄风挡 16.24 mm（阈值 15 mm） |
| measure | **pass** | 4/4；车身 / 轮胎 / 风挡 / 格栅 |
| contract · blend | **pass** | 单位 / 变换 / 单根 / 命名 / tris / 材质 / UV 层 / 落地 |
| contract · FBX | **pass** | FBX 重新导入复核 |
| wrapper | **pass** | `blender-gate.ps1 -ContractOnly` |
| uv atlas | **fail（已知）** | 全局平铺 UV，不适配烘焙/光照贴图 |

证据：`gate/mesh.json`、`normals.json`、`selfint.json`、`buried-true.json`、
`thickness.json`、`measure-*.json`、`aabb.json`、`contract-blend.json`、
`contract-fbx.json`、`wrapper/manifest.json`、`uv.json`。

## 6. 形体对照

| 视图 | 参考 W/H | 模型 W/H | 差值 | 说明 |
|---|---|---|---|---|
| 正前 | 1.6877 | 1.7840 | +0.0962 | 前脸宽高比接近 |
| 正侧 | 2.4682 | 3.9464 | +1.4782 | 参考图带柔阴影，掩膜把阴影算进包围盒；模型剪影为透明通道，两者口径不一致 |

正前比例是有效对照；正侧的比例不作为 pass/fail 依据，只保留对照图。

## 7. 已知限制

1. 参考图为手绘/概念图，无相机标定；尺寸是设计输入。
2. 车身是低多边形风格化重建，翼子板是独立鼓包，不是连续冲压曲面。
3. UV 是全局平铺投影，UV atlas 门 fail；适合无缝材质，不适合烘焙。
4. 135 个独立对象便于逐件验收，不是性能优化后的合并网格。
5. 没有悬挂、刹车盘、发动机舱内部、可开合车门/机盖、骨骼或动画。
6. 跨对象装配干涉未单独建门；隐藏交叠按设计保留。

## 8. 复现

```powershell
$root = 'E:\Unity Development\Blender Modle\codex跑车建模测试'
$b = 'E:\SteamLibrary\steamapps\common\Blender\blender.exe'
$g = 'E:\Unity Development\.codex\skills\blender-asset-pipeline\scripts\blender_gate.py'

& $b -b --factory-startup --python (Join-Path $root 'scripts\build_car.py')
& $b -b --python (Join-Path $root 'scripts\render_views.py')
& $b -b (Join-Path $root 'out\sports_car.blend') --python $g -- mesh --objects SportsCar
& $b -b (Join-Path $root 'out\sports_car.blend') --python $g -- normals --objects SportsCar
& $b -b (Join-Path $root 'out\sports_car.blend') --python $g -- selfint --objects SportsCar
& $b -b (Join-Path $root 'out\sports_car.blend') --python 'E:\Unity Development\tools\blender_buried_true.py' --
```
