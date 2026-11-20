# 17 — HUD V2 加工入库与制作

- 状态：完成（Editor 主验收；本轮未重建 EXE）
- 依据：docs/hud-v2-integration.md、docs/hud-v2-assets.md。
- 目标：对已生成 UI 原图加工分类入库，制作替换 HUD，其他界面只替换素材。
- 改动路径：`<GAME:S>/Assets/_Game/Res/Texture/UI`、`Res/UIPrefabs/HUD.prefab`、`View/Hud*`、`MinimapChestMarker`、`UiAssets`、输入接入脚本；`Editor/SHudV2Builder` 与 Play 检查；`tools/process_hud_v2.py` 和分类镜像。
- 完成：45 拆件 + 遮罩、9 张共享素材覆盖、12 个配件独立图标补齐、HUD 的交互和实时显示、Addressables 同步。
- 保留：8/8 原始文件哈希不变、7 个非 HUD 预制体内容不变、86 个既有资源 GUID 不变。证据 `Logs/hud-v2-preservation.json`。
- 验收：HUD 45/45，连续重开 40/40，规则 321/321，统一 tests / 分类 / 九宫格通过；720p、1080p、宽屏、换弹、暂停、Boss、菜单和背包截图已查看。
- 日志：`Logs/hud-v2-play-check.log`、`restart-play-check.log`、`hud-v2-rules.log`、`hud-slices.log`。
- 截图：`Shots/hud-v2-*.png`。当前枪械模型为用户既有删除后的胶囊回退体，本轮未变更模型。
- 范围：无宝箱玩法新增，仅标记接入与临时测试；非 HUD 布局待用户后续设计；未提交或推送。

后续修正：用户反馈的满弹弧缺口、槽位栏右端遮挡、枪图标底框透出均修复；HUD 扩展验收 60/60，包含全部枪型端点填充、右端收口与不透明按钮底板检查，画面已确认。
