# FXM_S14_NoteGate · 四栏推进音符幕建模提示词

## 分析与计划
使用 blender-director→anime-style→prop-artist/vfx-fx→uv-workflow→materials→lod-pipeline→export-pipeline→unity-export 制作一件技能衍生物。主题与现有14木琴棘龙及 FXM_S14_MarchingNote 一致。此为完整危险栏的视觉补件，不重做棘龙或原音符。
玩家必须横移或利用掩体躲避，正常跳跃不能越过；3D外观要读出从地面到头顶的连续危险高度。不要做像可从中间钻过的空门框。

## 尺寸、轴向与造型
Unity 实测宽2.2m、高3.6m、厚0.25–0.4m；根在底边中心，+Y上、+Z推进。整个技能在运行时按地面直线推进，无世界位移烘焙。
主形：一个与已交付音符相同的实体音符核心，后方连着竖直窄幅五线谱“音幕”，五线不横向扩张超出栏宽。四角保留清晰外轮廓，中部用半透明谱线/连续波带表达封闭危险面。顶底装饰控制在2.2×3.6m内，不能出现判定外尖刺。
实体用旧金、深木、象牙色，发光部分由Unity染为危险橙红；不把黄色追光灯与红色攻击光混淆。无文字、数字、界面图框。

## 网格与材质
主网格 SM_FXM_S14_NoteGate_LOD0/1/2：1200/600/200 tris；最多2材质：实体核心、双面透明音幕。透明面与实体分对象，减少重叠层数，背面从玩家视角也清楚。
T_FXM_S14_NoteGate_BC/ORM/N/E.png 1024，音幕 alpha 1024；底色sRGB、ORM/N/E/alpha按线性使用。可复用现有核心图集时在manifest声明，不重复改写源贴图。半透明衰减由shader控制，不烘焙动态光照。
COL_独立集合导出一个2.2×3.6×0.35m简化代理用于验收尺寸；游戏实际采用逻辑扫掠判定，禁止导入后把它设为阻挡玩家的实体墙。

## 动作、命名、导出
静态网格默认无需骨架；如果音幕需要展开，用Generic root→core/curtain，刚性权重。
可选动作 Spawn 0.12s（30fps，实际4帧=0.1333s，必须如实记录）、Travel 0.6s/18帧循环原地、Dissolve 0.2s/6帧。淡出主要由材质完成，必须提供无动作静态可用版；不将30fps不存在的3.6帧标成精确0.12s。
Source/FXM_S14_NoteGate.blend；Model/FXM_S14_NoteGate.fbx；Animations/FXM_S14_NoteGate_<Action>.fbx；Collision/FXM_S14_NoteGate_COL.fbx；Textures/；Preview/；manifest.json。
FBX Scale1、Apply Unit、FBX All、-Z Forward/Y Up，网格变换已应用，根缩放1，保留原有敌人包轴转换约定；最终 Unity 实测 +Y 上/+Z前与米制。单动作单文件，30fps烘焙，不添加叶骨，不包含灯光相机。
交付正面、背面、侧面、45°、10m/20m游戏距离图，并放1.8m玩家站立/1.3m跳高参照，验证跳跃仍处于危险幕高度内。记录三档tris、材质、alpha排序、包围盒、原点、循环、贴图及哈希。未通过Unity测试须标待验收，不能标成最终可用。
