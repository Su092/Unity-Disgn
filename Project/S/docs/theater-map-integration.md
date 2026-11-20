# 鸣奏大剧院：正式地图导入与替换

日期：2026-11-18。用户交付完成的剧院模型，授权先完成场景地图导入与替换。

## 交付与入库
来源：`<GAME:S>/_Inbox/Environment/GrandTheater/Export/GrandTheater_Unity6000.unitypackage`。
保留交付 76 种模块、1191 个布局实例、1135 个碰撞体、8 套共享材质、LOD0/LOD1 和原始 GUID。模型、纹理、材质分别放入：
- `Assets/_Game/Res/Model/Environment/GrandTheater`
- `Assets/_Game/Res/Texture/Environment/GrandTheater`
- `Assets/_Game/Res/Material/Environment/GrandTheater`

交付模块已包含轴向校正和法线/Mask 导入设置，通用 SAssetPostprocessor 对这个目录保留交付设置，避免再次转换轴向或把线性贴图改为 sRGB。
原始交付文件未加工覆盖。旧 FoundryArena 资源保留；正式 Main 改用 `Assets/_Game/Res/Prefab/Maps/GrandTheater.prefab`，Addressables s_map 已登记。主场景重建入口同样指向剧院。

## 运行接入
- 保留 FoundryArena 组件类型兼容旧资产，增加 IsTheater、64×72 尺寸和独立导航数据；主动加载地址为 GrandTheater。
- 入口为门厅 (0,0,-32)，舞台 Y=1.2，二楼 Y=6。设置 16 个分布在一楼、舞台、二楼的安全敌人出生点。
- 按交付代理用途映射现有碰撞层：789 个 Both、133 个 Movement、213 个 Shot。楼梯移动用平滑坡面，射击用真实台阶。
- 导航从当前移动碰撞构建，922 个来源，0.5m 半径 / 2m 高 / 0.4m 跨阶 / 50° 坡度，0.12m 体素。保存为 `Res/Prefab/Environment/GrandTheater/Navigation.asset`。
- 敌人沿导航路径移动，使用现有 CharacterController 和重力；攻击前检查地图遮挡，避免隔楼板伤害。
- 小地图障碍根据玩家当前高度筛选，原 HUD 布局不变。
- 场景自己管理室内光照；不再叠加 GameRoot 的室外默认太阳。交付预览灯强度按 URP 游戏距离做 12 倍补偿，保留位置/色彩/朝向。
- Boss 暂用现有角色与技能，从舞台入场并在舞台内小范围移动。新地图不生成旧能量柱，Boss 状态接受地图柱数覆盖为 0；旧地图与默认规则仍保留 4 柱。地刺预警随实际楼层落地。
- 已有经验落地逻辑支持多层，实机验证二楼击杀经验不掉回一楼。

## 验证
- 环境 64/64：资源引用、LOD、出生点、13 条路线双向角色控制器通行、16 个出生点到大厅的导航连通。
- Play 16/16：真实主菜单开局、Addressables、门厅出生、敌人沿楼梯登上二楼、二楼经验、隔层遮挡、无柱 Boss、重开及导航/掉落清理。
- .NET 324/324：原 321 条，加 3 条无柱地图兼容/配置不污染断言。
- 截图已视觉检查：`Shots/theater-auditorium.png`、`theater-balcony.png`、`theater-final-auditorium.png`、`theater-final-balcony.png`。
- 日志：`Logs/theater-build.log`、`theater-check.log`、`theater-play-check.log`、`theater-rules.log`。
- 备份位置记录在 `Logs/theater-backup.txt`；保留开工前 Main、代码、旧地图、Addressables 和物理设置。

## 维护入口与范围
- Editor 菜单：S/Map/Build Grand Theater、S/Map/Verify Grand Theater。
- 请求文件：`Logs/theater-build.request`、`theater-check.request`、`theater-play.request`。
- 先等待脚本编译完成再启动 Play 检查，避免测试过程中热重载清空运行态字段。
- 正式地图材质为交付的 URP Lit；Blender 的专用赛璐璐节点/离线灯光不通过 FBX 自动等价迁移，当前不宣称与 Blender 渲染逐像素一致。
- 敌人概念图尚未用于替换敌人，Boss 的音律玩法仍待后续设计。本轮没有构建 EXE、提交或推送。

## 02 风格赛璐璐渲染

剧院八种共享材质使用 S/Theater Cel。暖光、中间色与蓝灰阴影按表面朝向和现场光照分档，黄铜高光读取金属遮罩，灯具保留自发光。PC 与 Mobile Renderer 在透明物绘制前运行 Theater Ink，用深度突变勾出几何轮廓。线色、宽度与浓度可在 `<GAME:S>/Assets/Settings/TheaterInk.mat` 调整。

已用编辑器在两个质量档渲染，PC Play Mode 剧院回归 16/16。观众席同机位样张为 `<GAME:S>/Shots/cel-before-hall.png` 与 `<GAME:S>/Shots/cel-final-hall.png`，二楼见 `<GAME:S>/Shots/cel-final-balcony.png`。移动设备 GPU 耗时待真机测量。
