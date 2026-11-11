---
name: blender-asset-pipeline
description: >-
  Blender 建模与资产交付的验收纪律与数值门：把"看着对"换成可重跑的脚本判据，
  覆盖网格健康（开边/非流形/退化/孤立点）、逐壳法线、埋面、自交、壁厚、世界尺寸、
  参考图量测与还原、装配接缝、修改器栈序、渲染取景自检，以及 Blender 5.2 API 变更。
  Use when modeling or modifying 3D assets in Blender, checking a mesh before import to
  Unity/FBX/GLB, doing reference-image-based reconstruction, diagnosing non-manifold /
  inverted normals / self-intersection / floating parts, choosing modifier order,
  or when Blender 5.x throws AttributeError on action.fcurves / compositor / EEVEE shadow.
  Runs with `scripts/blender_gate.py` (bpy-only, no addon, no MCP).
---

# Blender 资产管线：先定形状，再走流程，改一步看一眼

> **这套技能只有一条主张**：**"看着对"不是证据，数字才是。**
> 致命判断必须来自脚本；看图只用来确认脚本已经指出的异常。
>
> 配套脚本：`scripts/blender_gate.py`（纯 bpy，不需要 DSH / MCP / 任何 addon）。
> 先在 Blender 5.2.3 / 4.2+ 上跑 `-- selftest`，**11/11 通过**再信它的结论。

## 0. 三条铁律

**铁律 A：三态，不是二态。**
每个门返回 `pass` / `fail` / `degraded`。

| verdict | 含义 | 处置 |
|---|---|---|
| `pass` | 查完了，且没缺陷 | 放行 |
| `fail` | 查完了，确有缺陷 | 改几何 |
| `degraded` | **没查完 / 判不出来** | **补查** |

`degraded` **不是通过，也不是失败**。把 `degraded` 读成"没问题"是这套流程最常见、代价最大的错误。
典型成因：自交检查被跳过、法线不可判（壳未闭合）、壁厚阈值低于网格分辨率、采样没打到对面。

**铁律 B：一条判据至少一条独立通路。**
同一件事不许用"构建时那条通路"复核。判据是：**换通路后，如果构建逻辑本身有 bug，结论会翻转。**

| 构建时用了 | 验证时必须换成 |
|---|---|
| `obj.dimensions`（局部 bbox × scale，**不含旋转**） | `matrix_world @ v.co` 求世界 AABB |
| 内环优化的 best score | 独立脚本 / 另一个门复算 |
| 导出器自检 | 对导出文件复算 md5 + 单位盒 |
| "我看图觉得对" | 数值 + 画面两条证据，缺一不可 |

**铁律 C：数字必须可复算。**
每个数字要带来源：`min_mm` 来自哪次采样、`size_mm` 是哪个门给的、`md5` 是哪个文件。
没有来源的数字 = 没测。

## 1. 开工前：30 秒自检

```powershell
# 找 Blender（Steam 版也认）
$b = "E:\SteamLibrary\steamapps\common\Blender\blender.exe"
& $b --version

# 验证门本身没坏（必做：否则你分不清"模型干净"和"门坏了"）
& $b -b --factory-startup --python scripts\blender_gate.py -- selftest
```

`selftest` 必须 **11/11**。不通过就先修门，别看模型。

## 2. 标准流程（每步都有输入/输出/门）

```
① 量参考图     → spec（mm 数字，冻结）        → 无标定就不许写 mm
② 白模/blockout → 低模占位，确认比例与轮廓      → 尺寸门
③ 粗形 → 精修   → 每步取帧看一眼               → 网格健康门
④ 修改器栈      → 按目标排序，不靠背            → 复算 verts/faces/bbox
⑤ 清理 / 修法线 → recalc + 复检                → 门①②③
⑥ 装配          → manifest + 接缝交叠量         → 浮空门 + 干涉门
⑦ 渲染验证      → 同机位对照 + 逐帧取景自检      → 形体门
⑧ 交付          → GLB/FBX + manifest + md5     → 全门 pass
```

