---
name: blender-asset-pipeline
description: >-
  Blender 建模与资产交付的 Codex 工作流：把“看着对”换成可重跑的三态数值门，
  覆盖网格健康（开边/非流形/退化/孤立点）、逐壳法线、埋面、自交、壁厚、世界尺寸、
  参考图量测与还原、装配接缝、修改器栈序、读图纪律，以及 Blender 5.2 API 变更。
  Use when modeling or modifying 3D assets in Blender, validating a mesh before
  Unity/FBX/GLB import, reconstructing from reference images, debugging
  non-manifold geometry / inverted normals / self-intersection / floating parts,
  choosing modifier order, or fixing Blender 5.x API errors such as
  action.fcurves / compositor / EEVEE shadow.
metadata:
  short-description: Blender 建模与交付的数值门、流程与验收纪律（Codex 版）
---

# Blender 资产管线（Codex 工作方式版）

> **唯一主张：**“看着对”不是证据，数字才是。致命判断必须来自可重跑的脚本；
> 看图只用来确认脚本已经指出的异常。
>
> 本文件是 `E:\Unity Development\.cursor\skills\blender-asset-pipeline\SKILL.md`
> 的**改写安装版**，原文件保持只读、未修改。改写重点不是换措辞，而是把它变成
> **我在 Codex 里实际执行的工作流**：先验门、小步改、每步留证据、能力边界写清楚。
>
> 实测环境：**Blender 5.2.3 LTS**（`e13b728c6880`）/ Windows / PowerShell。
> 随包门脚本的 `-- selftest` 在本机 **11/11 通过**（2026-11-11）。

---

## 0. 30 秒路由：这是哪类任务？

| 任务 | 我先做什么 | 交付证据 |
|---|---|---|
| **新建模型** | 找 spec / 参考图；没有 mm 规格就先只做 blockout | 尺寸门 + 网格门 + 同机位图 |
| **改现有模型** | 复制 `.blend` 到工作目录；先跑一遍全门拿基线 | 改前/改后 gate JSON + 差异说明 |
| **只做验收** | 不建模；按 `references/验收清单.md` 独立跑门 | 4 行验收回执 |
| **参考图还原** | 先标定 `mm_per_px`，再量包络/站表 | 每视图 IoU + 尺寸门 + 特征线对照 |
| **导出 Unity / FBX / GLB** | 应用变换、检查材质槽/UV、导出后复算哈希和包围盒 | manifest + 导出件 sha256 |
| **Blender 5.x 报错** | 先查 `references/Blender5.2-API变更.md`，用能力探测而不是版本号 | 最小可跑片段 + 复现命令 |

### 不接的活（直接说明，不硬做）

- 布料 / 毛发 / 流体 / 烟等**没有稳定外轮廓**的对象：本流程的几何门不适用。
- **结构强度 / 承载 / 抗扭 / 装配工艺**：几何脚本只能回答“叠没叠、浮没浮、穿没穿”，
  不能给强度合格证。那要配合公差、标准、工况、工艺等人工设计输入。
- **没有 spec 却要求写死 mm / 交叠量**：先把假设写成 `provisional`，或回去要规格；
  不自己发明“通用倍数”。

### 能力边界（★ 先看这张表，避免把“没查”写成“通过”）

| 能力 | 本包有吗 | 怎么处理 |
|---|---|---|
| 网格健康 / 逐壳法线 / 埋面 / 自交 / 壁厚 / 世界尺寸 | ✅ `scripts/blender_gate.py` | 直接跑，落 JSON |
| 导入契约（单位 / 变换 / 命名 / 骨架 / 落地 / 材质 / UV 层 / 三角预算） | ✅ 工作区 `E:\Unity Development\tools\blender_contract.py` | 走 `blender-gate.ps1` 或单独跑 |
| 装配浮空 / 干涉 / 包络漂移 | ❌ 无随包脚本 | 按 `references/数值门.md` §7 另写或手测；没跑就写 `unresolved` |
| UV 岛重叠 / 贴图可用性 | ✅ 工作区 `E:\Unity Development\tools\blender_uv_gate.py` | 先跑 `--selftest`（6/6），再 `-- --objects ...` |
| 真·内部面（非启发式） | ✅ 工作区 `E:\Unity Development\tools\blender_buried_true.py` | 先跑 `--selftest`（4/4），再用它复核 `buried` |
| 材质槽 / Unity submesh | ✅ `blender_contract.py` 的 `check_material_slots` | 走契约门；单独查时断言 `len(mesh.materials)==1` |
| 结构强度 | ❌ 永远不在范围内 | 明确告诉用户“几何脚本不裁定” |

> `references/` 是原技能文档的副本，保留完整方法论。**与本文件冲突时以本文件为准**：
> 本文件按 `blender_gate.py` 的实际实现校正了“哪些门读求值网格”“哪些门脚本未随包”等口径。
> 工作区工具在 skill 目录之外；它们**不属于安装包**，但在这台机器上可用，优先用它们。

