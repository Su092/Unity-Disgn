# 工作区约定（DSH 自动加载）

## 建模任务：参考图先行（强制）

用户提出**建模/建场景/做资产**需求时，默认按下面顺序执行，不要跳步直接开建：

1. **先出参考图。** 用 `apimart-image` skill 生成参考图（`resolution=1k`），落到 `<项目>/refs/`。
   - 单视角（3/4 主视角）：
     `python "E:\Unity Development\.cursor\skills\apimart-image\scripts\apimart_image.py" --prompt "..." --out "<绝对路径>\refs\ref-34.png" --size 16:9 --resolution 1k`
   - **多视角必须走链式**（否则四张图各画各的，比例/细节对不上）：
     `python "E:\Unity Development\.cursor\skills\apimart-image\scripts\apimart_ref_chain.py" --plan "<绝对路径>\refs\plan-<name>.json"`
     plan 的 `anchor` 先出主视角，`views` 逐条以 anchor 为参考；每条的 `resolution` 写 `"1k"`，
     提示词里写 "Same exact object as the reference image" 并只换机位。
   - 密钥已在 `E:\Unity Development\tools\.apimart.key`，**不要再问用户**；**不要先跑测试图验证链路**。
2. **量测参考图。** 用 `blender_op`：`img_digest`（结构摘要）→ `img_probe`（轮廓/孔/对称/直线角度）→
   `img_measure`（点间距离）→ 需要毫米时先 `img_calib` 标定。没有标定就**给像素口径，不要猜毫米**。
3. **按参考图建模。** 选形先走决策树（分面硬表面 / 光滑硬表面 / 有机 / 重复阵列 / 布尔），
   再按 `blender-modeling` skill 的流水线推进；几何对齐参考图轮廓，比例以第 2 步的数字为准。
4. **验收。** `qc_*`（IoU / 剖面差）或 `visualreport_report` 同机位比对；`degraded` 不算通过。
   肉眼觉得"像"不算验收，要出数字。

### 例外（要说出口）

- 用户明确说「不要参考图 / 直接建模」→ 跳过第 1 步，并在回复里说明跳过了。
- 纯机械结构、无外观要求（例如只为验证装配/干涉的占位块）→ 可跳过第 1 步，同样要说明。

## 交付路径

- 参考图：`<项目>/refs/`
- 渲染/对照图：`<项目>/renders/`
- 导出：`<项目>/export/`

不要跨项目复用同一个 `out` 路径（素材不共享）。

## 环境事实（别重复探测）

- Blender：`E:\SteamLibrary\steamapps\common\Blender\blender.exe`（Steam 版 5.2.3 LTS）
- Blender 插件：DSH × Blender v3.1.0-alpha.1，Gateway `127.0.0.1:39877`，addon v2.0.0 / protocol 12
- GUI 会话需要 Blender 开着且 addon 已连接；`blender_session(action="doctor")` 回 `kind=ok` 才算通道健康
- 长活（>1 分钟）走 `blender_run(action="submit", kind="render"|"headless")`，别占着 GUI
