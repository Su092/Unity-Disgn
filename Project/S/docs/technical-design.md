# 技术设计 — S

## 1. 工程与资源

Unity 6000.6.4f1，URP 17.6.0，Input System 1.20.0，Addressables 2.11.2。主场景为 Assets/Scenes/Main.unity，Bootstrap 是启动入口。
正式地图为 Assets/_Game/Res/Prefab/Maps/FoundryArena.prefab，由 51 种交付模块按 layout.json 的 1169 个实例组装。Main 场景包含 S 启动节点和该地图实例；ArenaBuilder 优先绑定已有地图，缺少实例时才从 Addressables 的 S_Map / s_map 加载。
代码在 Assets/_Game，交付资产在 Assets/_Game/Res（Cfg / Model / Texture / UIPrefabs / Font / Shaders / Prefab）；Addressables 配置在 Assets/AddressableAssetsData。
Bootstrap 先等待 SRes.PreloadAll，再读取 TSV、校验 SData 并创建玩家和 GameRoot。禁止在预加载前读取运行资源。
场景、预制体由 Unity Editor 工具或 MCP 修改；UI 结构来自 UIPrefabs，运行态通过 *Refs 绑定，不以手改 YAML 作为常规流程。

## 2. 分层与职责

| 层/文件 | 职责 |
|---|---|
| Core/Loadout、GunRuntime | 作用域、枪械属性、读取与载荷结算、弹匣/换弹/指针 |
| Core/ItemFusion、ChainItem | 合成原子事务、实例等级和有效属性；不改共享配置 |
| Core/RunState、RunDirector、BossState | 经验/奖励/背包、时间轴、Boss 规则 |
| Core/SCfgLoader、SCfgValidator、STsv | 纯 C# 配置解析和校验；SDataLoader 是唯一 Unity 桥 |
| View/FoundryArena、ArenaBuilder、WorldPhysics | 地图标记、地图实例绑定、出生/刷怪/能量柱、角色与弹道碰撞分层 |
| View/GameRoot | 对局编排、刷怪、拾取奖励、暂停/光标、结算与清理 |
| View/ExperiencePickup | 原地经验晶体、1.5 米距离拾取、防重复与暂停 |
| View/PlayerWeapons、Projectile | 将 ResolveCast 结果实例化并执行碰撞与伤害 |
| View/ProjectileVisual、CombatFx | 弹丸外形/轨迹、枪口/命中/爆炸/光束表现 |
| View/RigidMeshRig、WeaponMotion、EnemyMotion | 利用现有网格分件驱动刚性动画 |
| View/InventoryView、DraggableItem | 四方向拖放、范围高亮、合成预览、奖励领取 |
| View/SRes、SAssets、SMat、UiAssets | 资源预加载/查找、网格与碰撞、共享材质、UI 资源 |
| Editor/S*Check | 编辑器静态与运行态专项诊断 |
| App/SelfCheck、SmokeTest、AutoPlay | 构建后实机检查、启动冒烟和自动游玩 |

## 3. 规则与交互同源

Core 除 SDataLoader 外不引用 Unity。Loadout.TargetsOf / EffectRangeOf / AffectedBulletCells 同时支持实战与 UI；Next/Prev 是物理邻格，载荷扫描另走 NextBulletCell。
预览复制 SlotState，不改变实际布局；真实合成验证来源和目标各有且仅有一个所有权位置，成功后保留目标位并消费来源，失效或重复拖放不产生物品。
RunState 的确定性随机在同种子、同候选条件下复现奖励。枪奖励每轮最多一把，替换前先验证背包能容纳旧枪配件，避免部分返还。

## 4. 碰撞与战斗表现

地图构建由 Editor/SFoundryMapBuilder 读取交付布局并用 PrefabUtility 组装、保存和绑定 Main；保留模块 LOD、共享 URP 材质和独立碰撞体。源布局不在运行时解析。Main 只允许一个活动 FoundryArena；SceneBuilder 重建场景时也必须附带地图。
16 个外缘刷怪点和玩家/Boss 出生使用预制体 Transform 引用。Boss 站位抬至平台上方 0.35 米。能量柱底座常驻，完整柱只在 Boss 入场启用；破坏时隐藏完整件、禁用其碰撞并启用交付残骸，沿用 BossState 破防通知。
WorldPhysics 统一楼梯分层：玩家/敌人根对象使用 FoundryPlayer，忽略 FoundryShot；普通弹、光束、地雷/力场、锯刃及敌方弹丸查询排除 FoundryMovement；经验落点查询排除 FoundryShot 并沿用排除角色胶囊的逻辑。
旧 SAssets 包围盒与即时禁用原语 Collider 的修复仍保留给其他对象；地图不再叠加旧 ArenaFloor、WallX/WallZ 或随机掩体。

Projectile.Init 统一创建 ProjectileVisual，覆盖 17 种子弹及敌方红弹；不在发射入口重复叠加旧原语。CombatFx 提供枪口、命中、爆炸环/碎屑、光束和连锁闪电，活动特效上限 80。SMat.Combat 共享材质，CombatGlow.shader 纳入 Always Included。
投射物逐帧扫掠检测，爆炸按目标去重；描述符数量上限 24、载荷递归上限 6。性能边界需要实机长局测试，不能仅凭专项截图认定达标。