---

## 1. 运行环境：先把门跑起来

### 1.1 定位 Blender 与门脚本

```powershell
$b = if ($env:BLENDER_EXE) { $env:BLENDER_EXE } else {
  'E:\SteamLibrary\steamapps\common\Blender\blender.exe'
}
$skill = 'E:\Unity Development\.codex\skills\blender-asset-pipeline'
$g     = Join-Path $skill 'scripts\blender_gate.py'

if (-not (Test-Path -LiteralPath $b)) { throw "找不到 Blender: $b" }
if (-not (Test-Path -LiteralPath $g)) { throw "找不到门脚本: $g" }
```

### 1.2 每次开工先验门（必做）

```powershell
& $b -b --factory-startup --python $g -- selftest
Write-Output "EXIT=$LASTEXITCODE"
```

期望最后一行 **`11 / 11 passed`**，退出码 `0`。

- 不是 11/11 ⇒ **先修门，别看模型**。否则你分不清“模型干净”和“门坏了”。
- 退出码：`pass=0` / `fail=1` / `degraded=2`。CI 里 `2` 也必须变红。

### 1.3 工作区一键入口（优先用）

本工作区已有 `E:\Unity Development\tools\blender-gate.ps1`：
门自检 → `.blend` 数值门 → FBX 重新导入复核 → 契约门 → `manifest.json`。

```powershell
powershell -ExecutionPolicy Bypass -File 'E:\Unity Development\tools\blender-gate.ps1' `
  -Blend 'E:\work\tower.blend' `
  -Fbx   'E:\work\out\Modle_Tower_Assault.fbx' `
  -Objects 'GEO-base,GEO-head' `
  -MinMm 1.2 -ResolutionMm 0.8 `
  -Expect '1000,1000,2000' -TolMm 3 `
  -RequireFloor -NoBone -UvUnwrap
```

- 道具/核心/出生门用 `-NoBone`；分件装配体用 `-ContractOnly`（单体水密门不适用）。
- 它内部把 `buried` 的判决交给 `tools\blender_buried_true.py`，启发式数字只作对照。
- 它当前把 `$SkillRoot` 指向 `.cursor\skills\blender-asset-pipeline`；
  `.codex` 与 `.cursor` 的 `blender_gate.py` 目前逐字节一致。
  **两份一旦分叉，要么改 wrapper 的 `$SkillRoot`，要么只按 §6 逐门跑 `.codex` 脚本。**

### 1.4 工作目录约定

我不直接改用户的原始资产。默认在工作区建：

```text
work/<任务名>/
  snapshots/      # 改拓扑前的 .blend 快照
  scripts/        # 我写的 bpy 脚本（apply_patch 维护）
  renders/        # 受控尺寸的渲染图
  gate/           # 每道门的 JSON
  export/         # GLB / FBX / manifest
```

规则：**原文件只读 → 复制到 `snapshots/` 或 `work/` → 在副本上改**。
拓扑改动前必须有一份可回退的 `.blend` 快照。

---

## 2. 我的操作契约（Codex 版）

这不是“建议”，是我执行这类任务时的默认行为。

1. **先读约束**：项目 `AGENTS.md` → 用户 spec → 现有资产命名/集合约定。
   没有 spec 就不写死 mm 级数字；先列假设并标 `provisional`。
2. **先列 3–6 步计划**：每一步必须有**一个可验证产物**（脚本、gate JSON、图、manifest）。
   不列“继续优化”这种无法验收的步骤。
3. **原文件不动**：只改副本；改前存快照；破坏性操作（批量删除、布尔并壳、覆盖导出）
   先向用户确认。
4. **脚本用 `apply_patch` 维护**：不手改二进制 `.blend`，不用 shell 重定向/heredoc 写代码。
5. **小步执行**：一段 bpy 脚本只做一件事；每段结束 `print` 对象名、`verts/faces`、
   世界 bbox、输出路径。没有 print 的脚本等于黑盒。
6. **改一次几何 → 重跑对应门**：不允许“上次跑过”当本次证据。
7. **`degraded` / `unresolved` 阻断推进**：先补查（加密网格、闭合、提高采样、换判据），
   再决定改几何还是改测法。
8. **MCP 与 headless 分工**：
   - `mcp__blender_execute_blender_code` / `get_scene_info`：看当前场景、做小实验、取事实；
   - `exec_command` + `blender -b --python ...`：跑门、批处理、可复跑证据；
   - **MCP 的口头结论不是门**：最终判决必须来自落盘的 gate JSON。
9. **读图有预算**：先看 L0 数字；只有 L0 出 FAIL 才读 L1/L2；整机 beauty 只在里程碑/交付。
   每轮 ≤6 张，每张 ≤800×450（MCP `look` 用 `max_size` 控制）。
10. **汇报固定四段**：结论 / 证据 / 未验证 / 下一步。不把“应该没问题”写成“通过”。

---

## 3. 三态铁律

每道门返回 `pass` / `fail` / `degraded`。

