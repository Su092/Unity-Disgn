# codex跑车建模测试 · 红色经典敞篷跑车

只参考 `refs/` 里的四张跑车图，从零完成建模、数值门、渲染和 FBX 交付。

![参考 3/4](refs/sport-ref-anchor.png)

![模型 3/4](renders/hero.png)

## 成果

- **135 个网格对象 / 12996 tris**
- 整车 **4.48 × 2.02 × 1.13 m**，`zmin = 0`
- 单根 `GEO-Body`
- 9 个材质：红色车漆、镀铬、橡胶、黑色内饰、玻璃、银色条纹、红色尾灯、深色格栅、打孔金属
- FBX + 9 张 `*_basecolor.jpg`

## 参考图特征 → 模型

| 参考特征 | 模型落点 |
|---|---|
| 长车头、短车尾 | 20 截面 loft 车身，前后轴距 2.40 m |
| 圆头灯 + 镀铬圈 | `GEO-HeadlightRing*` + 玻璃灯罩 |
| 椭圆格栅 + 横条 | `GEO-GrilleRing` + 5 根镀铬横条 |
| 镀铬前后杠 | 圆柱保险杠 + 防撞柱 |
| 五辐黑轮 + 银轮唇 | 轮胎 torus + 轮辋 + 5 辐条 + 镀铬轮唇 |
| 侧排气管 | 镀铬管 + 打孔隔热罩 |
| 双座敞篷 | 深色座舱、桶座、方向盘、透明风挡 |
| 银色中央条纹 | 机盖/尾盖分段银色条 + 镀铬中心线 |

![正侧](renders/side.png)

![正前](renders/front.png)

![后 3/4](renders/rear34.png)

## 门结果

| 门 | 结果 |
|---|---|
| mesh | **pass** 135/135 |
| normals | **pass** 135/135 |
| selfint | **pass** 135/135 |
| buried-true | **pass** 135/135 |
| thickness | **pass** 7/7（最薄 16.24 mm） |
| measure | **pass** 4/4 |
| contract · blend | **pass** |
| contract · FBX | **pass** |
| wrapper `blender-gate.ps1 -ContractOnly` | **pass** |
| uv atlas | **fail（已知）**：全局平铺 UV |

## 形体对照

![正前对照](renders/compare-front.png)

![正侧对照](renders/compare-side.png)

正前 W/H：参考 `1.6877` / 模型 `1.7840`，差 `0.0962`。
正侧参考图带柔阴影，掩膜把阴影算进包围盒，比例不作为 pass/fail 依据。

## 交付

```text
out/sports_car.blend
export/Modle_RedRoadster.fbx
export/Modle_*_basecolor.jpg
manifest.json
spec.md
gate/*.json
```

FBX 使用工作区约定：Forward -Z / Up Y，`FBX All`，Bake Axis Conversion 关闭，
材质由 Unity 侧按同目录 `*_basecolor.jpg` 重建。

## 复现

```powershell
$root = 'E:\Unity Development\Blender Modle\codex跑车建模测试'
$b = 'E:\SteamLibrary\steamapps\common\Blender\blender.exe'

& $b -b --factory-startup --python (Join-Path $root 'scripts\build_car.py')
& $b -b --python (Join-Path $root 'scripts\render_views.py')

powershell -ExecutionPolicy Bypass -File 'E:\Unity Development\tools\blender-gate.ps1' `
  -Blend (Join-Path $root 'out\sports_car.blend') `
  -Fbx (Join-Path $root 'export\Modle_RedRoadster.fbx') `
  -NoBone -RequireFloor -ContractOnly
```

## 已知限制

- 低多边形风格化重建，翼子板是独立鼓包，不是连续冲压曲面。
- UV 是平铺投影，不适合烘焙/光照贴图。
- 没有悬挂、刹车盘、发动机内部、开合件、骨骼或动画。
- 135 个独立对象便于逐件验收，不是性能优化后的合并网格。
