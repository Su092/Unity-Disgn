# 15 — 失败重开流程重置

- 状态：完成
- 依据：docs/technical-design.md「失败重开的局状态隔离」
- 根因：GameRoot 直接推进 SDataLoader 缓存里的 RunDirector，场景重载未清掉其计时及事件标记。
- 实现：从配置模板创建独立的局内导演；保留现有场景重载与选枪路径。
- 验收：规则回归、Unity 实际场景连续重开，检查倒计时、阶段、精英与 Boss 再触发、玩家及场景对象清理。

## 实现与验证

- RunDirector.CreateRun 深拷贝时间轴阶段、敌人池与精英参数；仅保留配置，不继承运行进度。GameRoot.Start 使用独立副本，继续保持现有 R 重载场景流程。
- 规则回归 321/321（新增 21 条：连续三次重开、缓存隔离、精英/Boss 再触发、不重复触发、空时间轴）。
- Unity 编译通过；SRestartPlayCheck 实测 40/40，使用 Input System 注入 R，完整经过两次失败重载和第三次开局。验证 05:00 精英/10:00 Boss 倒计时、初始阶段/威胁、独立导演、满血/等级/经验/击杀/背包、奖励状态、旧敌人/掉落/Boss 销毁、柱隐藏、重选武器与事件再次触发。
- 复验入口：Unity 菜单 S/Checks/Restart Play Check；结果 <GAME:S>/Logs/restart-play-check.log。
- 编辑器保持打开 Main，测试已退出 Play。本轮未重新打包 Windows EXE，未提交或推送 Git。
