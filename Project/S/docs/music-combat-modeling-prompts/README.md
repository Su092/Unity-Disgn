# 音律能力补充 3D 任务书

本轮现有 FXM_S08_BassWave、FXM_S14_FallingNote、FXM_S14_MarchingNote、FXM_S16_PluckedNote、FXM_S21_VentGust、FXM_S29_NoteShot 及音符枪已复用，无需重复建模。

新增资产任务：
- [舞台追光灯实体](SM_MusicFollowSpot.md)：当前用运行时光束和光斑表达，补灯具外壳。
- [四栏推进音符幕](FXM_S14_NoteGate.md)：当前使用交付音符加高度轮廓，补完整不可跳越的危险幕。

采用建模仓库 `.cursor/skills/blender-director/SKILL.md` 与 `references/asset-pipeline.md` 的分析→规格→轮廓→材质→LOD→导出→验证流程，导出遵循 export-pipeline 与项目既有 Generic FBX 约定。这两份是制作提示词，本轮未实际建模，也未替换用户已交付角色。

交付根：原 S_Music_Enemies 导出包新增 `SkillSupplements/<AssetID>/`；后续归档到 `<GAME:S>/_Inbox/chr/S_Music_Enemies/SkillSupplements`。渲染图、源 blend、模型与 manifest 分目录存放。
