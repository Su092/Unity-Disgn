# 音律敌人模型入库与调试

> 最新入库：完整重导出与两个技能补件已完成，见 [2026-11-19 补件与模型刷新验收](music-model-refresh.md)。下文保留原轮次记录。

更新：2026-11-19。本文件记录模型入库阶段。后续能力已实现，当前状态见 [能力实现记录](music-combat-implementation.md)；下方“玩法边界”保留为当时的历史说明。

## 交付与分类
源位置为建模仓库 enemy/S_Music_Enemies。07、16、21、29 使用 Export_v003，其余六种使用 Review_v001；没有用旧版覆盖已更新角色。
完整源包归档到 `<GAME:S>/_Inbox/chr/S_Music_Enemies/Imported_20261119`，运行资源在 `<GAME:S>/Assets/_Game/Res/Characters/Music`，按角色、Animations、纹理及衍生物分类。
159 个 FBX、50 张 PNG、21 份 manifest 已与归档原件进行 SHA-256 对照；生成资源不改原 FBX/PNG 字节。

已生成 17 个角色预制体：10 种敌人本体、6 款精英外观、1 个独立音符枪；另有 10 个衍生物预制体。统一位于 `Assets/_Game/Res/Prefab/Enemies`，登记现有 Addressables 敌人分组。121 个独立动作，含变体复用后验证 221 个动作实例。

## 导入和运行处理
- 保留用户锁定身高、Unity +Y 上/+Z 前与单位比例；11 视觉悬空 0.6m，07/19 视觉离地 0.18m，21 移动体积采用本体 1.44m，不把风笛作为移动障碍。
- 采用 Generic 骨架，保持 FBX 轴转换层并校验每条动画绑定；关闭根运动，移动由现有角色控制器驱动。
- 同材质零件按每个 LOD 合并为一个蒙皮渲染器，保留骨骼和动画节点；每角色三个 LOD，每档一个蒙皮 draw。
- 新建 S/Music Character Cel 材质适配 BC/ORM/E，沿用剧院三档赛璐璐受光，发光仅作用于发光贴图。
- 受击代理 FBX 是蒙皮网格：先 BakeMesh，再转换到目标骨骼空间，生成随骨骼运动的凸网格 trigger。移动胶囊与受击网格分离。
- 正式普通/精英出生和 Boss 入口已换成音律模型。精英变体仅外观不同，无新增变体能力或额外缩放。
- 五种普通怪死亡动画统一 0.4s，立即关闭受击与移动碰撞，取消额外 0.35s 尸体等待；击杀、掉落仍在死亡时一次结算。
- 对既有 Boss 技能调用做动作名兼容，保证可播放新角色动作。

## 当前玩法边界
此次完成模型、材质、动作、碰撞、LOD、加载和出生接入；没有将模型入库等同于新能力实现。
现有四类行为与数值表仍保留：Crawler 随机显示 02/19、Brute 显示 07、Bomber 显示 03、Turret 显示 11。精英从 08/14/21 及其外观随机选取，Boss 外观随机 16/29。
因此 11 当前是悬空视觉的原远程策略，不是已完成自由三维飞行；03 当前仍沿用原 Bomber 策略。完整音律怪行为、14 音符连击、29 召唤/音符枪/激光、聚光灯转移及其他新技能仍待按名册实现。
独立音符枪和十种衍生物已做成可加载预制体，尚未在新技能逻辑中生成。不改已确认的技能设计。

## 验收证据
- Unity 资产专项：814/814，通过尺寸/离地、三档合并 LOD、材质、Avatar、受击网格、221 个动作采样、原地动画和时长。日志 `<GAME:S>/Logs/music-enemy-validation.log`。
- Unity Play：268/268，通过 Addressables 载入、所有动作状态、受击区域、真实普通/精英/Boss 出生、暂停冻结、真实弹丸单次伤害、单次击杀和经验掉落、0.4s 普通怪死亡及 0.46s 内销毁、重开清理。日志 `<GAME:S>/Logs/music-enemy-play.log`。
- 独立规则：324/324（dotnet loadout-tests）。Unity 脚本编译和渲染未发现本轮 C# 或 Shader 编译错误。
- 预览：`<GAME:S>/Shots/music-enemies-lineup.png`、`<GAME:S>/Shots/music-enemies-theater.png`。截图为验收摆放，不保存临时对象到 Main；剧院截图临时使用 3m 近裁面排除已有占位枪模，正式相机参数不变。
- 旧模型保留；没有构建 Windows 播放器、提交或推送。短程专项不代表长局性能与全部动画穿插的最终美术验收。

## 重建入口
`S/Enemies/Import Music Delivery` 重建角色、衍生物和 Addressables；`S/Enemies/Validate Music Delivery` 执行资产专项；`S/Enemies/Run Music Play Check` 执行运行态验证并退出测试 Play。
导入清单为 `Assets/_Game/Res/Characters/Music/import-plan.json`；源码 `SMusicEnemyImporter.cs`、`SMusicEnemyPlayCheck.cs`、`MusicEnemyAssets.cs`。