| verdict | 含义 | 我做什么 |
|---|---|---|
| `pass` | 查完了，且没缺陷 | 放行，记录字段 |
| `fail` | 查完了，确有缺陷 | 看非 0 字段，改几何，重跑 |
| `degraded` | **没查完 / 判不出来** | **补查**；不是通过，也不是失败 |

**最常见的错误读法：把 `degraded` 读成“没问题”。**
典型成因：自交检查被跳过、法线不可判（壳未闭合）、壁厚阈值低于网格分辨率、
内向射线没打到对面、参数错/找不到对象。

另外两条：

- **脚本没跑 = 没测。** 不要用“上次是 pass”“看起来没变”代替。
- **换一条计算通路复核**：构建用 `obj.dimensions`，验证必须用 `matrix_world @ v.co`；
  构建用内环 best score，验证必须独立复算。若构建逻辑有 bug，结论应能翻转。

---

## 4. 标准流程（每步都有产物）

```text
⓪ 任务单/spec → ① 标定 → ② blockout → ③ 粗形/精修
→ ④ 修改器栈 → ⑤ 清理/法线 → ⑥ 装配 → ⑦ 渲染验证 → ⑧ 交付
```

| 步 | 输入 | 我做什么 | 产物 / 门 | 不通过时 |
|---|---|---|---|---|
| ⓪ | 参考图 / 文字需求 | 写清单位、包络、接口、面数预算、交付格式；缺的标 `provisional` | `spec.md` | 缺关键规格 ⇒ 问用户 |
| ① | 正交图 / 照片 | 标定 `mm_per_px`；照片只对取点平面严格成立 | `calibration.json` | 无标定 ⇒ 不写 mm |
| ② | spec | 低模占位，确认比例/轮廓；`GEO-` 命名，blockout 分集合 | `-- measure` | 改包络，不急着加细节 |
| ③ | blockout | 粗形 → 精修；每步取帧/门检 | `-- mesh` + 小图 | 先修拓扑再继续 |
| ④ | 精修网格 | 按**目标**排修改器栈；取求值网格对拍 | `verts/faces/bbox` + 门 | 改顺序后重跑门 |
| ⑤ | 修改器结果 | 合并重复点 → 溶解退化 → 重算法线 → 复检 | `-- mesh` / `-- normals` | 回到 ③ 改几何 |
| ⑥ | 多件 | 装配、接缝交叠、浮空/干涉 | manifest + 装配检查 | 隐藏交叠白名单化 |
| ⑦ | 成品 | 同机位对照 + 取景自检 | L0 数字 + L1/L2 图 | 先修数字再做 beauty |
| ⑧ | 全部 | 导出 GLB/FBX + manifest + sha256 | 全门 `pass` | `degraded` 不算完成 |

**任何一步 `degraded` 都不推进。** 先补查，再决定是改几何还是改判据。

---

## 5. 写代码前：3 条语义检查 + 1 个骨架

### 5.1 三条不能机械判定的坑（动手前逐条念）

1. **长轴 / 宽轴 / 薄轴**：这个件哪个轴是长？哪个轴是“看得出形状”的宽面？相机在哪侧？
   先在注释里写 `(长, 宽, 薄) = (局部?, 局部?, 局部?)`，再动手。
   **永远让宽轴朝向英雄机位。** 从薄轴看过去的剑就是一根细棍。
2. **收尖**：要收尖的那圈顶点，是否**先压到中线（x=y=0）再 `remove_doubles`**？
   只按比例缩放一定得到平头 / 退化拓扑。
3. **headless 慎用 `bpy.ops`**：脚本里有 `object.mode_set` / `mesh.*` / `loopcut` /
   `transform.*` / `uv.*` 吗？有 ⇒ 优先改 bmesh 或 data API。

### 5.2 headless 安全写法速查

| 想做的事 | 不要用（headless 易 poll 失败） | 改用 |
|---|---|---|
| 合并重复点 | 编辑模式 + `mesh.remove_doubles` | `bmesh.ops.remove_doubles` |
| 重算法线 | `mesh.normals_make_consistent` | `bmesh.ops.recalc_face_normals` |
| 平滑着色 | `object.shade_smooth()` | `for p in mesh.polygons: p.use_smooth = True` |
| 环切 / 挤出 | `mesh.loopcut_slide` / 模态操作 | bmesh 几何构造 |
| 选对象 | `object.select_all()` | 直接设 `view_layer.objects.active` / 操作 data |

必须用 ops 时，用 `bpy.context.temp_override(...)` 补齐 context，或改走 GUI 通道。

### 5.3 最小脚本骨架

```python
import bpy, bmesh
from mathutils import Vector

def log(*a):
    print("[build]", *a)

def mesh_stats(obj):
    me = obj.data
    mw = obj.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    log(obj.name, "verts", len(me.vertices), "faces", len(me.polygons),
        "size_m", tuple(round(v, 4) for v in (mx - mn)))

def clean(obj, merge=1e-4):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

# 建对象后立刻命名；blockout 与成品分集合
obj.name = "GEO-example"
obj.data.name = "MESH-example"

# 导出/布尔前应用变换
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

clean(obj)
mesh_stats(obj)
```

