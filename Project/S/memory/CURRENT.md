# 当前快照 — S

## 2026-11-20 发布快照：曲谱装配、赛璐璐贴图与控制台修复

本节是当前状态；下方旧记录中的“未提交/推送”和旧规格是当时的历史状态。

- 地图为 GrandTheater，六款音律武器与音乐敌人已接入。
- 曲谱背包 15 格，合成最高 Lv.3。出生点立方体作为谱架占位，靠近按 F 打开装配并暂停；左键顺序安装、拖放安装/替换/合成、右键卸下，R 或整理按钮按类型、稀有度和编号排序并补空。
- Tab 只折叠/展开 HUD 的曲谱与乐器槽位预览，不直接打开背包。乐器图标保留底框，曲谱图标不加框；小地图右上，倒计时靠近暂停。品质配色：衍生红、普通子弹蓝、高品质子弹金。多余文字已移除。
- 谱面、背包、描边关闭/整理图标及简洁预览底框经审核入库。追光压暗仅在需要激光灯的阶段生效。
- APIMart 参考现有模型颜色贴图生成 33 张重绘并经用户批准替换，原尺寸、透明通道、GUID 与数据贴图保持。原图备份与同镜头渲染对比：<GAME:S>/_Inbox/cel-texture-review-v1/comparison/index.html。
- 六款乐器重复 LODGroup 与 UI 预制体关闭时 Selectable 注册列表越界已修复；清理旧 API 警告；设备模拟器退出后恢复普通 Game 视图。控制台回归 47 项、曲谱交互 42 项通过，最后检查 0 错误/0 警告。
- 提交前规则断言 354/354，通过检查时补齐六张曲谱 UI 在 Python 公共分类表中的登记；完整 tests（规则断言与 UI 分类）RESULT ALL PASS。
- FPS/TPS 切换、角色持握和 Motion Matching 仅讨论，尚未实现；Motion Matching 按用户要求暂不接入。
- 本轮提交不新增 EXE 构建，已完成的 Unity Play/资源与规则验证不等于全量构建验证。

对应 S 工程提交：7e6b7c3800c5eba9e42230728dabe7e6f015ecd9。

实现与验证详情：[曲谱/贴图/控制台](../docs/score-cel-console-release.md)。



### 入场速度与前景音符（已完成）
入场速度为此前140%，时长约0.929秒；退场1.1秒和固定单曲线不变。12个浮动音符放大50%，使用独立前景层；新增6张音符柔光蒙版，增强线谱多尺度柔光，复用加色材质。实机46/46通过，UI素材登记检查通过。54帧引擎采样预览：<GAME:S>/Shots/upgrade-ui/index.html。


更新：2026-11-18。权威工程为机器 profile 的 `<GAME:S>`，枢纽 `Project/S/unity` 指向该工程。本次以开发副本替换原正式工程，冲突采用开发副本；原正式工程与枢纽 S 文档已完整备份。


## 升级线谱二倍速度与折角修复（2026-11-20）
进场2.6→1.3秒，退场2.2→1.1秒，固定曲线保留。折角根因为97点覆盖像素重心受抗锯齿波动影响（身体段最大3.78px）；源素材中心平滑（拟合RMS0.067px），未重新生成图片。改五笔画等权亚像素中心、平滑拟合、1025点三次补偿、解析切线与512段网格，预处理流程同步。Unity44/44通过，近景已查看，59帧预览 <GAME:S>/Shots/upgrade-ui/index.html。未构建/提交/推送。

## 升级线谱固定曲线输送（2026-11-19）
最新用户要求：整体太急，严格沿一条曲线运动。现使用固定S曲线和弧长查表，所有材质点共享一个距离偏移、段间弧长不变，删除此前分段插值/压缩/回摆。进场2.6秒、退场2.2秒，长匀速滑行和缓停。图标/飞行音符中心沿同一曲线；停靠后音符浮动、框上移展开及选中入包保留。Unity42/42通过，含1722个曲线样本和间距守恒，88帧预览 <GAME:S>/Shots/upgrade-ui/index.html。未构建/提交/推送。

## 升级线谱飞行感修订（2026-11-19）
用户反馈像整体推入，现已移除父节点横向平移。改为每段材质点沿不同时间的曲线路径飞行，前端领飞、尾端跟随、上扬回摆；图标与音符共享谱线轨迹和倾斜。进场1.25s、退场1.1s，停稳后仍渐入信息框。Unity42/42通过，58帧新版预览 <GAME:S>/Shots/upgrade-ui/index.html。未构建/提交/推送。

