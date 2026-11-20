# 玩家原地跳跃修复

完成：2026-11-18。

## 原因与修改
原控制器先调用水平 CharacterController.Move，再读取 isGrounded。原地输入为零时，零位移调用丢失上一轮重力碰撞的 Below 标记，导致按空格不能起跳；换弹没有锁定跳跃输入。真人和 AI 分支都有相同问题。

在 `<GAME:S>/Assets/_Game/View/PlayerController.cs` 中统一 MovePlayer：先读取上一帧完整移动的接地结果，再处理冲刺、跳跃、重力，将水平和竖直位移合并为一次 Move；落地清理下落速度，撞顶清理上升速度。保留原跳跃高度、速度和输入规则。

## 验证
新增 Editor 自动检查 SPlayerJumpPlayCheck，通过 Input System 注入真实键盘事件，在 Main 的实际 CharacterController 上测试。
修复前：原地、换弹、AI 原地、二楼原地均起跳 0 米；移动跳跃正常约 1.268 米。初次检查的换弹完成等待时间短于配置时长，已改为按 Stats.Reload 等待，该项不作为修复前故障证据。
修复后：23/23 通过，原地、换弹中、移动中、AI、二楼与落地后再跳均上升约 1.268 米；空中不能二段跳；换弹正常结束；暂停不跳跃，恢复不补发。

日志：`<GAME:S>/Logs/player-jump-before.log`、`<GAME:S>/Logs/player-jump-play-check.log`。
控制器修复前备份：`<GAME:S>/Logs/player-controller-before-jump.cs.txt`。
Unity 编译与 Play 检查完成，退出 Play；未构建 EXE、提交或推送。
