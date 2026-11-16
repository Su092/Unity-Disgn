# 当前快照 — S

更新：2026-11-16。权威工程为机器 profile 的 `<GAME:S>`，枢纽 `Project/S/unity` 指向该工程。本次以开发副本替换原正式工程，冲突采用开发副本；原正式工程与枢纽 S 文档已完整备份。

## 工程与 Git

- 工程分支 main，远端 `git@github.com:Su092/Project-S.git`，保留原历史和 origin 跟踪配置。
- 本轮本地工程提交：`685e8b2db3023178aa6bea5d125ef0b6f2fee751`，工作区已干净。
- 旧工作目录变为指向 `<GAME:S>` 的兼容联接，只有一个活动工程和一份 `.git`，本会话通过旧入口访问同一工程。
- 枢纽与工程仍是两个独立仓库；枢纽不追踪 unity 联接内的工程内容。本轮未推送远端。
- 备份目录名 `S_migration_backup_20261116_182214`，位于工程父目录；`project-before` 为原正式工程，`hub-S-before` 为原 S 文档，`retired-source-files` 保存已整合的合成文档及两份一次性补丁脚本。
- 实际路径见工程 `Logs/migration-audit.json`、`migration-backup-location.txt`。备份含源/目标/枢纽的工作区与暂存 diff、原 HEAD、769 文件哈希清单。
- 迁移瞬间 769 文件 SHA-256 及 Git porcelain 状态全部一致。之后仅整理 README、整合合成过程文档和移出两份已执行的临时补丁脚本，游戏代码与资产未因迁移改变。

## 已完成的功能

| 功能 | 当前行为 |
|---|---|
| 经验拾取 | GameRoot 在死亡原地创建 ExperiencePickup，进入 1.5 米才加经验；无磁吸、无到期；暂停不拾取、防重复；对局结束清理。击杀计数和精英回血保持击杀时处理 |
| 物理作用域 | Next/Prev 是后一格/前一格，不跨空槽、不绕回。载荷扫描另走 NextBulletCell，不混用语义 |
| 背包效果预览 | 点击、悬停、拖动显示来源、覆盖格和真正生效子弹；安装/交换/合成预览复制布局，不改实际装配 |
| 障碍碰撞 | 局部 bounds 避免世界 AABB 放大；箱、桶、墙、柱用视觉网格碰撞；视觉原语碰撞立即禁用，柱破坏关闭子碰撞 |
| 子弹与爆炸 | ProjectileVisual 覆盖 17 种子弹和敌方红弹；CombatFx 提供枪口、命中、爆炸、光束和闪电；共享材质，活动特效上限 80 |
| 网格动画 | RigidMeshRig 拆分已有网格并保留几何/材质；WeaponMotion 按真实换弹进度驱动弹匣/机件并模拟枪模后座；EnemyMotion 驱动步行、旋翼和攻击，暂停冻结 |
| 起手与枪奖励 | 全部 6 把枪任选 1 把开局；升级每轮 10% 概率最多出现一把未持有枪。携带上限 2，满额替换当前枪，先校验旧配件返包空间；奖励期间可整理背包再返回 |
| 扩件与合成 | 17 子弹 + 34 衍生，共 51 件、10 作用域；新增 12 衍生并调整旧件范围。同 ID/类型/等级二合一至 Lv.5，支持包↔包、包↔枪、枪↔枪，成品留目标位，不需额外空间 |
| 实例与抽取 | 合成校验所有权，重复/失效拖放不复制或丢失；有效属性不改共享配置。史诗跨轮可重复，同轮三选一不重复；gun_third 保留旧存档兼容但所有初始枪默认开放 |

等级强度为 1 / 1.5 / 2 / 2.5 / 3；连续正向收益按强度、整数收益按级变化，负面代价不随等级加重。详细公式、配置镜像和交互边界见 loadout-spec.md。

## 验证证据

| 检查 | 结果 | 证据与范围 |
|---|---|---|
| 迁移后规则 | 300/300 通过 | check.ps1 -Task tests 的 dotnet 阶段，从新工程读取配置 |
| 迁移后统一 tests | 未通过 | UI 分类审计缺少 12 个新增配件独立图标，规则通过不能代替整体通过 |
| 迁移后 Unity 导入/编译 | 通过 | Logs/migration-unity-compile.log：batchmode 正常退出，return code 0，无 C# 编译错误；不等同播放器构建 |
| Git 连通性 | 通过 | git fsck --connectivity-only 退出 0，历史、分支和远端保留 |
| 枢纽路径 | 补查通过 | profile 和 Project/S/unity 均指向同一工程；doctor 仅因可选 hub.link 为空为 degraded，未将其记成全通过 |
| 碰撞专项（迁移前） | 267/267 | Logs/obstacle-collision-check.log |
| 弹丸视觉（迁移前） | 166/166 | Logs/projectile-visual-check.log；Shots/projectile-visual-sheet.png |
| 网格动画（迁移前） | 66/66 | Logs/mesh-motion-check.log；Shots/mesh-motion-sheet.png |
| 战斗运行态（迁移前） | 18/18 | Logs/combat-play-check.log |
| 合成运行态（迁移前） | 41/41 | Logs/fusion-play-check.log；Shots/fusion-inventory.png |
| 完整 build / smoke / shots / all | 本次未执行 | 不以旧产物或编译成功声称完整构建通过 |

迁移前专项日志随工程完整迁移，已复核 RESULT，迁移本身未重跑这些专项。经验拾取 SelfCheck 断言已增加，但不能用其他专项次数代替其构建后执行证据。

## 待完成

1. 新配件通过 UiAssets.ItemIcon 复用旧图标，尚不满足一 ID 一文件。缺 crossfire、forward_battery、gap_bounce、gap_lens、rear_battery、rear_blast、rear_boost、rear_frost、ring_burn、twin_boost、whole_boost、whole_guidance 的 `item_<id>.png/.meta`；按美术管线补齐并登记 Addressables，再跑分类审计。
2. 完整构建、启动冒烟、实机自检和截图验收；先按工程锁规则确认编辑器退出，不用旧日志替代本版本验证。
3. 拾取与合成改变经验效率和强度曲线，历史 calibration-log 需重新校准；长局性能与弹幕/爆炸压力测试待执行。
4. 方案存档仍未实现。后座当前只作用枪模，不改变镜头瞄准与弹道。

## 维护约定

- 数据为 11 张 TSV，资产统一在 Assets/_Game/Res；启动等待 SRes.PreloadAll，新增资源登记 Addressables 分组/标签。
- Core 除 SDataLoader 桥外零 Unity 依赖；规则与预览共用 Loadout，升级共用 ItemFusion。
- UI 结构改 UIPrefabs 和 Editor 工厂，运行态用 *Refs；不延续手改 YAML 做法，字体统一 UiKit.Font。
- 模型 +Y 上、+Z 前，保留导入旋转；材质走 SMat，CombatGlow 纳入构建包含列表。
- 光标与暂停由 GameRoot.SyncCursorToState 统一裁决；保留默认域/场景重载，避免缓存跨 Play。
- Addressables 异步内容构建不能被 -quit 提前结束；核对日志和真实资源产物再进入播放器验证。
- tools/loadout-tests/loadout-tests.csproj 已纳入 Git；新增 Core 文件检查显式 Compile Include。
- 本轮只同步 Project/S，其他游戏和枢纽全局未提交改动保留。后续在既有规格、任务及本快照更新，不堆叠冲突结论。