## 音律升级界面终版入库与演出（2026-11-19）
63张独立Sprite：四色框、6音符、线谱/柔光2层、51去底盘配件图标。非线性左入，图标上移同步框展开淡入，暂停选择，框反向收起，选中曲线飞入左上主武器图标，其余随线谱右出；进退场锁定点击且奖励仅提交一次。现有满包保留奖励/Tab整理路径，替换页与新配件品质按用户要求留后续。绿色乐器、蓝色普通子弹、金色现有Rare/Epic子弹、红色衍生。顺带纠正旧长笛/圆号HUD名称及图标为拇指琴/手风琴（模型渲染，保留GUID）。
Unity36/36、规则338/338、分类/九宫格审计通过，16:9/21:9已视觉复核。动效预览 <GAME:S>/Shots/upgrade-ui/index.html；说明 docs/music-upgrade-ui.md；任务 breakdown/music-upgrade-ui.md。未构建/提交/推送。

## HUD受伤边缘已恢复与原型清单（2026-11-19）
修复HUD V2生成器Color.clear清零RGB导致红色边缘变黑的问题；HudView当帧设置白色RGB/alpha0.6，0.5秒非缩放时间淡出，重复有效受伤重置，重开清零，不拦鼠标。增量修改HUD.prefab与两处生成器，现有布局和渐变贴图保留。Unity18/18通过，含真实扣血、无敌、暂停淡出、16:9/21:9渲染像素和中心透明验证。截图 <GAME:S>/Shots/hud-damage/。
原型清单 docs/ui-prototype-checklist.md：优先背包/三选一/开局乐器选择，再首页/暂停/结算；解锁与音量可嵌入，现有HUD无需重画。见 docs/hud-damage-feedback.md、breakdown/33-hud-damage-and-ui-list.md。未构建/提交/推送。

## 六款音律武器已入库替换（2026-11-19）
6模型/51动作/18贴图清单校验后分类入库，生成独立Mesh/Avatar/Animation/Material与6个Prefab；运行无FBX/Editor依赖。Gun.tsv仅改model映射，S_Weapon组接入预加载；乐器按米制骨架播放发射/调律/Equip，大提琴AimIdle。旧RigidMeshRig仅用于旧枪，修复低帧率点射动画丢失，暂停与换弹进度同步。第一人称位置/FOV与材质可见度已调试；交付无玩家手臂，未制作手部IK。
验证：资产183/183、实际Play178/178、规则338/338，重导133GUID稳定；最大实际动画图网格偏差2.5e-06m。截图 <GAME:S>/Shots/weapons/index.html。源美术简化/UV密度/全行程穿插未完整验收，未构建/提交/推送。详见 docs/music-weapon-import.md、breakdown/32-music-weapon-import.md。

## 六武器建模任务包（2026-11-19）
按指定 Blender 技能模板完成六份独立建模任务书（小提琴/拇指琴/手鼓/大提琴/竖琴/手风琴），含首版尺寸、功能分件、骨架/手部挂点、动作时长、LOD、命名、FBX与白名单交付规格。APIMart链式重生成12张干净背景参考：各款完整主图+结构多视图，与MD同文件夹。图像解码/SHA-256/逐张查看、六款Gun.tsv参数、相对链接与ZIP完整性均检查。AI多视图非工程标定，密集结构数量以文字为准。
索引 docs/weapon-modeling-prompts/README.md；图库同目录 index.html；整包 <GAME:S>/_Inbox/music-weapon-modeling-20261119/MusicWeapons_Modeling_Package.zip。仅参考和任务书，未建模/入库/修改玩法，未提交推送。

## 武器吹奏类概念替换（2026-11-19）
用户要求改善第一人称表现，已将 02 长笛换为拇指琴（双拇指快速拨片），06 圆号换为手风琴（双手拉合风箱、重音抛射），保留 smg/launcher 原定位及其他四款。APIMart 2/2 新图完成，1536×1024，解码/SHA-256/视觉检查完成。总览 <GAME:S>/_Inbox/music-weapons-concepts-20261119/index.html 已更新；旧图与旧总览保留。仅概念和文档变化，游戏内 HUD 名称/图标/模型/玩法未改。

## 音律六武器概念图（2026-11-19）
已用 APIMart / gpt-image-2 生成 6 张独立概念板，沿用 02 复古动漫赛璐璐与已有映射：01 小提琴/rifle、02 长笛/smg、03 手鼓/shotgun、04 大提琴/sniper、05 竖琴/beam、06 圆号/launcher。各含主体、调律/持握结构及第一人称攻击小图；6/6 完成，1536×1024，解码/SHA-256/逐图查看完成。总览 <GAME:S>/_Inbox/music-weapons-concepts-20261119/index.html；见 docs/music-weapon-concepts.md。仅概念候选，未修改玩法、模型、预制体或正式贴图，未提交/推送。

## 音律敌人按清单规范入库（2026-11-19）
已替换整目录入库方式：新增菜单 S/Enemies/Import Music Delivery (Manifest)，先预检完整交付，再仅导入清单的 154 个模型/动作 FBX 和 45 张贴图。当前包其余 241 个文件跳过；FBX 归项目 Editor/MusicImport/Sources，运行 Mesh/Animation/Material/Texture 各归 Res 对应 Enemies/Music 分类，29 个预制体不依赖项目 Editor 源文件。
473 个已有资源分类迁移且独立比对 GUID 全保留，73 个无引用交付资料/旧碰撞资产归档到 _Inbox，原 Characters/Music 混放目录移除。全量重导成功（相同输入复制 0 文件），原生 GUID/锁定体型/动作/轮廓受击箱保留。
验证：预检 9/9、资产 814/814、原生依赖 145/145、补件 19/19、几何 765/765（4641 姿态样本）、受击覆盖 1020/1020、模型 Play 494/494、技能 Play 63/63。已退出测试 Play，未构建/提交/推送。见 [规范入库与操作说明](../docs/music-import-workflow.md)、breakdown/29-music-import-workflow.md。

