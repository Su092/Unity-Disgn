# Blender 5.2 API 变更（实测报错对照表）

> **实测环境：Blender 5.2.3 LTS**（`e13b728c6880`，2026-10-22）。
> 每条都实际跑过验证，不是推测。4.2 LTS 用户多数不受影响 —— 表里注明适用范围。

## 0. 速查表

| 症状 | 原因 | 改法 | 影响版本 |
|---|---|---|---|
| `'Action' object has no attribute 'fcurves'` | 5.x 改 layered / slotted action | 走 `layers → strips → channelbag(slot)`，**不是**退回手工烘焙 | 5.0+ |
| `'Scene' object has no attribute 'node_tree'` | 5.0 起合成器改成节点组 | `scene.compositing_node_group = ng`，输出用 `NodeGroupOutput` | 5.0+ |
| `glare_type` 无效 / read-only | Glare 的 Type/Quality 变成 **MENU 输入插座** | `gl.inputs['Type'].default_value` | 5.x |
| `Node type CompositorNodeMixRGB undefined` | 5.x 删了旧 Mix/Math/Composite | 合成器树里改用 **着色器节点** `ShaderNodeMix` / `ShaderNodeMath` | 5.x |
| `bpy_prop_collection[slice]: slice steps not supported` | `vertices[::n]` 步长切片不支持 | 用 range 循环 | 5.x |
| `CyclesRenderSettings has no attribute 'use_persistent_data'` | 属性移到 `scene.render` | `scene.render.use_persistent_data` | 5.x |
| `Scene.frame_set() expected int, not float` | 帧号必须整数 | `int(1 + round(t * fps))` | 一直如此 |
| `'CyclesMaterialSettings' has no attribute 'displacement_method'` | 5.2 挪到 Material 本体 | `mat.displacement_method = 'BUMP'` | 5.2+ |
| `Shadow buffer full (3040 / 2048)` 刷屏 | 阴影池是枚举且上限 2048 | 减投影灯，只留 2–4 盏 | 5.x |
| `Mesh has no attribute 'use_auto_smooth'` | 5.x 移除 | 用修改器式平滑或逐面 `use_smooth` | 5.x |

## 1. 分层动作（layered / slotted action）★ 最容易误判的一条

### 结论先行

**`action.fcurves` 原生不存在，但 fcurve 完全可遍历、可改插值、可新建通道。**
**不要**因为拿不到 `.fcurves` 就退回"手工按缓动采样打关键帧"——那是更差的办法
（帧数暴涨、丢 Bezier 手感、改不动已有动画）。

**"逐帧烘焙"是导出需求，不是 API 限制**，两者别混为一谈。

### 实测结构（5.2.3）

```
hasattr(action,'layers')      → True
len(action.layers)            → 1
hasattr(action,'fcurves')     → False     ★
action.is_action_layered      → True
action.slots                  → ['OBAnim']   （identifier = 'OB'+对象名）
ad.action_slot.identifier     → 'OBAnim'
```

### ⚠ 先破除一个陷阱

某些扩展会给 `Action` 装一个 `fcurves` 兼容垫片
（实测 `mmd_tools` 的 `compat/action_compat.py` 就是，类名 `ActionGroupsCompatibility`）。
它**只暴露第一个 channelbag**（源码注释原文："Only the first channelbag is used"）。

所以 **`hasattr(action, "fcurves")` 不能用来判断"是不是 4.x"** —— 有它也不代表全量可用。
判版本请判结构：`len(getattr(action, "layers", []))` 或 `action.is_action_layered`。

### 结构硬约束

实测（5.2.3）：`action.layers.new()` 建第二个 layer → `RuntimeError: An Action may not have more than one layer`；
`layer.strips.new()` 建第二个 strip → `RuntimeError: A layer may not have more than one strip`。

**1 action = 1 layer = 1 strip = N 个 channelbag（每个 slot 一个）。**

所以"遍历会重复拿到同名通道"这种担心**不成立**；
真正的风险是**方向相反的** —— 把不同 slot 误当成重复。

### 三种取 channelbag 的入口

```python
import bpy
from bpy_extras import anim_utils

arm  = bpy.data.objects['骨架']
ad   = arm.animation_data
act  = ad.action
slot = ad.action_slot            # ActionSlot；identifier 形如 'OB'+对象名

# ① 按 slot 取（推荐：明确只处理"当前对象自己那条"）
cb = anim_utils.action_get_channelbag_for_slot(act, slot)
fcurves = list(cb.fcurves) if cb else []          # ★ cb 可能为 None，必须判空

# ② 从 animdata 取"已分配 slot"的 channelbag
cb = anim_utils.animdata_get_channelbag_for_assigned_slot(ad)
fcurves = list(cb.fcurves) if cb else []

# ③ 遍历所有 slot（会拿到**其它对象**的数据，只在确实要全量时用）
for layer in act.layers:
    for strip in layer.strips:
        for sl in act.slots:
            c = strip.channelbag(sl)
            if c:
                ...   # c 属于 sl 这个 slot，不是"重复"

# ④ 确保某条通道存在（必要时创建）
fc = act.fcurve_ensure_for_datablock(arm, 'pose.bones["腕.R"].rotation_euler', index=0)
```

