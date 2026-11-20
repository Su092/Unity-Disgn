# HUD V2 素材入库与接入

用户于 2026-11-18 授权原图加工入库、HUD 制作与替换。上一轮仅原图的限制在本轮解除。素材遵守 UI 分类唯一目录与 Catalog，已有资源覆盖图片保留 GUID；新增以 Editor API 导入。

HUD 按 hud-v2-assets.md 已确认规则制作，实际准心居中；10:00 倒数，到零停留 00:00，Boss 出现后上方显示血条。主菜单不显示战斗 HUD；暂停显示恢复入口，结算不可被 Esc 或暂停按钮恢复战斗。Alt 释放光标并抑制视角与开火，移动仍正常。

小地图北向固定、玩家居中，显示场景实际障碍轮廓和敌人，宝箱通过 MinimapChestMarker 标记真实宝箱；现有无宝箱玩法，不新增奖励、不标普通箱。范围先取玩家周围半径 35 米。

非 HUD 界面仅替换通用面板、边框、按钮与配件图标素材，RectTransform、层级、事件和布局保持原样。主验收覆盖 HUD 截图、不同枪槽数、重装填、切枪、暂停/Alt、Boss、连续重开和小地图。

## 入库与维护

- 原图：`<GAME:S>/_Inbox/hud-v2-20261118/raw`，不覆盖；加工可重现入口 `tools/process_hud_v2.py`，中间件和源映射见同目录 `processed`、`processing-report.json`。
- 正式图像：`Assets/_Game/Res/Texture/UI/Common`、`Frame`、`Widget`、`Icon`；配件唯一目录 `Icon/Items`，新增 12 张专属配件图标，现有 51 件均有图像。
- 45 设计拆件 + 圆形遮罩，另覆盖 9 张共用面板/按钮/边框。原有图像 GUID 保留。弹药弧统一为正右侧 90°，底轨与填充同心配准；数值和文字由运行时绘制。
- 唯一分类源仍为 `UiAssets.Catalog`；`tools/hud-v2-catalog.json` 用于 Python 管线镜像，分类审计覆盖两者。
- HUD 重建：Unity 菜单 `S/UI/Build HUD V2 Only` 或写入 `Logs/hud-v2-build.request`。通过 Editor API 保存 HUD 并同步 Addressables；不批量重建其他界面。
- HUD 行为：`HudV2View`；地图：`HudMinimapView`、`HudObstacleGraphic`、`MinimapChestMarker`。武器与玩家输入通过 `GameRoot.HudPointerHeld` 共用光标判定。
- 非 HUD 预制体 7 个与开工备份逐字节相同；86 个既有资源 meta 的 GUID 均保持，证据 `Logs/hud-v2-preservation.json`。
- 工作区已有原枪械 FBX 删除，当前枪械显示原有胶囊回退体。本轮不恢复或替换这些用户既有改动。

## 验收完成

2026-11-18：HUD Play 45/45，连续重开 40/40，规则 321/321，统一 tests / 63 静态素材与 51 配件分类 / 九宫格均通过。720p、1080p、2560×1080 宽屏及菜单、背包、换弹、暂停、Boss 截图已检查，见 `<GAME:S>/Shots/hud-v2-*.png`。最终证据见 CURRENT 与 breakdown/17。

测试按 Input System Dynamic 阶段注入独立设备，测试结束移除；连续重开脚本也在 Dynamic 阶段注入 R，避免 Editor 缓冲消费事件。不更改项目输入设置。暂停加载图标显式检查 Paused，防止暂停当帧残余 deltaTime 多转一次。

编辑器测试已结束并回到 Main；未重建 EXE，未提交或推送。

## HUD 边缘修正（2026-11-18）

依据用户截图：满弹弧缺少顶部填充、末格覆盖槽位栏右端、武器图标透出后方底框。填充值改为完整 0–1 区间；所有枪槽数均在末格外预留右端九宫格收口及间隔；主、副武器均新增不透明圆底，位于装饰框和枪图标下方。仅重建 HUD，其他界面保持。

按钮禁用态的默认 alpha=0.5 也会影响 Image 底板，因此武器按钮单独保持禁用态 alpha=1；不按 Alt 时底板依然遮住后方轨道。弹药底轨只保留设计边线，不再出现未填满的上端缺口。

边缘修正验收：HUD Play 60/60；6/8/10/12 格及满弹、换弹、主副枪截图确认。记录 `<GAME:S>/Logs/hud-edge-play-check.log`，仅 HUD 预制体变化。
