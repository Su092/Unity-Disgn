# 音律模型原生资源入库

按用户要求，将本批敌人、音符枪、衍生物和补件的运行时预制体转换为独立 Unity 资源。原始 FBX 已实存于工程 Assets 内，本轮进一步提取 FBX 中的网格、Avatar 等子资源，运行预制体不再依赖 FBX 文件或模型预制体连接。贴图、材质、动作与控制器保持工程内资源，保留既有预制体 GUID、绑定关系及玩法。FBX 作为后续更新的导入源保留。导入脚本也调用相同转换流程，避免回退为 FBX 子资源引用。

验收：递归检查 29 个预制体依赖无 FBX/Blend/OBJ，验证网格与骨架完整，再执行动画/命中和技能 Play 检查。已完成，下方记录本轮结果。

## 已落地
- 17 个角色/变体/音符枪、10 个既有衍生物、2 个补件，共 29 个独立预制体。
- 新提取 25 个 Mesh 和 29 个 Avatar，位于 `<GAME:S>/Assets/_Game/Res/Characters/Music/Native/<AssetID>/`。已有原生网格、动画、材质和贴图继续复用。
- 保留全部既有预制体 GUID；FBX 仍留在工程中作为导入源，运行预制体的递归依赖中不再包含模型源文件。
- `SMusicNativeAssets.Detach` 已接入角色与补件两套导入器；模型重导入后生成原生资源再保存预制体。`S/Enemies/Convert Music Models To Native Assets` 可转换现有整批资源。
- 改前预制体和导入器备份：`<GAME:S>/Logs/music-native-before-*`。

## 验证
原生资源/递归依赖 145/145、敌人资产 814/814、模型 Play 268/268 已通过；技能 Play 63/63 通过。所有预制体 GUID 前后相同。

本轮无 C#/Shader 编译错误或运行异常；测试退出 Play。未提交、推送或构建 EXE。
