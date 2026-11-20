# 音律敌人合并网格修复（2026-11-19）

## 结果
已修复覆盖现有 Mesh 未完整更新原生几何缓冲的问题，重建 17 个角色/变体/枪械预制体的三档 LOD 和受击代理，并刷新 10 个既有技能衍生物、音符墙和追光灯。原诊断中 02/03/08/11/14/19 的 10 个受影响预制体已与新源文件一致。

所有资源仍为独立 Unity 资产，29 个运行预制体递归无 FBX/Blend/OBJ 依赖。124 个既有 .asset 与全部既有预制体 GUID 对照备份均未改变；253 个原始交付文件 SHA-256 保持一致，未修改或重新要求建模源文件。

## 实现
新增 `SMusicAssetWriter`，以显式 Mesh API 清除旧缓冲并更新位置、法线、切线、颜色、UV、索引格式、子网格/baseVertex、全部骨骼权重、bindposes、BlendShape 和 bounds；即时校验复制结果并标记持久化。角色导入器、补件导入器、原生子资源提取统一调用，避免下次重导出再次混用新旧数据。非 Mesh 资产继续原有序列化保存方式。

权重读取遵循 [Unity 6 文档](https://docs.unity.cn/6000.6/Documentation/ScriptReference/Mesh.GetBonesPerVertex.html)：取得 Mesh 所有的只读权重数组视图，再交给 SetBoneWeights，不自行 Dispose 这些视图。

## 本轮验证
| 检查 | 结果 |
|---|---|
| Mesh 覆盖回归 | 顶点数量/索引/baseVertex、UV2/4、法线切线、旧颜色清除、权重/绑定、BlendShape、持久化重载、重复导入、蒙皮变碰撞、GUID 均通过 |
| 原始分件对比全部 LOD | 765/765，17 个预制体 × 3 LOD；221 个动作实例 × 3 LOD × 7 时点 = 4641 个姿态采样，最大误差 0.0000013m |
| 基础资产 | 814/814 |
| 独立原生资源依赖 | 145/145 |
| 音墙/追光灯补件 | 19/19 |
| 实际 Animator / 模型 Play | 489/489；新增 221 次实际 Animator 输出与原始分件的形变对比，最大误差 0.0000308m |
| 技能 Play | 63/63；命中、精英/Boss 技能、追光转移、暂停、死亡与重开清理 |

采样覆盖各动作的 0%、10%、25%、50%、75%、90%、100%，并非逐帧穷举；拓扑及骨骼映射权重另作精确比较。实际 Animator 检查在每个动作 51% 位置执行，避免只用 SampleAnimation 验证而漏掉运行绑定问题。

日志均位于 `<GAME:S>/Logs/`：`music-mesh-copy-regression.log`、`music-geometry-validation.log`、`music-enemy-validation.log`、`music-native-validation.log`、`music-supplements-validation.log`、`music-enemy-play.log`、`music-combat-play.log`。

截图：`Shots/music-s08-fixed.png`（实际 Animator 修复后姿态）、`Shots/music-enemies-theater.png`、`Shots/music-elite-skills.png`。原始错误截图和诊断日志保存在 `Logs/music-mesh-fix-before-20261119_142812/`；原诊断报告仍保留历史证据。

无本轮编译/Shader/运行异常；测试已退出 Play，无遗留请求。枢纽状态已更新。未构建 EXE、提交或推送。
