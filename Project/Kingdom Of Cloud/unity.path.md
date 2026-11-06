# Unity 工程联接说明

本仓库不包含 Unity 工程本体（避免 `Library` 与嵌套 Git）。

本地开发时在本目录创建目录联接：

```bat
mklink /J "E:\Unity Development\Project\Kingdom Of Cloud\unity" "D:\Kingdom Of Cloud"
```

- 工程路径：`D:\Kingdom Of Cloud`
- 工程远端：`git@github.com:Su092/Kingdom-Of-Cloud.git`
- 绑定说明：见同级 `PROJECT.md`
