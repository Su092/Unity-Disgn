# 改写记录：Codex 工作方式版

## 1. 来源与去向

| 项 | 值 |
|---|---|
| 原技能 | `E:\Unity Development\.cursor\skills\blender-asset-pipeline` |
| 原 `SKILL.md` SHA256 | `0BFA703887BCE28A2E51CCC93C18D206CE307824DAD3616A662B8362CC890DA3` |
| 原 `scripts/blender_gate.py` SHA256 | `51F0D4640A411F74EE66F48BA0CE634B1E62F502D4152B25AB53431122DA94EC` |
| 安装位置 | `E:\Unity Development\.codex\skills\blender-asset-pipeline` |
| 改写日期 | 2026-11-11 |
| 实测环境 | Blender 5.2.3 LTS（`e13b728c6880`）/ Windows / PowerShell |

**原目录未做任何写入。** 安装完成后可用上面的哈希复核两个关键原文件。

## 2. 为什么改写

原技能是一份“宿主无关”的方法论文档，主要面向 DSH/通用 agent；
它在 Codex 里能读，但**不能直接当作执行手册**：缺少工具分工、路径解析、落盘证据、
能力边界和汇报格式，而且有几处与实际脚本实现不一致。

本次改写把它变成**我在 Codex 里实际会执行的流程**，保留方法论，重写操作层。

## 3. 主要改动

| 区域 | 原版 | Codex 版 |
|---|---|---|
| 入口 | 直接进入“三条铁律” | 先做 **30 秒任务路由** + **能力边界表** |
| 工具 | 不指定宿主工具 | 明确 `exec_command` / `apply_patch` / Blender MCP / `view_image` 的分工 |
| 路径 | 固定 `.cursor` 路径 | 用 `$b` / `$g` / `$skill` 解析，支持 `BLENDER_EXE`，默认指向新安装位置 |
| 证据 | “脚本 + 看图”原则 | 每步必须落 **gate JSON**；MCP 口头结论不算门 |
| 工作方式 | 偏原则 | 10 条操作契约：只读原件、快照、小步 print、改一次跑一次门、四段汇报 |
| 读图 | L0–L3 + 成本模型 | 增加 Codex 取图方式（`mcp__blender_look` 的 `max_size` / `target` / `views`） |
| 交付 | 清单 | 增加 manifest JSON 模板、sha256 命令、`unresolved` 口径 |
| 错误处理 | 分散在各 reference | 增加“症状 → 先查 → 处置”速查表 |
| 快速命令 | 分散 | 末尾一张可直接复制的命令卡 |

## 4. 按脚本实测校正的口径

这些不是文风改动，是**读错会得出反向结论**的地方：

1. **哪些门读求值网格**
   - 实际：`mesh` / `normals` / `buried` / `selfint` / `thickness` 读 `obj.data` 基础网格；
     只有 `measure` 走 `world_bbox()` 的求值网格。
   - 原 `验收清单.md` 写成“`measure` 与 `buried`/`selfint` 都走求值网格”，与脚本不符，已在副本中改正。
2. **`all` 不等于全验收**
   - 不传 `--min-mm` / `--expect` 时，壁厚和尺寸门没有真正的阈值；
     `all` 仍可能返回 `pass`。交付必须逐门显式传参。
3. **`buried` 是射线启发式**
   - 闭合单连通壳在数学上不可能有内部面，`buried > 0` 多为遮挡；
     不能照着“删内部面”处理。原技能坑七已说明，但脚本仍是启发式，SKILL 里明确标注。