## 5. 现有网格动画

RigidMeshRig 以连通部分拆分已有可读网格，保留原顶点、三角面、UV、法线和材质；缓存键包含网格实例、分类及局部变换，不依赖浮动世界矩阵。
WeaponMotion 使用实际 MagBarFill 驱动倾枪、弹匣/弹鼓移出与装回、拉机动作；射击使用弹簧回弹表现后座，仅改变模型，不改变镜头瞄准或弹道。
EnemyMotion 依据实际速度驱动腿/臂/机体/旋翼；Enemy 的攻击前摇结束后才判断攻击条件。战斗动画使用缩放时间，暂停冻结。

## 6. 长期约束

- 暂停与光标由 GameRoot.SyncCursorToState 统一裁决，所有等待用户操作的面板必须解锁光标。
- UI 动画需要非缩放时间；战斗逻辑/动画遵循暂停时间。
- 模型 +Y 上、+Z 前，保留 FBX 导入旋转；不靠任意清零或补偿旋转掩盖问题。
- 材质由 SMat 缓存；新增着色器必须检查构建包含，避免编辑器可见而播放器被剥离。
- InputSystemUIInputModule 配套新 Input System；SInputFix 关闭触摸模拟，输入路由允许 Game View 接收设备。
- EditorSettings 保持默认域/场景重载，避免静态缓存跨 Play 引用已销毁对象。
- Build/Library/Logs/Shots 可再生且不追踪；_Inbox 原料、Assets 及 .meta 需要追踪。
- 枢纽和工程是独立仓库，代码不通过枢纽 unity 联接重复入库。

## 7. 验证与当前限制

统一入口 scripts/check.ps1 支持 tests / setup / assets / ui / build / smoke / shots / map / all。纯规则测试项目文件已纳入 Git；无需换机手动重建 csproj。
tests 同时执行规则断言与 UI 分类审计，任一失败均不算全通过。验证结果必须检查日志 RESULT、进程结束及实际产物。
地图专项入口为 check.ps1 -Task map（SFoundryMapBuilder.Validate），运行态使用 Logs/foundry-play.request；其他专项入口包括 SObstacleCollisionCheck、SProjectileVisualCheck、SMeshMotionCheck、SCombatPlayCheck、SFusionPlayCheck；运行态检查通过 Logs/*.request 触发并写日志和截图。
本轮的次数、迁移编译结果与尚未执行的构建验证记在 memory/CURRENT.md。

当前新增 12 配件通过 UiAssets.ItemIcon 别名复用已有图标，缺少一 ID 一文件的独立 PNG/.meta，UI 分类审计未通过。旧校准数据不代表加入拾取和合成后的平衡；长局性能与完整构建回归仍需另行验收。


## 敌人资产接入（Review_v002）

使用 <GAME:S>/_Inbox/chr/S_Foundry_Enemies/Review_v002 的 9 个角色与 56 个原地动作。普通与精英分别使用独立预制体和交付尺寸；精英数值倍率保持，取消额外的视觉 1.4 倍缩放。URP 材质按交付图集绑定，三个 LOD 明确配置。模型、动画、碰撞参考保留在 Res/Characters，运行时仅通过 S_Enemy 分组预加载正式预制体。

原有网格拆分动画由导入 Generic 骨骼动作替代；攻击动作按现有伤害前摇对齐，死亡立即结算并关闭碰撞，视觉尸体短暂保留。碰撞代理按绑定骨骼跟随，移动胶囊不参与射击查询；复合受击代理必须按敌人去重，防止一发子弹重复扣血。Boss 使用交付体型、挂点与技能动作。所有 prefab/材质/导入设置通过 Editor API 生成。

交付包标记 REVIEW / NO-SHIP 的美术精修、纹理密度及全帧穿插等未完成项保留，不用游戏导入通过替代原始美术验收。


导入实施补充：模型 FBX 保留 ARM_<asset> 层，独立动作 FBX 将该层折叠为根；导入器把动作曲线绑定到模型的真实路径并保存 .anim，避免根轴旋转覆盖和骨骼动作静止。新角色保留 FBX 模型轴转换，动作曲线不覆盖模型根节点或骨架外层转换；按实际攻击/炮口挂点验证 +Z 向前。交付碰撞 FBX 未包含网格，使用 tools/extract_enemy_proxies.py 从原 .blend 只读提取。交付根目录、原始模型及动作不改写。

维护入口：S/Enemies/Import Foundry Delivery、S/Enemies/Validate Foundry Prefabs；统一验证脚本新增 -Task enemies。完整重导前先以 Blender 执行代理提取脚本。生成后的 prefab、.anim、材质和网格均应随游戏仓库追踪；原交付位于 _Inbox。


## 失败重开的局状态隔离（2026-11-18）

结算按 R 重开仍重载 Main，并重新选择初始武器。SDataLoader 只缓存配置；GameRoot 每次启动从时间轴配置创建独立 RunDirector，不能推进缓存中的模板。新局计时、威胁、阶段、精英次数、Boss 入场标记均归零，配置中的时间、敌人池及 Boss 阶段保持原值。场景重载负责销毁旧敌人、掉落、弹丸和 UI，并新建玩家、背包与奖励队列。验收覆盖精英前失败、Boss 已入场失败及连续两次重开。