**任何一步 `degraded` 都不推进。** 先补查，再决定是改几何还是改判据。

## 3. 必踩的坑 · 九条（完整版见 `references/六条坑.md`）

这是整套技能里**实战价值最高**的部分。九条里有六条能机械判定（交给门），三条是语义、只能在写代码前念一遍。

| # | 坑 | 能机械判定？ | 落在哪 |
|---|---|---|---|
| 一 | 细长件 **长轴 / 宽轴 / 薄轴** 语义反了 | ❌ | 写代码前 checklist |
| 二 | **拼件接缝**：看得见 ≠ 真连上；隐藏交叠 vs 真穿模 | ✅ 部分 | 干涉门 + 连通门 |
| 三 | **收尖只靠缩放** → 得到平头 | ❌ | 写代码前 checklist |
| 四 | headless 下滥用 `bpy.ops` → poll/context 报错 | ❌ | 写代码前 checklist |
| 五 | **法线朝内** → 一切"穿模/内含"判据整体反号 | ✅ | 法线门（逐壳） |
| 六 | 预览装置看不清几何突变（白对白） | ⚠ 半 | 装置默认值 |
| 七 | **启发式把「遮挡」判成「埋住」** → 凹腔件整片误杀 | ✅ | `tools/blender_buried_true.py`（定理 + 壳间包含） |
| 八 | **贴图「节点在 ≠ 可用」**：缺 UV / UV 是投影不是展开 | ✅ | `tools/blender_uv_gate.py` |
| 九 | **Boolean `TRANSFER` 搬进空材质槽** → Unity 多 submesh | ✅ | 契约门 `check_material_slots` |

**写代码前 checklist（三条不可机械判定的，动手前逐条念）**：

1. **长轴/宽轴/薄轴**：这个件哪个轴是长？哪个轴是"看得出形状"的宽面？相机在哪侧？
   先在注释里写 `(长, 宽, 薄) = (局部?, 局部?, 局部?)` 再动手。**永远让宽轴朝向英雄机位。**
2. **收尖**：要收尖的那圈顶点，是不是**先压到中线（x=y=0）再 `remove_doubles`**？
   只按比例缩放**一定**得到平头。
3. **headless**：这段脚本里有 `object.mode_set` / `mesh.*` / `loopcut` / `transform.*` / `uv.*` 吗？
   有 ⇒ 改 bmesh 或 data API。

**怎么验**：三条各自能在代码里指出对应的一行；机械判定的三条必须出现在交付回执里。

## 4. 数值门清单（★ 这是唯一的权威门表）

跑法见 `scripts/blender_gate.py`，字段含义见 `references/数值门.md`。

| # | 门 | 通过判据 | 命令 |
|---|---|---|---|
| ① | 网格健康 | `nonmanifold_edges=0` / `degenerate_faces=0` / `loose_verts=0` / `loose_edges=0` | `-- mesh` |
| ② | 法线 | **逐连通壳**一致朝外；`unknown`/未闭合 ⇒ 不给 pass | `-- normals` |
| ③ | 埋面 | `buried_count=0`（`Delete Loose` 删不掉这些） | `-- buried` |
| ④ | 自交 | `pair_count=0`（三角级，相邻共点面已排除） | `-- selfint` |
| ⑤ | 壁厚 | `min_mm >= 阈值`，且阈值 ≥ 网格分辨率 | `-- thickness --min-mm 1.2` |
| ⑥ | 尺寸 | 世界 AABB 与 spec 偏差 ≤ 公差 | `-- measure --expect 400,400,800 --tol-mm 3` |
| ⑦ | 浮空 | 无悬空件（装配级，需另跑连通性） | 见 `references/数值门.md` §装配 |
| ⑧ | 干涉 | 无异常互穿；允许的隐藏交叠**白名单化** | 见 `references/数值门.md` §装配 |
| ⑨ | 形体 | 同机位对照图 **+** 数值 bbox，两条都要 | 见 `references/参考图还原SOP.md` |
| ⑩ | 面数 | 对三角面预算 | `-- mesh` 的 `tris` |