4. **skill 目录内只有 `blender_gate.py`**
   - 原目录与本安装包的 `scripts/` 都只有 `blender_gate.py`；
     `blender_buried_true.py` / `blender_uv_gate.py` / `blender_contract.py` 在
     **工作区级** `E:\Unity Development\tools\`，不属于 skill 安装包。
   - 这些工作区工具可用，且本次已实测自检：
     `blender_buried_true.py` **4/4**、`blender_uv_gate.py` **6/6**。
     所以 SKILL 里把它们写成“工作区工具”，并给出实际命令，而不是笼统写“没有”。
   - `check_material_slots` 是 `blender_contract.py` 里的函数，不是独立脚本；
     交付优先走 `tools\blender-gate.ps1`。
5. **单位假设**
   - `measure` / `thickness` 按 `1 BU = 1 m` 换算 mm；场景单位不是米时读数是 `BU×1000`，
     不是真实 mm。SKILL 里已写明先统一单位或自行换算。

## 5. 保留的内容

- 三态判定（`pass` / `fail` / `degraded`）与“`degraded` 不是通过”；
- 九条坑的实测细节、修改器栈按目标排序、参考图还原 SOP、IoU 的必要不充分性；
- L0–L3 读图纪律与 token 成本模型；
- Blender 5.2 API 变更与能力探测写法；
- 上游 MIT 归属与 `NOTICE.md`。

## 6. 验证记录

### 6.1 门自检

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' `
  -b --factory-startup `
  --python 'E:\Unity Development\.codex\skills\blender-asset-pipeline\scripts\blender_gate.py' `
  -- selftest
```

结果：**11 / 11 passed**，退出码 `0`，Blender 5.2.3 LTS。

### 6.2 冒烟测试

用 1 m 立方体跑 `mesh` / `normals` / `measure`，确认安装路径下的脚本能读 `.blend`、
能落 JSON、退出码与 `verdict` 一致。具体结果见安装后的验证回执。

另外实测工作区工具：

- `blender_buried_true.py -- --selftest`：**4 / 4 passed**；
- `blender_uv_gate.py -- --selftest`：**6 / 6 passed**；
- 立方体 `all --min-mm 1.2 --expect 1000,1000,1000`：`verdict=pass`，
  `measure.size_mm=[1000,1000,1000]`，`thickness.min_mm=999.99`。

### 6.3 原文件未改动

安装前后分别计算原 `SKILL.md` 与 `scripts/blender_gate.py` 的 SHA256；
两者应与 §1 表中的值一致。

## 7. 安装布局

```text
E:\Unity Development\.codex\skills\blender-asset-pipeline\
  SKILL.md
  ADAPTATION.md
  NOTICE.md
  references\
    数值门.md
    六条坑.md
    参考图还原SOP.md
    修改器与清理.md
    验收清单.md
    Blender5.2-API变更.md
  scripts\
    blender_gate.py
```

不含 `__pycache__`。`scripts/blender_gate.py` 与原文件逐字节一致（仅复制，未改代码）。

**不在安装包内、但在本工作区可用：** `E:\Unity Development\tools\blender-gate.ps1`、
`blender_buried_true.py`、`blender_uv_gate.py`、`blender_contract.py`、`blender_export_unity.py`。

## 8. 使用提醒

- 这是一个**项目级** Codex skill 目录；是否被自动发现取决于当前 Codex 版本的 skill 搜索路径。
  如果会话里没有自动加载，直接把
  `E:\Unity Development\.codex\skills\blender-asset-pipeline\SKILL.md`
  作为上下文文件读入即可。
- 不要同时维护 `.cursor` 与 `.codex` 两份内容而不留痕；以本目录为 Codex 使用版，
  `.cursor` 原版保持只读作为来源。
- `tools\blender-gate.ps1` 当前把 `$SkillRoot` 指向 `.cursor\skills\blender-asset-pipeline`；
  两份 `blender_gate.py` 目前逐字节一致。若以后只改 `.codex` 版，记得同步改 wrapper
  的 `$SkillRoot`，否则一键入口仍跑旧代码。
- ~~`E:\Unity Development\.agents\skills\blender-asset-pipeline` 还有一份旧版副本~~
  **2026-11 已删除**：`.agents/skills/` 与根 `apimart-image/` 两处副本按用户要求移除，
  skill 收敛为单一源头 `.cursor/skills/`。本目录（`.codex/skills/`）是唯一的例外 ——
  它是给 Codex 宿主的**派生改写版**，内容有意与原版不同。
