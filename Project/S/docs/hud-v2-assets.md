# HUD V2：确认规则与原始素材拆件

> 2026-11-18 后续阶段已获加工/入库授权并实施，当前接入说明见 [hud-v2-integration.md](hud-v2-integration.md)；本文中的原图阶段限制仅为当时记录。


- 日期：2026-11-18；依据：用户 hud.png（1920×1080）及八条确认。
- 本轮终点：完成拆件、提示词与 APIMart 原始素材生成。禁止在本轮执行裁切、去底、缩放、Sprite/Addressables 入库、预制体制作或 HUD 功能改造。
- 产物：<GAME:S>/_Inbox/hud-v2-20261118/；调用 skill：<HUB>/.cursor/skills/apimart-image/SKILL.md。
- skill 的默认 Assets 接入步骤由用户明确要求暂缓；本次仅落 _Inbox。所有 UI 原图明确 2k。

## 已确认功能

1. 左上大图标为当前枪，小图标为备用枪；切枪互换，单枪隐藏备用图标与箭头。配件按物理槽位显示，保留空槽与读取指示，数量随枪为 6/8/10/12，不固定为示意图的 8 格。
2. 圆形小地图固定北向，玩家固定中心，使用明显的玩家/朝向标识；仅显示障碍、敌人、宝箱。经验、Boss 专属图标、能量柱等不显示。Boss 如作为敌人存在，也不新增独立类别标记。障碍轮廓由场景数据生成，不让 AI 虚构地图。
3. 生存倒计时从 10:00 开始。暂停停止计时，失败重开重新从 10:00 开始。00:00 后具体文案留待功能接入时处理；素材不烘入数字。
4. 准心位于实际瞄准中心。弹药条在其正右侧，保留弹量数字；换弹时进度同步增长，准心替换为旋转加载图标。加载图标只需一张静态原件，旋转由运行时实现。
5. 右下三个道具格只显示占位，没有使用、数量、冷却或获得机制。
6. Boss 出现时血条显示在倒计时上方。其他辅助信息本轮不增加美术素材或固化额外显示规则。
7. Alt 按住释放鼠标用于 HUD 点击，松开恢复瞄准；Esc 直接暂停。交互状态通过色彩/透明度切换，不生成重复按钮贴图。
8. 左下头像、血条、经验条、等级按草图分层。头像采用匿名封闭面罩的工业探索者作为 UI 初稿，不定义新角色玩法或模型。

## 布局基准与分层

1920×1080 为本轮拆件参考。四角靠边锚定，准心严格居中；计时位于上方中线，Boss 条在计时上方，顶部武器栏按槽数伸长。小地图在左上武器栏下方，不移动玩家离开其中心。

| 功能 | 后续计划显示尺寸（参考像素，可布局验收调整） | 分层与运行时职责 |
|---|---|---|
| 当前枪 / 备用枪 | 110 / 80 圆形 | 圆框 + 六枪之一图标；大小复用同一原件 |
| 配件栏 | 圆槽 64–70；最多 12 槽 | 长条底 + 空槽 + 配件图标 + 读取叠层；空槽不折叠 |
| 小地图 | 240 圆形 | 圆形裁切遮罩 + 地图数据 + 三类标记 + 外框；玩家箭头旋转、地图不旋转 |
| 计时 | 160×56 左右 | 空底板 + 动态字体，不生成数字贴图 |
| Boss 血条 | 500×24 左右 | 空框轨道 + 单独填充 + 动态名称/血量 |
| 准心 / 装填加载 | 约 28–48 | 准心开合/加载旋转属程序效果 |
| 右侧弹药弧 | 隐圆半径约 90–110 | 底轨 + 同轴填充，面向准心一侧开口；弹药数字另绘 |
| 左下生命 / 经验 | 480×24 / 440×18 左右 | 各自底轨框 + 填充 + 动态数据 |
| 左下头像 | 110 圆形 | 头像原画 + 裁切遮罩 + 圆框；等级另绘 |
| 暂停 / 道具格 | 80 方形 / 120 方形×3 | 按钮底与符号分离；道具只用中性占位符 |

## 复用与非贴图项

- 现有 39 张配件圆形图标继续复用；补齐 rear_boost、twin_boost、forward_battery、rear_battery、crossfire、gap_lens、rear_frost、ring_burn、gap_bounce、rear_blast、whole_boost、whole_guidance 共 12 张缺失字形的原图。此轮不加工成圆图标，因此既有正式素材缺图问题尚未入库修复。
- 字体沿用 UiRounded；等级、槽位、弹量、血量、倒计时、Boss 名、快捷键均为动态文本。
- 颜色变化、悬停/按下、稀有度、数值填充、准心散射、加载旋转、地图障碍与裁切遮罩均不生成逐帧图片。
- 右下不生成药剂/炸弹等具体道具，避免暗示尚未确认的玩法。
- 风格沿用工业科幻：石墨灰框体、骨白符号、少量琥珀，生命红、经验青；小地图玩家青、敌人红菱形、宝箱金色箱形，形状也区分含义。
- 原图采用纯黑底、留白分件；不承诺原图已经透明或可直接当 Sprite 使用。本轮不得执行去底/裁切/重采样。

## 原始素材板与组件

| 原图 | 布局 | 独立组件数 | 内容 |
|---|---|---:|---|
| 01_frames.png | 3×2 | 6 | 基础框体：weapon_rail, portrait_frame, attachment_socket, minimap_bezel, pause_button_base, item_slot |
| 02_bars.png | 2×3 | 6 | 血量经验与 Boss 条：hp_track_frame, hp_fill, xp_track_frame, xp_fill, boss_track_frame, boss_fill |
| 03_combat.png | 2×2 | 4 | 准心换弹与右侧弹药弧：crosshair, reload_spinner, ammo_arc_track, ammo_arc_fill |
| 04_markers.png | 3×2 | 6 | 地图标记与操作符号：map_player_heading, map_enemy, map_chest, pause_glyph, weapon_swap, read_cursor |
| 05_weapons.png | 3×2 | 6 | 六类武器独立图标：gun_rifle, gun_smg, gun_shotgun, gun_sniper, gun_beam, gun_launcher |
| 06_portrait.png | 1×1 | 1 | 匿名角色头像：operator_portrait |
| 07_states.png | 2×2 | 4 | 计时与状态叠层：timer_plate, weapon_selected_ring, attachment_read_ring, utility_placeholder |
| 08_modifiers.png | 4×3 | 12 | 补齐十二个配件字形：rear_boost, twin_boost, forward_battery, rear_battery, crossfire, gap_lens, rear_frost, ring_burn, gap_bounce, rear_blast, whole_boost, whole_guidance |

共 8 张原图，45 个设计拆件。原图格位为设计合同，实际生成结果仍需视觉核对；后续加工阶段须精确配准弧形与九宫格边距。

## 原图检查结果

8/8 任务完成，8/8 文件可解码且 SHA-256 与下载回执一致，全部长边 2048。已逐张人工视觉查看，无烘焙文字或组件重叠。结果详见 <GAME:S>/_Inbox/hud-v2-20261118/validation.json。

原图阶段注意项：弹药底弧与填充生成为约 180° 右半圆（提示词目标为 90°），功能方向正确，后续加工时需按准心布局确定弧度并精确配准；本轮不裁弧。武器/头像细节需在后续实际显示尺寸下验收。黑底、原始留白、原始像素均保留。此检查不等于成品 Sprite 或游戏布局验收。
