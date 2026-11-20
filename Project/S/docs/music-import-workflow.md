# 音律敌人规范入库

## 执行口径

完整交付包保留在 <GAME:S>/_Inbox。Unity 只接收明确文件清单，不递归复制交付目录。当前清单为 154 个模型/动作 FBX、45 张实际使用的贴图，共 199 个输入；源交付的 blend、预览、视频、报告、未使用贴图和旧碰撞代理不进入 Assets。当前包额外 241 个文件被跳过。

## 分类路径

以下均相对 <GAME:S>：

| 类型 | 路径 | 当前数量 |
|---|---|---|
| 入库清单/源 FBX | Assets/_Game/Editor/MusicImport/ | 154 个源 FBX；仅编辑器使用 |
| 独立网格 | Assets/_Game/Res/Model/Enemies/Music/ | 76 个 Mesh |
| 动画和骨架 | Assets/_Game/Res/Animation/Enemies/Music/ | 125 个动作、29 个 Avatar、18 个 Controller |
| 材质 | Assets/_Game/Res/Material/Enemies/Music/ | 25 个 |
| 贴图 | Assets/_Game/Res/Texture/Enemies/Music/ | 45 张 PNG、1 个灯口发光纹理资产 |
| 运行预制体 | Assets/_Game/Res/Prefab/Enemies/ | 29 个音律角色和衍生物，位置/GUID 保留 |

原 Characters/Music 混放目录已清空移除。473 个资源以 AssetDatabase.MoveAsset 分类迁移，GUID 与编辑前备份独立比对 473/473 一致。73 个无引用旧文件及其 meta 保留在 _Inbox/chr/S_Music_Enemies/LegacyUnityArchive；包含 27 个描述/报告 JSON、18 个旧受击代理 Mesh、15 张未使用贴图和 13 个旧碰撞 FBX。未修改原始建模交付。

## 后续操作

在 Unity 菜单选择 **S / Enemies / Import Music Delivery (Manifest)**，选择完整交付根目录：根下为各敌人文件夹和 SkillSupplements。输入按 delivery-files.json 精确读取；新增敌人、变体、动作或贴图需先审核并更新清单和 import-plan.json，不能靠复制新目录自动入库。

流程：全部输入预检 → 仅复制内容变化的清单文件 → 按配置生成原生网格/动画/材质/预制体 → 校验外观受击箱、路径依赖和 GUID。预检包括必需文件、重复目标、越界/链接路径、文件类型、编号、米单位与锁定身高；预检失败不写 Assets。

已有输入文件更新前备份至 _Inbox/chr/S_Music_Enemies/ImportBackups；保留原 meta，不覆盖 GUID。几何与动画规格在 Unity 重建后继续校验，异常明确报错并保留日志，不能将不完整重建标为成功。记录在 Logs/music-delivery-receipt.json（逐文件 SHA-256/GUID/复制数量/状态）。

菜单 **Rebuild Music Enemy Prefabs** 仅使用已登记并暂存的输入重建角色；技能补件仍由 Import Music Skill Supplements 重建。二者写入同一分类路径，不会恢复旧混放结构。tools/prepare_music_import_layout.py 是本次一次性迁移配方生成器，不是后续交付导入入口。

## 验证

- 预检 9/9：有效交付、缺件、越界源路径、未登记 blend、重复目标、越界目标、漏清单项、编号错误、身高改变。
- 新入口全量重导完成：17 个角色/变体/音符枪 + 12 个技能衍生物。输入内容相同，复制数为 0；已有运行资源 GUID 全部保留。
- 原生依赖 145/145、角色资产 814/814、补件 19/19；29 个预制体不依赖项目 Editor 源文件。
- 独立动画几何验证 765/765，4641 个姿态/LOD 样本，最大顶点误差 0.0000013m；外观受击箱 1020/1020 姿态 >=80%，最低 95.414%。
- Unity 模型 Play 494/494，含真实子弹、外围命中、防重复伤害、死亡、转向和重开。技能 Play 63/63，通过三类精英、双 Boss、召唤物、音符枪、追光与重开清理；编辑器已退出测试 Play。

本次编辑前备份：<GAME:S>/Logs/music-import-before-20261119_145848。
证据：Logs/music-delivery-migrate.log、music-delivery-migration-guids.log、music-delivery-preflight.log、music-delivery-layout.log、music-delivery-receipt.json、music-geometry-validation.log、music-enemy-play.log、music-combat-play.log。未构建 EXE、提交或推送。
