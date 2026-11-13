# 技术设计 — S

> 配套：`loadout-spec.md`（规则与数值）、`data-schema.md`（数据字段）。
> 本文只写**实现结构与硬约束**。

## 1. 分层

```
App     Bootstrap（场景入口，纯代码构建）  SelfCheck（-scheck 实机自检）
  │
View    GameRoot（局内编排：刷怪/经验/威胁/暂停）
        PlayerController  PlayerWeapons  Projectile  Enemy  EnemyBullet
        HudView（HUD）  InventoryView（背包与三选一）
  │            只读 Core 的结果，不回写规则
Core    Loadout（结算）  GunRuntime（轮转/弹匣）  RunState（经验/威胁/背包/抽取）
        SData（数据解析与查询）  SJson（零依赖 JSON）  LoadoutTypes（数据模型）
  │            零 UnityEngine 依赖
Tools   tools/loadout-tests（dotnet 控制台，直接链接 Core 源码跑断言）
```

**硬约束**：`Core/` 不得出现 `using UnityEngine`（唯一例外是 `SDataLoader.cs`，它是桥）。

这条约束换来的是：整条配件结算可以在 dotnet 下用 121 条断言回归，不用开编辑器。

**为什么值得**：本作最贵的 bug 是「链解析顺序错」「弹药算错」「分裂指数爆炸」——这些全是纯函数问题。
放进 Core 后，改一个数值跑 `dotnet run` 就能 1.6 秒内知道有没有破坏算例。

## 2. 文件职责

| 文件 | 层级 | 职责 |
|------|------|------|
| `Core/SJson.cs` | Core | 手写 JSON 解析（支持 `//` 注释）。不用 `JsonUtility`（不支持字典/数组嵌套）也不用 `System.Text.Json`（Unity 默认引用里没有） |
| `Core/LoadoutTypes.cs` | Core | `ProjectileDesc` `BulletDef` `ModifierDef` `GunDef` `ChainItem` `Scope` 等 |
| `Core/Loadout.cs` | Core | **结算核心**：`ResolveCast`（链解析）`ResolveGun`（枪械件）`ComputeAmmo` `ValidateInsert` |
| `Core/GunRuntime.cs` | Core | 轮转指针、弹匣、换弹、射速冷却；`TryFire` 是唯一开火入口 |
| `Core/RunState.cs` | Core | 等级曲线、威胁、背包、三选一抽取、mulberry32 |
| `Core/SData.cs` | Core | `sdata.json` → 强类型；`MakeItem` `BuildStarterSlots` |
| `Core/SDataLoader.cs` | Core(桥) | **唯一**引用 UnityEngine 的 Core 文件，从 `Resources` 读文本 |
| `View/GameRoot.cs` | View | 场景构建、刷怪表、经验结算、威胁推进、暂停、爆炸结算 |
| `View/PlayerController.cs` | View | 第一人称移动/视角/冲刺/跳跃（新 Input System 直读设备） |
| `View/PlayerWeapons.cs` | View | 持枪、切枪、开火 → 实例化弹丸；散射在瞄准锥内随机 |
| `View/Projectile.cs` | View | 飞行、重力、追踪、穿透、反弹、命中、爆炸 |
| `View/Enemy.cs` | View | 四种敌人 AI；吃护甲/燃烧/减速/空蚀 |
| `View/EnemyBullet.cs` | View | 敌人抛射物 |
| `View/HudView.cs` | View | 运行时构建 HUD；轮转条与准星散射可视化 |
| `View/InventoryView.cs` | View | 背包、拖拽配件、三选一界面；打开即 `timeScale=0` |
| `App/Bootstrap.cs` | App | 唯一场景入口，纯代码组装 |
| `App/SelfCheck.cs` | App | `-scheck` 实机自检 + 截图 + 退出码 |
| `Editor/SceneBuilder.cs` | Editor | `S/重建主场景`、`S/应用工程设置`、批处理 `BatchSetup` |
| `Editor/BuildPlayer.cs` | Editor | 打包到 `Build/Windows/S.exe`，批处理 `BuildBatch` |

## 3. 数据流

```
sdata.json ──SDataLoader──▶ SData ──┬─▶ RunState（经验/威胁/背包/抽取）
                                    └─▶ GunRuntime（每把枪：Slots + Cursor + Ammo）
                                              │  TryFire
                                              ▼
                                        Loadout.ResolveCast ──▶ CastResult
                                              │  （ProjectileDesc[] + AmmoCost + Warnings）
                                              ▼
                                        PlayerWeapons.SpawnCast ──▶ Projectile（场景对象）
                                              │ 命中
                                              ▼
                                        Enemy.TakeDamage / GameRoot.Explode
```

- **规则 → 表现单向**。View 只读 Core 结果，从不修改 `ProjectileDesc`。
- 一次开火只经过一条路径：`GunRuntime.TryFire` → `Loadout.ResolveCast`。UI 预览也用同一个函数
  （`HudView` 调 `ResolveCast` 算「下一发期望」），所以 HUD 数字与实际伤害不可能不一致。

## 4. 确定性

| 项 | 做法 |
|----|------|
| 抽取随机 | `RunState` 内 mulberry32，种子来自启动时间；**不用** `UnityEngine.Random` |
| 结算 | 无随机。散射的随机偏移只在 `PlayerWeapons.SpawnCast`（表现层） |
| 断言可复现 | `tools/loadout-tests` 不走 Unity，输入固定，输出逐位可比 |
| 为什么表现层随机不影响验收 | 断言测的是「描述符」，不含弹道方向 |

## 5. 性能与实现要点

