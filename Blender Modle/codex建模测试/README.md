# codex建模测试 · 木制哥特式教堂

从 **APIMart 生成参考图** 到 **用 `blender-asset-pipeline` 完成分件建模、数值门、渲染、FBX 交付** 的一次完整走通。

![参考图 3/4](refs/church-ref-hero.png)

![模型 3/4](renders/hero.png)

## 1. 这次做了什么

```text
参考图（4 视角，链式一致性）
  → 规格与体量（27.3 × 15.4 × 24.6 m）
  → 分件建模（653 对象 / 9224 tris）
  → 逐件数值门（mesh / normals / selfint / buried-true / thickness / measure）
  → 契约门（.blend + FBX 两条通路）
  → 渲染对照（hero / side / west）
  → FBX + 5 张 basecolor 贴图 + manifest
```

## 2. 参考图

用 `apimart_ref_chain.py` 链式生成：anchor 先出，其余视角以 anchor 的 URL 为参考，
保证是同一座建筑。提示词、任务 ID、URL 都在 `refs/`。

| 视角 | 文件 |
|---|---|
| 3/4 hero | `refs/church-ref-hero.png` |
| 西立面 | `refs/church-ref-west.png` |
| 南侧立面 | `refs/church-ref-side.png` |
| 屋顶俯视 | `refs/church-ref-top.png` |

![西立面参考](refs/church-ref-west.png)

![南侧参考](refs/church-ref-side.png)

## 3. 模型

单西塔 + 中殿 + 双侧廊 + 八角半圆室 + 西门廊。

**木构读法**

- 竖板墙 + 外露深色框架（竖柱 / 腰线 / 檐口压条）
- 尖券窗、尖券门、玫瑰窗（12 辐 + 中心毂）
- 4 开间 × 2 侧扶壁，退台 + 小尖顶
- 中殿双坡屋面 + 侧廊单坡屋面 + 八角尖塔 + 十字
- 程序化木纹 / 板缝 / 瓦行 / 铅条玻璃纹理

![侧立面](renders/side.png)

![西立面](renders/west.png)

## 4. 门结果

| 门 | 结果 | 说明 |
|---|---|---|
| mesh | **pass** | 653/653；非流形 / 开边 / 退化 / 孤立点全 0 |
| normals | **pass** | 653/653；逐壳 |
| selfint | **pass** | 653/653；`pair_count=0` |
| buried-true | **pass** | 653/653；单壳定理 + 多壳包含 |
| thickness | **pass** | 15/15；最薄 153.1 mm |
| measure | **pass** | 6/6；塔身 / 尖塔 / 墙 / 半圆室 / 门廊 |
| contract · blend | **pass** | 单位 / 变换 / 单根 / 命名 / tris / 材质 / UV 层 / 落地 |
| contract · FBX | **pass** | FBX 重新导入复核；单根 `GEO-Plinth` |
| uv atlas | **fail（已知）** | 全局平铺 UV，不适配烘焙/光照贴图 |

完整数字见 `spec.md` 与 `gate/*.json`。

## 5. 形体对照

![西立面对照](renders/compare-west.png)

![侧立面对照](renders/compare-side.png)

参考图是长中殿大教堂，本模型是紧凑单塔教堂。侧视 H/L：
**参考 0.6285 / 模型 0.9022（差 +0.2737）**。这条偏差没有被“拉长糊过去”，
作为已知限制保留。

## 6. 交付物

```text
out/church.blend
export/Modle_WoodenGothicChurch.fbx
export/Modle_TimberDark_basecolor.jpg
export/Modle_PlankPale_basecolor.jpg
export/Modle_Shingle_basecolor.jpg
export/Modle_Glass_basecolor.jpg
export/Modle_Iron_basecolor.jpg
manifest.json
```

FBX 按工作区约定：**Forward -Z / Up Y**、`FBX All`、`Bake Axis Conversion` 关闭、
材质由同目录 `*_basecolor.jpg` 在 Unity 侧重重建。

## 7. 复现

```powershell
$root = 'E:\Unity Development\Blender Modle\codex建模测试'
$b = 'E:\SteamLibrary\steamapps\common\Blender\blender.exe'

# 生成参考图（需要 APIMart 网络）
python 'E:\Unity Development\.cursor\skills\apimart-image\scripts\apimart_ref_chain.py' `
  --plan (Join-Path $root 'refs\plan-church.json')

# 建模
& $b -b --factory-startup --python (Join-Path $root 'scripts\build_church.py')

# 渲染
& $b -b --python (Join-Path $root 'scripts\render_views.py')

# 一键契约门（FBX 交付通路）
powershell -ExecutionPolicy Bypass -File 'E:\Unity Development\tools\blender-gate.ps1' `
  -Blend (Join-Path $root 'out\church.blend') `
  -Fbx (Join-Path $root 'export\Modle_WoodenGothicChurch.fbx') `
  -NoBone -RequireFloor -ContractOnly
```

## 8. 已知限制

- 参考图无相机标定，尺寸是设计输入，不是毫米级反推。
- 侧视比例与参考图不一致；模型更紧凑。
- UV 是平铺投影，UV atlas 门 fail；适合无缝木纹/瓦片，不适合烘焙。
- 653 个独立对象便于逐件验收，不是性能优化后的合并网格。
- 跨对象装配干涉没有单独建门；隐藏交叠按设计保留。
- 几何脚本不裁定结构强度。