## 音律敌人外观受击箱与移动朝向（2026-11-19）
17 个敌人/变体/Boss/音符枪预制体已改为跟随骨骼的分段外观受击箱，覆盖头部、肢体和乐器。按已说明默认口径，扩大的是射击受击范围，躯干移动阻挡保留。导入器接入同一生成器，重导不会回退；16 滚筒弱点与死亡关闭受击箱保留。
普通怪、精英寻路/冲锋、Boss 移动按碰撞/导航处理后的实际水平位移转向，移除移动时朝玩家的覆盖。验收：1020/1020 动作姿态面积采样超过 80%，最低 95.414%；资产 814/814、原生依赖 145/145、Unity Play 494/494（含外围命中只扣一次血和贴墙转向）、技能 Play 63/63。编辑器已退出测试 Play，未构建/提交/推送。见 [受击箱与朝向](../docs/music-hitboxes-facing.md)、breakdown/28-music-hitboxes-facing.md。

## 音律网格拉伸已修复（2026-11-19）
新增 SMusicAssetWriter，统一显式更新 Mesh 几何/索引/权重/绑定数据，保留 GUID。已重建所有音律角色三档 LOD、受击代理及技能衍生物，原 6 类/10 个预制体的新旧网格混用问题解决。原始建模交付未改动；29 个运行预制体继续无 FBX 源依赖。
本轮验收：几何 765/765（4641 姿态采样，最大误差 0.0000013m）、资产 814/814、独立资源 145/145、补件 19/19、实际 Animator/模型 Play 489/489、技能 Play 63/63；覆盖保存重载及重复导入回归。已查看修复后画面，编辑器退出测试 Play，未构建/提交/推送。详见 [网格修复验收](../docs/music-mesh-fix.md)、breakdown/27-music-mesh-fix.md。下方“待修复”条目为历史诊断，已由本节取代。

## 音律敌人网格拉伸：已诊断，待修复（2026-11-19）
用户截图已复现，08 原始 FBX 同一动作显示正常，合并网格拉面。导入器使用 EditorUtility.CopySerialized 覆盖 Mesh 时未完整更新几何缓冲，导致旧网格与新骨骼绑定信息混用；复制临时 Mesh 的实验已复现。02/03/08/11/14/19 共六类、含变体十个预制体受影响。07/16/21/29及音符枪本轮对应样本几何一致。
此前资产/Play/原生依赖检查没有验证动画形变后的网格一致性，因此“全部通过”不代表画面正确；上述六类模型当前不能视为美术验收通过。只新增诊断工具、截图和文档，未修改正式模型或运行逻辑，修复尚未执行。详见 [网格拉伸诊断](../docs/music-mesh-diagnosis.md)、breakdown/26-music-mesh-diagnosis.md。截图 Shots/music-s08-source-diagnosis.png 与 music-s08-imported-diagnosis.png。

## 音律模型转为独立 Unity 资源（2026-11-19）
按用户“导入引擎，不要引用”要求，29 个敌人/变体/音符枪/衍生物预制体已解除 FBX 子资源依赖，提取 25 个 Mesh 与 29 个 Avatar 到 Res/Characters/Music/Native，原生动作、材质、贴图和既有网格继续使用工程内资产。所有预制体 GUID 保留；递归依赖无 FBX/Blend/OBJ，外部 Blender 目录不参与运行。FBX 仅保留为导入源；两套导入器已接入独立资源提取，后续入库不会回退。
本轮检查：原生资源 145/145、资产 814/814、模型 Play 268/268、技能 Play 63/63。编辑器已退出测试 Play，未构建/提交/推送。详见 [原生资源入库](../docs/music-native-assets.md)、breakdown/25-music-native-assets.md。

## 音律模型重新导出与技能补件入库（2026-11-19）
完整 Export_v003 交付已入库：02/03/08/11/14/19 更新为 v002，07/16/21/29 保持 v003，现有 GUID 和体型/技能规则保留。17 个角色/变体/音符枪预制体重建；新增完整音符墙 FXM_S14_NoteGate 与实体追光灯 SM_MusicFollowSpot，已替换临时音墙轮廓、接入真实灯口与 yaw/pitch 追踪，29 灯光转移/回归有效。此前“缺两个3D补件”已解决。
本轮重新执行：资产 814/814、补件 19/19、模型 Play 268/268、技能 Play 63/63、自然 AI 7/7；253 个源文件 SHA-256 一致。截图 Shots/music-elite-skills.png、music-follow-spot-front.png、music-enemies-theater.png。测试已退出 Play，未构建 EXE/提交/推送。详见 [重新入库验收](../docs/music-model-refresh.md)、breakdown/24-music-model-refresh.md。

