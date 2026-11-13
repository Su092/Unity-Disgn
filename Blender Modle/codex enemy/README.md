# Codex Crawler

基于 `ref_crawler.png` 制作的低多边形四足机械爬行体。

## 文件

- `codex_crawler.blend`：可直接编辑的 Blender 场景
- `export/codex_crawler.glb`：glTF 2.0 导出
- `export/codex_crawler.fbx`：Unity 用 FBX 导出
- `renders/codex_crawler_hero.png`：主视角预览
- `renders/codex_crawler_rear.png`：后侧视角预览
- `manifest.json`：尺寸、对象、材质、门检和哈希
- `scripts/build_crawler.py`：可重跑建模脚本
- `scripts/validate_asset.py`：整体尺寸/材质/落地校验

## 规格

- 单位：米，Z-up（导出时转换为 Unity 轴向）
- 整体包围盒：3.10 × 3.30 × 1.93 m
- 29 个独立分件，8 种纯色材质
- 1468 顶点 / 2820 三角面
- 脚底最低点：Z = 0

尺寸是根据单张透视图估算的 provisional 规格，不是工程毫米图。

## 校验

`mesh` / `normals` / `buried` / `selfint` / `thickness` / `overall_bbox` 均通过，
FBX 与 GLB 重新导入后均为 29 个网格、3.10 × 3.30 × 1.93 m。

尚未制作骨骼、动画、碰撞体、LOD 或 UV 贴图。

## 重跑

```powershell
& 'E:\SteamLibrary\steamapps\common\Blender\blender.exe' -b --factory-startup `
  --python 'E:\Unity Development\Blender Modle\codex enemy\scripts\build_crawler.py'
```
