# 任务：配件范围预览、扩件与合成

- 状态：规则与交互完成；独立图标与完整构建验收待完成。
- 依据：docs/loadout-spec.md、docs/data-schema.md、docs/gameplay-spec.md。
- 范围：Core/Loadout、ItemFusion、LoadoutTypes、RunState；View/InventoryView、DraggableItem、ItemTooltip；Cfg/Modifier、GunModifier；Editor/SFusionPlayCheck；tools/loadout-tests。

## 已完成

物理前后格与十种作用域；点击/悬停/拖动范围高亮；十二种衍生配件与旧件范围调整；同种同级四方向拖放合成至 Lv.5；实例独立等级、原子所有权校验、预览同源、史诗跨轮重复抽取。
原有装卸/交换保留；非法合成不消费、不误卸下；满背包合成不需额外空位。

## 验收证据

纯规则断言 300/300；迁移前 SFusionPlayCheck 41/41，截图 Shots/fusion-inventory.png。
统一 tests 的 UI 分类检查未通过：十二个新增 item_<id> 独立图标缺失，当前复用已有图标，需按美术管线补齐 PNG/.meta、登记并接入 Addressables 后重跑。
方案存档、合成后平衡、完整 build/smoke/shots 与长局性能不标记完成。