**①② 返回"已分配 slot 那一个"；③ 返回"所有 slot 的并集"。**
**多 slot 时 ③ 天然比 ①② 多，它们不是"同一批" —— 别混用。**

### 可直接抄的 helper

```python
def action_fcurves(action, slot=None):
    """取 action 的 fcurve。

    slot 给定 → 只取该 slot 的 channelbag（推荐，语义最明确）。
    slot 为 None → 取全部 slot 的并集（按对象身份去重，不会丢数据）。

    兼容：4.x 走 action.fcurves；5.x 走 layered channelbag。
    注意：不要用 getattr(action,"fcurves") 判版本——扩展可能装了只暴露
    第一个 channelbag 的兼容垫片。
    """
    if action is None:
        return []

    # 5.x 分层结构优先判（结构判定，不是属性判定）
    if getattr(action, "layers", None):
        out, seen = [], set()
        for layer in action.layers:
            for strip in layer.strips:
                targets = [slot] if slot is not None else action.slots
                for sl in targets:
                    try:
                        cb = strip.channelbag(sl)
                    except Exception:
                        continue
                    if not cb:
                        continue
                    for fc in cb.fcurves:
                        # 按对象身份去重：不同 slot 的同名通道是**不同数据**
                        key = fc.as_pointer()
                        if key not in seen:
                            seen.add(key)
                            out.append(fc)
        return out

    # 4.x 及更早
    try:
        return list(action.fcurves)
    except Exception:
        return []


# —— 用法 ——
ad = bpy.data.objects['骨架'].animation_data

# 只改"当前对象自己那条"（最常见、最安全）
for fc in action_fcurves(ad.action, ad.action_slot):
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'

# 要处理这个 action 的全部 slot 时，才省略第二个参数
for fc in action_fcurves(ad.action):
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'
```

> ★ **不要按 `(fc.data_path, fc.array_index)` 去重。**
> 实测反例：两个对象共用一个 action（2 个 slot），两者的
> `pose.bones["腕.R"].rotation_euler[0]` data_path 完全相同，但数据不同
> （实测 `[0, 0.6]` vs `[0, 1.1]`，`as_pointer()` 也不同）。
> 按 data_path 去重 → 6 条变 3 条，**静默丢掉另一个对象的一整份动画**，且不报错。
> 这正是"没报错当通过"的典型陷阱。

### 实测边界（都验过，可以依赖）

| 情况 | 结果 |
|---|---|
| `action_get_channelbag_for_slot(act, None)` | 返回 `None`，**不抛异常** |
| 传别的 action 的 slot | 同样返回 `None`，不抛 |
| `animdata_get_channelbag_for_assigned_slot(None)` | 返回 `None` |
| 已分配 action 但**还没打关键帧** | `len(slots)==0`、`action_slot is None` → ①返回 `None`，**直接取 `.fcurves` 会 `AttributeError: 'NoneType'`** |
| `action.layers.new()` / `strips.new()` 建第二个 | `RuntimeError`（1 layer / 1 strip 是硬约束） |
| 改 `kp.interpolation` 是否真生效 | ✅ 求值验证：Bezier `0.156/0.5/0.844` vs Linear `0.25/0.5/0.75`（与解析值一致） |
| 改完要不要 `fc.update()` | 不需要，实测不调也正确求值 |
| `fcurve_ensure_for_datablock` 建通道 | ✅ 返回 `FCurve`；**前置条件：action 必须已分配给对象**，否则 `RuntimeError: Assign action ... before calling this function` |
| `pose_bone.animation_data` | ✅ 不存在，`AttributeError`；动画数据在 **armature object** 上 |
| `ActionSlot.identifier` | 形如 `'OB'+对象名`（`'OBO1'`），shape key 是 `'KE'+名`，**不是**固定 `'OBA'` |

### 验收判据（别用"没报错"当通过）

```python
fcs = action_fcurves(ad.action, ad.action_slot)
assert fcs, "没拿到任何 fcurve"
n = sum(len(fc.keyframe_points) for fc in fcs)
print(f"fcurves={len(fcs)} keys={n}")
# 多 slot 时要额外核对：每个 slot 的数量与真值是否分别对得上，
# 不能只看总数——总数对得上也可能是"一个多一个少"凑出来的。
```

> 这条对 **FBX 骨骼动画导出**尤其关键：按 data_path 去重会静默丢一份动画，
> 而导出流程通常"没报错"，于是错误会被带进 Unity。

## 2. 合成器（Compositor）改造成节点组

### 实测确认