## 音律精英与 Boss 能力实现（2026-11-19）
08/14/21 精英、16/29 Boss、栏杆音符枪和追光机制已接入正式出生/AI，精英变体共用能力。14 落音0.5s悬停、0.9s敲击、四栏4–8组/0.8s/独立20%双击和不可跳过已实现；29 35%血量精英、80%减伤不叠乘、3枪上限、5%/10%血量、两轮各合计3–5发、末轮4s跟踪激光与聚光灯转移已实现。舞姬圆舞/实际路径倒带及滚筒弱点奖励已实现。新Boss停用旧护盾与旧召唤调度。
APIMart生成2048图集，先洪水去底再按alpha裁切，四张VFX入库。缺舞台追光灯实体与14完整音幕两个3D补件，已交付独立建模提示词；当前光束、音符与危险轮廓可用。
规则338/338、Unity专项53/53、自然AI调度7/7；无本轮编译/Shader错误。详见 [能力实现记录](../docs/music-combat-implementation.md)、[3D补件任务书](../docs/music-combat-modeling-prompts/README.md)。截图 Shots/music-elite-skills.png、music-note-gun.png、music-boss-skills.png。编辑器已退出测试Play，未构建EXE、提交或推送。此前“新能力尚未实现”仅为上一轮模型入库时的历史状态。

## 音律敌人模型入库与调试（2026-11-19）
已将六种 Review_v001 与四种 Export_v003 合并入库，正式出生改用音律模型。17 个角色/变体/音符枪预制体，10 个衍生物，121 个独立动作；锁定比例、三档合并蒙皮 LOD、赛璐璐材质、骨骼受击代理已配置。五种普通怪 0.4s 死亡已落实到运行态，去掉额外尸体等待。
资产 814/814、Play 268/268、规则 324/324；预览 Shots/music-enemies-lineup.png、music-enemies-theater.png。见 [集成记录](../docs/music-enemy-integration.md) 和 breakdown/22-music-enemy-integration.md。
新精英/Boss 技能与衍生物生成尚未实现，现阶段保留旧策略，具体外观映射和边界见集成记录。未构建 EXE、提交或推送。以下旧条目为历史记录，本节为最新模型状态。

## 普通怪死亡动画提速规格（2026-11-19）
已修订 02/03/11/19/07 的建模提示词：Death 从 0.9–1.2s 统一改为 0.40s，30fps、frame 0–12；前 0.10s 明确死亡，0.30s 前完成主体动作，不追加尸体停留。精英/Boss 不变。仅文档调整，未修改实际动画或游戏代码。见 [提示词索引](../docs/enemy-modeling-prompts/README.md)。

## 单敌人建模提示词（2026-11-19）
已按用户指定 arjun988 blender 仓库的 skill 规则编写 10 份独立 Markdown，见 [建模提示词索引](../docs/enemy-modeling-prompts/README.md)。含已锁定高度、造型/部件、精英外观变体、骨架挂点、动作表、能力衍生物、命名、三档 LOD、碰撞与 Unity FBX 导出规范。29 附独立音符枪；14 保留 0.9s/0.8s 与双击规则。普通怪能力仍留空。文档、链接与关键参数已检查；本轮未建模、未修改游戏代码/资产，未进行模型或 Unity 运行验收。

## 怪物与能力衍生物概念图（2026-11-19）
已完成 7 张 APIMart 概念图，普通怪 1 张、精英 3 张、Boss 2 张、音符枪专项 1 张。指挥家终章用修正版，已逐张查看并登记清单。入口为 <GAME:S>/refs/music-enemy-production-20261119/index.html。形象细化及衍生物提案待用户评审，建模比例遵循锁定名册。

## 精英与 Boss 能力修订（2026-11-19）
29 召唤 1 只精英，仅生命降至 35%，Boss 期间减伤 80% 并可用能力 2，召唤物死亡聚光灯回归。音符枪上限 3 把，普通血量为 Boss 最大生命的 5%，能力 3 期间为 10%。能力 3 开始为旧枪回血并补足三把，Boss 期间减伤 80%。前两轮每轮合计随机分配 3–5 次射击，末轮存活枪同步持续跟踪激光，瞄准点速度约标准步行速度的 30%。14 双击独立判定，两击消耗 1 次，推进音符不可跳过。回血按回满、重叠减伤保持 80% 等执行口径见名册，激光时长等待试做调参。

## 02 风格赛璐璐渲染（2026-11-19）
正式剧院采用三档受光及深度描边，见 [地图集成记录](../docs/theater-map-integration.md)。PC Play Mode 16/16 通过，已导出观众席与二楼同机位对比图。

