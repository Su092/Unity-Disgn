# 任务 04：表现层（材质池 / 音效 / 后处理）

- 状态：**完成**（2026-11-12）
- 依据：`docs/art-style.md` §1 §5、`docs/audio-spec.md`

## 三件事

| 项 | 内容 | 解决什么 |
|----|------|----------|
| **材质池** | `SMat` 按 (shader, 颜色, smoothness) 缓存共享材质 | 消除瞬态对象（弹丸/火花/爆炸球）的材质实例泄漏 |
| **程序化音效** | `SfxBank` 合成 14 个 clip + 16 音源池 + 类别限流 | 从「全静音」到有完整听觉反馈 |
| **后处理** | `SPostFx` 代码建 Volume：Bloom + Vignette + 冷阴影暖高光 | 画面从平灰变有层次 |

## 材质池

### 问题

`SMat.Lit` 每次调用都 `new Material`，而弹丸、命中火花、爆炸球每帧都在生成。
连发 9 发/秒 × 3 发分裂 = 每秒几十个新材质实例，且永不释放。

### 方案

- 共享缓存：`Lit(color, smoothness)` / `Unlit(color)` 按 key 复用
- 独立实例：`NewLitInstance()` 给需要各自贴图/平铺的场合（地面、墙板）
- **所有改色必须走 `MaterialPropertyBlock`**：材质共享后，直接写 `sharedMaterial.SetColor` 会污染所有使用者

### 实测

| 时刻 | 缓存材质数 |
|------|-----------|
| 战斗前（基线） | 5 |
| 战斗后（3.5 秒连射 + 分裂 + 爆炸） | **5** |

断言：`材质池未泄漏`，判据 `after <= 基线 + 4`。

### 顺带修的三处污染

| 文件 | 问题 | 修法 |
|------|------|------|
| `Pillar.cs` | 血量变色直接写 `sharedMaterial` | 改 `MaterialPropertyBlock` |
| `ZoneGate.cs` | 开门动画直接写 `sharedMaterial` | 同上 |
| `SAssets.Textured` | 复用 `SMat.Lit` 的共享实例再改贴图，会互相覆盖 | 改走 `NewLitInstance()` |

## 程序化音效

### 为什么合成

初版零音频素材。用代码合成先验证**节奏与限流**，之后换真素材只需替换 clip 表。

### 14 个 clip

| 分组 | clip |
|------|------|
| 枪械三轨 | `shoot_body`（机械）/ `shoot_shot`（弹药）/ `shoot_tail`（收尾） |
| 命中 | `hit_soft`（打敌人）/ `hit_wall`（打墙） |
| 爆炸 | `explode` |
| 玩家 | `hurt` / `pickup` / `levelup` |
| UI | `ui_click` / `ui_hover` |
| 威胁 | `enemy_near` / `boss_phase` / `shield` |

### 三层限流（audio-spec §4）

1. **类别最小间隔**：`shoot` 45ms、`hurt` 120ms、`enemy` 1.1s…
2. **音源池 ≤16**：全忙时复用最旧
3. **音高随机 ±8%**：避免连发机械重复

### 三轨如何随配件变化（audio-spec §3）

| 触发条件 | 音效变化 |
|----------|----------|
| 弹速 ×1.3 以上 | `shot` 音高 +2 半音 |
| 存在时间 >1.0s | `tail` 音量提升（0.12→0.30） |
| 分裂（>1 发） | 追加一层 1.18 倍音高的弱化副本 |
| 有溅射 | 命中时叠加低频爆音 |

## 后处理

`SPostFx.Apply(cam)` 代码创建全局 Volume（不依赖 .asset 引用，避免断链）：

| 效果 | 参数 | 作用 |
|------|------|------|
| Bloom | 强度 0.55 / 阈值 0.92 | 发光条与弹丸出光晕 |
| Vignette | 强度 0.24 | 聚焦中心 |
| ColorAdjustments | 对比 +12 / 饱和 +8 | 画面不发灰 |
| SplitToning | 冷阴影 `#293D6B` / 暖高光 `#85704C` | 工业科幻色调 |

**不做景深与运动模糊**：FPS 里会晕（art-style §1 明令）。

## 验收

| 项 | 结果 |
|----|------|
| 实机自检 | **73/73 passed**（新增 8 条：音效库/合成数/池上限/Volume 全局/Profile/材质池不泄漏/音源占用） |
| 材质池 | 基线 5 → 战斗后 **5**（零增长） |
| 全量 `check.ps1` | `RESULT ALL PASS` |

## 明确未做

- 音效是合成音，非真实录音素材（节奏与限流已可验证，音色待替换）
- 无音乐层（探索/战斗/高压分层未做）
- 无音量设置界面、无混音分组（Master/SFX/Music/UI 未分离）
- `enemy_near` 已合成但未接入（需要「敌人接近」检测逻辑）
- 无 `keycap` 键位提示接入