```
hasattr(scene,'node_tree')                → False     ★
hasattr(scene,'compositing_node_group')   → True
CompositorNodeRLayers                     → OK
CompositorNodeGlare                       → OK
NodeGroupOutput                           → OK
CompositorNodeComposite                   → RuntimeError  ★ 已移除
CompositorNodeMixRGB                      → RuntimeError  ★ 已移除
```

### 最小可跑片段（Fog Glow 泛光；照抄即可）

```python
import bpy

sc = bpy.context.scene
ng = bpy.data.node_groups.get("Comp") or bpy.data.node_groups.new("Comp", "CompositorNodeTree")
sc.compositing_node_group = ng          # 5.0+：不是 sc.node_tree

ng.nodes.clear()
ng.interface.new_socket(name="Image", in_out='OUTPUT', socket_type="NodeSocketColor")

rl = ng.nodes.new('CompositorNodeRLayers')
gl = ng.nodes.new('CompositorNodeGlare')
gl.inputs['Type'].default_value = 'Fog Glow'      # MENU 插座，不是 gl.glare_type
gl.inputs['Quality'].default_value = 'High'
gl.inputs['Threshold'].default_value = 1.0
gl.inputs['Size'].default_value = 8.0
gl.inputs['Strength'].default_value = 0.45
out = ng.nodes.new('NodeGroupOutput')             # 不是 CompositorNodeComposite

ng.links.new(rl.outputs['Image'], gl.inputs['Image'])
ng.links.new(gl.outputs['Image'], out.inputs['Image'])
sc.render.use_compositing = True
```

### Glare 节点实有的输入插座（5.2.3 实测）

```
['Image', 'Type', 'Quality', 'Threshold', 'Smoothness', 'Clamp', 'Maximum',
 'Strength', 'Saturation', 'Tint', 'Size', 'Streaks', 'Streaks Angle',
 'Iterations', 'Fade', 'Color Modulation', 'Diagonal', 'Sun Position',
 'Jitter', 'Kernel Data Type', 'Kernel', 'Kernel']
```

`hasattr(gl, 'glare_type')` → **False**。所有参数走 `inputs[...]`。

### 旧的 Mix / Math 怎么办

合成器树里**改用着色器节点**：`ShaderNodeMix` / `ShaderNodeMath` / `ShaderNodeValToRGB` 仍可 `nodes.new`。
叠加用 `CompositorNodeAlphaOver`，调色用 `CompositorNodeColorBalance` / `CompositorNodeCurveRGB`。

## 3. 其他 5.x 变更

### 步长切片

```python
# ❌ me.vertices[::2]  → RuntimeError: slice steps not supported
# ✅
step = 2
pts = [me.vertices[i].co.copy() for i in range(0, len(me.vertices), step)]
```

### 渲染持久数据

```python
# ❌ scene.cycles.use_persistent_data     → 属性不存在
# ✅
scene.render.use_persistent_data = True
```

### 帧号

```python
# ❌ scene.frame_set(1.5)   → expected int, not float
# ✅
fps = scene.render.fps
scene.frame_set(int(1 + round(t * fps)))
```

### 材质位移 / 透明混合（5.2+）

```python
# ❌ mat.cycles.displacement_method
# ✅
mat.displacement_method = 'BUMP'
mat.surface_render_method = 'BLENDED'      # 枚举只有 'DITHERED' / 'BLENDED'
```

### EEVEE 阴影

控制台每帧刷 `Shadow buffer full (3040 / 2048)`，且 `shadow_pool_size='4096'` **静默无效**。

- 阴影池是**枚举**且上限就是 `'2048'`（2 GB）⇒ `scene.eevee.shadow_pool_size = '2048'`；
- 主力手段是**减投影灯**：`light.use_shadow = False`（点光/面光都算），只留 2–4 盏；
- 大场景再降 `scene.eevee.shadow_resolution_scale`。

### 自动平滑

```python
# ❌ mesh.use_auto_smooth   → 5.x 已移除
# ✅ 逐面标记（headless 最稳）
for p in mesh.polygons:
    p.use_smooth = True
# 或加修改器（Smooth by Angle / Weighted Normal）
```

## 4. 4.2 LTS ↔ 5.2 兼容写法

写要跨版本跑的脚本时，用**能力探测**而不是版本号判断：

```python
def get_compositor(scene):
    """返回 (节点树, 是否为独立节点组)。"""
    if hasattr(scene, "compositing_node_group"):
        ng = scene.compositing_node_group
        if ng is None:
            ng = bpy.data.node_groups.new("Comp", "CompositorNodeTree")
            scene.compositing_node_group = ng
        return ng, True
    return scene.node_tree, False       # 4.x


def set_glare(node, type_name="Fog Glow"):
    """Glare 类型：5.x 是插座，4.x 是属性。"""
    if "Type" in node.inputs:
        node.inputs["Type"].default_value = type_name
    elif hasattr(node, "glare_type"):
        node.glare_type = type_name
```

**判据**：`hasattr` 判**能力**，不判版本号 —— 扩展垫片会让版本判断失效（见 §1）。
