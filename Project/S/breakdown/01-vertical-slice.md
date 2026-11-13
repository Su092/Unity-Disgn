# 任务 01：垂直切片（可玩闭环）

- 状态：**完成**（2026-11-12）
- 依据：`docs/loadout-spec.md`、`docs/gameplay-spec.md`、`docs/technical-design.md`

## 目标

把「射击 → 击杀 → 吃经验 → 升级三选一 → 拖拽装链 → 打得更狠」这条闭环做成可运行、可断言的最小版本。

## 实际落地

| 模块 | 文件 | 说明 |
|------|------|------|
| 结算核心 | `Core/Loadout.cs` | 链解析、作用域、枪械件、弹药 |
| 轮转/弹匣 | `Core/GunRuntime.cs` | 指针、换弹、射速冷却 |
| 局内状态 | `Core/RunState.cs` | 等级曲线、威胁、背包、三选一、mulberry32 |
| 数据 | `Core/SData.cs` + `Resources/Data/sdata.json` | 3 枪 / 10 子弹 / 15 衍生 |
| 玩家 | `View/PlayerController.cs` | WASD、视角、冲刺、跳跃 |
| 武器 | `View/PlayerWeapons.cs` + `View/Projectile.cs` | 开火、散射、穿透、反弹、追踪、爆炸 |
| 敌人 | `View/Enemy.cs` | 4 种 AI；护甲/燃烧/减速/空蚀 |
| 编排 | `View/GameRoot.cs` | 刷怪、经验、威胁、区域、暂停 |
| UI | `View/HudView.cs`、`View/InventoryView.cs` | HUD、轮转条、准星；背包拖拽、三选一 |
| 入口 | `App/Bootstrap.cs` | 纯代码构建场景 |
| 自检 | `App/SelfCheck.cs` | `-scheck` 实机断言 + 截图 |
| 工具 | `Editor/SceneBuilder.cs`、`Editor/BuildPlayer.cs`、`Editor/ShaderSetup.cs` | 场景/打包/着色器 |
| 验证 | `scripts/check.ps1`、`tools/loadout-tests/` | 一键四任务 |

## 验收记录（实测）

| 项 | 结果 |
|----|------|
| `dotnet run`（结算断言） | **121/121 passed** |
| Unity 编译 | 0 errors |
| `-Task build` | `RESULT build Succeeded (0 errors)`，102 MB |
| `-Task shots` | `SELFCHECK RESULT 33/33 passed`，6 张截图 |

## 过程中修掉的真实缺陷（都是「只在实机暴露」的）

| # | 问题 | 现象 | 修法 |
|---|------|------|------|
| 1 | URP Lit 被剥离 | 播放器里 `Shader.Find` 返回 null → `new Material` 抛异常 → 整个 `Bootstrap.Awake` 断掉，游戏黑屏 | ① `SMat` 多级兜底；② `ShaderSetup` 写入 Always Included Shaders |
| 2 | `StandaloneInputModule` | 新 Input System 下 UI 完全不响应，拖拽失效 | 改 `InputSystemUIInputModule` |
| 3 | `Win/Lose` 未真正暂停 | 结算界面出现但游戏继续跑 | 改走 `SetPaused(true)` |
| 4 | `WaitForSeconds` 在暂停时永久挂起 | 自检卡死 90s | 改 `WaitUnscaled` |
| 5 | `CaptureScreenshot` 帧末捕获 | 截到的是「已关闭 UI」的画面，自检假绿 | 截图改成协程，等两帧 |
| 6 | 自检只验状态位不验画面 | 背包没显示也判 PASS | 加 `IsBagVisible` / 卡片计数等可观测断言 |
| 7 | `Application.dataPath` 在播放器里是 `S_Data` | 日志/截图落到 `Build/Windows/`，`check.ps1` 找不到 | 向上找含 `Assets` 的工程根 |
| 8 | `m_trigger` 载荷语义自相矛盾 | 后继作用域 + 引用其后子弹 ⇒ 必然自我重放 | 移出初版，换成 `m_blast`（溅射+伤害） |
| 9 | 同名上限 2 与「霰粒×4」算例冲突 | 规格自相矛盾 | 以规则为准，改算例与文档 |
| 10 | 单发枪 1 位导致 DPS 结构性落后 | 位少 ⇒ 链短 ⇒ 先天弱 | 引入 `damageMul`（连发 1.0 / 榴弹 2.6 / 单发 3.6），在链结算后乘 |

## 明确未做（留给后续切片）

- 无真箱庭（单平面 + 随机方块）
- 无 Boss（第 5 区域清完直接结算）
- 无音效
- 无自制模型（全是 Primitive）
- 无拖拽落点「生效目标数」实时预览（只有文案提示）
- 无局外成长存档
