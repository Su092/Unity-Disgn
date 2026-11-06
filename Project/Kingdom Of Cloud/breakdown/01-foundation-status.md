# 任务：底座盘点与后续入口

- 状态：进行中（程序底座已存在；玩法内容未按概念拆解落地）
- 依据：`docs/concept.md`、`docs/00-overview.md`
- 目标：明确已有运行时能力，后续玩法切片从此承接，不重复造底座

## 已有（实现侧）

路径均相对 `unity/`：

| 路径 | 职责 |
|------|------|
| `Assets/_Game/Scripts/Core/Singleton.cs` | 场景内单例基类 |
| `Assets/_Game/Scripts/Core/GameManager.cs` | 运行状态、暂停、时间缩放 |
| `Assets/_Game/Scripts/Player/PlayerController.cs` | CharacterController 第三人称移动 |
| `Assets/_Game/Scripts/Camera/CameraFollow.cs` | 第三人称跟随与环绕 |
| `Assets/_Game/Editor/McpLocalHttpBootstrap.cs` | MCP HTTP 8765 连桥 |
| URP 17.6.0 | Pipeline / Renderer / Global Volume 底座 |

## 场景挂接验收

1. `GameSystems` + `GameManager`  
2. 玩家：`CharacterController` + `PlayerController`，Tag `Player`  
3. 主相机：`CameraFollow`，Target → 玩家  

默认输入：WASD 移动、鼠标视角、Space 跳、Left Shift 冲刺、Esc 暂停。

## 下一步（待新拆解文件）

- 知识锁 / 压力分层 / 锁合粒子：先写 `docs/` 系统设计，再新建 `breakdown/02-*.md`  
- 渲染下一阶段（压力雾、体积云、锁合材质）：单独拆解，勿塞进本文件末尾追加

## 验收

- 打开工程可用现有底座进 Play  
- 新玩法只通过新的 `breakdown/NN-*.md` 启动，不在本文件底部堆需求
