# 3D 素材管线（Blender → FBX → Unity）

> 生图走 `asset-pipeline.md`；本文只管 3D 模型。视觉标准见 `art-style.md`。
> 方法论在 skill `blender-asset-pipeline`；本文件定义**星轨防线自己的口径与数值**。

## 1. 一句话原则

**"看着对"不是证据，数字才是。** 几何正确性由脚本判据给出，图片只用来确认脚本已经指出的异常。

## 2. 入口

```powershell
# 建模完成后，一条命令跑完全部检查
powershell -ExecutionPolicy Bypass -File "E:\Unity Development\tools\blender-gate.ps1" `
    -Blend "E:\work\tower.blend" `
    -Fbx   "E:\Star Defanse\Assets\Resources\Art\Models\tower_assault\Modle_Tower_Assault.fbx" `
    -Objects "GEO-Tower" `
    -MinMm 1.2 -ResolutionMm 1.0 `
    -Expect "1000,1000,2000" -RequireFloor
```

| 步骤 | 内容 | 失败含义 |
|------|------|----------|
| 0 | gate `selftest` | 门本身坏了，所有结论作废 |
| 1 | `.blend` 六道数值门 | 构建通路的几何缺陷 |
| 2 | FBX 重新导入后六道数值门 + 契约门 | **导出/单位/轴转换**引入的问题 |
| 3 | `manifest.json` | 交付回执：units / bbox / objects / md5 |

退出码：`0=pass`、`1=fail`、`2=degraded`。**`degraded` 必须补查，不许当通过。**

| 场景 | 命令 |
|------|------|
| 新件交付前（完整） | `tools\blender-gate.ps1 -Blend <源> -Fbx <导出> -MinMm 1.2 -Expect "..." -RequireFloor` |
| 存量件体检（只契约门） | `tools\blender-gate.ps1 -Fbx <路径> -ContractOnly` |
| 存量全量体检 | `tools\blender-audit-models.ps1` |
| 导出 FBX | `tools\blender_export_unity.py`（见 §4） |

## 3. 两套门的分工

### 3.1 数值门（技能自带 `blender_gate.py`）

| # | 门 | 判据 |
|---|---|---|
| ① | 网格健康 | `nonmanifold_edges=0` / `degenerate_faces=0` / `loose_verts=0` / `loose_edges=0` |
| ② | 法线 | **逐连通壳** `signed_volume>0`；未闭合壳不给 pass |
| ③ | 埋面 | 启发式 `buried_count` **只作对照**；判决看 `blender_buried_true.py`：闭合单壳按定理判 0，多壳逐壳做壳间包含检测。凹腔件（灯罩、杯、笼）上启发式必假阳性 |
| ④ | 自交 | `pair_count=0`（相邻共点面已排除） |
| ⑤ | 壁厚 | `min_mm >= 阈值`，且阈值 ≥ 网格分辨率 |
| ⑥ | 尺寸 | 世界 AABB 与 spec 偏差 ≤ 公差 |
| ⑦ | UV 可用性 | `-UvUnwrap`：岛间重叠 0 / UV 在 [0,1]² / 覆盖率 ≥ 15% / 密度比 ≤ 1.10（`tools/blender_uv_gate.py`） |

**UV 层存在 ≠ UV 展开可用**：箱式三平面投影的 UV 层存在、不退化，`check_uvs` 判 pass，
但多套投影叠在同一 UV 空间（实测重叠 2001 对），烘焙 / AO / 光照贴图全废。
单体件交付请加 `-UvUnwrap`。

适用范围：**单体件**（一个连通壳，或先 Boolean UNION 成实体）。分件装配体不适用，见 §3.3。

### 3.2 契约门（本工程 `tools/blender_contract.py`）

数值门管不到、但会让模型在 Unity 里出错的事：

| 检查 | 判据 | 对应 Unity 侧后果 |
|------|------|-------------------|
| 单位 | `scale_length = 1.0`、Metric | 缩放错一个数量级 |
| 变换已 apply | `matrix_world` 旋转=0、缩放=1、无负缩放 | 落地与朝向各按各的算 |
| 单一网格根 | 根数 ≤ 1 | 多根导致落地基准不一致 |
| 命名 | `GEO-` 前缀 | 迭代时互相覆盖 / 分不清 blockout 与成品 |
| 三角预算 | 默认 ≤ 60000 | 移动端性能 |
| 材质 + 贴图 | 每件有材质且带 `TEX_IMAGE` 节点 | Unity 侧无 basecolor 可重建 |
| 材质槽 | 无空槽 / 无重复引用 / `material_index` 不越界 | Boolean `TRANSFER` 会搬进 `None` 槽，Unity 多出 submesh |
| UV 层 | 有 UV 层且未退化为单点（u/v 跨度 ≥ 1e-4） | 有贴图节点但没 UV ⇒ 采样固定一个纹素，渲染成死色 |
| 骨架契约 | 有 `Yaw` 骨骼、有无 `Muzzle*` | 瞄准失效；Yaw 轨道剔除规则不成立 |
| 落地基准 | 世界最低点 z ≈ 0（`--require-floor`） | 陷地或悬空 |

**为什么"缺骨架"判 `degraded` 而不是 `pass`**：判不了朝向契约，就是没查完。道具件请显式传 `--no-bone`；
`--no-bone` 只表示**不要求 Yaw 骨骼**，场景里有没有骨架都不影响结论（只报告实际骨骼）。

## 3.3 ★ 分件装配体：单体水密门不适用

本工程的模型都是**分件装配体**（塔 = `Base / Yaw / Head / Barrel_R / Muzzle_R / Barrel_L / Muzzle_L`
共 7 个网格），不是单体水密壳。对这类件硬跑数值门①–④会得到一片 fail，而那些"缺陷"是装配语义的
正常产物：

| 门 | 分件装配体上的表现 | 是否本工程的缺陷 |
|---|---|---|
| ① 网格健康 | `nonmanifold_edges` 几十到几百 | 部件贴合共边，正常 |
| ② 法线 | 未闭合壳 ⇒ `degraded` / 部分 `fail` | 开放壳无"整体朝向"，判不了 |
| ③ 埋面 | `buried_count` 上千 | 部件互相插入，正常 |
| ④ 自交 | `pair_count` 上千 | 同上 |

实测（`Modle_Tower_Assault`）：`mesh=fail(70 非流形)`、`buried=1588`、`selfint=1081`，
但这件在实机里完全正常，`verify` 与 `shots` 都是全绿。

**结论**：存量分件装配体**只跑契约门**；数值门留给新做的单体件（或先 Boolean UNION 成实体再测）。

```powershell
# 存量件体检（只契约门）
powershell -ExecutionPolicy Bypass -File tools\blender-audit-models.ps1
```

实测结果：13 个 `Modle_*` 全部 `pass`（三角数 22k–26k，全部在 60000 预算内）。

## 4. 导出契约

一律用 `tools\blender_export_unity.py`，不要手点导出：

```powershell
& $b -b model.blend --python "E:\Unity Development\tools\blender_export_unity.py" -- `
    "E:\Star Defanse\Assets\Resources\Art\Models\tower_assault\Modle_Tower_Assault.fbx" `
    --objects "GEO-Tower,RIG-Tower"
