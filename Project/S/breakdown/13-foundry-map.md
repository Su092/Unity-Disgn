# 任务：失控铸造场地图接入

- 状态：完成。
- 依据：docs/gameplay-spec.md、docs/technical-design.md；环境交付 README 与预览。
- 目标：将交付布局制作成正式地图预制体并替换旧竞技场，接入出生、刷怪、Boss 柱和移动/射击分层。
- 范围：View/ArenaBuilder、FoundryArena、WorldPhysics、Pillar、相关弹道/控制器；Editor/SFoundryMapBuilder 与专项检查；Main 场景及 Addressables 地图分组。

## 验收

使用 Unity Editor API 生成并保存预制体和 Main 场景；核对布局实例、材质、LOD、出生点及刷怪点；使用生产 CharacterController 检查八条高台通路；确认子弹不命中移动坡面、经验落点和 Boss 柱破坏正确；运行正常开局、构建及实机冒烟，截图与交付预览对照。

## 实测结果

地图校验 53/53；运行态联调 19/19；纯规则 300/300。Windows 构建成功（0 errors、9 个 bundle）；启动冒烟 32/32、实机自检 123/123。细节见 CURRENT。截图为 Shots/foundry-map-overview.png、foundry-map-player.png 及本轮实机截图。

## 保留

交付源 .blend、FBX、模块预制体和巡检场景保留，不重新建模。开工时已存在的贴图导入设置、物理图层及 URP 设置改动不回退。旧独立图标缺失是既有素材验收问题，单独记录。
