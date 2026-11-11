# NOTICE —— 来源、许可与本地改动

## 上游

本技能派生自 **[sixtysevenlf/dsh-blender-plugin](https://github.com/sixtysevenlf/dsh-blender-plugin)** 的
`skills/blender-modeling/`（版本 v3.1.0-alpha.1）。

- 上游许可：**MIT**，Copyright © 2026 sixtyseven67
- 上游自身派生自两个 MIT 项目：
  - [RobLe3/cc-blender-skill](https://github.com/RobLe3/cc-blender-skill)
  - [arjun988/blender-skills](https://github.com/arjun988/blender-skills)
- 上游保留了上述归属；本技能一并保留。

```
MIT License

Copyright (c) 2026 sixtyseven67

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 本地改动（与上游的差异）

### 1. 剥离宿主依赖 —— 这是主要改动

上游技能是 **DSH（DeepSeek Harness）插件**的一部分，正文大量引用宿主工具
（`blender_op` / `blender_py` / `blender_see` / `blender_run` / `blender_inspect`、
`audit_mesh` / `asm_scan` / `gate_run` / `visualreport_report` 等 228 个 op）。

**本技能不含也无法含这些工具** —— 它们只在 DSH 宿主里存在。因此：

| 上游写法 | 本地改为 |
|---|---|
| `blender_op(op="audit_mesh", ...)` | `blender_gate.py -- mesh`（纯 bpy 实现） |
| `asm_scan` / `asm_gate`（装配门） | 保留**方法论与口径**，标注为"需自测/另写" |
| `deliver_verify` / `qc_render_views` | 保留**判据与陷阱**，实现指引见 `数值门.md` §7 |
| 6 个模型工具的通道语义（§0.1–0.2 大半） | **整节删除** —— 对非 DSH 宿主无意义 |
| 228 op 的 family/op 速查表 | **整节删除** |

**保留下来的是与工具无关的部分**：六条坑的实测细节、修改器栈序、读图纪律与成本模型、
参考图还原 SOP、三态判定口径、验收纪律、Blender 5.2 API 变更。

### 2. 新增 `scripts/blender_gate.py`

上游没有独立可执行的门（能力全在 DSH op 里）。本技能新增一个**纯 bpy**
（只需 `bpy` / `bmesh` / `mathutils`，无第三方依赖、无 addon、无 MCP）的数值门：

- 六道门：`mesh` / `normals` / `buried` / `selfint` / `thickness` / `measure`
- 三态 `verdict`，退出码 `pass=0 / fail=1 / degraded=2`
- **含 `-- selftest`**：11 条已知答案的用例，含"大正向壳 + 分离小反向壳"这条
  专门守"聚合 `signed_volume` 会漏判"的用例

### 3. 在 Blender 5.2.3 LTS 上实测校正

上游声明测试目标为 **Blender 4.2 LTS**，5.x 未验证。
本技能在 **5.2.3 LTS** 上逐条验证，并据此改写：

- 验证 `hasattr(action,'fcurves') → False`、`scene.node_tree` 不存在、
  Glare 参数变成插座、`vertices[::n]` 步长切片报错等（记录在 `Blender5.2-API变更.md`）；
- `blender_gate.py` 的 selftest 在 5.2.3 上 **11/11 通过**；
- 修正了上游一处易误导的表述：`Action.fcurves` 的缺失是**入口变了**，
  而不是"逐帧烘焙"的理由 —— 上游已澄清，本技能沿用并加强。

## 未包含的上游内容及原因

| 未包含 | 原因 |
|---|---|
| `runtime/py/` 的 41.8k 行 Python 库 | 那是上游插件本体（BSD-3-Clause），不是技能文档；需要时可 `offline_bootstrap.py` 单独用，但不属本技能交付范围 |
| DSH 插件安装 / Gateway / addon zip | 与 Blender 本身无关 |
| 上游 228 op 的目录细节 | 无宿主即不可调用 |

## 使用声明

本技能提供的是**方法论 + 可执行的门**，不保证任何具体模型的几何正确性。
所有 `pass` 结论仅对"脚本实际测过的项"成立；未覆盖项在 `references/数值门.md` §7
明确列为"需自测"，**不得视为已通过**。
