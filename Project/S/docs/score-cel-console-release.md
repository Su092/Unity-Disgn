# 曲谱装配、赛璐璐重绘与控制台修复

更新：2026-11-20。工程 <GAME:S>，枢纽 <HUB>/Project/S。

## 已实现

- 背包容量 15，配件合成上限 Lv.3。谱架当前由出生点固定立方体占位，F 交互打开曲谱装配并暂停，关闭恢复；Tab 仅控制左上槽位预览。
- 点击顺序安装、左键拖动安装/替换/合成、右键卸下；R 与整理按钮共用排序和补空逻辑，整理不自动合成。
- 曲谱图标无外框、乐器图标保留底框；槽位预览规格统一。小地图右上、倒计时靠近暂停；删除不需要的说明文本。
- 衍生配件为红色，普通子弹蓝色、高品质子弹金色。新素材使用 APIMart，先审核后处理入库；已批准的谱面、图标、描边按钮、简洁底框已应用。
- 33 张模型颜色贴图按原图参考重绘，并按用户要求先保存旧渲染、再替换和拍摄同镜头对比；原透明通道、尺寸、meta/GUID、材质引用与法线等数据图保留。
- 对比页与原图备份保留在 <GAME:S>/_Inbox/cel-texture-review-v1；实际场景截图在 comparison/before 与 comparison/after。35 个模型对照使用同一预览设置，旧组采用备份贴图补拍。

## 控制台修复

六把乐器模型及根节点重复注册 LODGroup：保留根节点三档 LOD，导入器同步移除继承的重复组件。uGUI 2.6 的静态注册表在 Prefab Mode/Play 切换后与存活按钮不一致：通过编辑器生命周期兼容桥恢复注册，未修改 PackageCache 或屏蔽异常。升级废弃的 FindObjectsByType 无排序接口。Device Simulator 会主动禁用真实鼠标，切回普通 Game 视图后恢复正常。

曲谱交互测试改在真实游戏更新中执行；EditorApplication.update 的默认 640×480 Screen 值不可用于实际 Canvas 的点击射线测试。

## 验证与范围

- 规则断言 354/354。
- 控制台专项 47 项，含注册表容量、乱序禁用、恢复、六款武器、预制体打开期间进出 Play。
- 曲谱真实 UI 交互 42 项。
- 33 张颜色贴图与入库 SHA-256 一致；Unity 纹理/材质 71 项检查通过。
- 最后控制台 0 错误/0 警告。
- 提交前 tests 发现六张 score_* 图片未同步到 Python 分类清单，已补齐公共 hud-v2-catalog.json，重跑完整 tests 为 RESULT ALL PASS。
- 本轮未重新构建播放器。FPS/TPS、完整玩家持握与 Motion Matching 尚未接入；后者按用户要求搁置。

日志位置：<GAME:S>/Logs/console-regression.log、score-workbench-check.log、console-audit-latest.txt。日志和可再生缓存不进入 Git。