## 音律怪物分级与体型（2026-11-19）
普通小怪 02、03、11、19、07，精英 08、14、21，Boss 16、29。三种精英各有两款外观草案。体型图与身高规格见 [怪物名册](../docs/music-enemy-roster.md)，已收录 3 种精英与 2 位 Boss 的能力初稿，普通小怪能力待填。

## 原地与换弹跳跃修复（2026-11-18）
已修复 PlayerController 零水平位移覆盖接地状态的问题，真人与 AI 共用一次合并 Move。Unity Play 23/23 通过：原地、移动、换弹、二楼、落地再跳，另验证暂停、恢复与防二段跳。详见 docs/player-jump-fix.md；未构建 EXE/提交/推送。

## 音律敌人概念候选（2026-11-18）
追加已完成：新增三张 09–16、17–24、25–32，与原图合计 32 个候选。统一选择页 index.html 已更新；3/3 生成并逐张视觉检查，能力待用户选择后设计。
已生成一张 4×2、01–08 编号敌人候选图，音律主题与 02 赛璐璐风格，不限剧院。APIMart / gpt-image-2 / 1k，1672×941，已视觉检查。位置 `<GAME:S>/refs/music-enemy-concepts-20261118/index.html`，详见 docs/music-enemy-concepts.md。筛选已于本轮完成，名单与能力草案见上方新名册；未修改模型、玩法。

## 剧院正式地图已替换（2026-11-18）
已导入 GrandTheater 完整交付：76 模块、1191 实例、1135 碰撞体。Main 与地图加载入口改用 GrandTheater.prefab；64×72 室内地图、舞台、四楼梯和二楼环路保留，资源已分类。已接入多层敌人导航、楼层遮挡与小地图高度筛选，旧能量柱不再生成，Boss 临时沿用现有模型在舞台活动。
环境 64/64、Play 16/16、规则 324/324 通过；真实敌人上楼、二楼经验与重开清理已验证。详见 docs/theater-map-integration.md；旧地图和交付保留，未构建 EXE/提交/推送。

## 剧院地图设计（2026-11-18）
已完成 docs/theater-map-prompt.md：沿用已选战斗音律与 02 复古动漫赛璐璐，设计完整室内大剧院；参考规模 64×72m、舞台高 1.2m、可达二楼高 6m、四处楼梯与上下层环路。旧 Boss 台、能量柱不约束新布局。继承旧场景模块化、1024 平铺/Trim、LOD0/LOD1 和独立碰撞交付规范。
当前为提示词/任务书交付，尚未建模、导入或替换 Unity 场景；见 breakdown/19-theater-map.md。多层敌人导航、掉落、刷怪和小地图需在正式接入时验证。

## 主题风格概念探索（2026-11-18）

已选定**战斗音律主题 + 02 复古动漫赛璐璐**。先完成 HUD 换肤；场景与角色尚未迁移。原 8 张风格概念保留在 <GAME:S>/refs/theme-style-concepts-20261118，详见 docs/theme-style-exploration.md。

## HUD 边缘与九宫格修正（2026-11-18）
用户提供的 376×420 小地图框、256×256 头像框已原样替换，完整装饰保留；按实际圆心/比例适配 HUD，N 移到圆内菱形下方。血量/经验/Boss 框恢复原生端头，源像素九宫配合 PPU 缩放，填充限制在内部。73/73 HUD 验收，满/半/空截图已看；100 节点保持、5 节点按此反馈调整。
后续素材先洪水填充去背景，再按 alpha 完整边缘裁切；不再用圆环裁剪删除花纹。用户透明图优先原样使用，当前加工脚本始终尊重 user-overrides。详见 docs/hud-music-skin.md；截图 <GAME:S>/Shots/hud-border-fixed-gameplay.png。

## 音律主题 HUD 已替换（2026-11-18）
11 张 APIMart/gpt-image-2/2k 原始图集已生成并加工为 87 张资源，分类入库，HUD 经 Editor API 更新。暖金/象牙白边框、午夜蓝底、六种乐器徽章、51 种音符配件、动漫头像及调律进度。仅 HUD 显示名映射乐器；共享配件图标同步换新。
保持现有布局：105 个 RectTransform 完全一致，7 个非 HUD 预制体与 34 张其他贴图不变，120 原 GUID 保留。规则 321/321、HUD Play 68/68、分类与九宫格通过；1920/1280/宽屏及 6/8/10/12 槽位截图已看。
预览 <GAME:S>/_Inbox/hud-music-20261118/index.html；当前加工入口 tools/process_hud_music.py。详见 docs/hud-music-skin.md、breakdown/18-hud-music-skin.md。场景、模型和玩法未改；未打包、提交或推送。

## HUD V2：加工入库、预制体替换与验收完成（2026-11-18）

后续截图反馈已修复：满弹弧恢复完整填充；6/8/10/12 格的末格均让出右端收口；主、副枪图标新增不透明圆底，按钮禁用态也保持 alpha=1，避免轨道透出。HUD 已重新通过 Editor API 生成。本轮 HUD 运行验收 **60/60**，截图 `Shots/hud-edge-6-slots.png`、`-8-slots.png`、`-10-slots.png`、`-12-slots.png` 及更新的 `hud-v2-gameplay-1920.png` 已确认。其他界面未修改，未打包、提交或推送。


