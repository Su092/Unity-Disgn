# Unity 工程联接说明

本仓库不包含 Unity 工程本体（避免 `Library` 与嵌套 Git）。

本地首次拉取后，在本目录创建目录联接：

```bat
mklink /J "E:\Unity Development\Project\Star Defanse\unity" "E:\Star Defanse"
```

- 工程路径：`E:\Star Defanse`（与枢纽同盘，可直接 Junction）
- 工程远端：`git@github.com:Su092/Star-Defanse.git`
- 工程编辑器版本：`unity/ProjectSettings/ProjectVersion.txt` = `6000.6.4f1`
- 联接已被工作区 `.gitignore` 的 `Project/*/unity/` 规则忽略
- 绑定、验证命令与禁忌：见同级 `PROJECT.md`

删除联接（不会删工程本体）：

```bat
rmdir "E:\Unity Development\Project\Star Defanse\unity"
```