**收尖的正确写法（先压到中线，再合并；不是只缩放）：**

```python
bm = bmesh.new(); bm.from_mesh(obj.data); bm.verts.ensure_lookup_table()
max_z = max(v.co.z for v in bm.verts)
top = [v for v in bm.verts if abs(v.co.z - max_z) < 1e-3]
for v in top:
    v.co.x = 0.0
    v.co.y = 0.0
bmesh.ops.remove_doubles(bm, verts=top, dist=1e-3)
bm.to_mesh(obj.data); bm.free(); obj.data.update()
```

### 5.4 命名与结构

- 对象一建就命名：`GEO-<part>`；网格数据同名 `MESH-<part>`。
- blockout / 成品分集合：`COL_Blockout` / `COL_Geo`。
- 布尔、导出前应用变换（至少 rotation + scale）。
- 拓扑改动前存快照；不要在原始资产上直接试。

---

## 6. 数值门：命令、判据、读法

### 6.1 权威门表

```powershell
$work  = 'E:\path\to\work\<task>'
$model = Join-Path $work 'model.blend'
$objs  = 'GEO-body,GEO-handle'      # 也可传集合名；省略或 * = 场景全部网格
$outDir = Join-Path $work 'gate'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
```

| # | 门 | 命令 | 通过判据 | 已知口径 |
|---|---|---|---|---|
| ① | 网格健康 | `-- mesh --objects $objs` | `nonmanifold_edges=0` / `degenerate_faces=0` / `loose_verts=0` / `loose_edges=0` | `boundary_edges>0` 只对“应为闭合壳”的件是缺陷 |
| ② | 法线 | `-- normals --objects $objs` | **逐壳** `state=pass`；`fail`/`n/a` 都不算通过 | 不看聚合 `signed_volume` |
| ③ | 埋面 | `-- buried --objects $objs` | `buried_count=0` | **射线启发式**；闭合单壳的 >0 多为遮挡，见 §6.3 |
| ④ | 自交 | `-- selfint --objects $objs` | `pair_count=0` | 贴合接触可能报 1+；允许的接触要白名单 |
| ⑤ | 壁厚 | `-- thickness --min-mm 1.2 --resolution-mm 0.8` | `min_mm >= 阈值` 且 `samples_below=0` | 开放曲面没打对面 ⇒ `degraded` |
| ⑥ | 尺寸 | `-- measure --expect 400,400,800 --tol-mm 3` | `out_of_tolerance=[]` | 世界 AABB，按 1 BU = 1 m 换算 |

**一把梭（只在参数齐全时有意义）：**

```powershell
& $b -b $model --python $g -- all --objects $objs `
  --min-mm 1.2 --resolution-mm 0.8 --expect 400,400,800 --tol-mm 3 `
  --out (Join-Path $outDir 'all.json')
```

> `all` 只会用你传的阈值。**不传 `--min-mm` / `--expect` 时，壁厚和尺寸门没有真正的验收条件**，
> 不能拿“all 是 pass”当交付证据。交付时逐门显式跑。

### 6.2 JSON 怎么读

```json
{
  "verdict": "pass",
  "gate": "mesh",
  "plugin": "blender_gate.py",
  "version": "1.0.0",
  "blender": "5.2.3 LTS",
  "objects": { "GEO-body": { "counts": { "...": 0 } } },
  "missing": [],
  "summary": "verdict=pass · mesh · 1 对象"
}
```

- `verdict` 是总判决；`objects.<name>` 是逐对象明细。
- 单门时 `objects.<name>` 直接是门结果（如 `counts` / `size_mm`）；
  `-- all` 时每个对象多一层 `gates`，总判决仍在顶层 `verdict`。
- `missing` 非空 ⇒ `degraded`，先改 `--objects`，不要当几何结论。
- `notes` / `error` 是补查入口；先读它们，再决定改几何还是改测法。
- 退出码与 `verdict` 一致；CI 里 `1` 和 `2` 都要失败。

### 6.3 逐门读法（容易读反的地方）

**① mesh**

- `boundary_edges > 0` 只说明是开放网格。薄片、开口罩是有意的；闭合壳才是缺陷。
- 有 `nonmanifold_edges` 先修拓扑，别继续倒角/细分。

**② normals**

- 必须逐壳看。聚合 `signed_volume` 会把“大正向壳 + 分离的小反向壳”加成正数，漏掉反向块。
- 未闭合壳的“整体朝向”无意义 ⇒ `n/a`，**不给 pass**。
- 任何“穿模 / 内含 / 深入多少”的判据都以法线朝外为前提；法线没验，结论不成立。

**③ buried**

`blender_gate.py` 的实现是：从面中心沿外法线打射线，命中别的面就算 `buried`。