```

脚本固定的前提（与 `STAssetPostprocessor` 对齐）：

| 项 | 值 | 为什么 |
|----|----|--------|
| 命名 | `Modle_*.fbx` / `Anim_*.fbx` | Unity 侧按前缀分流导入规则，不符直接拒导 |
| 轴 | Forward `-Z` / Up `Y` | 与 Unity 导入设置一致，避免两边各转一次 |
| 单位 | `FBX_SCALE_ALL` + `apply_unit_scale` | Unity Scale Factor 1.00 的前提 |
| 动画 | 只有 `--anim` 才 `bake_anim` | `Modle_` 带动作会在 Unity 里混入多余片段 |
| 叶子骨 | 默认导出 | 与现有 FBX 结构保持一致 |
| 贴图 | `embed_textures=False` | 由 Unity 运行时按 `*_basecolor.jpg` 重建材质 |

`Anim_Tower_*` 的根节点轨道与 `Yaw` 轨道会被 `STAssetPostprocessor` 剔除；
**骨骼必须直接叫 `Yaw`**，不能叫 `Yaw_L` / `AimYaw`。

## 5. 修法速查（踩过的坑）

| 症状 | 处置 |
|------|------|
| `buried_count > 0`（join 出来的重叠壳） | Boolean **UNION** 并成实体；别"选中再删"，删完留下开边 |
| `pair_count > 0` | 先看法线是否已验证；法线朝内会让所有穿模判据整体反号 |
| 壁厚 `degraded` | 阈值低于网格分辨率 ⇒ 先加密网格再测 |
| 法线 `degraded` | 壳未闭合，整体朝向无意义；闭合后再判，或按口部法线单独核对 |
| 尺寸对不上 | 优先查是否 `.blend` 里没 apply 变换，或 FBX 单位设置不一致 |
| 分件装配体数值门全 fail | 预期行为，见 §3.3；只跑契约门，或先 UNION 成实体 |
| 导入通路报"旋转未应用" | 轴转换的合法产物（Unity `Bake Axis Conversion` 关闭），只作报告 |
| 塔在 Unity 里躺平 | `Pitch` 与 FBX 轴转换叠加了两次；看 `technical-design.md` §6 |
| 炮塔底座跟着转 | 转的是根节点而不是 `Yaw` 骨骼 |

## 6. 读图纪律

| 级 | 形式 | 何时读 |
|---|---|---|
| L0 | 数值指标表 | 每一轮 |
| L1 | 二值轮廓叠合图（≤800×450） | 阶段门 |
| L2 | 异常区域小裁切（≤320×320，≤6 张） | 仅当 L0 出 FAIL |
| L3 | 整机 beauty | 仅交付给用户看 |

L0 不出 FAIL 不许读 L1/L2；L3 不作为几何正确性依据。每轮读图 ≤6 张、每张 ≤800×450。

## 7. 现有模型现状

`Assets/Resources/Art/Models/` 下 18 个 FBX 均为外部制作，**没有对应 `.blend` 源文件**，
且都是**分件装配体**（见 §3.3）。因此存量件只跑契约门：

```powershell
# 全量体检（13 个 Modle_*，按塔/非塔自动决定是否要 Yaw 骨架）
powershell -ExecutionPolicy Bypass -File "E:\Unity Development\tools\blender-audit-models.ps1"

# 单个件
powershell -ExecutionPolicy Bypass -File "E:\Unity Development\tools\blender-gate.ps1" `
    -Fbx "E:\Star Defanse\Assets\Resources\Art\Models\tower_assault\Modle_Tower_Assault.fbx" `
    -ContractOnly -Out "E:\Unity Development\tools\_gate\audit-tower-assault"
```

2026-11-10 实测：13 件 `Modle_*` 契约门 **全部 pass**，三角数 22k–26k（预算 60000）。
（4 个 `Anim_*` 不含网格，契约门不适用；它们的轨道约束由 `STBuild.CheckModels` 校验。）

> 存量件是**已验收的运行中资源**，体检结论只作记录，不要为了过门而改动它们；
> 改动会使 `check.ps1 -Task verify` 的动画轨道断言失效（见 `technical-design.md` §6）。

## 8. 验收

1. `blender-gate.ps1` 退出码 0，`manifest.json` 里各门 `verdict=pass`。
2. 把模型放到位后跑 `check.ps1 -Task verify` → `RESULT 资源校验通过`。
3. `check.ps1 -Task build` → `RESULT Succeeded`。
4. `ST.exe -autoshot` → `MODEL 4/4`、`FACING 3/3` 全绿，看截图确认姿态与朝向。
