# 音律主题 HUD 换肤 — 已完成
2026-11-18。用户选定**战斗音律 + 02 复古动漫赛璐璐**，本轮完成 HUD 素材生成、加工、分类入库及预制体替换，沿用既有布局和玩法。
## 结果
- APIMart / gpt-image-2 / 2k，引用概念 02 原图，11 张生产图集、11 个成功任务，原图 SHA-256 验证。
- 33 个 HUD 设计拆件 + 51 个配件图标 + 3 个派生资源（HUD 继续按钮、结算底板、徽章圆形遮罩），共 **87 张 RGBA Sprite**。
- 象牙白与暖金边框、午夜蓝底、珊瑚红生命条、金色经验条、青色能量弧、成年动漫演奏者头像。配件采用音符、演奏符号及效果方向图形。
- 六个 HUD 武器徽章/名称映射为：rifle 小提琴、smg 长笛、shotgun 手鼓、sniper 大提琴、beam 竖琴、launcher 圆号。仅 HUD 显示名变化，数据 ID、机制和其他界面文本未迁移。
- 换弹在 HUD 显示“调律”，仍按原进度填充右侧弧并旋转中心音符加载标志。低弹量数字警示、暂停冻结、重开计时沿用。
- 51 张配件图标是共享资源，背包等界面同步使用新图标。其他界面的底板、布局保持本轮之前的状态。
## 文件和可重现流程
原图、提示词、任务回执、加工清单、保留范围报告：<GAME:S>/_Inbox/hud-music-20261118。
清单登记：<HUB>/tools/apimart-assets.json（本批 id 前缀 s-hud-music-）。
加工：<GAME:S>/tools/process_hud_music.py；分类：UiAssets.Catalog 与 tools/hud-v2-catalog.json。
入库：<GAME:S>/Assets/_Game/Res/Texture/UI/{Frame,Widget,Icon,Icon/Items}，同名覆盖保留 GUID。
新增 HUD 专用准心/三条填充/继续按钮/结算板/徽章遮罩，避免换掉非 HUD 共用底板。
预制体：HUD.prefab 由 S/UI/Build HUD V2 Only 经 Editor API 保存，并刷新 Addressables。
旧 tools/process_hud_v2.py 保留作为上一版加工记录；当前音律主题使用 process_hud_music.py。
预览页：<GAME:S>/_Inbox/hud-music-20261118/index.html。
## 加工要点
技术黑底去除，实底内部保留不透明度；环形中心透明。逐图校正图集裁切边界。
装饰端帽压入现有九宫格边距。两层弹药弧统一中心和半径，保留 0..1 完整填充。
画像/徽章使用独立内圈遮罩，圆框按实际圆形笔画定中心；小地图顶部装饰分离，不再使圆心偏移。
## 验证
- Unity 实际编译和 HUD-only 构建通过。
- HUD Play **68/68**：资源加载、所有武器徽章及物理槽位、边框留白、不透明底、满/空弹药、调律、暂停/恢复、Alt、地图、Boss、失败重开。
- 规则 **321/321**，统一 tests、分类与九宫格审计通过。当前分类总计 70 静态素材 + 51 配件图标。
- **105 个 RectTransform** 路径/锚点/轴心/位置/尺寸与换肤前一致；7 个其他预制体逐字节不变。
- 120 个原有 UI 资源 GUID 不变；34 张非本轮替换贴图不变；41 个场景/配置/其他预制体文件及 meta 哈希不变；11 张原图完整。
- 截图已查看：Shots/hud-music-final-gameplay-1920.png、-1280.png、-wide.png、-reload.png、-paused.png、-boss.png，以及 -edge-{6,8,10,12}-slots.png。
- 日志：Logs/hud-music-play-check.log、hud-music-rules.log、hud-music-slices.log；保留审计 tools/audit_hud_music.py。
## 范围
场景、角色、第一人称模型和玩法数值未做主题迁移。已有原枪模删除后的白色胶囊回退仍会出现在实机截图中。
编辑器验收后退出 Play，保持 Main；未打包 EXE、未提交、未推送。

## 用户修正：边缘与九宫格
采用用户交付的 376×420 小地图边框与 256×256 头像框，保留原图所有边缘细节，不再按圆形带裁掉装饰。HUD 以真实圆心对齐，按原宽高比适配。血量/经验/Boss 条保留原图端头，重新设置源像素九宫边距与显示缩放，填充限制在内部。后续抠图先洪水填充清理背景，再依 alpha 完整边缘裁切。

## 2026-11-18：完整边缘替换与条框九宫格修正
用户交付的 hud_minimap_bezel.png（376×420）、hud_portrait_frame.png（256×256）已逐字节复制到正式 Frame 分类，同名 GUID 保留，未二次裁边、重采样或删除装饰。源文件归档于 <GAME:S>/_Inbox/hud-music-20261118/user-overrides，SHA-256 核对一致。
小地图按真实圆心与原始宽高比调整 Bezel 的尺寸和 pivot，圆框仍对齐玩家中心；完整菱形保留。“N” 放到菱形下方、圆内，避免压到配件栏。头像/主副乐器的内圆遮罩按新框内缘重做，四周花纹全部保留。

血条、经验条与 Boss 条恢复未经横向压缩的原图端头，原生框尺寸分别为 855×85、937×80、863×91。源像素九宫边距分别为 (104,16,104,16)、(82,16,82,16)、(108,16,108,16)。Builder 设置 pixelsPerUnitMultiplier=原图高/显示高，让端头等比缩放、仅中段拉长；填充按框内安全边界设置，满值不覆盖装饰。填充纹理按实际显示长宽比处理，避免胶囊两端被横向拉扁。九宫审计已计算 PPU 后的实际边距。

**后续抠图规则**：先用洪水填充清除连通的技术背景，再依据 alpha 的完整外沿裁切；实底图保留封闭的暗部，空心符号清理内部背景；禁止先按亮度包围盒截取、按理想圆环删除边缘花纹。用户已经扣好的透明图优先原样使用，通过 HUD 尺寸、轴心与遮罩适配。通用入口 tools/ui_cutout.py，当前及旧版处理脚本均已接入；当前脚本识别 user-overrides，后续重加工不会覆盖用户修图。

本次只改变 5 个明确节点：Health/Fill、Experience/Fill、BossBar/Fill、Minimap/Bezel、Minimap/North；另外 100 个布局节点不变。7 个其他预制体不变，120 原 UI GUID、场景/配置与其他保留文件核对通过。
验收：HUD Play 73/73；用户图原始尺寸/长宽比、三条源像素缩放通过；0/50/100% 截图已查看；分类、九宫与 Python 语法检查通过。核心玩法未改，本次没有重跑规则测试。
证据：Logs/hud-border-play-check.log、hud-border-slices.log；Shots/hud-border-fixed-bars.png、hud-border-fixed-gameplay.png。未打包、提交、推送。
