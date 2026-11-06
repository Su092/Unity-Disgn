# URP 基础底座已落地

更新：2026-09-30  
Unity：2022.3.62f3c1  
包：`com.unity.render-pipelines.universal@14.0.12`

## 已完成

- 工程从 Built-in 切到 **URP**
- Color Space：**Linear**（原本已是）
- Graphics + 各 Quality Level 均指向同一 Pipeline Asset
- `lightsUseLinearIntensity` / `lightsUseColorTemperature`：开
- 附带修好 `Assets/_Game/Scripts/**/*.meta` 无效 GUID（此前脚本被 Unity 忽略）

## 关键资产

| 路径 | 用途 |
|------|------|
| `Assets/_Game/Settings/URP/KingdomOfCloud_URP.asset` | URP Pipeline Asset |
| `Assets/_Game/Settings/URP/KingdomOfCloud_Renderer.asset` | Universal Renderer |
| `Assets/_Game/Settings/URP/KingdomOfCloud_GlobalVolumeProfile.asset` | 全局后处理 Profile |
| `Assets/_Game/Scenes/Bootstrap.unity` | 底座场景（Build Index 0） |
| `Assets/_Game/Prefabs/Rendering/GlobalVolume.prefab` | 可复用全局 Volume |
| `Assets/_Game/Materials/M_DefaultLit.mat` | URP Lit 默认材质 |

## Pipeline 默认参数（底座）

- HDR：开；Color Grading：**HighDynamicRange**
- MSAA：关（相机用 SMAA）
- 主光 Per-Pixel；附加光 Per-Pixel，上限 8
- 阴影距离 150；4 cascade；软阴影开
- Render Scale：1

## Bootstrap 场景内容

- Main Camera：HDR、Post-processing 开、SMAA High、Depth Texture On
- Directional Light：暖白、软阴影；设为 `RenderSettings.sun`
- Global Volume：ACES Tonemap / Bloom / ColorAdjustments / WhiteBalance / Vignette
- 环境：Trilight 冷蓝环境光 + ExponentialSquared 雾（浅蓝）

## 未做（下一阶段）

- 压力区驱动雾/Volume 切换
- 体积云 / Renderer Feature
- 锁合粒子与凝固云材质
- 完整天空大气

## 验证

- `manage_graphics pipeline_get_info` → Universal (URP)
- Console：无 Error/Warning（修 meta 后）
