# SM_MusicFollowSpot · 舞台追光灯建模提示词

## 分析与制作目标
使用 blender-director 流程，调用 prop-artist / anime-style / materials / rigging / animation / lod-pipeline / collision-proxy / export-pipeline / unity-export。为 PC Unity 音律战斗制作可转向舞台追光灯实体。只做此灯，不改地图或敌人。

美术锚点：现有鸣奏大剧院和音律敌人，02 复古动漫赛璐璐；午夜蓝 #172439、象牙白 #E7D7B8、旧黄铜 #A87A38、酒红 #6D2539。粗大轮廓、清晰二级结构和少量平面色块，不画照片级噪点或科幻枪械细节。
现有参考仅约束主题；不得自行更改角色体型或把灯光做成伤害红激光。

## 尺度与轮廓
1 Blender 单位=1m。灯头外径 0.38m，长 0.52m；U 形支架总宽 0.52m，总高 0.64m；吊装杆长 0.25m，可拆。
主形：短圆筒光学头、黄铜镜圈、深色遮扉、U 架；二级：四叶柔角遮扉、两侧转轴、简化电缆。镜片为单独材质/网格，可独立发光，禁止整壳发光。
提交正面/侧面/45°轮廓与1.8m人物比例图，先确认轮廓再细化。

## 原点、骨架、动作与挂点
导入 Unity 后 +Y 上、+Z 为灯头零姿态光轴。根原点在吊装接口中心；根缩放1。
Generic 骨架 ARM_SM_MusicFollowSpot：root→yaw→pitch；灯体刚性权重1，不做弹性变形。
Socket_Mount 在根；Socket_LightOrigin 在镜片正中心，+Z 出光；Socket_HeadPivot 在俯仰转轴。
动作单独 FBX，30fps，约束烘焙：
- Idle：1.0s，0–30帧，静止循环。
- FocusIn：0.5s，0–15帧，遮扉轻开；光强由游戏控制。
- FocusOut：0.5s，0–15帧，遮扉轻合。
- RigTest：2.0s，0–60帧，展示 yaw ±90°、pitch -70°至0°，仅验收不作运行自动转向。
运行时脚本负责追踪位置，禁止在 FBX 烘焙一整条世界运动轨迹。不要导出真实 Light/Camera。

## 网格、材质与优化
SM_SM_MusicFollowSpot_LOD0/1/2：目标 1800/900/350 tris；灯头、支架共享1张1024图集，镜片可第二材质。统一256px/m参考纹理密度，近景镜片可512px/m并记manifest。
T_SM_MusicFollowSpot_BC/ORM/N/E.png，BC为sRGB，其余线性；ORM=R遮蔽/G粗糙度/B金属。禁止将光束烘焙进底色。
COL_SM_MusicFollowSpot 为独立集合、独立FBX，仅灯体简化凸体，不把光束当碰撞体；运行默认仅装饰，碰撞由关卡决定。

## 导出与验收
源 Source/SM_MusicFollowSpot.blend；Model/SM_MusicFollowSpot.fbx；Animations/SM_MusicFollowSpot_<Action>.fbx；Collision/SM_MusicFollowSpot_COL.fbx；Textures/*.png；Preview/*；manifest.json。
FBX选中导出、Scale1、Apply Unit、FBX All、-Z Forward/Y Up、Apply Transform；Add Leaf Bones关闭，Only Deform Bones需保留挂点；每文件一个动作，30fps，关闭简化。沿用已验收敌人包的实际轴转换，以 Unity 实测 +Y/+Z 为最终判据，不能只写导出选项当验收。
材质与动作导出前通过 asset-optimization 检查；同骨架路径三档LOD，无负缩放、丢权重、非流形；Unity导入1:1后验证尺寸、挂点朝向、全角度转向无自穿插。
manifest写版本、真实尺寸、tris、材质槽、纹理规格、骨骼/挂点、动作帧范围与循环、轴向、文件哈希、验证结果及未完成项。不得将占位或未验收包标为PASS。