**一把梭**：
```powershell
& $b -b model.blend --python scripts\blender_gate.py -- all --min-mm 1.2 --out gate.json
```

**MUST**：对象一建就命名（`GEO-` 前缀）；blockout 与成品分离；布尔/导出前应用变换；拓扑改动前先存快照。
**MUST NOT**：用单张成品图验收形体；在法线未验证的前提下下穿模结论；拿单视图 IoU 当"整体像不像"；把 `degraded` 当通过。

## 5. 装配（多件拼装）

单件跑 ①–⑥；装配完成后加跑 ⑦⑧。

- **看得见 ≠ 连上**：面贴面即使数值接触，渲染也有缝。展示模型的做法是**隐藏交叠**——在不可见处压进去一点。
- **交叠量由本项目 spec 明文规定**。**没有通用倍数、百分比或下限**。spec 没写就回去问规格，别自己发明一个数。
- **隐藏交叠 ≠ 真穿模**：前者是设计意图，后者是缺陷。区分靠"不可见面 + 不捅穿薄壳 + 白名单"。
- **逐轴 AABB 重叠是粗筛，不是结论**：只在"接口法线与某根世界轴一致、且轴对齐盒适用"时读**那一根轴**。
  旋转/斜置接口必须沿真实接口局部坐标量真实表面。
  反例：3 mm 薄板搭接给 `{x:180, y:200, z:1.5}` —— 180/200 是**板本身多大**，与交叠无关。
- **AABB 相交 ≠ 真有交叠**：全内含的浮块同样给三轴正重叠。所以交叠检查**必须与浮空检查并跑**。
- **别拿"分量数=1"当连通判据**：贴而未焊天然是多分量。
- **几何脚本不裁定结构强度**。能不能承载、抗扭、装得上，由配合公差、标准、工况、工艺决定 —— 那是要人给的设计输入。

## 6. 修改器栈：没有通用顺序

不存在"背下来"的固定链。修改器栈是**按目标函数排序的求值链**，只换两三条顺序，**拓扑和尺寸都会变**。

实测（同一 1 m 立方体，Blender 5.2）：

| 顺序 | verts / faces | bbox 最长边 |
|---|---|---|
| Bevel(0.2/2段) → SubSurf(2) | **866 / 864** | **0.9904 m** |
| SubSurf(2) → Bevel(0.2/2段) | **98 / 96** | **0.8395 m** |

两边都"对"，`bbox` 差 **15%**。⇒ 顺序靠**目标**决定。

| 目标 | 顺序 | 为什么 |
|---|---|---|
| 镜像件浑然一体 | **Mirror 在前**，Bevel/SubSurf 后 | 镜像缝先焊成连续面，再统一倒角 |
| 阵列单元各自带倒角 | **Bevel 在前**，Array 后 | 后级只复制前级结果；反了倒角作用在整排接缝上 |
| 薄壳边缘圆润 | **Solidify 在前**，Bevel 后 | 先有厚度才有"实心边"可倒（反着放倒角基本被吃掉：54 面 → 6 面） |
| 光滑曲面但保棱 | **Bevel 在前**，SubSurf 后 | 倒角提供支撑边，细分才不会把棱圆掉 |
| 分面硬表面（装甲/军模） | **不要 SubSurf** | 细分把棱全圆成"肥皂" |
| 布尔开孔 | Boolean **尽量靠后**，导出前 apply | 保持非破坏；布尔后的 n-gon 影响后续细分 |

**顺序对不对，用回执判，不靠背**：取 `evaluated_get(depsgraph).to_mesh()` 的 `verts/faces/bbox` 与目标对拍，**改了顺序就重跑门**。

## 7. 读图纪律（决定 token 和效果）

视觉成本 ≈ 像素面积。`tokens ≈ W×H / 750`。

| 用途 | 尺寸 | ≈tokens | 相对 |
|---|---|---|---|
| 整机 beauty | 1600×900 | 1920 | **25×** |
| 部位 QC | 960×540 | 691 | 9× |
| 二值轮廓叠合 | 800×450 | 480 | 6× |
| **异常小裁切** | 240×240 | **77** | **1×** |

