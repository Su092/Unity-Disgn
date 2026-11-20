# 六款音律武器入库与替换

已按交付清单将6个模型FBX、51个动作FBX和18张贴图复制进项目并分类入库。只修改Gun.tsv的model列，射速/伤害/弹药/槽位及原UI文案保持现有配置。

| 游戏ID | 乐器 | 预制体ID | 动作数 |
|---|---|---|---|
| rifle | 小提琴 | SW01_Violin | 8 |
| smg | 拇指琴 | SW02_Kalimba | 8 |
| shotgun | 手鼓 | SW03_FrameDrum | 8 |
| sniper | 大提琴 | SW04_Cello | 11 |
| beam | 竖琴 | SW05_Harp | 8 |
| launcher | 手风琴 | SW06_Accordion | 8 |

## 资源与重复导入

- 暂存交付：<GAME:S>/_Inbox/weapons/MusicWeapons_v001，import-plan.json与各manifest保留哈希来源。
- FBX导入源：Assets/_Game/Editor/WeaponImport/Sources，仅所需模型和动作，未导入整个Blender工程。
- 运行资源：Res/Model/Weapons/Music、Animation/Weapons/Music、Material/Weapons/Music、Texture/Weapons/Music；六个独立预制体在Res/Prefab/Weapons。
- Mesh、Avatar和AnimationClip均为独立Unity资产；预制体递归依赖没有FBX或Editor路径。S_Weapon Addressables组沿用model前缀与Model标签。
- 菜单 S/Weapons/Import Music Weapon Delivery 重新校验完整清单后导入；不更换已有GUID。导入必须在非Play状态，独占命令行前遵循工程锁规则。

重新导出后的更新步骤：先执行 python tools/stage_music_weapons.py <交付目录>（可先加 --dry-run，只检查不写入），再执行上述Unity导入菜单。脚本按固定六款映射、输入类型及SHA-256预检，统一成功后才更新暂存区。

## 第一人称表现

MusicWeaponVisual通过Playables驱动导入骨架；GunRuntime继续负责弹药和发射，动画无伤害事件。调律片段按真实换弹进度定位，暂停时冻结。切枪后新模型播放Equip；保持0.3s原切枪限制。循环演奏与多弹丸读取分离，已修复低帧率单发可能错过表现窗口的问题。保留轻量整体后座，不再将新模型送入RigidMeshRig拆分。

按米制尺寸放置，采用每款ViewPosition/ViewEuler；大提琴已抬高，瞄准时通过位移适配FOV。导入三档LOD，第一人称固定LOD0；无实体碰撞。Music Character Cel新增默认0的WeaponFill材质参数，只有六款武器启用0.75，使近景木色更清楚，原敌人默认表现保留。

51个动作全部入库。当前自动运行态使用Idle、Equip、Fire/FireLoop、FireRecover、Reload和大提琴AimIdle；Move、Unequip、Inspect、AimIn/Out保留，尚未增加对应输入和双手IK。交付包没有玩家手臂，本轮未另造手部模型。

## 验证与截图

- 资产与五时点三档LOD几何：183/183。
- Unity Play：178/178，覆盖六款实际选枪、发射、换弹进度、暂停、模型切换、重开和常规/瞄准FOV；51个实际动画图采样与源FBX形变比较通过。
- .NET玩法规则：338/338。
- 重导133个已有资源GUID全保留。
- <GAME:S>/Shots/weapons/index.html：30张游戏相机截图（待机/发射/调律/瞄准/21:9），不含Overlay HUD。
- 详细日志：Logs/music-weapon-import.log、music-weapon-validation.log、music-weapon-play.log、music-weapon-import-report.json。

交付源仍有概念装饰简化、UV密度及全行程穿插等未完整美术验收项；本轮几何一致性通过不等于上述美术项目全部通过。没有重新打包exe，没有提交或推送。
