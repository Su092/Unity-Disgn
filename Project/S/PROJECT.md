# S — 配件构筑型 FPS Roguelite

枪是容器，配件构成射击方式。当前工程已统一到机器配置的 <GAME:S>，枢纽 unity 联接指向该工程；原工作路径只作为兼容联接，不再保留第二套开发副本。

| 项 | 当前值 |
|---|---|
| 枢纽 | <HUB>/Project/S |
| 工程 | <GAME:S>；远端 git@github.com:Su092/Project-S.git，分支 main |
| 环境 | Unity 6000.6.4f1 / URP 17.6.0 / Input System 1.20.0 / Addressables 2.11.2 |
| 入口 | Assets/Scenes/Main.unity → Bootstrap → SRes 预加载 → GameRoot |
| 代码 | Assets/_Game/App、Core、View、Editor |
| 数据 | Assets/_Game/Res/Cfg/*.tsv，11 张三行表头 |
| 交付资源 | Assets/_Game/Res/Model、Texture、UIPrefabs、Font、Shaders、Prefab |
| 内容 | 6 枪 / 17 子弹 + 34 衍生配件 / 10 物理作用域 / Lv.1～5 合成 |
| 局内 | 全武器选 1 开局，升级每轮 10% 概率出枪，击杀掉落经验需走近领取 |
| 验证 | 规则 300/300；统一 tests 的独立图标审计未通过，详见 memory/CURRENT.md |

## 目录与开发流程

docs 保存唯一规格，breakdown 保存任务，control 保存操作约定，memory 保存当前证据。先规格、再拆解、再改工程，结束后更新 CURRENT。
工程 README 只保留运行、验证、目录说明；过程文档不放在工程 docs。截图在工程 Shots，原料在 _Inbox，枢纽只放 Markdown。
Core 除 SDataLoader 桥外零 Unity 依赖。UI 结构由预制体与 *Refs 管理；场景/预制体用 Editor 工具或 MCP，不以手改 YAML 搭建。

## 运行与验证

用指定 Unity 打开 <GAME:S> 的 Main 场景后 Play，菜单选择初始武器再开始。
验证入口是 unity/scripts/check.ps1；tests 无需编辑器，Unity 独占任务前按枢纽规则确认工程锁。完整 all 包含会重建场景/资产/构建的步骤，应按任务需要执行。
tools/loadout-tests/loadout-tests.csproj 已纳入工程 Git，克隆后可直接 dotnet run。
当前 Packages/manifest.json 未安装 Unity MCP；有需要时按枢纽统一配置安装，不将缺少 MCP 误认为工程无法运行。
Git 与文档同步记录见 breakdown/12-project-migration.md 和 memory/CURRENT.md。