已按用户确认的 hud.png 制作并替换 HUD。45 个设计拆件 + 圆形遮罩已去底、裁切、配准并分类入库到 `Assets/_Game/Res/Texture/UI/{Common,Frame,Widget,Icon,Icon/Items}`；另覆盖 9 张共享底板/按钮/边框，新增 12 个专属配件图标，51 件配件现均有对应图标。8 张原始素材 SHA-256 全部保持。原图来源、提示词和生成回执见 docs/hud-v2-assets.md、hud-v2-prompts.md 及 `<GAME:S>/_Inbox/hud-v2-20261118`。

当前行为：左上主/副武器及物理槽位（6/8/10/12，保留空格、读取光环）；北向固定小地图（玩家居中并显示朝向、414 个地图障碍轮廓、敌人及显式宝箱标记）；10:00 倒计时，到零停止，Boss 血条在其上方；准心居中、正右侧弹药弧，换弹时弧形进度增长且准心旋转加载；左下头像/等级/血量/经验，右下三个无功能道具占位；Alt 释放鼠标并抑制视角与开火，Esc/按钮暂停与恢复。主菜单立即隐藏战斗 HUD，结算后不能用 Esc 恢复战斗。

其他界面仅使用替换后的共享素材，7 个非 HUD 预制体逐字节保持原样，86 个既有资源 GUID 不变。HUD 由 Editor API 保存，Addressables 分类与预加载已同步。重建入口 `S/UI/Build HUD V2 Only`；加工入口 `tools/process_hud_v2.py`。文档见 docs/hud-v2-integration.md、breakdown/17-hud-v2-integration.md。

验收：HUD Play **45/45**；连续两轮真实失败→R→重开及第三局事件 **40/40**；规则 **321/321**；统一 tests、UI 分类（63 静态资源 + 51 配件图标）、九宫格审计均通过。截图 `Shots/hud-v2-gameplay-1920.png`、`-1280.png`、`-wide.png`、`hud-v2-reload.png`、`-paused.png`、`-boss.png`、`-menu.png`、`-inventory.png` 已查看。日志 `Logs/hud-v2-play-check.log`、`restart-play-check.log`、`hud-v2-rules.log`、`hud-slices.log`、`hud-v2-preservation.json`。

当前尚无宝箱玩法；真实宝箱接入时挂 `MinimapChestMarker`，开启后隐藏；已用临时标记验证显示及重开清理。当前工作区既有原枪械模型删除，截图仍为原有胶囊回退枪模；未恢复用户删除。本轮未重建 EXE，未提交或推送；编辑器退出测试 Play 并保持 Main。

## 失败重开修复（2026-11-18）

GameRoot 原先直接推进静态 SDataLoader 缓存中的 RunDirector，按 R 重载 Main 后继续使用旧计时、精英次数和 Boss 入场标记。现在每次创建独立时间轴副本；重开重新选枪后从初始阶段开始，精英倒计时 05:00、Boss 倒计时 10:00，旧局场景对象随重载清理。

验证：规则 321/321；Unity 编译通过；真实失败→R→重载→选枪连续两轮及第三局事件触发 40/40。测试入口 S/Checks/Restart Play Check，日志 <GAME:S>/Logs/restart-play-check.log。编辑器已退出测试 Play 并保持 Main；本轮没有重新打包 EXE，没有提交或推送。更早的构建/冒烟结果仍为当时版本证据。详见 breakdown/15-run-restart.md。

## 工程与 Git

- 工程分支 main，远端 `git@github.com:Su092/Project-S.git`，保留原历史和 origin 跟踪配置。
- 上次已推送工程提交为 685e8b2；本次地图、敌人接入及用户交付资源为新的工作区改动，尚未提交或推送。
- 旧工作目录变为指向 `<GAME:S>` 的兼容联接，只有一个活动工程和一份 `.git`，本会话通过旧入口访问同一工程。
- 枢纽与工程仍是两个独立仓库；此前两个仓库已推送。本次地图任务尚未提交或推送。
- 备份目录名 `S_migration_backup_20261116_182214`，位于工程父目录；`project-before` 为原正式工程，`hub-S-before` 为原 S 文档，`retired-source-files` 保存已整合的合成文档及两份一次性补丁脚本。
- 实际路径见工程 `Logs/migration-audit.json`、`migration-backup-location.txt`。备份含源/目标/枢纽的工作区与暂存 diff、原 HEAD、769 文件哈希清单。
- 迁移瞬间 769 文件 SHA-256 及 Git porcelain 状态全部一致。之后仅整理 README、整合合成过程文档和移出两份已执行的临时补丁脚本，游戏代码与资产未因迁移改变。

## 已完成的功能