| 情况 | 怎么读 | 处置 |
|---|---|---|
| 闭合 + 单连通壳，`buried > 0` | 数学上不可能有内部面 ⇒ 这是**遮挡**（凹腔、环箍、竖梃挡住对面） | **不要删面**；按遮挡记录，复核可见性 |
| 多壳（join / 复制 / 布尔残留） | 可能是真埋面 | 先 `-- selfint` + 法线；优先 Boolean UNION，不要“选中再删” |
| 删了埋面 | 必须复检 `boundary_edges=0` / `nonmanifold_edges=0` | 只盯面数变少 = 把穿模换成破面 |

> 原技能里的 `blender_buried_true.py`（定理 + 壳间包含）**不在 skill 目录内**。
> 但它在本工作区 `E:\Unity Development\tools\blender_buried_true.py` 可用（selftest 4/4）；
> 单壳遮挡判断按上表做，需要用真判据时跑它，不要自己另写一套。

**④ selfint**

- 三角级 BVH；相邻共点面已排除。
- **贴合接触可能给 1+**。设计允许的接触要写进白名单，不要拿 `pair_count` 当穿模开关。
- 本门是单体自交；跨对象干涉要另跑装配检查（未随包）。

**⑤ thickness**

- 没打到对面（开放曲面）⇒ `degraded`，不是 fail（薄片本来就没厚度）。
- `min_mm` 低于测量分辨率 ⇒ `degraded`。**别拿粗网格下细结论。**
- 曲率大处会低估（射线斜穿）。

**⑥ measure**

- 走**求值网格** + `matrix_world @ v.co`。未 apply 的修改器（Mirror/Array/Boolean）**算数**。
- 不要用 `obj.dimensions` 验证：它是“局部 bbox × scale”，**不含旋转**。
- 脚本按 `1 BU = 1 m` 换算。场景单位不是米时，读数是 `BU×1000`，不是真实 mm；
  先统一单位，或自己换算并在回执里写明。

**★ 未求值 vs 求值（脚本实际行为）**

| 门 | 读什么 |
|---|---|
| `mesh` / `normals` / `buried` / `selfint` / `thickness` | **`obj.data` 基础网格**；未 apply 的修改器不算数 |
| `measure` | **求值网格**；未 apply 的修改器算数 |

所以：带 Mirror 的半个件跑 `mesh` 会报基础网格的开边；这不是建模错误，但你**必须知道**
自己在测哪一层。交付前 apply 相关修改器，或明确在回执里标注。

### 6.4 skill 目录之外的检查（先跑工作区工具，别默认通过）

**装配级三项**（详见 `references/数值门.md` §7）：

| 检查 | 判据 | 口径陷阱 |
|---|---|---|
| 浮空 | 无悬空件；可见浮块 ≥ 全模型最长 bbox 边 1% 要查 | 别拿“连通分量数=1”当判据：贴而未焊天然多分量 |
| 干涉 | 无异常互穿；允许的隐藏交叠白名单化 | `unresolved` ≠ 无干涉；贴合接触常判不了 |
| 包络 / 尺寸漂移 | 关键 bbox 与 spec 偏差 ≤ 公差 | 用 `-- measure` 的 `size_mm` 逐条比，不目测 |

**UV / 材质**：

- 有 `TEX_IMAGE` 节点 ≠ 可用：必须有 UV 层，且不是箱式/柱面投影叠在同一 UV 空间。
- 机械判据：UV 全在 `[0,1]²`、岛间包围盒不重叠、覆盖率 ≥15%、texel 密度比 ≤1.10；
  视觉证据是棋盘格渲染等大、不拉伸、无重叠。
- 本工作区有 `E:\Unity Development\tools\blender_uv_gate.py`（selftest 6/6）；
  单体件交付优先加 `blender-gate.ps1 -UvUnwrap`。
- Boolean `TRANSFER` 会搬进空材质槽 ⇒ Unity 多一个 submesh。应用后断言
  `len(me.materials) == 1`，清空 `material_index` 再赋唯一材质。

**没跑这些检查时，回执里写 `unresolved`，不许写 `pass`。**

---

## 7. 装配（多件拼装）

单件跑 ①–⑥；装配完成后加跑浮空 / 干涉 / 包络。

- **看得见 ≠ 连上**：面贴面即使数值接触，渲染也会有缝。展示模型的做法是**隐藏交叠**——
  在不可见处压进去一点。
- **交叠量由本项目 spec 明文规定，没有通用倍数、百分比或下限。**
  spec 没写就回去问规格，别自己发明一个数。
- **隐藏交叠 ≠ 真穿模**：前者是设计意图，后者是缺陷。区分靠“不可见面 + 不捅穿薄壳 + 白名单”。
- **逐轴 AABB 重叠是粗筛，不是结论**：只在“接口法线与某根世界轴一致、且轴对齐盒适用”时
  读**那一根轴**。旋转/斜置接口必须沿真实接口局部坐标量真实表面。
  反例：3 mm 薄板搭接给 `{x:180, y:200, z:1.5}` —— 180/200 是**板本身多大**，与交叠无关。
