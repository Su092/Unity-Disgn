# 任务：现状盘点与收口

- 状态：进行中（盘点完成，待排期执行）
- 依据：`docs/00-overview.md`、`docs/gameplay-spec.md`、`docs/technical-design.md`
- 目标：把「已经做完的」和「必须补的」分开，避免后续在已完成的系统上重复开发

## 一、已完成（可直接信任）

| 能力 | 证据 |
|------|------|
| 完整对局模拟（召唤 / 合成 / 词条 / 波次 / 拦截 / 战力结算 / 胜负） | `Core/RunState.cs`；`tests` 123 项断言 |
| 静态数据驱动（塔 / 干员 / 词条 / 敌人 / 波次 / 关卡 / 调参全部来自 JSON） | `Resources/Data/sldata.json` + `Core/STData.cs` |
| 3D 战场（模型实例化、瞄准、弹道、特效、落地、朝向） | `View/STBattleView.cs`、`STGroundSnap`、`STUnitFSM` |
| 全代码构建 UI（菜单 / 编队 / 关卡 / HUD / 弹窗 / 结算） | `View/STUi.cs`、`STScreens.cs`、`HudView.cs` |
| 九宫格等比自适应（短边 × 0.22 边距 + 运行时缩放） | `STBuild.FixUiBorders`、`STSliceFit`、`UI SLICE/TEXT` 自检 |
| 素材管线（APIMart 清单 + 地形/车道分离 + 九宫格修复） | `tools/*.json`、`paint_lane.py`、`ui_*.py` |
| 打包与实机自检（输入 / 模型 / 朝向 / 存档 / 飘字 + 20 张截图） | `Editor/STBuild.cs`、`App/STAutoShot.cs` |
| 4 关 10 波内容、8 干员、18 词条、4 职业、5 敌人 | `sldata.json` |

上一次资源校验结论：`RESULT 资源校验通过`（模型 / 动画 / 贴图 / 字体逐项 PASS）。

## 二、必须补的（按优先级）

### P0 文档与仓库存真

| # | 事项 | 改动 | 验收 | 状态 |
|---|------|------|------|------|
| 1 | 工程 `README.md` 写「URP 兼容管线」，实际是内置管线（`ForwardBase` Pass，无 URP 包、无 RP Asset） | 已改为「C# + 内置渲染管线 + 自定义赛璐璐着色器 + Legacy 动画」 | 与 `PROJECT.md` 一致 | 完成 2026-11-10 |
| 2 | 工程内 `Docs/ART-STYLE.md` 迁入枢纽 `docs/art-style.md` | 已删除工程 `Docs/`，README 与 `tools/make_plate_thin.py` 注释改为指向枢纽 | 工程内不再有文档目录 | 完成 2026-11-10 |
| 3 | 工程根残留早期产物：`canvas/`（Cursor Canvas 元数据）、`TowerDesigns/`(42)、`UiC6/`(2)、`UiStyleTests/`(25) | 已整体移入 `tools/_archive/` 并加入 `.gitignore`（`/tools/_archive/`、`/TowerDesigns/`、`/UiStyleTests/`、`/UiC6/`）；Git 中移除 70 个跟踪文件（约 87 MB） | `git status` 只剩文档改动；文件仍在磁盘，可按 `docs/asset-pipeline.md` 原位还原 | 完成 2026-11-10 |
| 4 | 根目录散落日志：`build.log` `verify.log` `unity_*.log` `ui_*.log` | 已移入 `tools/_archive/logs/`（8 份）；已重跑 `tests / verify / build / shots` | 根目录只剩 `icon.png` / `README.md` / `.gitignore`；`build.log` OUTPUT 已指向 `E:/Unity Development/Project/Star Defanse/unity/Build/ST.exe` | 完成 2026-11-10 |

### P1 数值与手感

| # | 事项 | 说明 |
|---|------|------|
| 5 | 结算星级阈值 | 现按核心剩余比例直算，未调优 |
| 6 | `nexus` 关卡车道只有 10 个路径点 | 短而急，是否过简单需实机对局验证 |
| 7 | 强化价增长 1.42× 与召唤价 1.28× 的比例 | 决定「铺开 vs 押词条」的强度曲线，需按 4 关实测校准 |
| 8 | BOSS 波（第 10 波） | 8400 HP + 2 精英 + 4 重甲，需确认满配编队可解 |

### P2 技术债

| # | 事项 | 说明 |
|---|------|------|
| 9 | `STBattleView.cs` 85 KB、`STScreens.cs` 37 KB | 按子系统拆分（战场 / 相机 / 特效 / 弹道；菜单 / 编队 / 关卡 / 弹窗） |
| 10 | `Art/Sprites/` 27 张位图已废弃 | 删文件并移除 `STBuild.CheckSprites` 校验 |
| 11 | `Assets/Shots/` 目录混在 `Assets` 下 | 建议挪到工程根 `Shots/`（已有），避免误打进包 |
| 12 | 无任何 Prefab | 单场景全代码构建是刻意选择，但编辑器内无法可视化调场景；若后续要接美术，需评估 |

## 三、风险

- **确定性依赖**：`RunState` 一旦引入 `Time.deltaTime` / `Random` / 字典遍历顺序，`tests` 会随机挂。
- **九宫格边距**：靠 `verify` 自动写 `短边 × 0.22`；若有人手改 `.meta` 或跳过 verify，
  HUD 信息牌会立刻被压扁（历史 bug 复发点）。
- **着色器 Always Included**：新增运行时 `Shader.Find` 的着色器若忘了写进 Always Included，
  编辑器正常、打包后全消失。
- **FBX 重导**：参数一旦改动，动画根轨道与 `Yaw` 剔除规则会失效，塔与敌人姿态会整体歪掉。
- **DNS 污染**：生图链路依赖脚本内置 DoH；手写请求会得到「提交成功但永远查不到结果」的假象。

## 四、建议排期

1. 先做 P0 的 1–4（文档与仓库清理，半天量，风险最低）。
2. 再按 P1 出一轮实机对局记录（4 关各 3 局），用真实数据调数值。
3. P2 与技术债择机，不阻塞玩法验证。
