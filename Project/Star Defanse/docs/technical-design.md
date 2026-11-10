# 技术设计 — 星轨防线

## 1. 分层

```
App      STMain（流程 / 输入 / 存档 / 音效）  STAutoShot（实机自检）  STLevelShot
  │            ↑ 读状态、发指令
View     3D 战场（STBattleView）  UI（STUi / STScreens / HudView / BannerView）
  │            ↑ 只消费事件，不改逻辑
Core     RunState（对局模拟）  STData（静态数据查询）      ← 零 Unity 依赖
  └──────────────────────────────────────────────
Editor   导入规则 / 资源校验 / 打包 / 场景生成 / 逻辑自检
```

**硬约束**：`Core/` 不得 `using` 任何 `GameObject` / 渲染 / 输入 API。
这条约束换来的是 —— 整局对局可以在无场景的情况下跑（`STSimTests` 123 项断言走这条路径）。

## 2. 文件职责

| 文件 | 职责 |
|------|------|
| `Core/STData.cs` | 反序列化 `Resources/Data/sldata.json` + 纯查询（职业/干员/词条/敌人/波次/关卡/调参），无状态 |
| `Core/RunState.cs` | 局内模拟：路径、召唤、移动、合成、词条、塔/敌/拦截/弹道、波次调度、胜负、事件广播 |
| `View/STBattleView.cs` | 3D 战场：模型实例化、炮塔瞄准、弹道、特效、相机与灯光 |
| `View/STUi.cs` / `STScreens.cs` / `HudView.cs` | 代码构建 UI：HUD、菜单、编队、关卡、弹窗、结算 |
| `View/STFxSystem.cs` | 战场特效与飘字（飘字走 Overlay Canvas，永远盖在 3D 之上） |
| `View/STUnitFSM.cs` | 单位动画状态机（`FSM` 表在 `STBattleView` 顶部） |
| `View/STUnitView.cs` | 单位模型与骨骼引用（Yaw / Pitch 节点） |
| `View/STAssets.cs` | `Resources` 加载 + 命名规则 + 缓存（塔贴图按职业 + 等级拼接） |
| `View/STMesh.cs` | 程序化网格：底盘、台面、光环、弹道、血条（顶点色复用材质） |
| `View/STShaders.cs` | 着色器解析与兜底（`StarLane/ModelLit`、`StarLane/Unlit`） |
| `View/STInput.cs` | 输入适配：屏幕像素 → 1080×1920 设计坐标（左上原点、y 向下），键盘快捷键 |
| `View/STSliceFit.cs` | 九宫格四角等比自适应（布局稳定后补算 `pixelsPerUnitMultiplier`） |
| `View/SfxBank.cs` | 程序化音效：启动烘焙成 `AudioClip`，8 个 `AudioSource` 轮询 + 1 秒限流 14 次 |
| `View/BannerView.cs` | 顶部横幅（WAVE 01 / ELITE INBOUND / BOSS APPROACHING）与 toast |
| `View/STGroundSnap.cs` | 生成后第一帧用真实 `Renderer.bounds` 把单位最低点压到 y=0 |
| `View/STGateVortex.cs` | 出生门漩涡自转 |
| `App/STMain.cs` | 屏幕切换（`Menu / Formation / Levels / Battle`）、固定步长循环、指针拖拽、存档、音效 |
| `App/STAutoShot.cs` | `-autoshot` 实机自检与截图（输入 / 塔姿态 / 朝向 / 存档 / 飘字 / UI 九宫格） |
| `App/STLevelShot.cs` | `-shotlevel N` 单关战场预览截图 |
| `Editor/STAssetPostprocessor.cs` | PNG / FBX / 字体导入规则（Sprite 类型、九宫格边距、动画轨道剔除） |
| `Editor/STBuild.cs` | `VerifyResources`（资源校验 + 九宫格边距写入）、`BuildPlayer`（打包） |
| `Editor/STSimTests.cs` | 逻辑回归断言集（headless） |
| `Editor/STSetup.cs` | 批处理入口 `RunSimTests` / `VerifyResources` / `BuildPlayer` |
| `Editor/STSceneBuilder.cs` | 生成 `Main.unity`（只含一个 App 根节点）与竖屏工程设置 |
| `Editor/STShaderSetup.cs` | 把自定义着色器写入 Always Included Shaders（幂等） |
| `Editor/STUiBorders.cs` | 显式修复九宫格边距并强制重导入 |

## 3. 数据流

```
sldata.json ──STData──▶ RunState（种子 + 编队）
                             │  每帧 Step(dt)  →  内部状态
                             └─▶ List<STEvent> ──▶ STMain 分发 ──▶ STBattleView / HudView / STFxSystem / SfxBank
```

- **逻辑 → 表现单向**：`View` 只读 `RunState` 的只读属性与事件，从不回写。
- **指令 → 结果**：玩家操作走 `RunState.Summon / DragTower / MoveHero / Upgrade / PickAffix`，
  统一返回 `RunResult { Ok, Reason, Kind, Cost, Events }`；`Reason` 是给 UI 的提示码
  （`gold` / `no-platform` / `different-tower` / `level-mismatch` / `max-level` / `locked` …）。
- 事件种类：`Summon Unlock Move Merge Affix GuardSpawn GuardDown GuardReturn Hit Kill Leak Spawn Wave Shot HeroShot Explosion WaveClear Victory Defeat`。

