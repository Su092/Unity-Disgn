# 音律模型重新导出入库（2026-11-19）

## 本轮结果
已使用建模仓库 `enemy/S_Music_Enemies/Export_v003` 完整交付更新正式工程。该目录名不代表所有资产的修订号；02/03/08/11/14/19 为 manifest v002，07/16/21/29 为 v003。后四种主体及动作与上一轮一致，仍核对并刷新清单。10 种敌人、6 种精英外观变体与音符枪均已重建预制体，继续共用 121 个角色/枪械独立动作。未改变锁定体型和战斗参数，5 种普通怪死亡保持 0.4 秒。

## 归档、分类与引用
- 原始交付快照：`<GAME:S>/_Inbox/chr/S_Music_Enemies/Reexport_20261119_135947`，包含预览、README 与交付验收文件；未将 Blender 工作源文件纳入 Unity。
- 正式模型：`<GAME:S>/Assets/_Game/Res/Characters/Music/<AssetID>/`，按模型、动作、碰撞、贴图保存，既有文件及预制体 GUID 保留。
- 交付资源合计 167 个 FBX；253 个 FBX/PNG/JSON 入库源文件核对 SHA-256 全部一致，128 个文件新增或变化。详细记录 `<GAME:S>/Logs/music-model-refresh-source.json`。
- 重建 17 个角色/变体/枪械预制体与 10 个既有衍生物，新增下述 2 个补件；预制体统一进入 `Res/Prefab/Enemies` 的既有 Addressables 规则。
- 旧交付归档及旧衍生物保留；已读脚本/导入计划改前备份在 `Logs/music-refresh-before-*`。

## 补件接入
### FXM_S14_NoteGate
实测 Unity 包围盒 **2.2 × 3.6 × 0.35m**，底部中心为原点。三档 LOD，实体音符/框架用赛璐璐材质，单层音幕使用双面透明材质，关闭深度写入并保留深度测试。运行时不生成阻挡碰撞体。14 的四栏技能改用此完整模型，移除临时矩形线框；判定仍为不可跳过的 3.6m 高音墙，墙体遮挡、跨楼层隔离及敲击节奏不变。

### SM_MusicFollowSpot
三档 LOD、壳体与独立镜片材质，Generic 骨架、Idle/FocusIn/FocusOut/RigTest 四个动作入库。新增 `MusicFollowSpotRig` 按真实 yaw/pitch 和 `Socket_LightOrigin` 跟踪目标，安装点固定在场景顶部可用表面，旋转头部追踪，光源与光束起点绑定灯口。FocusIn/Out 为 0.5s，暂停时冻结。保留精英/Boss 出场追光、29 召唤时转向召唤物、召唤物死亡后回归的规则；回合结束与重开清理实体灯具。补件交付碰撞仅作为参考，不进入游戏阻挡层。近景发现镜片沿用壳体图集后不发光，已将独立镜片接入持久化白色发光蒙版（生成的 1×1 Unity Texture 资产），确保保存/重新加载后仍保持发光；交付源贴图未改动。

## 验收（本轮重新执行）
| 检查 | 结果 | 日志 |
|---|---:|---|
| 敌人资产、比例、绑定、原地动作、时长 | 814/814 | `Logs/music-enemy-validation.log` |
| 补件 LOD、材质、尺寸、挂点、动作、唯一地址 | 19/19 | `Logs/music-supplements-validation.log` |
| 模型 Play：221 次动作播放、真实命中、死亡/经验、暂停、重开 | 268/268 | `Logs/music-enemy-play.log` |
| 技能 Play：补件加载、追光指向/转移、音墙跳跃/遮挡/楼层、枪械及 Boss | 63/63 | `Logs/music-combat-play.log` |
| 正常 AI 自主释放能力 | 7/7 | `Logs/music-combat-auto.log` |

已查看本轮实机截图：`Shots/music-enemies-theater.png`、`Shots/music-elite-skills.png`、`Shots/music-follow-spot.png`、`Shots/music-follow-spot-front.png`。音幕透明表现与灯具挂载已在正式剧院中确认。未出现本轮 C#/Shader 编译错误或运行异常；所有新导入资源均已有 meta，测试已退出 Play。此次未改规则核心，因此未重复 .NET 规则测试；上轮 338/338 为历史结果。

未构建 EXE、提交或推送。源交付 manifest 的“待游戏验收”文字作为原始交付记录原样保留，本节是正式工程验收记录。