- **AABB 相交 ≠ 真有交叠**：全内含的浮块同样给三轴正重叠。所以交叠检查**必须与浮空检查并跑**。
- **别拿“分量数=1”当连通判据**：贴而未焊天然是多分量。
- **几何脚本不裁定结构强度**。能不能承载、抗扭、装得上，由配合公差、标准、工况、工艺决定——
  那是要人给的设计输入。

装配回执建议字段：

```text
part_pair | overlap_mm(spec/actual) | floating? | true_penetration? | whitelisted? | verdict
```

---

## 8. 修改器栈：没有通用顺序

不存在“背下来”的固定链。修改器栈是**按目标函数排序的求值链**，只换两三条顺序，
**拓扑和尺寸都会变**。

实测（同一 1 m 立方体，Blender 5.2）：

| 顺序 | verts / faces | bbox 最长边 |
|---|---|---|
| Bevel(0.2/2段) → SubSurf(2) | **866 / 864** | **0.9904 m** |
| SubSurf(2) → Bevel(0.2/2段) | **98 / 96** | **0.8395 m** |

两边都“对”，`bbox` 差 **15%**。⇒ 顺序靠**目标**决定。

| 目标 | 顺序 | 为什么 |
|---|---|---|
| 镜像件浑然一体 | **Mirror 在前**，Bevel/SubSurf 后 | 镜像缝先焊成连续面，再统一倒角 |
| 阵列单元各自带倒角 | **Bevel 在前**，Array 后 | 后级只复制前级结果；反了倒角作用在整排接缝上 |
| 薄壳边缘圆润 | **Solidify 在前**，Bevel 后 | 先有厚度才有“实心边”可倒 |
| 光滑曲面但保棱 | **Bevel 在前**，SubSurf 后 | 倒角提供支撑边，细分才不会把棱圆掉 |
| 分面硬表面（装甲/军模） | **不要 SubSurf** | 细分把棱全圆成“肥皂” |
| 布尔开孔 | Boolean **尽量靠后**，导出前 apply | 保持非破坏；布尔后的 n-gon 影响后续细分 |

**顺序对不对，用回执判，不靠背：**

```python
import bpy
dg = bpy.context.evaluated_depsgraph_get()
ev = obj.evaluated_get(dg)
me = ev.to_mesh()
print("verts", len(me.vertices), "faces", len(me.polygons))
ev.to_mesh_clear()
```

取求值网格的 `verts/faces/bbox` 与目标对拍；**改了顺序就重跑门**。

### 清理序列（固定顺序）

```text
合并重复点 → 溶解退化 → 重算法线 → 复检
```

先重算法线再合并，等于在脏拓扑上算朝向，结论不可靠。
内部面不要用 `Delete Loose`（它一个面都不删）；按 `references/修改器与清理.md` §2 分成因处理。

---

## 9. 读图纪律（Codex 版）

视觉成本 ≈ 像素面积。`tokens ≈ W×H / 750`。

| 用途 | 尺寸 | ≈tokens | 相对 |
|---|---|---|---|
| 整机 beauty | 1600×900 | 1920 | **25×** |
| 部位 QC | 960×540 | 691 | 9× |
| 二值轮廓叠合 | 800×450 | 480 | 6× |
| **异常小裁切** | 240×240 | **77** | **1×** |

**一张整机图 = 25 张 240×240 小裁切。**

### 四级证据制

| 级 | 形式 | 何时允许读 |
|---|---|---|
| **L0** | 数值指标表（期望 vs 实际 + PASS/FAIL） | 每一轮、每次改动 |
| **L1** | 二值轮廓叠合图（≤800×450） | 每个阶段门 |
| **L2** | 异常区域小裁切（≤320×320，一次 ≤6 张） | **仅当 L0 出 FAIL** |
| **L3** | 整机成品 beauty | 仅里程碑/交付，**只给用户看** |

**纪律**：L0 不出 FAIL，不许读 L1/L2；L3 不作为几何正确性依据。
**每轮 ≤6 张图，每张 ≤800×450。**

### 在 Codex 里怎么取图

- 现场场景：`mcp__blender_look`，显式给 `target`、`max_size`（QC 用 480–768）、
  `shading`（检查几何用 `solid`，检查材质用 `material`）、`views`（英雄位 + 斜 45°）。
- 本地渲染文件：`view_image`，先确认文件存在和尺寸，再读。
- 只看事实用 `mcp__blender_get_scene_info`，不要把它的文本当渲染图。

### 读图前后

**读图前先写断言**：这张图要验证哪 2–3 条可测命题？
**读图后写三分法**：

```text
【确认看到的】
【推断的】
【我没有能力判断的】
```

无法用数字证实的视觉判断，必须标 **“未经证实的视觉印象”**，不得写成“通过”。

### 预览装置默认值（否则“白对白”看不出几何突变）

