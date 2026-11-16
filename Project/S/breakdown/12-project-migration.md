# 任务：统一 S 工程与枢纽记录

- 状态：工程迁移与规格同步完成，最终 Git 记录和校验见 CURRENT。
- 授权：用户指定以当前操作副本替换正式 S 工程，包含 Git，S 冲突以当前实现为准。
- 依据：PROJECT.md、control/workflow.md、枢纽多工程规则。

## 执行结果

1. 原正式工程整体保留于迁移备份的 project-before，包含其 .git、未提交内容和缓存；枢纽 S 文档备份于 hub-S-before。
2. 当前操作副本整目录迁入 <GAME:S>，其 .git 原样保留；旧工作路径改为到 <GAME:S> 的兼容联接。
3. 枢纽 Project/S/unity 与机器 profile 均指向 <GAME:S>，不复制工程到枢纽 Git。
4. 迁移瞬间核对 769 个 Git 已跟踪/未忽略文件 SHA-256 全部一致，porcelain -z 状态逐字节一致，历史 HEAD 为 3cc9c276bd8715fa9492938ae588354f0e2d306a。
5. 本轮七类功能并入既有规格；工程 docs/accessory-fusion.md 的规则并入 loadout-spec.md。旧一次性补丁脚本移出活动工程并保存在迁移备份中。
6. 所有冲突采用当前实现，包括经验 1.5 米拾取、不吸附、不到期；不合并原正式工程另一套经验字段与实现。

## 验收与恢复依据

Logs/migration-audit.json 保存真实目录和备份位置；备份还含源/目标/枢纽 diff、暂存差异与源文件哈希。
恢复时须关闭工程，按备份目录恢复原正式工程及需要恢复的枢纽 S 文档；不要把兼容联接当独立副本删除内容。
当前机器 doctor 为 degraded：仅可选 hub.link 为空，已补查真实枢纽路径、profile 和 S 联接。其他游戏与全局配置不在本次改动范围。
迁移后规则 300/300；素材分类审计缺十二个新增配件独立图标，不能声称完整 tests/all 通过。