**一张整机图 = 25 张 240×240 小裁切。**

**四级证据制**：

| 级 | 形式 | 何时允许读 |
|---|---|---|
| **L0** | 数值指标表（期望 vs 实际 + PASS/FAIL） | 每一轮、每次改动 |
| **L1** | 二值轮廓叠合图（≤800×450） | 每个阶段门 |
| **L2** | 异常区域小裁切（≤320×320，一次 ≤6 张） | **仅当 L0 出 FAIL** |
| **L3** | 整机成品 beauty | 仅里程碑/交付，**只给用户看** |

**纪律**：L0 不出 FAIL，不许读 L1/L2；L3 不作为几何正确性依据。
**每轮 ≤6 张图，每张 ≤800×450。** 读图前先写断言（这张图要验证哪 2–3 条可测命题）；
读图后写三分法：**【确认看到的】【推断的】【我没有能力判断的】**。
无法用数字证实的视觉判断，必须标 **"未经证实的视觉印象"**，不得写成"通过"。

## 8. Blender 5.2 API 变更（实测，会直接报错）

完整表 + 可直接抄的代码见 `references/Blender5.2-API变更.md`。最高频的四条：

| 症状 | 改法 |
|---|---|
| `'Action' object has no attribute 'fcurves'` | 走 `action.layers → strips → channelbag(slot)`，**不是**退回手工烘焙 |
| `Scene object has no attribute 'node_tree'` | `scene.compositing_node_group = ng`，输出用 `NodeGroupOutput` |
| `glare_type` 无效 / read-only | Glare 的 Type/Quality 变成 **MENU 输入插座**：`gl.inputs['Type'].default_value` |
| `vertices[::n]` 步长切片报错 | `[verts[i] for i in range(0, n, step)]` |

## 9. 交付前最终清单

逐条打勾，缺一项就是没做完：

- [ ] ①–⑥ 门全 `pass`（`degraded` 一律不算）
- [ ] 法线是**逐壳**判的，不是聚合 `signed_volume`
- [ ] spec 里每条接口的 `overlap_mm` 都核对过
- [ ] 关键尺寸带**来源**（哪个门、哪次采样）
- [ ] 交付件带 `manifest`（units/bbox/objects/md5）
- [ ] 形体有**同机位对照图 + 数值 bbox** 两条证据
- [ ] 已知限制写明（未实现项 / 精度边界 / 不确定项）
- [ ] `.blend` 与导出件的 md5 留档

## 10. 参考文档

| 文件 | 内容 |
|---|---|
| `references/数值门.md` | 每道门的字段含义、口径陷阱、装配级补充门 |
| `references/六条坑.md` | 九条坑的完整实测细节 + 可直接抄的修法 |
| `references/参考图还原SOP.md` | 参考图 → mm 数字 → 模型的九步 |
| `references/验收清单.md` | 给**独立验证者**用的 4 行输出规范（约 4k 字符） |
| `references/Blender5.2-API变更.md` | 5.2 报错对照表 + layered action / 合成器可跑片段 |
| `references/修改器与清理.md` | 修改器栈序、删除内部面的正确做法 |

## 11. 来源与许可

本技能的方法论派生自 [sixtysevenlf/dsh-blender-plugin](https://github.com/sixtysevenlf/dsh-blender-plugin)
的 `skills/blender-modeling`（MIT，Copyright © 2026 sixtyseven67），其本身派生自
[RobLe3/cc-blender-skill](https://github.com/RobLe3/cc-blender-skill) 与
[arjun988/blender-skills](https://github.com/arjun988/blender-skills)（均 MIT）。

**本地改动**：剥离全部对 DSH 宿主工具（`blender_op` / `blender_py` / `blender_run` 等）的依赖，
改为纯 bpy 可执行；新增 `scripts/blender_gate.py` 独立数值门（含 selftest）；
在 Blender 5.2.3 LTS 上实测校正了判据。详见 `NOTICE.md`。