- 材质：中性灰（Base Color ≈ 0.18、Roughness ≈ 0.6、Metallic = 0），不要纯白；
- 光照：单侧强太阳（斜 45°，angle ≈ 1–3° 硬阴影）+ 很弱环境光；
- 背景：中灰或渐变，不用纯白/纯黑；
- 每次至少两个机位：英雄机位（像不像）+ 斜 45° 检查位（缝、浮空、穿模）。

**判据：如果一张图看不出板缝在哪，这张图就不能作为 QC 证据。**

---

## 10. Blender 5.2 API 速查

完整表 + 可抄代码见 `references/Blender5.2-API变更.md`。最高频的六条：

| 症状 | 改法 |
|---|---|
| `'Action' object has no attribute 'fcurves'` | 走 `action.layers → strips → channelbag(slot)`；不是退回手工烘焙 |
| `Scene object has no attribute 'node_tree'` | `scene.compositing_node_group = ng`，输出用 `NodeGroupOutput` |
| `glare_type` 无效 / read-only | Glare 的 Type/Quality 变成 **MENU 输入插座**：`gl.inputs['Type'].default_value` |
| `vertices[::n]` 步长切片报错 | `[verts[i] for i in range(0, n, step)]` |
| `Mesh has no attribute 'use_auto_smooth'` | 逐面 `p.use_smooth = True`，或 Smooth by Angle / Weighted Normal |
| `mat.cycles.displacement_method` 不存在 | `mat.displacement_method = 'BUMP'`（5.2+） |

**用 `hasattr` 判能力，不判版本号**：扩展可能装只暴露第一个 channelbag 的 `fcurves` 垫片。

---

## 11. 交付

### 11.1 manifest（必需）

```json
{
  "asset": "lamp",
  "units": "m",
  "source_blend": "work/lamp/snapshots/lamp-v3.blend",
  "exports": [
    { "path": "work/lamp/export/lamp.glb", "sha256": "...", "bytes": 123456 }
  ],
  "bbox_mm": [420, 420, 2100],
  "objects": ["GEO-base", "GEO-post", "GEO-head"],
  "gates": {
    "mesh": "pass", "normals": "pass", "buried": "pass",
    "selfint": "pass", "thickness": "pass", "measure": "pass"
  },
  "assembly": { "floating": "unresolved", "interference": "unresolved" },
  "known_limits": ["UV gate not run", "assembly interference not run"]
}
```

哈希：

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath $exportPath |
  Select-Object Hash, Path