| 点 | 做法 / 理由 |
|----|-------------|
| 投射物用 `SphereCast` 逐帧检测 | 高速弹丸（140 m/s）用 `Rigidbody` 会穿模；手动步进可控 |
| 穿透后推 0.3 m | 避免同一帧重复命中同一个 Collider |
| 分裂代数上限 3（`MaxSplitGeneration`） | 防止 `分裂×分裂×分裂×分裂` 指数爆炸（3^4 = 81）。上限 3 代 = 最多 27 发/颗 |
| 爆炸用 `OverlapSphere` + 去重 HashSet | 一个敌人有多个 Collider 时不重复结算 |
| 材质每次 `new Material` | 初版可接受；后续应改为共享材质 + 顶点色/材质属性块 |
| HUD 每帧调 `ResolveCast` | 每帧仅 1–3 次链解析（≤6 项），可忽略；换来数字绝对准确 |
| UI 全部代码构建 | 无 Prefab 引用断链风险；代价是无法在编辑器可视化调布局 |

## 6. 关键约定（不要回退）

| 约束 | 原因 |
|------|------|
| `Core/` 不引用 UnityEngine | 否则 dotnet 断言跑不了，最贵的 bug 失去保护 |
| 结算只走 `Loadout.ResolveCast` | HUD 预览与实战必须同源，否则数字对不上 |
| 枪械件只在 `Recalc()` 结算 | 施法时再算会与「同名只生效一次」冲突 |
| `damageMul` 在链结算**之后**乘 | 保证 §9 算例可复现；也让配件先后不受枪影响 |
| 弹丸描述符不可变式使用 | View 只读；修改描述符必须发生在 Core 内 |
| 新 Input System 必须配 `InputSystemUIInputModule` | 混用 `StandaloneInputModule` 会让 UI 完全无响应（已踩过） |
| 场景只有一个 `S` 节点 | 其余全靠代码；手拖会被运行时覆盖 |
| 暂停一律走 `Time.timeScale = 0` | 且用 `unscaledDeltaTime` 驱动 UI 动画，否则暂停后 UI 冻结 |

## 7. 已知技术债（初版接受）

| 项 | 影响 | 处理 |
|----|------|------|
| 每次生成弹丸都 `new Material` | 长时间游玩会累积材质实例 | 后续换共享材质池 |
| 敌人视觉是胶囊体 + 颜色 | 无打击感、无受击反馈动画 | 等美术资产 |
| 敌人 AI 只有直线趋近/固定距离 | 无掩体寻路、无协同 | 初版够用；箱庭手工摆点 |
| 无音效 | 开枪/命中/受伤全静音 | `audio-spec.md` 已写规格，未实装 |
| 无 Boss | 第 5 区域清完直接结算 | 拆解 P2 |
| 世界是平面 + 立方体 | 不是真正的「箱庭」多区域 | 拆解 P2 换成手工场景 |
| `SJson` 手写解析 | 无 schema 校验、错误信息不如专用库 | 数据只在开发期改，可接受 |
| 背包网格用 `GridLayoutGroup` | 拖拽时布局重排可能抖动 | 目前可用，后续换绝对定位 |

## 8. 自检体系

| 入口 | 覆盖 | 判据 |
|------|------|------|
| `tools/loadout-tests`（dotnet） | **213 条断言**：24 条 §9 算例、装配校验、轮转/弹药/换弹、枪械件、36 条拖拽预览、区域推进、Boss 状态机 | `RESULT n/n passed`，退出码 0 |
| `S.exe -scheck` | 实机：数据加载、刷怪、开火扣弹、轮转、改装重算、升级、三选一、背包暂停、伤害、结算，并出 6 张截图 | `selfcheck.log` 末尾 `SELFCHECK RESULT n/n passed`，退出码 0 |
| `scripts/check.ps1` | 串起上面两条 + 打包 | `RESULT` 行全绿 |

**已知坑（会让 CI 莫名其妙变红）**：本工程是 Unity 播放器构建，默认开启 Force Single Instance。
上一个 `S.exe` 未退出时，新进程**静默退出且不写 `selfcheck.log`**，
表现为 `RESULT shots FAIL（未生成 selfcheck.log）`。
`check.ps1` 已在 shots 前自动清理残留实例；手动跑自检前请先 `Get-Process S | Stop-Process -Force`。

**判据纪律**：
- 断言里的期望值**写死在测试代码里**，不从 `sdata.json` 反算。数据被改坏时测试必须变红。
- `-scheck` 必须真的 `TryFire` 并检查弹药变化，不能只检查对象存在。
- 截图不是装饰：UI 布局错位、文字重叠只能靠看图发现。

## 9. 验证命令

```powershell
# 纯逻辑断言（1.6 秒）
cd "E:\S\tools\loadout-tests"; dotnet run -c Release

# 一键全量
powershell -ExecutionPolicy Bypass -File "E:\S\scripts\check.ps1"

# 只跑实机自检
& "E:\S\Build\Windows\S.exe" -scheck -screen-width 1600 -screen-height 900 -screen-fullscreen 0
Get-Content "E:\S\selfcheck.log"
```

## 10. Unity 工程约定

| 项 | 值 |
|----|-----|
| 工程根 | `E:\S`（枢纽内 `unity\` 为 Junction） |
| 编辑器 | Unity 6000.6.4f1 |
| 渲染 | URP 17.6（`PC_RPAsset`） |
| 输入 | Input System 1.19+，后端 `activeInputHandler = 1`（仅新输入） |
| 运行时根 | `Assets/_Game/` |
| 数据 | `Assets/Resources/Data/sdata.json` |
| 场景 | `Assets/Scenes/Main.unity`（只有 `S` 节点） |