## 4. 确定性与坐标系

- 随机数只用 `mulberry32`（`RunState.Rng()`），种子 `SeedValue`；同种子同操作 → 结果逐字节一致。
- 战斗层坐标 = 1080×1920 设计像素，**左上原点、y 向下**（与 Godot 原版一致）；
  `STInput` 负责把屏幕像素换算进来，`STBattleView` 负责换算到 3D 世界。
- 车道是折线 `path[]`，`RunState.PathPos(dist)` / `PathAngle(dist)` 按累计长度取点，
  所以「地图上画的路」与「敌人走的路」共用同一组数据。

## 5. 渲染

- **内置管线**，未装 URP（`GraphicsSettings.m_CustomRenderPipeline` 为空）。
- 两个自定义着色器：`StarLane/ModelLit`（赛璐璐：厚描边 + 双色平涂 + 硬边高光）、
  `StarLane/Unlit`（UI 层与特效）。
- 所有材质都是运行时 `new Material(...)`，**必须**把着色器写进 Always Included Shaders
  （`STShaderSetup`），否则打包后 `Shader.Find` 返回 null：编辑器正常、播放器里射程圆 /
  血条 / 弹道 / 模型全部消失。`STShaders` 里还留了 `Unlit/Transparent` → `Sprites/Default` 兜底。
- 程序化网格集中在 `STMesh`，用顶点色区分颜色，避免材质实例爆炸。

## 6. 关键实现约定（踩过的坑，不要回退）

| 约束 | 原因 |
|------|------|
| 炮塔**只转 `Yaw` 骨骼**，底座永不旋转；瞄准角自校准（生成时记录静止炮口朝向） | 转根节点会让底座跟着转；手填常数会随模型迭代失效 |
| `Body` 同时应用 `Pitch` 与 `Yaw`（`Quaternion.Euler(Pitch, Yaw, 0)`） | 漏掉 `Yaw` 会让敌人整体倒着走 |
| 动画轨道剔除只删「路径**末段**恰好是 `Yaw`」的轨道 | 用子串匹配会误删后坐 / 炮口闪光等后代轨道 |
| FBX 重导参数：`Scale 1.00 / FBX All / Forward -Z / Up Y / Apply Unit / Use Space Transform`，`Apply Transform` 不勾 | FBX 会把轴转换烘焙成根节点 `RotX(-90°)` 轨道；敌人靠它立起来，塔的姿态另由 `Pitch` 校正 |
| 飘字走**屏幕空间 Overlay Canvas** | 放 3D 层会被血条等 Always+Transparent 材质挡住 |
| 落地由 `STGroundSnap` 在生成后一帧按真实 `Renderer.bounds` 压到 y=0 | 手填 `localPosition.y` 会悬空或陷地，模型换一批就全错 |
| 逻辑必须确定性 | 否则 `tests` 失败、bug 复现不了 |
| 工程内不使用 SVG，素材一律 PNG/JPEG 位图 | 运行时只走 `Resources.Load<Sprite>`，不引矢量管线 |
| 场景里只有一个入口节点 | 所有视图运行时构建，手拖引用必然断链 |

## 7. 自检体系

| 入口 | 覆盖 |
|------|------|
| `check.ps1 -Task tests` → `STSimTests` | 123 项逻辑断言：召唤/合成/词条/波次/护甲/拦截/胜负/确定性 |
| `check.ps1 -Task verify` → `STBuild.VerifyResources` | 位图可加载、模型与动画齐全、模型含网格与 basecolor、动画根轨道/Yaw 轨道已剔除、字体存在；顺带写入九宫格边距 |
| `check.ps1 -Task build` → `STBuild.BuildPlayer` | Windows x64 打包到 `Build/ST.exe`，日志写 `build.log` |
| `ST.exe -autoshot` → `STAutoShot` | `INPUT / MODEL / FACING / SAVE / FX` 五组实机自检 + `UI SLICE` / `UI TEXT` 九宫格检查 + 20 张截图 |

`shots` 任务的截图清单：`01-menu` `02-levels` `03-formation` `04-battle-start`
`05-after-summon` `05b-after-input` `06-mid-run` `07-affix-modal` `08-elite` `09-boss`
`10-result` `11-guide` `12-pause` `13-range-click` `14-range-drag`。

**判据**：`UI SLICE n/n` 要求四边之和 < 控件尺寸；`UI TEXT n/n` 要求文字字形框落在内容区内。
改布局或换素材后这两行必须全绿，否则就是玩家反馈的「UI 被压扁 / 文字压在花纹上」。

## 8. 已知技术债

- 工程根残留早期产物已在 2026-11-10 归档到 `tools/_archive/` 并从 Git 移除：
  `canvas/`、`TowerDesigns/`、`UiStyleTests/`、`UiC6/`、旧日志（见 `docs/asset-pipeline.md`）。
- `STBattleView.cs`（85 KB）与 `STScreens.cs`（37 KB）单文件过大，视图与布局混在一起，值得按子系统再拆。
- `Resources/Art/Sprites/` 27 张图已不被运行时使用，但 `STBuild.CheckSprites` 仍在校验。
- 单场景 + 全代码构建便于迭代，但没有任何 Prefab，编辑器里无法可视化调场景。
