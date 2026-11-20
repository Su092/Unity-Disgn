# 受伤边缘恢复

原因：HUD V2生成器将Image设为Color.clear（RGB为0），运行时只恢复alpha导致彩色纹理被乘成黑色。保留现有中心透明的红色渐变素材，修正预制体和两处生成器为白色RGB/透明alpha；受伤当帧显示alpha0.6，0.5秒使用非缩放时间淡出，连续有效受伤重置淡出，不拦截鼠标。无敌与无敌帧沿用GameRoot现有逻辑。仅恢复受伤闪边，不新增持续低血量特效。

验证完成：Unity运行态18/18通过。真实扣血触发、无敌帧阻断、连续受伤重置、无敌/零伤害不闪、非缩放时间淡出、重开清零、16:9与21:9实际像素比对均通过；中央采样像素受伤前后无变化。截图：<GAME:S>/Shots/hud-damage/before-16x9.png、hit-16x9.png、before-21x9.png、hit-21x9.png。对比前已预热离屏URP，避免首帧可见性缓存影响判定。日志Logs/hud-damage-check.log。

原型清单见 [需要提供的UI原型](ui-prototype-checklist.md)。未重生成整套HUD、未修改布局，未构建或提交推送。