| 功能 | 当前行为 |
|---|---|
| 正式地图 | 失控铸造场 FoundryArena 预制体替换旧程序化地图；51 模块、1169 布局实例、16 刷怪点；保留预览布局、LOD、材质及碰撞；Boss 柱按阶段启用并切换残骸 |
| 经验拾取 | GameRoot 在死亡原地创建 ExperiencePickup，进入 1.5 米才加经验；无磁吸、无到期；暂停不拾取、防重复；对局结束清理。击杀计数和精英回血保持击杀时处理 |
| 物理作用域 | Next/Prev 是后一格/前一格，不跨空槽、不绕回。载荷扫描另走 NextBulletCell，不混用语义 |
| 背包效果预览 | 点击、悬停、拖动显示来源、覆盖格和真正生效子弹；安装/交换/合成预览复制布局，不改实际装配 |
| 障碍碰撞 | 局部 bounds 避免世界 AABB 放大；箱、桶、墙、柱用视觉网格碰撞；视觉原语碰撞立即禁用，柱破坏关闭子碰撞 |
| 子弹与爆炸 | ProjectileVisual 覆盖 17 种子弹和敌方红弹；CombatFx 提供枪口、命中、爆炸、光束和闪电；共享材质，活动特效上限 80 |
| 网格动画 | 枪械由 RigidMeshRig / WeaponMotion 驱动换弹与后座；正式敌人由 EnemyVisual 播放交付的 Generic 骨骼动作，暂停冻结 |
| 起手与枪奖励 | 全部 6 把枪任选 1 把开局；升级每轮 10% 概率最多出现一把未持有枪。携带上限 2，满额替换当前枪，先校验旧配件返包空间；奖励期间可整理背包再返回 |
| 扩件与合成 | 17 子弹 + 34 衍生，共 51 件、10 作用域；新增 12 衍生并调整旧件范围。同 ID/类型/等级二合一至 Lv.5，支持包↔包、包↔枪、枪↔枪，成品留目标位，不需额外空间 |
| 实例与抽取 | 合成校验所有权，重复/失效拖放不复制或丢失；有效属性不改共享配置。史诗跨轮可重复，同轮三选一不重复；gun_third 保留旧存档兼容但所有初始枪默认开放 |

等级强度为 1 / 1.5 / 2 / 2.5 / 3；连续正向收益按强度、整数收益按级变化，负面代价不随等级加重。详细公式、配置镜像和交互边界见 loadout-spec.md。

## 本轮敌人替换

使用 <GAME:S>/_Inbox/chr/S_Foundry_Enemies/Review_v002，导入四类普通敌人、四类独立精英和 Boss，正式 prefab 位于 Assets/_Game/Res/Prefab/Enemies。模型/图集/动作/受击网格位于 Res/Characters/Foundry，S_Enemy / s_enemy 预加载九个角色。保留原交付和旧资产，未提交或推送。

采用交付尺寸、URP 贴图与三个 LOD；精英取消旧视觉放大和光晕，数值倍率保持。EnemyVisual 使用 56 个交付动作生成的 Generic 动画；攻击按原伤害前摇对齐，普通敌人死亡立即结算、关闭碰撞并保留短暂死亡动作。旧 EnemyMotion 不再参与正式敌人生成。Boss 使用新体型、骨骼炮口、技能动作与发光状态；脚部贴合平台，漫游中心限制在半径 5.95 米内，为机体留出空间。

交付修复：碰撞 FBX 只有骨架，已从 .blend 的 proxy_role/bind_bone 只读提取并按骨骼绑定受击代理。模型 FBX 比动作 FBX 多 ARM_<asset> 层，已重映射曲线并保留模型根轴转换，验证 +Y 向上和 +Z 向前。复合受击网格使用敌人级去重，光束和穿透弹不会因命中多个部件重复扣血；环架上部开口可穿透。

验证：资产 156/156，敌人运行态 65/65，地图回归 19/19，规则 300/300；Windows 构建零错误，11 张配置表、10 个 bundle，启动冒烟 32/32，实机自检 132/132。证据为 Logs/enemy-import-check.log、enemy-play-check.log、enemy-build-command.log、enemy-check-results.json、smoke.log、selfcheck.log；画面见 Shots/enemies-gameplay.png 和 Shots/08-boss.png。

源包仍为 REVIEW / NO-SHIP：完整美术精修、纹理密度、全帧穿插与长局性能未全部验收。游戏导入和专项通过不等同于最终美术验收。

## 本轮地图接入

正式地图为 Assets/_Game/Res/Prefab/Maps/FoundryArena.prefab，由 51 种交付模块按 layout.json 的 1169 个实例组装。Main 场景包含 S 启动节点和该地图实例；ArenaBuilder 优先绑定已有地图，缺少实例时才从 Addressables 的 S_Map / s_map 加载。

玩家和敌人的移动层、所有弹道的查询层以及经验落点已接入交付楼梯分层；地图实例不存在巡检控制器或重复相机。开工前已存在的交付文件、物理图层和纹理设置未回退。

本轮在 Unity Editor API 中生成预制体与 Main，不手改场景 YAML。闭包前原 Main 及相关设置、工作区 diff 保存在 Logs/foundry-before-*。地图源码和原始交付保留在 _Inbox。