```

### 11.2 交付前最终清单

- [ ] `-- selftest` 11/11（本次会话）
- [ ] ①–⑥ 门全 `pass`（`degraded` 一律不算）
- [ ] 法线是**逐壳**判的，不是聚合 `signed_volume`
- [ ] spec 里每条接口的 `overlap_mm` 都核对过
- [ ] 关键尺寸带**来源**（哪道门、哪次采样）
- [ ] 交付件带 manifest（units/bbox/objects/sha256）
- [ ] 形体有**同机位对照图 + 数值 bbox** 两条证据
- [ ] 已知限制写明（未实现项 / 精度边界 / 不确定项）
- [ ] `.blend` 与导出件的 sha256 留档
- [ ] 未跑的门写 `unresolved`，不伪装成 `pass`

### 11.3 给用户的汇报格式

```text
结论：<做完/没做完 + 一句判断>
证据：<门名 + 关键字段 + 数值；文件路径；sha256>
未验证/风险：<没跑的门、精度边界、假设>
下一步：<需要用户决定的事，或明确“无”>
```

如果用户要的是**独立验收**，按 `references/验收清单.md` 的固定 4 行输出，不要复述构建历史。

---

## 12. 常见失败 → 我的处置

| 症状 | 先查 | 处置 |
|---|---|---|
| `selftest` 不是 11/11 | 门脚本/Blender 路径/版本 | 先修门，不建模 |
| `verdict=degraded` + `error` | 参数、对象名、集合名 | 改 `--objects`，重跑 |
| `verdict=degraded` + `notes` | 精度、闭合、采样、无对面 | 加密/闭合/提高采样；补查后再判 |
| `Operator ... poll() failed` | headless 用了 context 依赖的 ops | 改 bmesh/data API，或 `temp_override` |
| 法线 `fail` | 壳是否闭合、是否逐壳反向 | 先 `recalc_face_normals`，复检；再谈穿模 |
| 单壳 `buried > 0` | 是否闭合、是否真的单壳 | 按遮挡记录，不要删面 |
| 多壳 `buried > 0` | `selfint`、法线、是否 join 残留 | Boolean UNION；删面后必须复检开边 |
| 导出后 Unity 多 submesh | 空材质槽 / 重复材质 / `material_index` 越界 | 清槽、统一索引、断言 `len(materials)==1` |
| 贴图一片死色 | 是否有 UV 层 / UV 是否退化 | 先补 UV；节点在 ≠ 可用 |
| 形体“看着不对”但门都过 | 是否只有轮廓证据、相机/宽轴是否对 | 加同机位对照 + 特征线；别只刷 IoU |

---

## 13. 参考文档

| 文件 | 内容 |
|---|---|
| `references/数值门.md` | 每道门的字段含义、口径陷阱、装配级补充门 |
| `references/六条坑.md` | 九条坑的完整实测细节 + 可直接抄的修法 |
| `references/参考图还原SOP.md` | 参考图 → mm 数字 → 模型的九步 |
| `references/验收清单.md` | 给**独立验证者**用的 4 行输出规范 |
| `references/Blender5.2-API变更.md` | 5.2 报错对照表 + layered action / 合成器可跑片段 |
| `references/修改器与清理.md` | 修改器栈序、删除内部面的正确做法 |
| `ADAPTATION.md` | 本 Codex 版改了什么、验证了什么、原文件在哪 |

**工作区工具（不在 skill 目录内，但本机可用）：**

| 文件 | 用途 | 自检 |
|---|---|---|
| `E:\Unity Development\tools\blender-gate.ps1` | 一键：自检 → 数值门 → FBX 复核 → 契约门 → manifest | 内部先跑三个 selftest |
| `E:\Unity Development\tools\blender_buried_true.py` | 真·内部面（单壳定理 + 多壳包含） | `-- --selftest`：4/4 |
| `E:\Unity Development\tools\blender_uv_gate.py` | UV 岛重叠 / 范围 / 覆盖率 / 密度 | `-- --selftest`：6/6 |
| `E:\Unity Development\tools\blender_contract.py` | 单位 / 变换 / 命名 / 骨架 / 落地 / 材质 / UV 层 / 三角预算 | 由 wrapper 调用 |
| `E:\Unity Development\tools\blender_export_unity.py` | Unity 轴向/单位固定的 FBX 导出 | 导出回执 |

**阅读顺序**：本文件 → 需要细节时再读对应 reference。不要把整本 references 一次性塞进上下文。

---

## 14. 来源与许可

本技能的方法论派生自 [sixtysevenlf/dsh-blender-plugin](https://github.com/sixtysevenlf/dsh-blender-plugin)
的 `skills/blender-modeling`（MIT，Copyright © 2026 sixtyseven67），其本身派生自
[RobLe3/cc-blender-skill](https://github.com/RobLe3/cc-blender-skill) 与
[arjun988/blender-skills](https://github.com/arjun988/blender-skills)（均 MIT）。

本安装版由 `E:\Unity Development\.cursor\skills\blender-asset-pipeline` 改写而来，
**未修改原目录中的任何文件**。完整来源、许可与本地改动见 `NOTICE.md` 和 `ADAPTATION.md`。

---

## 附录：快速命令卡

```powershell
$b = 'E:\SteamLibrary\steamapps\common\Blender\blender.exe'
$g = 'E:\Unity Development\.codex\skills\blender-asset-pipeline\scripts\blender_gate.py'
$model = 'E:\path\to\model.blend'
$objs  = 'GEO-body'
$outDir = 'E:\path\to\work\gate'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

& $b -b --factory-startup --python $g -- selftest

& $b -b $model --python $g -- mesh    --objects $objs --out (Join-Path $outDir 'mesh.json')
& $b -b $model --python $g -- normals --objects $objs --out (Join-Path $outDir 'normals.json')
& $b -b $model --python $g -- buried  --objects $objs --out (Join-Path $outDir 'buried.json')
& $b -b $model --python $g -- selfint --objects $objs --out (Join-Path $outDir 'selfint.json')
& $b -b $model --python $g -- thickness --objects $objs --min-mm 1.2 --resolution-mm 0.8 `
  --out (Join-Path $outDir 'thickness.json')
& $b -b $model --python $g -- measure --objects $objs --expect 400,400,800 --tol-mm 3 `
  --out (Join-Path $outDir 'measure.json')

Write-Output "EXIT=$LASTEXITCODE"
```

工作区工具：

```powershell
$tools = 'E:\Unity Development\tools'

# 一键交付门（推荐；内部含 FBX 重新导入复核）
powershell -ExecutionPolicy Bypass -File (Join-Path $tools 'blender-gate.ps1') `
  -Blend $model -Fbx 'E:\path\to\out\Modle_X.fbx' -Objects $objs `
  -MinMm 1.2 -ResolutionMm 0.8 -Expect '400,400,800' -TolMm 3 -NoBone -UvUnwrap

# 单独复核
& $b -b --factory-startup --python (Join-Path $tools 'blender_buried_true.py') -- --selftest
& $b -b --factory-startup --python (Join-Path $tools 'blender_uv_gate.py') -- --selftest
& $b -b $model --python (Join-Path $tools 'blender_buried_true.py') -- --objects $objs --out (Join-Path $outDir 'buried-true.json')
& $b -b $model --python (Join-Path $tools 'blender_uv_gate.py') -- --objects $objs --out (Join-Path $outDir 'uv.json')
```
