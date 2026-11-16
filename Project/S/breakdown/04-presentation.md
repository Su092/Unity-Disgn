# 任务：碰撞对齐与战斗动画表现

- 状态：本轮实现与专项检查完成；长局性能和完整构建回归待完成。
- 依据：docs/art-style.md、docs/technical-design.md、docs/gameplay-spec.md。
- 路径：View/SAssets、ArenaBuilder、Pillar、ProjectileVisual、CombatFx、RigidMeshRig、WeaponMotion、EnemyMotion、Enemy、PlayerWeapons；Res/Shaders/CombatGlow.shader；对应 Editor/S*Check。

## 已完成

静态障碍碰撞使用视觉网格；局部包围盒避免世界 AABB 放大；视觉原语碰撞即时禁用，消除同帧空气挡路/挡弹。
十七种子弹形态、轨迹与场效果，枪口/命中/爆炸分层表现，共享材质和特效上限。
基于已有枪/敌人网格分件：真实换弹进度驱动弹匣和机件，弹簧后座驱动枪模；敌人按实际运动和攻击阶段播放刚性动作。

## 验收证据

迁移前障碍 267/267、弹丸视觉 166/166、网格动画 66/66、战斗运行态 18/18。日志和截图位于工程 Logs / Shots，随工程完整迁移。
这些专项结果不代表完整构建或长局性能通过；迁移后的编译检查和待办记录在 memory/CURRENT.md。
