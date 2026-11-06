# 控制：场景 / 预制体 / 实现路径

## 编辑器

- 只用 **Unity 6000.6.4f1**（`D:\Unity\6000.6.4f1\Editor\Unity.exe`）
- 勿用 2022 LTS / 团结引擎打开本工程

## 文档与代码归属

| 类型 | 位置 |
|------|------|
| 项目文档 / 拆解 / 本控制文件 / 记忆 | `E:\Unity Development\Project\Kingdom Of Cloud\` |
| 运行时脚本、资源、场景、预制体 | `unity/Assets/_Game/`（即 `D:\Kingdom Of Cloud\Assets\_Game\`） |

不在游戏工程根下再建过程文档目录。

## 操作优先级

1. **优先 Unity MCP**（本工程 Coplay HTTP `8765`）：建物体、挂组件、改 Transform、做 Prefab、存场景  
2. **MCP 不可用**：给出逐步手动步骤（菜单、物体名、Inspector 字段、保存路径、验收）  
3. **禁止默认写** `[MenuItem]` / EditorWindow / 一键装配菜单（用户点名才写）

## 禁止

- 手写 YAML 冒充场景/Prefab 搭建  
- 用 Editor 菜单脚本绕过 MCP  
- 只给笼统说明不给步骤  
- 改动其它 `Project/<游戏>/` 内容

## 失败时步骤格式

```text
目标：
前置：Unity 版本 / 打开的场景 / 需要的资源
步骤：
1. 菜单或 Hierarchy 操作
2. Inspector 字段 = 具体值
3. 保存路径（如 Assets/_Game/Res/Prefab/xxx.prefab）
验收：进 Play 后应看到什么
```