## 验证证据

| 检查 | 结果 | 证据与范围 |
|---|---|---|
| 地图几何/标记/移动/碰撞 | 53/53 通过 | Logs/foundry-map-check.log；check.ps1 -Task map |
| 地图生产运行态 | 19/19 通过 | Logs/foundry-play-check.log；正常开局、弹丸越过移动坡面、高台经验、光束碎柱与 Boss 通知 |
| 本轮纯规则 | 300/300 通过 | Logs/enemy-rules.log |
| 迁移后规则 | 300/300 通过 | check.ps1 -Task tests 的 dotnet 阶段，从新工程读取配置 |
| 迁移后统一 tests | 未通过 | UI 分类审计缺少 12 个新增配件独立图标，规则通过不能代替整体通过 |
| 迁移后 Unity 导入/编译 | 通过 | Logs/migration-unity-compile.log：batchmode 正常退出，return code 0，无 C# 编译错误；不等同播放器构建 |
| Git 连通性 | 通过 | git fsck --connectivity-only 退出 0，历史、分支和远端保留 |
| 枢纽路径 | 补查通过 | profile 和 Project/S/unity 均指向同一工程；doctor 仅因可选 hub.link 为空为 degraded，未将其记成全通过 |
| 碰撞专项（迁移前） | 267/267 | Logs/obstacle-collision-check.log |
| 弹丸视觉（迁移前） | 166/166 | Logs/projectile-visual-check.log；Shots/projectile-visual-sheet.png |
| 网格动画（迁移前） | 66/66 | Logs/mesh-motion-check.log；Shots/mesh-motion-sheet.png |
| 战斗运行态（迁移前） | 19/19 | Logs/combat-play-check.log |
| 合成运行态（迁移前） | 41/41 | Logs/fusion-play-check.log；Shots/fusion-inventory.png |
| 本轮 Windows 构建 | 通过，0 errors | Logs/enemy-build-command.log；11 张配置表、10 个 Addressables bundle |
| 本轮启动冒烟 | 32/32 通过 | smoke.log；check.ps1 -Task smoke，真实 UI 开局选枪并确认 |
| 本轮实机自检与截图 | 132/132 通过 | selfcheck.log；check.ps1 -Task shots，含经验拾取、多级奖励及 Boss 流程 |
| 完整 all | 未通过验收 | 12 个配件独立图标缺失仍未解决，不将专项通过等同于全量通过 |

迁移前专项日志随工程完整迁移，已复核 RESULT，迁移本身未重跑这些专项。本轮地图接入后重新构建播放器并执行冒烟与实机自检；经验测试明确点击配件奖励，避免随机枪械改变背包计数和测试武器，战斗及 Boss 测试期间保持自动领奖。实际游戏的随机枪械与升级暂停规则不变。

实机截图 Shots/01-start.png、Shots/08-boss.png 已核对新地图和暗色背景；地图总览为 Shots/foundry-map-overview.png。

## 待完成

1. 新配件通过 UiAssets.ItemIcon 复用旧图标，尚不满足一 ID 一文件。缺 crossfire、forward_battery、gap_bounce、gap_lens、rear_battery、rear_blast、rear_boost、rear_frost、ring_burn、twin_boost、whole_boost、whole_guidance 的 `item_<id>.png/.meta`；按美术管线补齐并登记 Addressables，再跑分类审计。
2. 拾取与合成改变经验效率和强度曲线，历史 calibration-log 需重新校准；长局性能与弹幕/爆炸压力测试待执行。
3. 方案存档仍未实现。后座当前只作用枪模，不改变镜头瞄准与弹道。

## 维护约定

- 数据为 11 张 TSV，资产统一在 Assets/_Game/Res；启动等待 SRes.PreloadAll，新增资源登记 Addressables 分组/标签。
- Core 除 SDataLoader 桥外零 Unity 依赖；规则与预览共用 Loadout，升级共用 ItemFusion。
- UI 结构改 UIPrefabs 和 Editor 工厂，运行态用 *Refs；不延续手改 YAML 做法，字体统一 UiKit.Font。
- 模型 +Y 上、+Z 前，保留导入旋转；材质走 SMat，CombatGlow 纳入构建包含列表。
- 光标与暂停由 GameRoot.SyncCursorToState 统一裁决；保留默认域/场景重载，避免缓存跨 Play。
- Addressables 异步内容构建不能被 -quit 提前结束；核对日志和真实资源产物再进入播放器验证。
- tools/loadout-tests/loadout-tests.csproj 已纳入 Git；新增 Core 文件检查显式 Compile Include。
- 本轮只同步 Project/S，其他游戏和枢纽全局未提交改动保留。后续在既有规格、任务及本快照更新，不堆叠冲突结论。

出画速度已改为入画的1.3倍，按弧长计算时长约0.71秒；信息框收起0.4秒。实机46/46通过，49帧预览已更新：<GAME:S>/Shots/upgrade-ui/index.html。
